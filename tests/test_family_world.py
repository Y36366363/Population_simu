import unittest

from population_simu.family_config import FamilyScenario
from population_simu.family_world import FamilyWorld


def family_scenario(max_children=2, seed=11, **country_overrides):
    country = {
        "id": "TST",
        "name": "测试国",
        "initial_clans": 30,
        "initial_development": 0.3,
        "annual_development_gain": 0.003,
        "initial_urbanization": 0.4,
        "annual_urbanization_gain": 0.002,
        "education_access": 0.6,
        "cost_of_children": 0.7,
        "baseline_family_resources": 100,
        "initial_children_per_family": 3,
        "policies": [
            {
                "start_year": 2000,
                "end_year": None,
                "name": "hard-cap",
                "max_children": max_children,
                "enforcement": 1.0,
            }
        ],
    }
    country.update(country_overrides)
    return FamilyScenario.from_dict(
        {
            "name": "family-test",
            "simulation": {
                "start_year": 2000,
                "end_year": 2025,
                "random_seed": seed,
                "international_migration_rate": 0.0,
            },
            "countries": [country],
        }
    )


class FamilyWorldTests(unittest.TestCase):
    def test_one_founder_household_per_clan(self):
        world = FamilyWorld(family_scenario())
        self.assertEqual(len(world.clans), 30)
        self.assertEqual(len(world.households), 30)
        self.assertEqual({len(clan.branch_ids) for clan in world.clans.values()}, {1})

    def test_strict_child_cap_applies_to_seed_and_births(self):
        world = FamilyWorld(family_scenario(max_children=1))
        world.run(2020)
        self.assertTrue(all(home.children_ever_born <= 1 for home in world.households.values()))

    def test_people_keep_valid_family_and_clan_references(self):
        world = FamilyWorld(family_scenario())
        world.run(2025)
        for person in world.living_people:
            self.assertIn(person.clan_id, world.clans)
            self.assertIn(person.household_id, world.households)
            self.assertIn(person.id, world.households[person.household_id].member_ids)

    def test_reproducible_history(self):
        first = FamilyWorld(family_scenario(seed=55)).run()
        second = FamilyWorld(family_scenario(seed=55)).run()
        self.assertEqual([row.flat_dict() for row in first], [row.flat_dict() for row in second])

    def test_medical_training_can_reach_license(self):
        world = FamilyWorld(family_scenario())
        country = world.countries["TST"]
        person = next(person for person in world.living_people if 22 <= person.age <= 67)
        person.occupation = "medical_trainee"
        person.training_years = country.medical_training_years - 1
        person.human_capital = 1.0
        person.licensed = False
        world.rng.random = lambda: 0.5
        world._career_transitions()
        self.assertEqual(person.occupation, "medical")
        self.assertTrue(person.licensed)

    def test_v3_institution_metrics_are_exported(self):
        world = FamilyWorld(family_scenario())
        row = world.run(2002)[-1].flat_dict()
        for key in (
            "unemployment_rate",
            "injury_rate",
            "homeownership_rate",
            "licensed_physician_share",
            "state_sector_share",
            "political_dynasty_share",
            "faction_concentration",
            "elite_marriage_share",
            "economic_cycle_index",
            "divorces",
            "remarriages",
            "internal_migrants",
            "rural_population_share",
            "gender_status_gap",
        ):
            self.assertIn(key, row)

    def test_economic_cycle_changes_over_time(self):
        world = FamilyWorld(family_scenario(cycle_amplitude=0.2, shock_probability=0.0))
        rows = world.run(2005)
        values = [row.economic_cycle_index for row in rows if row.country_id == "TST"]
        self.assertGreater(len(set(round(value, 5) for value in values)), 2)

    def test_high_divorce_rate_creates_divorce_events(self):
        world = FamilyWorld(family_scenario(base_divorce_rate=1.0))
        row = world.step()[0]
        self.assertGreater(row.divorces, 0)


if __name__ == "__main__":
    unittest.main()
