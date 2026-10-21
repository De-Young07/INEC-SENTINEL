-- Install once as database administrator. Private schema, no public API access.
CREATE SCHEMA IF NOT EXISTS sentinel;
REVOKE ALL ON SCHEMA sentinel FROM PUBLIC, anon, authenticated;
CREATE TABLE sentinel.observations (
 event_id TEXT PRIMARY KEY, site_id TEXT NOT NULL,
 mode TEXT NOT NULL CHECK (mode IN ('demo','field')),
 observed_at TEXT NOT NULL, received_at TEXT NOT NULL,
 success INTEGER NOT NULL CHECK (success IN (0,1)),
 seconds DOUBLE PRECISION NOT NULL CHECK (seconds > 0 AND seconds <= 3600),
 carrier TEXT NOT NULL, note TEXT NOT NULL);
CREATE INDEX obs_site ON sentinel.observations(site_id,mode,observed_at);
CREATE TABLE sentinel.incidents (
 id BIGSERIAL PRIMARY KEY, site_id TEXT NOT NULL,
 mode TEXT NOT NULL CHECK (mode IN ('demo','field')),
 status TEXT NOT NULL CHECK (status IN ('open','acknowledged','resolved')),
 opened_at TEXT NOT NULL, recovered_at TEXT, acknowledged_by TEXT, action_note TEXT);
CREATE UNIQUE INDEX one_open ON sentinel.incidents(site_id,mode) WHERE status!='resolved';
CREATE TABLE sentinel.audit (
 id BIGSERIAL PRIMARY KEY, incident_id BIGINT REFERENCES sentinel.incidents(id),
 at TEXT, action TEXT, actor TEXT, note TEXT);
CREATE TABLE sentinel.outbox (
 id BIGSERIAL PRIMARY KEY, incident_id BIGINT REFERENCES sentinel.incidents(id),
 mode TEXT, channel TEXT, body TEXT, status TEXT DEFAULT 'pending', created_at TEXT,
 provider_id TEXT, UNIQUE(incident_id,channel,body));
ALTER TABLE sentinel.observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentinel.incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentinel.audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentinel.outbox ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA sentinel FROM PUBLIC, anon, authenticated;
-- Provision the sentinel_runtime login separately; never commit its password.
