import sys
from pathlib import Path
import unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from readiness import screen, Scenario, allocate_visits, briefing, rehearsal_action


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            dict(shapeID='a', shapeName='<script>', tiles_count=0, mean_u_mbps=0, mean_lat_ms=999, total_tests=0),
            dict(shapeID='b', shapeName='Same name', tiles_count=12, mean_u_mbps=.1, mean_lat_ms=300, total_tests=40),
            dict(shapeID='c', shapeName='Same name', tiles_count=20, mean_u_mbps=10, mean_lat_ms=40, total_tests=80),
        ])

    def test_unknown_is_not_failure(self):
        result = screen(self.df).set_index('shapeID')
        self.assertTrue(pd.isna(result.loc['a', 'screening_score']))
        self.assertEqual(result.loc['a', 'evidence_status'], 'Insufficient evidence')
        self.assertEqual(result.loc['c', 'screening_score'], 0)

    def test_budget_capacity_and_unique_ids(self):
        chosen, summary = allocate_visits(pd.concat([self.df, self.df]), Scenario(250, 100, 10))
        self.assertEqual(chosen.shapeID.tolist(), ['b', 'a'])
        self.assertEqual(summary['estimated_spend'], 200)
        self.assertEqual(summary['unspent'], 50)
        self.assertEqual(summary['remaining_lgas'], 1)
        chosen, summary = allocate_visits(self.df, Scenario(0, 100, 10))
        self.assertTrue(chosen.empty)
        self.assertEqual(summary['estimated_spend'], 0)

    def test_export_escapes_names_and_notes(self):
        scenario = Scenario()
        chosen, summary = allocate_visits(self.df, scenario)
        report = briefing(self.df, chosen, scenario, summary, ['<script>bad</script>'])
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)

    def test_rehearsal_and_validation(self):
        self.assertEqual(rehearsal_action(False, 10), 'Check backup options')
        self.assertNotEqual(rehearsal_action(True, 30), rehearsal_action(True, 90))
        with self.assertRaises(ValueError):
            Scenario(100, 0, 1)
        with self.assertRaises(ValueError):
            rehearsal_action(True, float('nan'))


if __name__ == '__main__':
    unittest.main()
