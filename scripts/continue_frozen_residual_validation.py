"""Replay an already selected residual model, without selecting it again.

This is a diagnostic replication on previously inspected outcomes, not a new
untouched test. The legacy outcome column contains an aggregate GFR-like rate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path

import compare_calibration_residual_distributions as residual_model


ROOT = Path(__file__).resolve().parents[1]
YEARS = tuple(range(2010, 2020)) + (2021,)
STATES = set.union(*residual_model.REGIONS.values()) - {"11"}


def load_frozen_panel(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        raw = list(csv.DictReader(handle))
    rows = []
    for item in raw:
        state = item["state"].zfill(2)
        year = int(item["year"])
        value = float(item["asfr_15_44"])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid outcome for {(state, year)}")
        rows.append({"state": state, "year": year, "value": value,
                     "region": residual_model.region_for_state(state)})
    keys = Counter((row["state"], row["year"]) for row in rows)
    expected = {(state, year) for state in STATES for year in YEARS}
    duplicates = sorted(key for key, count in keys.items() if count != 1)
    missing = sorted(expected - set(keys))
    extra = sorted(set(keys) - expected)
    if duplicates or missing or extra:
        raise ValueError(f"panel key mismatch: duplicate={duplicates[:5]}, "
                         f"missing={missing[:5]}, extra={extra[:5]}")
    # Preserve the source ordering to reproduce the archived random stream.
    return rows


def fit_inputs(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    calibration = [row for row in rows if 2010 <= row["year"] <= 2017]
    residuals = residual_model.rolling_calibration_residuals(calibration)
    if any(row["target_year"] > 2017 for row in residuals):
        raise ValueError("residual uses post-calibration outcome")
    return calibration, residuals


def replay(rows: list[dict], selection: dict, *, draws: int, seed: int) -> dict:
    if draws < 2:
        raise ValueError("draws must be at least 2")
    chosen = selection["calibration_validation"]
    scale, distribution = chosen["selected_scale"], chosen["selected_distribution"]
    if scale not in {"pooled", "region", "state_shrunk"}:
        raise ValueError("unknown selected scale")
    if distribution not in {"normal", "empirical_quantile", "bootstrap_residual"}:
        raise ValueError("unknown selected distribution")
    if selection["calibration_years"] != list(range(2010, 2018)):
        raise ValueError("selection calibration years changed")
    calibration, residuals = fit_inputs(rows)
    observed = [row for row in rows if row["year"] in residual_model.TEST_YEARS]
    result = residual_model.summarize_candidate(
        observed, calibration, residuals, scale, distribution, draws, seed)
    return {
        "kind": "fixed_method_diagnostic_replication",
        "evaluation_design": "fixed_2017_origin_previously_inspected_holdout",
        "calibration_years": list(range(2010, 2018)),
        "evaluation_years": list(residual_model.TEST_YEARS),
        "calendar_horizons": [1, 2, 4],
        "method_reselected": False,
        "selected_scale": scale,
        "selected_distribution": distribution,
        "draws_per_state_year": draws,
        "seed": seed,
        "residual_count": len(residuals),
        "residual_target_max_year": max(row["target_year"] for row in residuals),
        "panel_audit": {"rows": len(rows), "states": len({r["state"] for r in rows}),
                        "unique_state_years": len({(r["state"], r["year"]) for r in rows})},
        "outcome_note": "Legacy asfr_15_44 is all live births / female population 15-44 * 1000, per source manifest; not an age-specific fertility rate.",
        "limitations": [
            "Previously inspected evaluation years; not new independent evidence or a fresh untouched test.",
            "Earlier method selection evaluated one-year validation horizons only; 2/4-year performance was not selection-validated.",
            "Intervals describe the trend baseline with residual uncertainty, not FamilyWorld or causal effects.",
            "State bootstrap does not account for every source of shared national/year shocks.",
        ],
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "data/observed/us_2021/us_research_panel_2010_2021_comparable.csv")
    parser.add_argument("--selection-artifact", type=Path, default=ROOT / "docs/artifacts/residual_uncertainty_comparison_2026-09-30.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260929 + 88001)
    args = parser.parse_args()
    selection = json.loads(args.selection_artifact.read_text())
    report = replay(load_frozen_panel(args.panel), selection, draws=args.draws, seed=args.seed)
    paths = [args.panel, args.selection_artifact, Path(__file__),
             Path(residual_model.__file__),
             ROOT / "data/observed/us_2021/us_fertility_manifest.json"]
    report["source_sha256"] = {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
                               hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    previous = selection["final_test_result_selected_once"]
    report["difference_from_archived_result"] = {
        metric: report["result"][metric] - previous[metric]
        for metric in ("mape", "rmse", "crps", "coverage", "mean_interval_width")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output),
                      "difference_from_archived_result": report["difference_from_archived_result"],
                      "by_year": report["result"]["by_year"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
