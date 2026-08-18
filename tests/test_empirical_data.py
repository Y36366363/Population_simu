import unittest

from population_simu.empirical_data import parse_acs_housing_response


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


if __name__ == "__main__":
    unittest.main()
