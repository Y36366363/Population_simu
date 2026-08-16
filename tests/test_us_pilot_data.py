import csv
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "observed" / "us_2021"


class USPilotDataTests(unittest.TestCase):
    def test_single_age_population_has_both_sexes(self):
        with (DATA / "us_population_single_age_sex_2021.csv").open() as file:
            rows = list(csv.DictReader(file))
        self.assertEqual({row["sex"] for row in rows}, {"F", "M"})
        self.assertEqual({int(row["age"]) for row in rows}, set(range(101)))

    def test_cdc_life_tables_are_complete_single_age(self):
        for sex in ("male", "female"):
            with (DATA / f"us_life_table_{sex}_2021.csv").open() as file:
                rows = list(csv.DictReader(file))
            self.assertEqual({int(row["age"]) for row in rows}, set(range(101)))
            self.assertTrue(all(0 <= float(row["death_rate"]) <= 1 for row in rows))


if __name__ == "__main__":
    unittest.main()
