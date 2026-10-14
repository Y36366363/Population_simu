import copy
import unittest

from scripts.compare_marriage_matching_profiles import compare_matching_profiles


def profile(*, candidate: bool, seconds: float) -> dict[str, object]:
    diagnostics = {"_men_by_woman_age": {"calls": 8 if candidate else 0}}
    segment = {
        "years": 2,
        "end_population": 10,
        "end_households": 6,
        "end_transfer_records": 3,
        "step_seconds_per_year": seconds,
        "phases": {
            "_form_family_branches": {"calls": 2, "seconds_per_year": seconds / 2},
        },
        "nested_diagnostics": diagnostics,
    }
    return {
        "kind": "family_world_phase_profile",
        "configuration": {"years": 4, "seeds": [7]},
        "runs": [{"seed": 7, "early": copy.deepcopy(segment), "late": copy.deepcopy(segment)}],
    }


class MarriageMatchingProfileTests(unittest.TestCase):
    def test_accepts_matched_state_phase_calls_and_stable_pool_count(self):
        report = compare_matching_profiles(
            profile(candidate=False, seconds=2.0),
            profile(candidate=True, seconds=1.0),
        )
        self.assertTrue(report["acceptance"]["passed"])
        self.assertEqual(report["aggregate"]["country_pools_per_year"], 4)
        self.assertEqual(
            report["aggregate"]["median_candidate_to_baseline_pairing_ratio"]["early"],
            0.5,
        )

    def test_rejects_endpoint_drift_or_incomplete_year_coverage(self):
        baseline = profile(candidate=False, seconds=2.0)
        candidate = profile(candidate=True, seconds=1.0)
        candidate["runs"][0]["early"]["end_population"] = 11
        candidate["runs"][0]["late"]["nested_diagnostics"]["_men_by_woman_age"]["calls"] = 7
        report = compare_matching_profiles(baseline, candidate)
        self.assertFalse(report["acceptance"]["passed"])
        self.assertFalse(report["aggregate"]["all_state_endpoints_equal"])
        self.assertFalse(report["aggregate"]["all_age_window_builds_cover_each_year"])

    def test_rejects_configuration_mismatch(self):
        baseline = profile(candidate=False, seconds=2.0)
        candidate = profile(candidate=True, seconds=1.0)
        candidate["configuration"]["years"] = 5
        with self.assertRaises(ValueError):
            compare_matching_profiles(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
