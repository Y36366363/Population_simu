from dataclasses import replace
import unittest

from population_simu.config import Scenario, SimulationConfig, PolicyConfig, RegionConfig
from population_simu.world import World
from population_simu.population_initialization import match_female_exposure_share
from population_simu.benchmarks import household_simulator_runner


class InitialPopulationTests(unittest.TestCase):
    def test_margin_fit_preserves_households_genealogy_and_random_state(self):
        for seed in (1, 7):
            for share in (0.18, 0.22):
                world = World(Scenario("test", SimulationConfig(initial_people=1200, random_seed=seed),
                                      PolicyConfig(), (RegionConfig("s", "s", 1.0),)))
                rng = world.rng.getstate()
                before = {pid: replace(p) for pid, p in world.people.items()}
                household_members = {h.id: list(h.member_ids) for h in world.households.values()}
                audit = match_female_exposure_share(world, share)
                self.assertEqual(audit["after"]["F_15_44"], round(1200 * share))
                self.assertEqual(world.rng.getstate(), rng)
                self.assertEqual({h.id: h.member_ids for h in world.households.values()}, household_members)
                for pid, person in world.people.items():
                    self.assertEqual(replace(person, age=before[pid].age), before[pid])
                    for parent_id in (person.mother_id, person.father_id):
                        if parent_id is not None:
                            self.assertEqual(person.age - world.people[parent_id].age,
                                             before[pid].age - before[parent_id].age)
                self.assertEqual(world.history[0].year, world.year)

    def test_invalid_shares_fail(self):
        for share in (float("nan"), 0, 1):
            with self.assertRaises(ValueError):
                match_female_exposure_share(None, share)

    def test_transform_applies_to_forecast_and_cached_independent_scale_worlds(self):
        calls = []
        def initialize(world, entity, year):
            calls.append((entity, year, world.year))
            match_female_exposure_share(world, 0.19)
        runner = household_simulator_runner(
            exposure_denominator="dynamic_female_15_44", independent_scale_paths=2,
            initial_population_transform=initialize)
        train = [{"entity": "A", "year": 2017, "asfr_15_44": 60,
                  "housing_cost_burden": 0.35}]
        runner(train, [2018, 2021], 7)
        self.assertEqual(calls, [("A", 2017, 2017)] * 3)
        runner(train, [2018, 2021], 8)
        self.assertEqual(calls, [("A", 2017, 2017)] * 4)


if __name__ == "__main__":
    unittest.main()
