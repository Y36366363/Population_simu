import unittest

from population_simu.family_config import FamilyScenario, PolicyEra


class FamilyConfigValidationTests(unittest.TestCase):
    def base(self, **simulation):
        return FamilyScenario.from_dict(
            {
                "name": "validation-test",
                "simulation": {"start_year": 2000, "end_year": 2005, **simulation},
                "countries": [
                    {
                        "id": "TST",
                        "name": "测试国",
                        "initial_clans": 2,
                        "initial_development": 0.3,
                        "annual_development_gain": 0.01,
                        "initial_urbanization": 0.4,
                        "annual_urbanization_gain": 0.01,
                        "education_access": 0.5,
                        "cost_of_children": 0.7,
                        "baseline_family_resources": 100,
                        "initial_children_per_family": 2,
                    }
                ],
            }
        )

    def test_rejects_invalid_simulation_ratio(self):
        with self.assertRaises(ValueError):
            self.base(adult_pairing_rate=1.2).validate()

    def test_rejects_unknown_surname_rule(self):
        with self.assertRaises(ValueError):
            self.base(surname_rule="patrilineal").validate()

    def test_rejects_overlapping_policy_eras(self):
        scenario = self.base()
        country = scenario.countries[0]
        scenario = FamilyScenario(
            name=scenario.name,
            simulation=scenario.simulation,
            countries=(country.__class__(**{
                **country.__dict__,
                "policies": (
                    PolicyEra(start_year=2000, end_year=2002, name="a"),
                    PolicyEra(start_year=2002, end_year=None, name="b"),
                ),
            }),),
        )
        with self.assertRaises(ValueError):
            scenario.validate()

    def test_rejects_invalid_fertility_age_profile(self):
        scenario = self.base()
        country = scenario.countries[0]
        invalid_country = country.__class__(**{**country.__dict__, "fertility_peak_age": 45})
        scenario = FamilyScenario(
            name=scenario.name,
            simulation=scenario.simulation,
            countries=(invalid_country,),
        )
        with self.assertRaises(ValueError):
            scenario.validate()
