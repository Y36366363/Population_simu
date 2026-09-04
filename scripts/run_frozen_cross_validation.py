"""Run pre-specified rolling-origin robustness checks for the frozen study."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import defaultdict

from population_simu.benchmarks import (
    compare_models_rolling, fixed_trend_runner, household_simulator_runner,
    reduced_form_runner, wpp_style_runner, paired_model_comparison,
    _median_forecast,
)
from population_simu.calibration import replay_errors_by_group, rolling_origin_splits
from population_simu.household_calibration import HouseholdCalibration


REGIONS = {
    "Northeast": {"09", "23", "25", "33", "34", "36", "42", "44", "50"},
    "Midwest": {"17", "18", "19", "20", "26", "27", "29", "31", "38", "39", "46", "55"},
    "South": {"01", "05", "10", "11", "12", "13", "21", "22", "24", "28", "37", "40", "45", "47", "48", "51", "54"},
    "West": {"02", "04", "06", "08", "15", "16", "30", "32", "35", "41", "49", "53", "56"},
}
def region_for_state(state: str) -> str:
    code = str(state).zfill(2)
    return next((name for name, codes in REGIONS.items() if code in codes), "Unknown")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial", type=int, nargs="+", default=[6, 7, 8])
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    parser.add_argument("--household-calibration-json", type=Path,
                        help="optional external artifact; do not use if it overlaps the untouched test")
    parser.add_argument("--allow-test-overlap", action="store_true",
                        help="仅用于外部验证；允许 artifact 年份与 test 重叠并在报告中标记")
    args = parser.parse_args()
    with args.panel.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["year"] = int(row["year"])
        row["asfr_15_44"] = float(row["asfr_15_44"])
        row["region"] = region_for_state(row.get("state", ""))
    external_calibration = None
    if args.household_calibration_json:
        artifact = json.loads(args.household_calibration_json.read_text(encoding="utf-8"))
        overlap = set(artifact.get("years", ())) & {2018, 2019, 2021}
        if overlap and not args.allow_test_overlap:
            raise SystemExit(f"外部校准 artifact 与 untouched test 重叠：{sorted(overlap)}；"
                             "如仅做外部验证，请显式加入 --allow-test-overlap")
        external_calibration = HouseholdCalibration.from_dict(artifact)
    models = {
        "naive_trend": fixed_trend_runner("asfr_15_44"),
        "cohort_proxy": wpp_style_runner("asfr_15_44"),
        "reduced_form": reduced_form_runner(),
        "household": household_simulator_runner(calibration=external_calibration),
        "household_no_housing": household_simulator_runner(
            calibration=external_calibration, use_housing=False),
        "household_no_household": household_simulator_runner(
            calibration=external_calibration, use_household_mechanisms=False),
    }
    reports = {}
    for initial in args.initial:
        reports[str(initial)] = compare_models_rolling(
            rows, models, initial_train_years=initial, horizon=1,
            metric="asfr_15_44", replicates=args.replicates,
            bootstrap_draws=args.bootstrap_draws, baseline="naive_trend",
        )
    paired = {}
    for initial, report in reports.items():
        paired[initial] = {
            name: paired_model_comparison(report, "naive_trend", name,
                                          metric="mape", bootstrap_draws=args.bootstrap_draws)
            for name in models if name != "naive_trend"
        }

    # State and Census-region error strata are computed from each fold's point
    # forecasts. Age strata are reported as unavailable unless the panel carries
    # an age field; aggregate ASFR cannot be retrofitted into age-specific error.
    strata_reports = {}
    for initial in args.initial:
        folds = rolling_origin_splits(rows, initial_train_years=initial,
                                      horizon=1, group="entity")
        by_model: dict[str, dict[str, list[float]]] = {
            name: defaultdict(list) for name in models
        }
        for fold_index, (train, test) in enumerate(folds):
            years = sorted({int(row["year"]) for row in test})
            for name, runner in models.items():
                samples = [list(runner(train, years, fold_index * args.replicates + i))
                           for i in range(args.replicates)]
                point = _median_forecast(samples, "asfr_15_44")
                point_by_entity = {str(row["entity"]): row for row in point}
                for row in test:
                    forecast = point_by_entity.get(str(row["entity"]))
                    if forecast is None:
                        continue
                    simulated = dict(forecast); simulated["region"] = row["region"]
                    observed = dict(row); observed["region"] = row["region"]
                    errors = replay_errors_by_group([observed], [simulated],
                                                     group="region", metrics=("asfr_15_44",))
                    by_model[name][str(row["region"])].append(
                        errors[str(row["region"])]["asfr_15_44"]["mape"])
                    by_model[name][str(row["entity"])].append(
                        replay_errors_by_group([observed], [simulated], metrics=("asfr_15_44",))
                        [str(row["entity"])]["asfr_15_44"]["mape"])
        strata_reports[str(initial)] = {
            name: {group: {"mean_mape": sum(values) / len(values), "n": len(values)}
                   for group, values in groups.items()}
            for name, groups in by_model.items()
        }

    result = {
        "panel": str(args.panel),
        "calibration_years": list(range(2010, 2018)),
        "untouched_test_years": [2018, 2019, 2021],
        "excluded_years": [2020],
        "reports": reports,
        "paired_vs_naive": paired,
        "error_strata": strata_reports,
        "age_strata": {"available": "age" in rows[0] if rows else False,
                       "note": "需要年龄分层观测和年龄分层预测；当前 ASFR 面板不具备"},
        "external_household_calibration": str(args.household_calibration_json)
        if args.household_calibration_json else None,
        "test_overlap_allowed": bool(args.allow_test_overlap),
        "interpretation": "窗口稳健性和预测比较，不是因果估计；不据此增加社会机制",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
