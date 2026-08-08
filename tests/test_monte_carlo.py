import unittest

from population_simu.monte_carlo import common_random_seeds, paired_sensitivity, summarize
from population_simu.validation import interval_error, series_error
from population_simu.family_monte_carlo import run_replicates
from pathlib import Path


class MonteCarloTests(unittest.TestCase):
    def test_common_random_seeds_are_reusable(self):
        self.assertEqual(common_random_seeds(7, 4), common_random_seeds(7, 4))
        self.assertNotEqual(common_random_seeds(7, 4), common_random_seeds(8, 4))

    def test_summary_reports_median_and_interval(self):
        result = summarize([1, 2, 3, 4, 5])
        self.assertEqual(result.median, 3)
        self.assertLessEqual(result.ci_low, result.median)
        self.assertGreaterEqual(result.ci_high, result.median)

    def test_paired_sensitivity_uses_each_seed(self):
        result = paired_sensitivity(lambda scenario, seed: len(scenario) + seed % 2, ["a", "bb"], [1, 2, 3])
        self.assertEqual(result["a"].n, 3)
        self.assertEqual(result["bb"].n, 3)

    def test_historical_error_metrics(self):
        result = series_error({2000: 10, 2001: 12}, {2000: 11, 2001: 10})
        self.assertEqual(result["n"], 2)
        self.assertAlmostEqual(result["mae"], 1.5)
        interval = interval_error({2000: 10}, [{2000: 11}, {2000: 12}])
        self.assertEqual(interval["n"], 2)

    def test_family_replicates_return_intervals(self):
        path = str(Path("scenarios/family_major_countries.json"))
        rows = run_replicates([path], years=1, replicates=2, seed=9)
        self.assertTrue(rows)
        self.assertTrue(all(row["n"] == 2 for row in rows))
        self.assertTrue(all(row["ci_low"] <= row["median"] <= row["ci_high"] for row in rows))
