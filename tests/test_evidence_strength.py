import unittest

from population_simu.evidence_strength import assess_rolling_origin_evidence


class EvidenceStrengthTests(unittest.TestCase):
    def test_three_expanding_folds_are_explicitly_exploratory(self):
        folds = [
            {"train_years": list(range(2010, year)), "test_years": [year]}
            for year in (2018, 2019, 2021)
        ]
        result = assess_rolling_origin_evidence(folds)
        self.assertEqual(result["level"], "exploratory_repeated_historical_check")
        self.assertEqual(result["independent_target_years"], 3)
        self.assertTrue(result["training_windows_overlap"])
        self.assertTrue(result["prior_tests_enter_later_training"])

    def test_five_disjoint_targets_can_only_reach_limited_validation(self):
        folds = [
            {"train_years": [2000 + i], "test_years": [2010 + i]}
            for i in range(5)
        ]
        result = assess_rolling_origin_evidence(folds)
        self.assertEqual(result["level"], "limited_out_of_sample_validation")
        self.assertFalse(result["training_windows_overlap"])
        self.assertFalse(result["prior_tests_enter_later_training"])
        self.assertIn("not confirmatory", result["claim_boundary"])

    def test_missing_folds_or_targets_are_rejected(self):
        for folds in ([], [{"train_years": [2000], "test_years": []}]):
            with self.subTest(folds=folds), self.assertRaises(ValueError):
                assess_rolling_origin_evidence(folds)


if __name__ == "__main__":
    unittest.main()
