import tempfile
import unittest
from pathlib import Path

from population_simu.fertility_panel import (
    merge_wonder_births_with_denominator,
    merge_stratified_wonder_births,
    read_wonder_tsv,
)


class FertilityPanelTests(unittest.TestCase):
    def test_merge_computes_asfr_and_parses_commas(self):
        rows = merge_wonder_births_with_denominator(
            [{"Entity": "Alabama", "State": "01", "Year": "2021", "Births": "50"}],
            [{"State": "01", "Year": "2021", "Female15_44": "1,000"}],
        )
        self.assertEqual(rows[0]["entity"], "Alabama")
        self.assertEqual(rows[0]["state"], "01")
        self.assertEqual(rows[0]["asfr_15_44"], 50.0)

    def test_duplicate_or_missing_denominator_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_wonder_births_with_denominator(
                [{"State": "Alabama", "Year": 2021, "Births": 10}],
                [
                    {"State": "Alabama", "Year": 2021, "Female15_44": 100},
                    {"State": "Alabama", "Year": 2021, "Female15_44": 100},
                ],
            )
        with self.assertRaises(ValueError):
            merge_wonder_births_with_denominator(
                [{"State": "Alabama", "Year": 2021, "Births": 10}],
                [{"State": "Alaska", "Year": 2021, "Female15_44": 100}],
            )

    def test_read_wonder_tsv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "births.tsv"
            path.write_text("State\tYear\tBirths\nAlabama\t2021\t50\n", encoding="utf-8")
            self.assertEqual(read_wonder_tsv(path)[0]["State"], "Alabama")

    def test_stratified_merge_requires_matching_parity_exposure(self):
        births = [{"State": "01", "Year": 2021, "Age": "30-34",
                   "Marital Status": "Married", "Live Birth Order": "01", "Births": 20}]
        exposure = [{"State": "01", "Year": 2021, "Age": "30-34",
                     "Marital Status": "Married", "Live Birth Order": "01", "Exposure": 400}]
        row = merge_stratified_wonder_births(births, exposure)[0]
        self.assertAlmostEqual(row["rate_per_1000"], 50.0)
        with self.assertRaises(ValueError):
            merge_stratified_wonder_births(births, [{**exposure[0], "Live Birth Order": "all"}])


if __name__ == "__main__":
    unittest.main()
