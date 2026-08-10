import unittest

from population_simu.calibration import replay_errors


class CalibrationTests(unittest.TestCase):
    def test_replay_errors_aligns_by_year(self):
        observed = [{"year": 2000, "population": 10}, {"year": 2001, "population": 12}]
        simulated = [{"year": 2000, "population": 9}, {"year": 2001, "population": 13}]
        result = replay_errors(observed, simulated, metrics=("population",))
        self.assertEqual(result["population"]["n"], 2)
        self.assertAlmostEqual(result["population"]["bias"], 0.0)


if __name__ == "__main__":
    unittest.main()

