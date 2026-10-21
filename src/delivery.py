"""Explicit delivery worker: python -m src.delivery [--watch]. Never sends demos.

Provider acceptance is not delivery or human acknowledgment. Ambiguous failures
are retained for operator review rather than automatically risking duplicate SMS.
"""
import argparse
import base64
import json
import os
import smtplib
import ssl
import time
import urllib.request
import urllib.parse
from email.message import EmailMessage
from .monitoring import connect, escalate


def send_email(body):
    message = EmailMessage()
    message['From'] = os.environ['SMTP_FROM']
    message['To'] = os.environ['SENTINEL_EMAIL_TO']
    message['Subject'] = 'SENTINEL connectivity incident'
    message.set_content(body)
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', '587')), timeout=20) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        refused = server.send_message(message)
        if refused:
            raise RuntimeError('Recipient refused')
    return 'SMTP accepted'


def send_sms(body):
    sid = os.environ['TWILIO_ACCOUNT_SID']
    if not sid.startswith('AC') or not sid.isalnum():
        raise ValueError('Invalid provider account identifier')
    auth = base64.b64encode(f"{sid}:{os.environ['TWILIO_AUTH_TOKEN']}".encode()).decode()
    payload = urllib.parse.urlencode({'From': os.environ['TWILIO_FROM'], 'To': os.environ['SENTINEL_SMS_TO'], 'Body': body}).encode()
    request = urllib.request.Request(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json', data=payload, headers={'Authorization': 'Basic '+auth})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)['sid']


def dispatch():
    escalate()
    if os.environ.get('SENTINEL_SEND') != '1':
        return {'status': 'preview_only', 'processed': 0}
    processed = 0
    for channel, required, sender in [
        ('email', ['SMTP_HOST','SMTP_FROM','SMTP_USER','SMTP_PASSWORD','SENTINEL_EMAIL_TO'], send_email),
        ('sms', ['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_FROM','SENTINEL_SMS_TO'], send_sms),
    ]:
        if not all(os.environ.get(k) for k in required):
            continue
        for _ in range(25):
            with connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute("SELECT * FROM outbox WHERE mode='field' AND status='pending' AND channel=? ORDER BY id LIMIT 1", (channel,)).fetchone()
                if not row:
                    break
                db.execute("UPDATE outbox SET status='sending' WHERE id=?", (row['id'],))
            try:
                provider_id = sender(row['body'])
                status = 'provider_accepted'
            except Exception:
                # Never log secrets, recipient details, or provider response bodies.
                status, provider_id = 'review_required', 'Check provider console before any retry'
            with connect() as db:
                db.execute('UPDATE outbox SET status=?,provider_id=? WHERE id=?', (status, provider_id, row['id']))
            processed += 1
    return {'status': 'worker_complete', 'processed': processed}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    while True:
        print(json.dumps(dispatch()), flush=True)
        if not args.watch:
            break
        time.sleep(15)
