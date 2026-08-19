import unittest

from population_simu.empirical_data import parse_acs_housing_response, parse_acs_summary_file, validate_housing_panel


class EmpiricalDataTests(unittest.TestCase):
    def test_acs_housing_parser_computes_burden_share(self):
        payload = [["NAME", "B25070_001E", "B25070_007E", "B25070_008E",
                    "B25070_009E", "B25070_010E", "state"],
                   ["Test", "100", "10", "10", "10", "20", "99"]]
        rows = parse_acs_housing_response(payload, 2017)
        self.assertAlmostEqual(rows[0]["housing_cost_burden"], 0.5)
        self.assertEqual(rows[0]["year"], 2017)

    def test_acs_housing_parser_rejects_missing_variable(self):
        with self.assertRaises(ValueError):
            parse_acs_housing_response([["NAME", "state"], ["Test", "99"]], 2017)

    def test_summary_file_parser_keeps_only_state_geographies(self):
        from tempfile import NamedTemporaryFile
        content = ("GEO_ID|B25070_E001|B25070_E007|B25070_E008|B25070_E009|B25070_E010\n"
                   "0400000US06|100|10|10|10|20\n0100000US|100|10|10|10|20\n")
        with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".dat") as file:
            file.write(content); file.flush()
            rows = parse_acs_summary_file(file.name, 2021)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], "06")

    def test_housing_panel_validation_is_separate_from_study_readiness(self):
        rows = [{"entity": "A", "state": "01", "year": 2021,
                 "housing_cost_burden": 0.4}]
        report = validate_housing_panel(rows, expected_min_states=1)
        self.assertTrue(report["ok"])
        self.assertEqual(report["years"], [2021])


if __name__ == "__main__":
    unittest.main()
