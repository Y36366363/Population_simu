import unittest

from population_simu.family_config import FamilyScenario, PolicyEra, Region


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

    def test_accepts_age_profiles_and_matrix(self):
        scenario = self.base()
        country = scenario.countries[0]
        configured = country.__class__(
            **{
                **country.__dict__,
                "fertility_age_profile": ((20, 0.25), (30, 1.0), (40, 0.2)),
                "mortality_age_profile": ((0, 0.01), (80, 0.2)),
                "migration_matrix": {"TST-urban": {"TST-rural": 1.0}},
                "regions": (
                    Region(
                        id="TST-urban", name="城市", urban=True,
                        amenity_supply=0.5, school_supply=0.8,
                        childcare_supply=0.7, medical_supply=0.6,
                        transport_access=0.9, safety_level=0.8,
                    ),
                    Region(id="TST-rural", name="乡村", urban=False),
                ),
            }
        )
        FamilyScenario(
            name=scenario.name,
            simulation=scenario.simulation,
            countries=(configured,),
        ).validate()

    def test_rejects_invalid_region_amenity_supply(self):
        scenario = self.base()
        country = scenario.countries[0]
        invalid = country.__class__(
            **{
                **country.__dict__,
                "regions": (Region(
                    id="r1", name="地区", urban=True, amenity_supply=1.2
                ),),
            }
        )
        with self.assertRaises(ValueError):
            FamilyScenario(
                name=scenario.name,
                simulation=scenario.simulation,
                countries=(invalid,),
            ).validate()

    def test_rejects_unknown_social_norm_source(self):
        scenario = self.base()
        country = scenario.countries[0]
        invalid = country.__class__(
            **{**country.__dict__, "social_norm_sources": {"neighbors": 1.0, "telepathy": 0.1}}
        )
        with self.assertRaises(ValueError):
            FamilyScenario(
                name=scenario.name,
                simulation=scenario.simulation,
                countries=(invalid,),
            ).validate()
