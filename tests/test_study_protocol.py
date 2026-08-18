import unittest

from population_simu.study_protocol import FERTILITY_STUDY, split_study_panel, validate_empirical_panel


class StudyProtocolTests(unittest.TestCase):
    def test_split_has_untouched_years(self):
        rows = [{"entity": "CA", "year": year, "asfr_15_44": 50,
                 "housing_cost_burden": 0.3, "childcare_supply": 0.4}
                for year in range(2007, 2022)]
        calibration, test = split_study_panel(rows)
        self.assertEqual(min(int(row["year"]) for row in calibration), 2007)
        self.assertEqual(max(int(row["year"]) for row in calibration), 2017)
        self.assertEqual(min(int(row["year"]) for row in test), 2018)
        self.assertEqual(max(int(row["year"]) for row in test), 2021)

    def test_missing_treatment_is_rejected(self):
        with self.assertRaises(ValueError):
            split_study_panel([{"entity": "CA", "year": 2010, "asfr_15_44": 50,
                                "housing_cost_burden": 0.3}])

    def test_design_period_is_valid(self):
        FERTILITY_STUDY.validate()

    def test_panel_validator_detects_duplicate_state_year(self):
        row = {"entity": "CA", "year": 2010, "asfr_15_44": 50,
               "births_15_44": 100, "female_15_44": 200,
               "housing_cost_burden": 0.3, "median_gross_rent": 1000,
               "rent_burden_share": 0.3, "childcare_supply": 0.4,
               "under5_formal_care_share": 0.2, "female_employment": 0.6,
               "unemployment": 0.08, "education": 0.3, "migration_rate": 0.01}
        report = validate_empirical_panel([row, dict(row)])
        self.assertFalse(report["ok"])
        self.assertEqual(report["duplicate_keys"], [("CA", 2010)])


if __name__ == "__main__":
    unittest.main()
