"""Report frozen household ablations with paired uncertainty and strata.

This report deliberately treats the household variants as mechanism models.  It
does not relabel their aggregate ASFR adapter as a formal age-marital-parity
hazard estimate or as a causal counterfactual.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from random import Random
from statistics import mean


REGIONS = {
    "Northeast": {"09", "23", "25", "33", "34", "36", "42", "44", "50"},
    "Midwest": {"17", "18", "19", "20", "26", "27", "29", "31", "38", "39", "46", "55"},
    "South": {"01", "05", "10", "11", "12", "13", "21", "22", "24", "28", "37", "40", "45", "47", "48", "51", "54"},
    "West": {"02", "04", "06", "08", "15", "16", "30", "32", "35", "41", "49", "53", "56"},
}


def region_for_state(state: str) -> str:
    code = str(state).zfill(2)
    return next((name for name, codes in REGIONS.items() if code in codes), "Unknown")


def error(actual: float, predicted: float) -> dict[str, float]:
    delta = predicted - actual
    return {
        "absolute_error": abs(delta),
        "squared_error": delta * delta,
        "absolute_percentage_error": abs(delta) / max(abs(actual), 1e-9),
        "signed_error": delta,
    }


def summarize(records: list[dict[str, float]]) -> dict[str, float | int]:
    if not records:
        return {"n": 0, "mae": None, "rmse": None, "mape": None, "bias": None}
    return {
        "n": len(records),
        "mae": mean(r["absolute_error"] for r in records),
        "rmse": (mean(r["squared_error"] for r in records)) ** 0.5,
        "mape": mean(r["absolute_percentage_error"] for r in records),
        "bias": mean(r["signed_error"] for r in records),
    }


def paired_bootstrap(values: list[float], *, seed: int, draws: int) -> dict[str, float | int]:
    if not values:
        return {"n": 0, "draws": draws, "mean": None, "lower_95": None, "upper_95": None}
    rng = Random(seed)
    samples = [mean(values[rng.randrange(len(values))] for _ in values) for _ in range(draws)]
    samples.sort()
    return {
        "n": len(values),
        "draws": draws,
        "mean": mean(values),
        "lower_95": samples[int(0.025 * (draws - 1))],
        "upper_95": samples[int(0.975 * (draws - 1))],
    }


def load_panel(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["year"] = int(row["year"])
        row["state"] = str(row.get("state", "")).zfill(2)
        row["asfr_15_44"] = float(row["asfr_15_44"])
        row["region"] = region_for_state(row["state"])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260919)
    parser.add_argument("--draws", type=int, default=4000)
    args = parser.parse_args()
    panel = load_panel(args.panel)
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    variants = ["full", "no_housing", "no_household"]
    test_years = [int(y) for y in artifact.get("untouched_test_years", artifact.get("test_years", []))]
    observed = {(str(r["entity"]), int(r["year"])): r for r in panel if int(r["year"]) in test_years}
    prediction = {}
    for row in artifact.get("rows", []):
        if row.get("variant") not in variants:
            continue
        key = (str(row["entity"]), int(row["year"]))
        value = row.get("asfr_15_44", row.get("asfr_scaled"))
        if value is not None:
            prediction[(row["variant"], key)] = float(value)
    units = []
    for key, actual_row in sorted(observed.items()):
        for variant in variants:
            pred = prediction.get((variant, key))
            if pred is None:
                raise ValueError(f"artifact 缺少严格键 {variant}/{key}")
            units.append({
                "entity": key[0], "year": key[1], "state": str(actual_row["state"]),
                "region": str(actual_row["region"]), "actual": float(actual_row["asfr_15_44"]),
                "variant": variant, "predicted": pred,
                **error(float(actual_row["asfr_15_44"]), pred),
            })

    overall = {variant: summarize([r for r in units if r["variant"] == variant]) for variant in variants}
    strata = {}
    for dimension in ("region", "state", "year"):
        strata[dimension] = {}
        groups = sorted({str(r[dimension]) for r in units})
        for group in groups:
            strata[dimension][group] = {
                variant: summarize([r for r in units if r["variant"] == variant and str(r[dimension]) == group])
                for variant in variants
            }

    # Same state-year units are reused for every contrast: this is paired, not
    # an independent-samples interval.
    paired = {}
    full_by_key = {(r["entity"], r["year"]): r for r in units if r["variant"] == "full"}
    for challenger in ("no_housing", "no_household"):
        challenger_by_key = {(r["entity"], r["year"]): r for r in units if r["variant"] == challenger}
        differences = [challenger_by_key[key]["absolute_percentage_error"] - row["absolute_percentage_error"]
                       for key, row in full_by_key.items()]
        paired[f"{challenger}_minus_full_mape"] = {
            "metric": "absolute_percentage_error difference",
            "lower_is_better": True,
            **paired_bootstrap(differences, seed=args.seed + len(paired), draws=args.draws),
        }

    payload = {
        "version": "2026-09-19",
        "kind": "household_mechanism_ablation_report",
        "scientific_status": "validated_for_predictive_interface",
        "formal_hazard_replay_ready": False,
        "panel": str(args.panel),
        "source_artifact": str(args.artifact),
        "calibration_years": list(range(2010, 2018)),
        "untouched_test_years": test_years,
        "prediction_models": ["naive_trend", "cohort_proxy", "reduced_form"],
        "mechanism_models": variants,
        "overall": overall,
        "stratified_errors": strata,
        "paired_confidence_intervals": paired,
        "bootstrap": {"seed": args.seed, "draws": args.draws, "unit": "state-year"},
        "interpretation": {
            "calibration": "household adapter parameters were fitted only on 2010-2017; test years are untouched.",
            "prediction": "naive_trend, cohort_proxy and reduced_form remain the short-horizon predictive baselines.",
            "mechanism": "full/no_housing/no_household are aggregate-ASFR mechanism diagnostics, not formal age-marital-parity hazards.",
            "causal_counterfactual": "not identified; paired intervals quantify predictive differences only.",
        },
        "limitations": [
            "Age, marital-status and parity exposure denominators are not available in the frozen panel.",
            "The 2020 test year remains excluded from the primary untouched test because ACS5 housing is a sensitivity input.",
        ],
        "units": units,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "units": len(units), "test_years": test_years,
                      "paired": paired}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
