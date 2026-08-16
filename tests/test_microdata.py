import unittest

from population_simu.microdata import (
    fertility_observations_from_weighted_rows,
    migration_records_from_pums,
)


class MicrodataTests(unittest.TestCase):
    def test_pums_weights_make_age_sex_od_hazard(self):
        rows = [
            {"AGEP": "20", "SEX": "1", "ST": "06", "MIGSP": "12", "PWGTP": "100"},
            {"AGEP": "20", "SEX": "1", "ST": "12", "MIGSP": "12", "PWGTP": "300"},
        ]
        records = migration_records_from_pums(rows, year=2021)
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0].flow, 100)
        self.assertAlmostEqual(records[0].exposure, 400)
        self.assertAlmostEqual(records[0].hazard, 0.25)

    def test_weighted_births_divided_by_exposure(self):
        births = [{"age": "25", "marital": "married", "parity": "first", "weight": "10"}]
        exposure = [{"age": "25", "marital": "married", "parity": "first", "weight": "100"}]
        rows = fertility_observations_from_weighted_rows(
            births, exposure, country="United States", year=2021)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0].rate, 0.1)


if __name__ == "__main__":
    unittest.main()
