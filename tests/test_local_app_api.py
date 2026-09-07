import unittest

from population_simu.local_app import available_scenarios, result_csv, run_scenario


class LocalApiTests(unittest.TestCase):
    def test_health_scenarios_and_run_contract(self):
        scenarios = available_scenarios()
        self.assertIn("family_major_countries.json", scenarios)
        result = run_scenario("family_major_countries.json", years=1, seed=7)
        self.assertTrue(result["history"])
        self.assertIn("population", result["snapshot"])
        self.assertIn("country", result["history"][0])
        self.assertIn("year", result["history"][0])
        self.assertIn("population", result_csv(result).splitlines()[0])


if __name__ == "__main__":
    unittest.main()
