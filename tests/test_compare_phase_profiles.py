import copy
import unittest

from scripts.compare_phase_profiles import compare_profiles


def profile(*, region_calls: int, seconds: float) -> dict[str, object]:
    desired_calls = 4
    segment = {
        "end_population": 10,
        "end_households": 6,
        "end_transfer_records": 3,
        "step_seconds_per_year": seconds,
        "phases": {
            "_summaries": {"seconds_per_year": seconds / 2},
            "_births": {"seconds_per_year": seconds / 4},
        },
        "nested_diagnostics": {
            "_desired_children": {"calls": desired_calls},
            "same_region": {"calls": region_calls},
            "same_kin": {"calls": 8},
            "shares_occupation": {"calls": 7},
        },
    }
    return {
        "kind": "family_world_phase_profile",
        "configuration": {"years": 4, "seeds": [7]},
        "source_sha256": {"src/population_simu/family_world.py": "old"},
        "runs": [{"seed": 7, "early": copy.deepcopy(segment), "late": copy.deepcopy(segment)}],
    }


class ComparePhaseProfilesTests(unittest.TestCase):
    def test_accepts_exact_state_and_merged_scan_relation(self):
        baseline = profile(region_calls=12, seconds=2.0)
        candidate = profile(region_calls=8, seconds=1.5)
        candidate["source_sha256"]["src/population_simu/family_world.py"] = "new"
        report = compare_profiles(baseline, candidate)
        self.assertTrue(report["acceptance"]["passed"])
        self.assertEqual(
            report["changed_source_files"], ["src/population_simu/family_world.py"]
        )
        self.assertEqual(
            report["aggregate"]["median_candidate_to_baseline_step_ratio"]["early"],
            0.75,
        )

    def test_rejects_endpoint_drift_without_using_timing_as_gate(self):
        baseline = profile(region_calls=12, seconds=2.0)
        candidate = profile(region_calls=8, seconds=4.0)
        candidate["runs"][0]["late"]["end_population"] = 11
        report = compare_profiles(baseline, candidate)
        self.assertFalse(report["acceptance"]["passed"])
        self.assertFalse(report["aggregate"]["all_state_endpoints_equal"])
        self.assertTrue(report["acceptance"]["timing_is_not_an_acceptance_gate"])

    def test_rejects_configuration_or_seed_mismatch(self):
        baseline = profile(region_calls=12, seconds=2.0)
        candidate = profile(region_calls=8, seconds=1.5)
        candidate["configuration"] = {"years": 5, "seeds": [7]}
        with self.assertRaises(ValueError):
            compare_profiles(baseline, candidate)
        candidate = profile(region_calls=8, seconds=1.5)
        candidate["runs"][0]["seed"] = 8
        with self.assertRaises(ValueError):
            compare_profiles(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
