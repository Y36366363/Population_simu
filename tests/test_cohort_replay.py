import unittest
from pathlib import Path

from population_simu.cohort_replay import (
    load_age_sex_death_rates,
    death_rate_profiles,
    load_world_bank_age_sex_groups,
    replay_age_sex_groups,
    reconcile_age_sex_snapshots,
)


ROOT = Path(__file__).parents[1]


class CohortReplayTests(unittest.TestCase):
    def test_real_world_bank_age_sex_sample_loads(self):
        path = ROOT / "data/observed/wb_age_sex_groups_sample.csv"
        rows = load_world_bank_age_sex_groups(path)
        self.assertEqual(len(rows), 816)
        self.assertEqual({row["sex"] for row in rows}, {"F", "M"})

    def test_real_death_rate_sample_loads(self):
        path = ROOT / "data/observed/owid_age_sex_death_rates_sample.csv"
        rows = load_age_sex_death_rates(path)
        self.assertGreater(len(rows), 1000)
        self.assertGreater(rows[0]["death_rate_per_1000"], 0)
        profiles = death_rate_profiles(rows, entity="China", year=1990)
        self.assertEqual(set(profiles), {"F", "M"})
        self.assertGreater(profiles["M"].rate(65), 0)

    def test_replay_aggregates_single_age_snapshot(self):
        observed = [{"entity": "A", "year": 2000, "sex": "F",
                     "age_min": 0, "age_max": 1, "population": 30}]
        snapshots = {2000: {"A": {"F": [10, 20], "M": [5, 5]}}}
        result = replay_age_sex_groups(observed, snapshots)
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["mae"], 0)

    def test_family_and_cohort_snapshots_reconcile(self):
        family = {"A": {"F": {0: 2, 1: 3}, "M": {0: 1}}}
        cohort = {"A": {"F": (2, 3), "M": (1, 0)}}
        result = reconcile_age_sex_snapshots(family, cohort)
        self.assertEqual(result["mae"], 0)


if __name__ == "__main__":
    unittest.main()
