import unittest

from population_simu.birth_diagnostics import ObservedBirthWorld, state_fingerprint, decompose
from population_simu.config import Scenario, SimulationConfig, PolicyConfig, RegionConfig
from population_simu.world import World


class BirthDiagnosticsTests(unittest.TestCase):
    def test_observation_preserves_entire_world_and_rng_each_year(self):
        for seed in (7, 31):
            scenario = Scenario("test", SimulationConfig(initial_people=200, random_seed=seed),
                                PolicyConfig(), (RegionConfig("a", "a", 1.0),))
            a, b = World(scenario), ObservedBirthWorld(scenario)
            for _ in range(4):
                actual = a.step()
                b.step()
                self.assertEqual(state_fingerprint(a), state_fingerprint(b))
                row = b.birth_observations[-1]
                self.assertEqual(actual.births, row["actual_births"])
                self.assertAlmostEqual(row["expected_births"], sum(c["probability"] for c in row["candidates"]))

    def test_exact_symmetric_accounting_including_zero_candidates(self):
        first = {"candidate_households": 0, "expected_births": 0}
        final = {"candidate_households": 10, "expected_births": 2}
        row = decompose(first, final)
        self.assertAlmostEqual(row["candidate_count_contribution"] + row["mean_probability_contribution"], 2)
