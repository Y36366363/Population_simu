import unittest

from population_simu.resource_experiment import run_cell, run_experiment


class ResourceExperimentTests(unittest.TestCase):
    def test_same_total_resources_are_diluted(self):
        rows = run_experiment([100], [1, 2, 3], trials=200, seed=9)
        investments = [row["investment_per_child"] for row in rows]
        self.assertGreater(investments[0], investments[1])
        self.assertGreater(investments[1], investments[2])

    def test_cell_is_reproducible(self):
        first = run_cell(resources=5, children=3, trials=300, seed=22)
        second = run_cell(resources=5, children=3, trials=300, seed=22)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
