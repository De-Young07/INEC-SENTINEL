import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from src.probe import run_once


class ProbeTests(unittest.TestCase):
    def test_offline_report_retries_with_original_identifier(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'SENTINEL_INGEST_TOKEN':'test-only'}):
            queue=Path(folder)/'queue.json'
            opener=Mock()
            opener.open.side_effect=OSError('offline')
            with patch('urllib.request.build_opener',return_value=opener):
                result=run_once('http://localhost:8600','site-1','test',queue)
            self.assertEqual(result['queued_reports'],1)
            original=json.loads(queue.read_text())[0]
            submitted=[]
            def respond(request,timeout):
                if request.full_url.endswith('/api/probe-upload'):
                    return io.BytesIO(b'{"received_bytes":65536}')
                submitted.append(json.loads(request.data))
                return io.BytesIO(b'{"duplicate":false}')
            opener.open.side_effect=respond
            with patch('urllib.request.build_opener',return_value=opener):
                result=run_once('http://localhost:8600','site-1','test',queue)
            self.assertEqual(result['queued_reports'],0)
            self.assertEqual(submitted[0],original)
            self.assertTrue(result['upload_completed'])

    def test_remote_plaintext_refused(self):
        with patch.dict(os.environ, {'SENTINEL_INGEST_TOKEN':'test-only'}):
            with self.assertRaises(ValueError):
                run_once('http://example.com','site-1','test',Path('unused.json'))
