import unittest

from population_simu.family_checkpoint import fingerprint_world
from population_simu.family_world import FamilyWorld
from population_simu.matching_diagnostics import (
    audit_matching_cost,
    profile_matching_costs,
    summarize_matching_cost_report,
)
from tests.test_family_world import family_scenario


class MatchingDiagnosticsTests(unittest.TestCase):
    def test_cost_audit_is_read_only_and_counts_filter_stages(self):
        world = FamilyWorld(family_scenario())
        before = fingerprint_world(world)
        report = audit_matching_cost(world, repeats=2)
        self.assertEqual(fingerprint_world(world), before)
        self.assertTrue(report["read_only_checks"]["world_fingerprint_unchanged"])
        self.assertTrue(report["read_only_checks"]["rng_state_unchanged"])
        counts = report["counts"]
        self.assertGreaterEqual(counts["age_window_candidates"], counts["active_candidates"])
        self.assertGreaterEqual(counts["active_candidates"], counts["after_household_filter"])
        self.assertGreaterEqual(counts["after_household_filter"], counts["after_maternal_filter"])
        self.assertGreaterEqual(counts["after_maternal_filter"], counts["after_paternal_filter"])
        self.assertEqual(counts["after_paternal_filter"], counts["weights_evaluated"])

    def test_paired_profile_keeps_every_annual_fingerprint_equal(self):
        report = profile_matching_costs(
            family_scenario(), years=4, checkpoints=[2, 4], seeds=[731], repeats=1
        )
        self.assertTrue(report["acceptance"]["all_paired_years_equal"])
        self.assertTrue(report["acceptance"]["all_audits_read_only"])
        self.assertEqual(len(report["runs"][0]["yearly_fingerprints"]), 4)
        self.assertEqual(len(report["runs"][0]["audits"]), 2)
        summary = summarize_matching_cost_report(report)
        self.assertEqual(len(summary["checkpoints"]), 2)
        shares = summary["checkpoints"][0]["stages"]
        self.assertAlmostEqual(
            sum(row["median_share_of_measured_stages"] for row in shares.values()),
            1.0,
            places=5,
        )

    def test_invalid_design_is_rejected(self):
        scenario = family_scenario()
        with self.assertRaises(ValueError):
            profile_matching_costs(
                scenario, years=4, checkpoints=[4, 2], seeds=[1], repeats=1
            )
        with self.assertRaises(ValueError):
            audit_matching_cost(FamilyWorld(scenario), repeats=0)
        with self.assertRaises(ValueError):
            summarize_matching_cost_report({"kind": "wrong"})


if __name__ == "__main__":
    unittest.main()
