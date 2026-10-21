"""Persistent pilot monitoring. Demo and field evidence never share incident state."""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    path = Path(os.environ.get('SENTINEL_DB', str(ROOT / 'data/monitoring.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS observations (
      event_id TEXT PRIMARY KEY, site_id TEXT NOT NULL, mode TEXT NOT NULL,
      observed_at TEXT NOT NULL, received_at TEXT NOT NULL, success INTEGER NOT NULL,
      seconds REAL NOT NULL, carrier TEXT NOT NULL, note TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS obs_site ON observations(site_id,mode,observed_at);
    CREATE TABLE IF NOT EXISTS incidents (
      id INTEGER PRIMARY KEY, site_id TEXT NOT NULL, mode TEXT NOT NULL,
      status TEXT NOT NULL, opened_at TEXT NOT NULL, recovered_at TEXT,
      acknowledged_by TEXT, action_note TEXT);
    CREATE UNIQUE INDEX IF NOT EXISTS one_open ON incidents(site_id,mode) WHERE status!='resolved';
    CREATE TABLE IF NOT EXISTS audit (
      id INTEGER PRIMARY KEY, incident_id INTEGER, at TEXT, action TEXT, actor TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS outbox (
      id INTEGER PRIMARY KEY, incident_id INTEGER, mode TEXT, channel TEXT,
      body TEXT, status TEXT DEFAULT 'pending', created_at TEXT, provider_id TEXT,
      UNIQUE(incident_id,channel,body));
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def queue(db, incident, message):
    body = f"SENTINEL [{incident['mode'].upper()}] Incident {incident['id']} | {incident['site_id']} | {message}"
    for channel in ('email', 'sms'):
        db.execute('INSERT OR IGNORE INTO outbox(incident_id,mode,channel,body,created_at) VALUES(?,?,?,?,?)',
                   (incident['id'], incident['mode'], channel, body, now()))


def record(data):
    received = now()
    observed = datetime.fromisoformat(data['observed_at'].replace('Z', '+00:00'))
    if observed.tzinfo is None:
        raise ValueError('Observation time must include a timezone')
    observed = observed.astimezone(timezone.utc)
    age = (datetime.fromisoformat(received) - observed).total_seconds()
    if age < -60:
        raise ValueError('Observation time is in the future')
    stamp = observed.isoformat()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM observations WHERE event_id=?', (data['event_id'],)).fetchone()
        if previous:
            fields = ['site_id', 'mode', 'success', 'seconds', 'carrier', 'note']
            if previous['observed_at'] != stamp or any(previous[k] != data[k] for k in fields):
                raise ValueError('Event identifier already used for different evidence')
            return {'duplicate': True}
        latest = db.execute('SELECT MAX(observed_at) FROM observations WHERE site_id=? AND mode=?', (data['site_id'], data['mode'])).fetchone()[0]
        db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?)', (data['event_id'], data['site_id'], data['mode'], stamp, received, data['success'], data['seconds'], data['carrier'], data['note']))
        # Late history is retained, but must not raise/resolve a current incident.
        if age > 900 or (latest and stamp <= latest):
            return {'duplicate': False, 'history_only': True}
        incident = db.execute("SELECT * FROM incidents WHERE site_id=? AND mode=? AND status!='resolved'", (data['site_id'], data['mode'])).fetchone()
        recent = db.execute('SELECT * FROM observations WHERE site_id=? AND mode=? ORDER BY observed_at DESC LIMIT 3', (data['site_id'], data['mode'])).fetchall()
        # Rule is illustrative: three failed uploads in 15 minutes. Slow success is not failure.
        failed = len(recent) == 3 and all(not r['success'] for r in recent) and (observed-datetime.fromisoformat(recent[-1]['observed_at'])).total_seconds() <= 900
        if failed and not incident:
            cursor = db.execute("INSERT INTO incidents(site_id,mode,status,opened_at) VALUES(?,?,'open',?)", (data['site_id'], data['mode'], received))
            incident = db.execute('SELECT * FROM incidents WHERE id=?', (cursor.lastrowid,)).fetchone()
            queue(db, incident, 'Three recent upload failures. Cause unconfirmed. Investigate site connectivity.')
            db.execute('INSERT INTO audit(incident_id,at,action,actor,note) VALUES(?,?,?,?,?)', (incident['id'], received, 'opened', 'rule-engine', 'Three failures within 15 minutes'))
        if incident and len(recent) >= 2 and all(r['success'] for r in recent[:2]) and (observed-datetime.fromisoformat(recent[1]['observed_at'])).total_seconds() <= 900:
            db.execute("UPDATE incidents SET status='resolved',recovered_at=? WHERE id=?", (received, incident['id']))
            queue(db, incident, 'Two consecutive successful uploads. Recovery observed; continue monitoring.')
            db.execute('INSERT INTO audit(incident_id,at,action,actor,note) VALUES(?,?,?,?,?)', (incident['id'], received, 'resolved', 'rule-engine', 'Two successful observations'))
        return {'duplicate': False, 'history_only': False}


def acknowledge(incident_id, actor, note):
    if len(actor.strip()) < 2 or len(note.strip()) < 3:
        raise ValueError('Enter an officer name and an action note')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM incidents WHERE id=?', (incident_id,)).fetchone()
        if not row:
            raise ValueError('Unknown incident')
        if row['status'] == 'resolved':
            raise ValueError('Recovered incident cannot be acknowledged')
        db.execute("UPDATE incidents SET status='acknowledged',acknowledged_by=?,action_note=? WHERE id=?", (actor, note, incident_id))
        db.execute('INSERT INTO audit(incident_id,at,action,actor,note) VALUES(?,?,?,?,?)', (incident_id, now(), 'acknowledged', actor, note))


def escalate():
    """One escalation per unacknowledged field incident after 15 minutes."""
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for row in db.execute("SELECT * FROM incidents WHERE mode='field' AND status='open'").fetchall():
            if (datetime.now(timezone.utc)-datetime.fromisoformat(row['opened_at'])).total_seconds() >= 900:
                if not db.execute("SELECT 1 FROM audit WHERE incident_id=? AND action='escalated'", (row['id'],)).fetchone():
                    queue(db, row, 'ESCALATION: no officer acknowledgment after 15 minutes. Assign an owner.')
                    db.execute('INSERT INTO audit(incident_id,at,action,actor,note) VALUES(?,?,?,?,?)', (row['id'], now(), 'escalated', 'rule-engine', 'Same configured recipients; regional routing requires configuration design'))


def snapshot(site_id=None):
    with connect() as db:
        observations = db.execute('SELECT * FROM observations ' + ('WHERE site_id=? ' if site_id else '') + 'ORDER BY observed_at DESC LIMIT 100', (site_id,) if site_id else ()).fetchall()
        incidents = db.execute('SELECT * FROM incidents ' + ('WHERE site_id=? ' if site_id else '') + 'ORDER BY id DESC LIMIT 100', (site_id,) if site_id else ()).fetchall()
        outbox = db.execute('SELECT * FROM outbox ORDER BY id DESC LIMIT 100').fetchall()
        audit = db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100').fetchall()
    return {'observations': [dict(r) for r in observations], 'incidents': [dict(r) for r in incidents], 'outbox': [dict(r) for r in outbox], 'audit': [dict(r) for r in audit], 'updated_at': now(), 'delivery': 'Configured for external delivery' if os.environ.get('SENTINEL_SEND') == '1' else 'Preview only — no messages sent'}
