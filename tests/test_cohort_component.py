import unittest

from population_simu.cohort_component import CohortComponentModel
from population_simu.hazards import AgeRateProfile


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


if __name__ == "__main__":
    unittest.main()
