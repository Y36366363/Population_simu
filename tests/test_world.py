import unittest

from population_simu.config import Scenario
from population_simu.world import World


def demo_scenario(**simulation_overrides):
    simulation = {
        "start_year": 2025,
        "years": 5,
        "initial_people": 200,
        "random_seed": 7,
        "baseline_tfr": 1.8,
    }
    simulation.update(simulation_overrides)
    return Scenario.from_dict(
        {
            "name": "test",
            "simulation": simulation,
            "policy": {},
            "regions": [
                {"id": "a", "name": "A", "initial_share": 0.6},
                {"id": "b", "name": "B", "initial_share": 0.4, "opportunity": 0.8},
            ],
        }
    )


class WorldTests(unittest.TestCase):
    def test_seed_population_exact_size(self):
        world = World(demo_scenario(initial_people=201))
        self.assertEqual(len(world.living_people), 201)

    def test_run_is_reproducible(self):
        first = World(demo_scenario()).run()
        second = World(demo_scenario()).run()
        self.assertEqual([row.flat_dict() for row in first], [row.flat_dict() for row in second])

    def test_history_and_family_references(self):
        world = World(demo_scenario())
        world.run(3)
        self.assertEqual(len(world.history), 4)
        self.assertEqual(world.history[-1].year, 2028)
        for person in world.living_people:
            self.assertIn(person.household_id, world.households)
            self.assertIn(person.id, world.households[person.household_id].member_ids)

    def test_zero_fertility_has_no_births(self):
        world = World(demo_scenario(baseline_tfr=0))
        world.run(4)
        self.assertEqual(sum(row.births for row in world.history), 0)

    def test_population_is_partitioned_by_region(self):
        world = World(demo_scenario())
        final = world.run(5)[-1]
        self.assertEqual(final.population, sum(final.population_by_region.values()))


if __name__ == "__main__":
    unittest.main()
