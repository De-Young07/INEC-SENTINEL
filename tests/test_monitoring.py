import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from src import monitoring, delivery


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'SENTINEL_DB': str(Path(self.temp.name)/'test.sqlite3'), 'SENTINEL_SEND': '0'})
        self.env.start()
        self.base = datetime.now(timezone.utc)-timedelta(seconds=10)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def report(self, n, success=False, mode='demo', age=0):
        return {'event_id': f'{mode}-{n}', 'site_id': 'site-1', 'mode': mode, 'observed_at': (self.base+timedelta(seconds=n)-timedelta(hours=age)).isoformat(), 'success': success, 'seconds': 10, 'carrier': 'test', 'note': ''}

    def test_lifecycle_and_deduplication(self):
        for i in range(3):
            monitoring.record(self.report(i))
        self.assertEqual(len(monitoring.snapshot()['incidents']), 1)
        self.assertTrue(monitoring.record(self.report(2))['duplicate'])
        monitoring.acknowledge(1, 'Operator', 'Investigating power')
        self.assertEqual(monitoring.snapshot()['incidents'][0]['status'], 'acknowledged')
        monitoring.record(self.report(3, True))
        self.assertNotEqual(monitoring.snapshot()['incidents'][0]['status'], 'resolved')
        monitoring.record(self.report(4, True))
        self.assertEqual(monitoring.snapshot()['incidents'][0]['status'], 'resolved')
        self.assertEqual(len(monitoring.snapshot()['outbox']), 4)

    def test_modes_late_reports_and_conflicting_id(self):
        for i in range(2):
            monitoring.record(self.report(i))
        monitoring.record(self.report(2, mode='field'))
        self.assertEqual(monitoring.snapshot()['incidents'], [])
        self.assertTrue(monitoring.record(self.report(3, age=2))['history_only'])
        with self.assertRaises(ValueError):
            monitoring.record(self.report(0, True))

    def test_stale_success_does_not_resolve(self):
        for i in range(3):
            monitoring.record(self.report(i))
        monitoring.record(self.report(3, True, age=2))
        self.assertEqual(monitoring.snapshot()['incidents'][0]['status'], 'open')

    def test_escalation_is_once_and_only_field(self):
        for mode in ('field','demo'):
            for i in range(3):
                monitoring.record(self.report(i, mode=mode))
        with monitoring.connect() as db:
            db.execute('UPDATE incidents SET opened_at=?', ((self.base-timedelta(hours=1)).isoformat(),))
        monitoring.escalate(); monitoring.escalate()
        events=[a for a in monitoring.snapshot()['audit'] if a['action']=='escalated']
        self.assertEqual(len(events),1)

    def test_delivery_off_and_demo_never_sent(self):
        for i in range(3):
            monitoring.record(self.report(i))
        with patch('src.delivery.send_email') as send:
            self.assertEqual(delivery.dispatch()['processed'], 0)
            with patch.dict(os.environ, {'SENTINEL_SEND':'1','SMTP_HOST':'host','SMTP_FROM':'a','SMTP_USER':'b','SMTP_PASSWORD':'c','SENTINEL_EMAIL_TO':'d'}):
                delivery.dispatch()
            send.assert_not_called()

    def test_field_delivery_acceptance_and_failure(self):
        for i in range(3):
            monitoring.record(self.report(i, mode='field'))
        env={'SENTINEL_SEND':'1','SMTP_HOST':'host','SMTP_FROM':'a','SMTP_USER':'b','SMTP_PASSWORD':'c','SENTINEL_EMAIL_TO':'d'}
        with patch.dict(os.environ, env), patch('src.delivery.send_email', return_value='accepted') as send:
            delivery.dispatch(); delivery.dispatch()
            self.assertEqual(send.call_count, 1)
        email = next(r for r in monitoring.snapshot()['outbox'] if r['channel']=='email')
        self.assertEqual(email['status'], 'provider_accepted')
        with monitoring.connect() as db:
            db.execute("UPDATE outbox SET status='pending' WHERE channel='email'")
        with patch.dict(os.environ, env), patch('src.delivery.send_email', side_effect=TimeoutError):
            delivery.dispatch()
        email = next(r for r in monitoring.snapshot()['outbox'] if r['channel']=='email')
        self.assertEqual(email['status'], 'review_required')
