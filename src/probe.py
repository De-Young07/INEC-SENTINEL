"""Opt-in synthetic upload probe. Local queue survives network interruption.

Run on an authorized site device; this tests SENTINEL's endpoint, not INEC.
"""
import argparse
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.parse
import uuid
from .monitoring import now


def run_once(url, site, carrier, queue_path):
    token = os.environ.get('SENTINEL_INGEST_TOKEN')
    if not token:
        raise ValueError('Set SENTINEL_INGEST_TOKEN on the probe device')
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')):
        raise ValueError('Use HTTPS except for localhost testing')
    headers = {'X-Sentinel-Token': token}
    # Refuse redirects: never forward the credential to another endpoint.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    pending = json.loads(queue_path.read_text()) if queue_path.exists() else []
    success = None
    if len(pending) < 10000:
        start, stamp = time.monotonic(), now()
        try:
            req = urllib.request.Request(url.rstrip('/')+'/api/probe-upload', data=b'0'*65536, headers=headers)
            with opener.open(req, timeout=60) as response:
                success = json.load(response).get('received_bytes') == 65536
        except Exception:
            success = False
        pending.append({'event_id': str(uuid.uuid4()), 'site_id': site, 'mode': 'field', 'observed_at': stamp, 'success': success, 'seconds': max(.001, min(3600, time.monotonic()-start)), 'carrier': carrier, 'note': 'Synthetic 64 KiB upload to SENTINEL; endpoint/device/auth failures can also cause failure'})
    def persist():
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = queue_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(pending), encoding='utf-8')
        temporary.replace(queue_path)
    persist()
    while pending:
        req = urllib.request.Request(url.rstrip('/')+'/api/observations', data=json.dumps(pending[0]).encode(), headers={**headers, 'Content-Type': 'application/json'})
        try:
            with opener.open(req, timeout=20) as response:
                response.read()
        except Exception:
            break
        pending.pop(0)
        persist()
    return {'upload_completed': success, 'queued_reports': len(pending)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8600')
    parser.add_argument('--site', required=True)
    parser.add_argument('--carrier', default='Unspecified')
    parser.add_argument('--queue', type=Path, default=Path('data/probe_queue.json'))
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    while True:
        print(json.dumps(run_once(args.url, args.site, args.carrier, args.queue)), flush=True)
        if not args.watch:
            break
        time.sleep(300)
