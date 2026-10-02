import csv
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import continue_frozen_residual_validation as continuation


class FrozenResidualContinuationTests(unittest.TestCase):
    def make_rows(self):
        return [{"state": state, "year": year,
                 "asfr_15_44": 60 - (year - 2010) * .5}
                for state in sorted(continuation.STATES) for year in continuation.YEARS]

    def read_rows(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "panel.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["state", "year", "asfr_15_44"])
                writer.writeheader()
                writer.writerows(rows)
            return continuation.load_frozen_panel(path)

    def test_exact_key_contract_rejects_duplicate_even_with_correct_count(self):
        rows = self.make_rows()
        self.assertEqual(len(self.read_rows(rows)), 550)
        rows[-1] = rows[-2].copy()
        with self.assertRaisesRegex(ValueError, "panel key mismatch"):
            self.read_rows(rows)

    def test_rejects_missing_extra_and_nonfinite_outcomes(self):
        for kind in ("missing", "extra_state", "nan", "inf", "negative"):
            with self.subTest(kind=kind):
                rows = self.make_rows()
                if kind == "missing":
                    rows.pop()
                elif kind == "extra_state":
                    rows[-1]["state"] = "11"
                else:
                    rows[-1]["asfr_15_44"] = {"nan": "nan", "inf": "inf", "negative": -1}[kind]
                with self.assertRaises(ValueError):
                    self.read_rows(rows)

    def test_test_outcome_perturbation_cannot_change_fit_or_forecast(self):
        rows = self.read_rows(self.make_rows())
        perturbed = [dict(row, value=row["value"] * 10) if row["year"] > 2017 else dict(row)
                     for row in rows]
        fit, residuals = continuation.fit_inputs(rows)
        other_fit, other_residuals = continuation.fit_inputs(perturbed)
        self.assertEqual((fit, residuals), (other_fit, other_residuals))
        history = [row for row in fit if row["state"] == "01"]
        # Four calendar years, despite the absent 2020 observation.
        self.assertEqual(continuation.residual_model.point_forecast(history, 2021), 54.5)
        observed = [row for row in rows if row["state"] == "01" and row["year"] == 2021]
        altered = [dict(row, value=1000) for row in observed]
        original = continuation.residual_model.summarize_candidate(
            observed, fit, residuals, "state_shrunk", "normal", 20, 123)
        changed = continuation.residual_model.summarize_candidate(
            altered, other_fit, other_residuals, "state_shrunk", "normal", 20, 123)
        for field in ("point", "interval_lower", "interval_upper"):
            self.assertEqual(original["scores"][0][field], changed["scores"][0][field])
        self.assertNotEqual(original["crps"], changed["crps"])


if __name__ == "__main__":
    unittest.main()
