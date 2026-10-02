"""Run expanding-window checks; these are not a fixed-2017 holdout evaluation."""
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
                        help="optional external artifact; must precede every rolling forecast unless explicitly auditing overlap")
    parser.add_argument("--allow-test-overlap", action="store_true",
                        help="仅用于外部验证；允许 artifact 包含某个 rolling 训练端点后的年份，并明确标记")
    parser.add_argument("--include-2020-sensitivity", action="store_true",
                        help="把带 ACS5 住房估计的 2020 面板作为敏感性测试年记录；不改变主规格")
    parser.add_argument("--residual-uncertainty", action="store_true",
                        help="加入fold训练期相邻变化尺度的高斯预测误差；有限抽样会使中位数点预测波动，机制不变")
    parser.add_argument("--conditional-housing-replay", action="store_true",
                        help="仅用于条件回放：household 读取预测年份的真实住房；其他基准无该信息，不能解释为公平事前预测比较")
    args = parser.parse_args()
    with args.panel.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["year"] = int(row["year"])
        row["asfr_15_44"] = float(row["asfr_15_44"])
        row["region"] = region_for_state(row.get("state", ""))
    # Keep the ACS5 sensitivity year out even if a combined panel was supplied.
    if not args.include_2020_sensitivity:
        rows = [row for row in rows if row["year"] != 2020]
    fold_sets = {
        initial: rolling_origin_splits(rows, initial_train_years=initial,
                                       horizon=1, group="entity")
        for initial in args.initial
    }
    fold_designs = {
        str(initial): [
            {
                "train_years": sorted({int(row["year"]) for row in train}),
                "train_end_year": max(int(row["year"]) for row in train),
                "test_years": sorted({int(row["year"]) for row in test}),
                "calendar_horizons": {
                    str(year): year - max(int(row["year"]) for row in train)
                    for year in sorted({int(row["year"]) for row in test})
                },
                "train_rows": len(train), "test_rows": len(test),
            }
            for train, test in folds
        ]
        for initial, folds in fold_sets.items()
    }
    future_housing = (
        {(str(r["entity"]), int(r["year"])): float(r["housing_cost_burden"])
         for r in rows if r.get("housing_cost_burden") not in (None, "")}
        if args.conditional_housing_replay else None
    )
    external_calibration = None
    external_future_years = []
    if args.household_calibration_json:
        artifact = json.loads(args.household_calibration_json.read_text(encoding="utf-8"))
        earliest_train_end = min(fold["train_end_year"]
                                 for folds in fold_designs.values() for fold in folds)
        artifact_years = artifact.get("years", artifact.get("calibration_years", ()))
        if not artifact_years:
            raise SystemExit("外部校准 artifact 缺少 years/calibration_years，无法审计训练时间范围")
        external_future_years = sorted(int(year) for year in artifact_years
                                       if int(year) > earliest_train_end)
        if external_future_years and not args.allow_test_overlap:
            raise SystemExit(f"外部校准 artifact 晚于最早 rolling 训练端点 {earliest_train_end}：{external_future_years}；"
                             "如仅做外部验证，请显式加入 --allow-test-overlap")
        external_calibration = HouseholdCalibration.from_dict(artifact)
    models = {
        "naive_trend": fixed_trend_runner("asfr_15_44"),
        "cohort_proxy": wpp_style_runner("asfr_15_44"),
        "reduced_form": reduced_form_runner(),
        "household": household_simulator_runner(calibration=external_calibration,
                                                 future_housing=future_housing),
        "household_no_housing": household_simulator_runner(
            calibration=external_calibration, use_housing=False,
            future_housing=future_housing),
        "household_no_household": household_simulator_runner(
            calibration=external_calibration, use_household_mechanisms=False),
    }
    reports = {}
    for initial in args.initial:
        reports[str(initial)] = compare_models_rolling(
            rows, models, initial_train_years=initial, horizon=1,
            metric="asfr_15_44", replicates=args.replicates,
            bootstrap_draws=args.bootstrap_draws, baseline="naive_trend",
            residual_uncertainty=args.residual_uncertainty,
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
        folds = fold_sets[initial]
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
        "evaluation_design": "expanding_window",
        "fixed_2017_holdout": False,
        "training_years_vary_by_fold": True,
        "calibration_years": sorted({year for folds in fold_designs.values()
                                     for fold in folds for year in fold["train_years"]}),
        "untouched_test_years": [],
        "evaluated_years": sorted({year for folds in fold_designs.values()
                                   for fold in folds for year in fold["test_years"]}),
        "fold_designs": fold_designs,
        "horizon_definition": "one observed target year per fold; calendar horizons may exceed one when observations are missing",
        "metric_definitions": {
            "rmse": "sqrt(sum of squared errors / number of state-year predictions), pooled within each fold and across folds; interval resamples whole folds",
            "mape": "mean entity MAPE per fold, then mean across folds",
        },
        "sensitivity_test_years": [2020] if args.include_2020_sensitivity else [],
        "excluded_years": [] if args.include_2020_sensitivity else [2020],
        "reports": reports,
        "paired_vs_naive": paired,
        "error_strata": strata_reports,
        "age_strata": {"available": "age" in rows[0] if rows else False,
                       "note": "需要年龄分层观测和年龄分层预测；当前 ASFR 面板不具备"},
        "external_household_calibration": str(args.household_calibration_json)
        if args.household_calibration_json else None,
        "test_overlap_allowed": bool(args.allow_test_overlap),
        "external_calibration_future_years": external_future_years,
        "information_set": {
            "conditional_housing_replay": bool(args.conditional_housing_replay),
            "future_observed_housing_models": ["household"] if args.conditional_housing_replay else [],
            "equal_observed_information": not args.conditional_housing_replay and not external_future_years,
            "external_calibration_uses_future_of_early_folds": bool(external_future_years),
            "note": ("household uses target-year observed housing; baselines do not. Conditional replay, not equal-information ex-ante forecasting."
                     if args.conditional_housing_replay else
                     "Default runners use only each fold's training observations; later folds may train on earlier evaluation years."),
        },
        "interpretation": "逐步扩窗回测；早期测试年可进入后续训练，不是固定2017起点的 untouched holdout。不同 initial 的重复目标年份不是独立证据。2020若纳入仅作ACS5敏感性；不是因果估计。",
        "uncertainty": {
            "residual_bootstrap": bool(args.residual_uncertainty),
            "common_residual_noise_across_models": False,
            "calendar_horizon_adjusted": False,
            "note": "若开启，区间来自各fold训练期州级相邻观测变化的高斯误差。残差seed按模型名区分，有限抽样的中位数点预测会波动；尺度尚未按日历跨度校准。",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
