import unittest
import math

from population_simu.cohort_component import CohortComponentModel
from population_simu.hazards import AgeRateProfile
from population_simu.fertility import FertilitySchedule


class CohortComponentTests(unittest.TestCase):
    def test_age_progression_births_and_deaths_close(self):
        model = CohortComponentModel(
            {"A": {"F": [0, 0, 100], "M": [0, 0, 100]}},
            start_year=2000,
            max_age=5,
            fertility_rates={"A": AgeRateProfile((2,), (0.1,))},
            mortality_rates={"A": {
                "F": AgeRateProfile((0,), (0.0,)),
                "M": AgeRateProfile((0,), (0.0,)),
            }},
        )
        before = model.total_population()
        result = model.step()
        self.assertEqual(result.year, 2001)
        self.assertAlmostEqual(result.births, 10.0)
        self.assertAlmostEqual(result.deaths, 0.0)
        self.assertAlmostEqual(model.total_population(), before + result.births)
        self.assertEqual(len(result.age_sex["A"]["F"]), 6)

    def test_migration_matrix_preserves_world_total(self):
        model = CohortComponentModel(
            {"A": {"F": [10], "M": [10]}, "B": {"F": [0], "M": [0]}},
            max_age=2,
            migration_hazards={"A": {"B": 1.0}},
        )
        before = model.total_population()
        result = model.step()
        self.assertAlmostEqual(result.internal_migrations, 20 * (1 - pow(2.718281828, -1)), places=5)
        self.assertAlmostEqual(model.total_population(), before)
        self.assertGreater(result.population_by_region["B"], 0)

    def test_invalid_migration_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            CohortComponentModel({"A": {"F": [1], "M": [1]}},
                                  migration_hazards={"A": {"missing": 0.1}})

    def test_external_node_and_age_specific_migration(self):
        model = CohortComponentModel(
            {"A": {"F": [0, 10], "M": [0, 10]}},
            max_age=2,
            external_nodes=("outside",),
            migration_hazards={"A": {"outside": AgeRateProfile((0, 1), (0.0, 1.0))}},
        )
        before = model.total_population()
        result = model.step()
        self.assertAlmostEqual(result.external_population_by_node["outside"], 20 * (1 - math.exp(-1)))
        self.assertAlmostEqual(model.total_population(), before)

    def test_parity_and_marital_fertility_schedule(self):
        schedule = FertilitySchedule({
            ("married", "first"): AgeRateProfile((20,), (0.2,)),
            ("married", "second"): AgeRateProfile((20,), (0.1,)),
        })
        model = CohortComponentModel(
            {"A": {"F": [0, 0, 100], "M": [0, 0, 100]}}, max_age=3,
            fertility_schedules={"A": schedule},
            fertility_state_weights={"A": {("married", "first"): 0.5,
                                             ("married", "second"): 0.5}},
        )
        self.assertAlmostEqual(model.step().births, 15.0)


if __name__ == "__main__":
    unittest.main()
