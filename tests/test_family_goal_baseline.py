import math
import unittest

from scripts.run_family_goal_baseline import (
    DEFAULT_SEEDS, build_parser, dynasty_variants, run_baseline, summarize_replicates,
)


class FamilyGoalBaselineTests(unittest.TestCase):
    def test_variants_change_only_the_named_factors(self):
        variants = dynasty_variants()
        baseline = variants["baseline"]
        for name, params in variants.items():
            changed = {key for key, value in vars(params).items() if value != getattr(baseline, key)}
            expected = {
                "baseline": set(),
                "lower_housing_pressure": {"housing_pressure"},
                "higher_welfare_floor": {"welfare_floor"},
                "lower_housing_and_higher_welfare": {"housing_pressure", "welfare_floor"},
            }[name]
            self.assertEqual(changed, expected)
            self.assertEqual(params.material_deadline, 58.0)
        self.assertEqual(variants["lower_housing_pressure"].housing_pressure, 0.20)
        self.assertEqual(variants["higher_welfare_floor"].welfare_floor, 0.45)

    def test_reproducible_runs_preserve_seed_and_sample_metadata(self):
        settings = dict(resources=[5], children=[1], trials=30, seeds=[41, 42], generations=2)
        first = run_baseline(**settings)
        self.assertEqual(first, run_baseline(**settings))
        self.assertEqual(first["configuration"]["trials_per_cell"], 60)
        self.assertEqual(first["configuration"]["total_seed_runs"], 10)
        self.assertEqual(first["configuration"]["total_simulated_founder_family_trials"], 300)
        for cell in first["resource_experiment"] + first["dynasty_experiment"]:
            self.assertEqual([run["seed"] for run in cell["replicates"]], [41, 42])
            self.assertTrue(all(run["result"]["trials"] == 30 for run in cell["replicates"]))
        self.assertFalse(first["aggregation"]["confidence_intervals"])
        self.assertEqual(len(first["reproducibility"]["source_sha256"]), 5)

    def test_aggregation_is_seed_mean_range_and_sample_sd(self):
        result = summarize_replicates([{"x": 1}, {"x": 2}, {"x": 6}], ("x",))["x"]
        self.assertEqual(result["mean"], 3)
        self.assertEqual(result["seed_min"], 1)
        self.assertEqual(result["seed_max"], 6)
        self.assertAlmostEqual(result["seed_sample_sd"], math.sqrt(7))
        self.assertEqual(result["n_seeds"], 3)
        single = summarize_replicates([{"x": 4}], ("x",))["x"]
        self.assertIsNone(single["seed_sample_sd"])

    def test_invalid_or_duplicate_inputs_are_rejected_before_simulation(self):
        invalid = [
            {"resources": []}, {"resources": [float("nan")]}, {"resources": [0]},
            {"resources": [5, 5]}, {"children": [0]}, {"children": [1, 1]},
            {"trials": 0}, {"generations": 0}, {"seeds": []}, {"seeds": [2, 2]},
            {"dynasty_resources": float("inf")},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                run_baseline(**overrides)

    def test_cli_defaults_match_the_baseline_protocol(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.resources, [5, 100, 300])
        self.assertEqual(args.children, [1, 2, 3])
        self.assertEqual(args.trials, 1000)
        self.assertEqual(args.seeds, list(DEFAULT_SEEDS))
        self.assertEqual(args.generations, 4)
        self.assertEqual(args.dynasty_resources, 100)


if __name__ == "__main__":
    unittest.main()
