import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import pandas as pd
from fastapi.testclient import TestClient
from src.web_api import app


class OperationsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'SENTINEL_DB': str(Path(self.temp.name)/'api.sqlite3'), 'SENTINEL_INGEST_TOKEN':'test-only-secret', 'SENTINEL_SEND':'0'})
        self.env.start()
        self.frame = patch('src.web_api.facilities', return_value=pd.DataFrame([{'site_id':'test:1','name':'Test clinic','source':'GRID3','shapeID':'LGA-1'}]))
        self.frame.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.frame.stop(); self.env.stop(); self.temp.cleanup()

    def test_facility_filters_pagination_and_limits(self):
        self.assertEqual(self.client.get('/api/facilities?q=clinic').json()['total'],1)
        self.assertEqual(self.client.get('/api/facilities?q=[').json()['total'],0)
        self.assertEqual(self.client.get('/api/facilities?offset=1').json()['items'],[])
        self.assertEqual(self.client.get('/api/facilities?limit=1000').status_code,422)

    def test_field_auth_site_time_and_idempotence(self):
        data={'event_id':'test1','site_id':'test:1','mode':'field','observed_at':datetime.now(timezone.utc).isoformat(),'success':False,'seconds':3}
        self.assertEqual(self.client.post('/api/observations',json=data).status_code,403)
        headers={'X-Sentinel-Token':'test-only-secret'}
        self.assertEqual(self.client.post('/api/observations',json=data,headers=headers).status_code,200)
        self.assertTrue(self.client.post('/api/observations',json=data,headers=headers).json()['duplicate'])
        data['event_id']='test2'; data['observed_at']='2026-01-01T12:00:00'
        self.assertEqual(self.client.post('/api/observations',json=data,headers=headers).status_code,422)
        data['site_id']='unknown'
        self.assertEqual(self.client.post('/api/observations',json=data,headers=headers).status_code,422)

    def test_probe_boundaries(self):
        self.assertEqual(self.client.post('/api/probe-upload',content=b'abc').status_code,403)
        headers={'X-Sentinel-Token':'test-only-secret'}
        result=self.client.post('/api/probe-upload',content=b'0'*65536,headers=headers)
        self.assertEqual(result.json()['received_bytes'],65536)
        self.assertEqual(self.client.post('/api/probe-upload',content=b'0'*262145,headers=headers).status_code,413)
        self.assertEqual(self.client.post('/api/probe-upload',content=b'',headers=headers).status_code,422)

    def test_hosted_monitoring_filters_and_requires_token(self):
        with patch.dict(os.environ, {'VERCEL':'1'}), patch('src.web_api.monitoring.snapshot', return_value={}) as snapshot:
            self.assertEqual(self.client.get('/api/monitoring').status_code,200)
            snapshot.assert_called_with(None, public_only=True)
            self.client.get('/api/monitoring',headers={'X-Sentinel-Token':'test-only-secret'})
            snapshot.assert_called_with(None, public_only=False)
            data={'event_id':'demo1','site_id':'test:1','mode':'demo','observed_at':datetime.now(timezone.utc).isoformat(),'success':False,'seconds':3}
            self.assertEqual(self.client.post('/api/observations',json=data).status_code,403)
            self.assertEqual(self.client.post('/api/incidents/1/acknowledge',json={'actor':'Tester','note':'Checking'}).status_code,403)
            with patch('src.web_api.monitoring.record', return_value={'duplicate':False}) as record:
                self.assertEqual(self.client.post('/api/observations',json=data,headers={'X-Sentinel-Token':'test-only-secret'}).status_code,200)
                record.assert_called_once()
