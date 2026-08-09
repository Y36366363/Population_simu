import json
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

    def test_snapshot_is_serializable_and_partitioned(self):
        world = FamilyWorld(family_scenario())
        snapshot = world.snapshot()
        json.dumps(snapshot, ensure_ascii=False)
        self.assertEqual(snapshot["year"], 2000)
        self.assertEqual(snapshot["households"], 30)
        self.assertEqual(snapshot["population"], sum(item["population"] for item in snapshot["countries"].values()))
        self.assertEqual(snapshot["households"], sum(item["households"] for item in snapshot["countries"].values()))
        self.assertEqual(len(snapshot["countries"]["TST"]["regions"]), 2)
        self.assertEqual(snapshot["region_history"][0]["year"], 2000)
        self.assertEqual(len(snapshot["region_history"][0]["regions"]), 2)

    def test_fertility_age_profile_is_configurable(self):
        world = FamilyWorld(family_scenario(fertility_peak_age=27, fertility_age_spread=10))
        country = world.countries["TST"]
        self.assertAlmostEqual(world._fertility_age_factor(27, country), 1.0)
        self.assertLess(world._fertility_age_factor(40, country), 0.2)

    def test_low_local_amenities_reduce_desired_children(self):
        low = FamilyWorld(family_scenario(regions=(
            {"id": "low", "name": "低服务地区", "urban": True, "amenity_supply": 0.1},
        )))
        high = FamilyWorld(family_scenario(regions=(
            {"id": "high", "name": "高服务地区", "urban": True, "amenity_supply": 0.95},
        )))
        low_home = next(iter(low.households.values()))
        high_home = next(iter(high.households.values()))
        self.assertLess(
            low._desired_children(low_home, low.countries["TST"]),
            high._desired_children(high_home, high.countries["TST"]),
        )

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
            "chronic_illness_share",
            "elder_dependency_ratio",
            "mean_household_care_burden",
            "catastrophic_medical_expense_share",
            "formal_childcare_coverage",
            "grandparent_care_coverage",
            "mean_childcare_gap",
            "sibling_investment_concentration",
        ):
            self.assertIn(key, row)

    def test_fiscal_capacity_and_technology_metrics_are_exported(self):
        world = FamilyWorld(
            family_scenario(
                technology_growth=0.04,
                automation_rate=0.25,
                carrying_capacity_scale=0.7,
            )
        )
        initial = world.run(2002)[0].flat_dict()
        later = world.history[-1].flat_dict()
        for key in (
            "tax_revenue", "public_spending", "fiscal_balance",
            "capacity_pressure", "technology_index", "automation_share",
            "labor_shortage_index",
        ):
            self.assertIn(key, later)
        self.assertGreater(later["technology_index"], initial["technology_index"])
        self.assertGreaterEqual(later["automation_share"], initial["automation_share"])

    def test_region_service_index_is_split_into_dimensions(self):
        world = FamilyWorld(
            family_scenario(
                regions=(
                    {
                        "id": "service", "name": "服务地区", "urban": True,
                        "amenity_supply": 0.2, "school_supply": 1.0,
                        "childcare_supply": 0.8, "medical_supply": 0.6,
                        "transport_access": 0.4, "safety_level": 0.9,
                    },
                )
            )
        )
        region = world.regions["TST"][0]
        self.assertGreater(region.service_index, region.amenity_supply)
        self.assertEqual(region.school_supply, 1.0)

    def test_economic_cycle_changes_over_time(self):
        world = FamilyWorld(family_scenario(cycle_amplitude=0.2, shock_probability=0.0))
        rows = world.run(2005)
        values = [row.economic_cycle_index for row in rows if row.country_id == "TST"]
        self.assertGreater(len(set(round(value, 5) for value in values)), 2)

    def test_high_divorce_rate_creates_divorce_events(self):
        world = FamilyWorld(family_scenario(base_divorce_rate=1.0))
        row = world.step()[0]
        self.assertGreater(row.divorces, 0)

    def test_chronic_disease_creates_care_and_medical_burden(self):
        world = FamilyWorld(
            family_scenario(
                chronic_disease_base_rate=1.0,
                healthcare_access=0.0,
                medical_cost_burden=1.0,
                public_long_term_care=0.0,
            )
        )
        world._health_and_care()
        self.assertTrue(any(person.chronic_condition for person in world.living_people))
        self.assertTrue(any(home.annual_medical_spending > 0 for home in world.households.values()))
        self.assertTrue(any(home.care_burden > 0 for home in world.households.values()))

    def test_public_long_term_care_reduces_household_burden(self):
        unsupported = FamilyWorld(
            family_scenario(seed=91, chronic_disease_base_rate=1.0, public_long_term_care=0.0)
        )
        supported = FamilyWorld(
            family_scenario(seed=91, chronic_disease_base_rate=1.0, public_long_term_care=1.0)
        )
        unsupported._health_and_care()
        supported._health_and_care()
        unsupported_total = sum(home.care_burden for home in unsupported.households.values())
        supported_total = sum(home.care_burden for home in supported.households.values())
        self.assertLess(supported_total, unsupported_total)

    def test_formal_childcare_reduces_childcare_gap(self):
        scarce = FamilyWorld(
            family_scenario(seed=121, childcare_capacity=0.0, grandparent_care_availability=0.0)
        )
        supplied = FamilyWorld(
            family_scenario(seed=121, childcare_capacity=1.0, grandparent_care_availability=0.0)
        )
        scarce._update_childcare_support()
        supplied._update_childcare_support()
        scarce_gaps = [home.childcare_gap for home in scarce.households.values() if home.childcare_gap]
        supplied_gaps = [home.childcare_gap for home in supplied.households.values() if home.childcare_gap]
        self.assertTrue(scarce_gaps)
        self.assertLess(sum(supplied_gaps), sum(scarce_gaps))

    def test_grandparent_can_supply_childcare(self):
        world = FamilyWorld(
            family_scenario(childcare_capacity=0.0, grandparent_care_availability=1.0)
        )
        home = next(iter(world.households.values()))
        grandmother = world._new_person(home, 66, "F")
        mother = world._new_person(home, 30, "F")
        mother.mother_id = grandmother.id
        world._new_person(home, 2, "M", mother_id=mother.id)
        world._update_childcare_support()
        self.assertGreater(home.grandparent_care_coverage, 0.0)
        self.assertLess(home.childcare_gap, 1.0)

    def test_dynamic_investment_responds_to_observed_achievement(self):
        world = FamilyWorld(
            family_scenario(dynamic_investment_strength=1.0, investment_need_weight=0.0)
        )
        home = next(
            home
            for home in world.households.values()
            if sum(world.people[pid].age <= 21 for pid in home.member_ids) >= 2
        )
        children = [world.people[pid] for pid in home.member_ids if world.people[pid].age <= 21]
        children[0].observed_achievement = 0.9
        children[1].observed_achievement = 0.1
        for child in children[2:]:
            child.observed_achievement = 0.5
        world._allocate_resources()
        self.assertGreater(children[0].annual_investment, children[1].annual_investment)

    def test_social_norm_sources_are_configurable(self):
        world = FamilyWorld(
            family_scenario(
                social_norm_strength=1.0,
                social_norm_sources={"neighbors": 0.0, "kin": 0.0, "colleagues": 0.0, "media": 1.0},
            )
        )
        baseline = FamilyWorld(family_scenario(social_norm_strength=0.0))
        home = next(iter(world.households.values()))
        self.assertAlmostEqual(
            world._desired_children(home, world.countries["TST"]),
            baseline._desired_children(next(iter(baseline.households.values())), baseline.countries["TST"]),
        )


if __name__ == "__main__":
    unittest.main()
