import unittest
from fastapi.testclient import TestClient
from src.web_api import app


class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_data_and_unknown_semantics(self):
        rows = self.client.get('/api/evidence').json()
        self.assertEqual(len(rows), 774)
        self.assertTrue(all(r['screening_score'] is None for r in rows if r['tiles_count'] == 0))

    def test_scoped_plan_and_budget(self):
        row = self.client.get('/api/evidence').json()[0]
        payload = {'ids': [row['shapeID']], 'budget': 200000, 'cost_per_visit': 100000, 'max_visits': 20}
        result = self.client.post('/api/plan', json=payload).json()
        self.assertEqual(result['summary']['selected'], 1)
        self.assertEqual(result['summary']['unspent'], 100000)
        payload['ids'] = []
        self.assertEqual(self.client.post('/api/plan', json=payload).json()['summary']['selected'], 0)

    def test_invalid_inputs_and_brief(self):
        self.assertEqual(self.client.post('/api/plan', json={'cost_per_visit': 0}).status_code, 422)
        self.assertEqual(self.client.post('/api/plan', json={'ids': ['invalid']}).status_code, 422)
        brief = self.client.post('/api/brief', json={'budget': 0})
        self.assertEqual(brief.status_code, 200)
        self.assertIn('0 proposed visits', brief.text)

    def test_frontend_served(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertIn(self.client.get('/app.js').headers['content-type'].split(';')[0], ('text/javascript', 'application/javascript'))
