import json
import unittest

from population_simu.simulation_validation import validate_scenario

from tests.test_experiments import small_scenario


class SimulationValidationTests(unittest.TestCase):
    def test_multi_seed_validation_checks_structure_without_claiming_accuracy(self):
        report = validate_scenario(small_scenario(), years=2, seeds=[7, 11])
        self.assertTrue(report["all_checks_passed"])
        self.assertEqual(report["scope"],
                         "internal consistency and reproducibility; not empirical accuracy")
        self.assertTrue(report["checkpoint_continuation"]["identical"])
        self.assertEqual(len(report["runs"]), 2)
        for run in report["runs"]:
            self.assertEqual(run["path_manifest"]["events"], 12)
            self.assertEqual(run["path_manifest"]["events"], run["expected_path_events"])
            self.assertTrue(run["all_population_balances_closed"])
            self.assertTrue(run["all_regional_balances_closed"])
            self.assertTrue(run["all_transfer_audits_passed"])
            self.assertTrue(run["all_genealogy_audits_passed"])
        json.dumps(report, allow_nan=False)

    def test_validation_design_rejects_invalid_replication(self):
        for settings in (
            {"years": 1, "seeds": [7]},
            {"years": 2, "seeds": []},
            {"years": 2, "seeds": [7, 7]},
            {"years": 2, "seeds": [True]},
        ):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                validate_scenario(small_scenario(), **settings)


if __name__ == "__main__":
    unittest.main()
