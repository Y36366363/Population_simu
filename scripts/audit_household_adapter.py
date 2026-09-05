"""Diagnostics for the frozen household forecast adapter and its ablations."""
from __future__ import annotations

import argparse, csv, json
from pathlib import Path
from statistics import mean, pstdev

from population_simu.benchmarks import household_simulator_runner
from population_simu.household_calibration import calibrate_household_parameters


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("panel", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    with args.panel.open(encoding="utf-8-sig", newline="") as h:
        rows = list(csv.DictReader(h))
    for r in rows:
        r["year"] = int(r["year"]); r["asfr_15_44"] = float(r["asfr_15_44"])
        r["housing_cost_burden"] = float(r["housing_cost_burden"])
    cal = calibrate_household_parameters([r for r in rows if r["year"] <= 2017])
    train = [r for r in rows if r["year"] <= 2017]
    years = [2018, 2019, 2021]
    full = household_simulator_runner(calibration=cal, use_housing=True)(train, years, 0)
    no_housing = household_simulator_runner(calibration=cal, use_housing=False)(train, years, 0)
    no_household = household_simulator_runner(calibration=cal, use_household_mechanisms=False)(train, years, 0)
    by_key = {(r["entity"], r["year"]): r["asfr_15_44"] for r in full}
    neutral = {(r["entity"], r["year"]): r["asfr_15_44"] for r in no_housing}
    stripped = {(r["entity"], r["year"]): r["asfr_15_44"] for r in no_household}
    housing = [r["housing_cost_burden"] for r in train]
    sensitivity = [abs(by_key[k] - neutral[k]) for k in by_key if k in neutral]
    mechanism = [abs(by_key[k] - stripped[k]) for k in by_key if k in stripped]
    result = {
        "panel": str(args.panel), "calibration_years": [2010, 2017],
        "calibration": cal.as_dict(),
        "housing_training": {"mean": mean(housing), "sd": pstdev(housing),
                              "min": min(housing), "max": max(housing)},
        "forecast_pairs": len(by_key),
        "housing_channel_abs_difference_mean": mean(sensitivity) if sensitivity else None,
        "household_mechanism_abs_difference_mean": mean(mechanism) if mechanism else None,
        "interpretation": {
            "scale": "adapter rescales simulated births to the last observed ASFR; this is predictive normalization, not an estimated causal effect",
            "housing": "difference between full and fixed-reference housing forecasts",
            "household": "difference between full World events and deterministic endpoint-trend ablation",
            "limits": "aggregate ASFR cannot identify age, marital or parity mechanisms"
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("forecast_pairs", "housing_channel_abs_difference_mean", "household_mechanism_abs_difference_mean")}, ensure_ascii=False))
    return 0

if __name__ == "__main__": raise SystemExit(main())
