import copy
import unittest

from scripts.compare_social_norm_aggregate_profiles import compare_aggregate_profiles


def profile(*, aggregated: bool, seconds: float) -> dict[str, object]:
    births = 3
    diagnostics = {
        "_desired_children": {"calls": 8},
        "_build_social_norm_index": {"calls": 4},
    }
    if aggregated:
        diagnostics["record_birth"] = {"calls": births}
    segment = {
        "years": 2,
        "end_population": 10,
        "end_households": 6,
        "end_transfer_records": 3,
        "modeled_births": births,
        "step_seconds_per_year": seconds,
        "phases": {
            "_summaries": {"seconds_per_year": seconds / 2},
            "_births": {"seconds_per_year": seconds / 4},
        },
        "nested_diagnostics": diagnostics,
    }
    return {
        "kind": "family_world_phase_profile",
        "configuration": {"years": 4, "seeds": [7]},
        "runs": [{"seed": 7, "early": copy.deepcopy(segment), "late": copy.deepcopy(segment)}],
    }


class SocialNormAggregateProfileTests(unittest.TestCase):
    def test_accepts_matched_state_and_one_update_per_birth(self):
        report = compare_aggregate_profiles(
            profile(aggregated=False, seconds=2.0),
            profile(aggregated=True, seconds=0.5),
        )
        self.assertTrue(report["acceptance"]["passed"])
        self.assertEqual(
            report["aggregate"]["median_candidate_to_baseline_step_ratio"]["late"],
            0.25,
        )

    def test_rejects_missing_birth_update_or_state_drift(self):
        baseline = profile(aggregated=False, seconds=2.0)
        candidate = profile(aggregated=True, seconds=0.5)
        candidate["runs"][0]["early"]["end_households"] = 7
        candidate["runs"][0]["late"]["nested_diagnostics"]["record_birth"]["calls"] = 2
        report = compare_aggregate_profiles(baseline, candidate)
        self.assertFalse(report["acceptance"]["passed"])
        self.assertFalse(report["aggregate"]["all_state_endpoints_equal"])
        self.assertFalse(report["aggregate"]["all_birth_updates_match_modeled_births"])

    def test_rejects_seed_mismatch(self):
        baseline = profile(aggregated=False, seconds=2.0)
        candidate = profile(aggregated=True, seconds=0.5)
        candidate["runs"][0]["seed"] = 8
        with self.assertRaises(ValueError):
            compare_aggregate_profiles(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
