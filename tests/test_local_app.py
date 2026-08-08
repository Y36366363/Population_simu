import json
import unittest

from population_simu.local_app import available_scenarios, run_scenario


class LocalAppTests(unittest.TestCase):
    def test_lists_family_scenarios(self):
        self.assertIn("family_major_countries.json", available_scenarios())

    def test_run_returns_snapshot_and_history(self):
        result = run_scenario("family_major_countries.json", years=1, seed=17)
        self.assertEqual(result["snapshot"]["year"], 1971)
        self.assertTrue(result["history"])
        self.assertTrue(result["region_history"])
        self.assertEqual(result["region_history"][-1]["year"], 1971)
        json.dumps(result, ensure_ascii=False)

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            run_scenario("../secret.json")
