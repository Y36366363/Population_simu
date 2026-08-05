import unittest

from population_simu.institution_experiment import REGIMES, run_institution_experiment


class InstitutionExperimentTests(unittest.TestCase):
    def test_all_switches_and_family_sizes_are_exported(self):
        rows = run_institution_experiment(trials=80, generations=3, seed=17)
        self.assertEqual(len(rows), len(REGIMES) * 3)
        self.assertEqual({row["regime"] for row in rows}, set(REGIMES))
        self.assertEqual({row["initial_children"] for row in rows}, {1, 2, 3})

    def test_anti_nepotism_reduces_occupational_persistence(self):
        rows = run_institution_experiment(trials=1200, generations=4, seed=31)
        baseline = next(
            row for row in rows if row["regime"] == "baseline" and row["initial_children"] == 1
        )
        reform = next(
            row
            for row in rows
            if row["regime"] == "anti_nepotism" and row["initial_children"] == 1
        )
        self.assertLess(
            reform["occupational_persistence_rate"], baseline["occupational_persistence_rate"]
        )


if __name__ == "__main__":
    unittest.main()
