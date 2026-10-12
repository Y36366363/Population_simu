import copy
import unittest

from scripts.compare_social_norm_index_profiles import compare_index_profiles


def profile(*, indexed: bool, step_seconds: float) -> dict[str, object]:
    segment = {
        "years": 2,
        "end_population": 10,
        "end_households": 6,
        "end_transfer_records": 3,
        "step_seconds_per_year": step_seconds,
        "nested_diagnostics": {
            "_desired_children": {"calls": 8},
            "same_region": {"calls": 0 if indexed else 100},
            "same_kin": {"calls": 0 if indexed else 100},
            "shares_occupation": {"calls": 0 if indexed else 40},
        },
    }
    if indexed:
        segment["nested_diagnostics"]["_build_social_norm_index"] = {"calls": 4}
    return {
        "kind": "family_world_phase_profile",
        "configuration": {"years": 4, "seeds": [7]},
        "runs": [{"seed": 7, "early": copy.deepcopy(segment), "late": copy.deepcopy(segment)}],
    }


class SocialNormIndexProfileTests(unittest.TestCase):
    def test_accepts_exact_state_calls_and_build_frequency(self):
        report = compare_index_profiles(
            profile(indexed=False, step_seconds=2.0),
            profile(indexed=True, step_seconds=0.5),
        )
        self.assertTrue(report["acceptance"]["passed"])
        self.assertEqual(
            report["aggregate"]["median_candidate_to_baseline_step_ratio"]["late"],
            0.25,
        )

    def test_rejects_state_drift_or_wrong_build_count(self):
        baseline = profile(indexed=False, step_seconds=2.0)
        candidate = profile(indexed=True, step_seconds=0.5)
        candidate["runs"][0]["early"]["end_population"] = 11
        candidate["runs"][0]["late"]["nested_diagnostics"]["_build_social_norm_index"]["calls"] = 3
        report = compare_index_profiles(baseline, candidate)
        self.assertFalse(report["acceptance"]["passed"])
        self.assertFalse(report["aggregate"]["all_state_endpoints_equal"])
        self.assertFalse(report["aggregate"]["all_index_build_counts_exact"])

    def test_rejects_mismatched_configuration(self):
        baseline = profile(indexed=False, step_seconds=2.0)
        candidate = profile(indexed=True, step_seconds=0.5)
        candidate["configuration"]["years"] = 5
        with self.assertRaises(ValueError):
            compare_index_profiles(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
