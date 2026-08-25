"""Run pre-specified rolling-origin robustness checks for the frozen study."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from population_simu.benchmarks import (
    compare_models_rolling, fixed_trend_runner, household_simulator_runner,
    reduced_form_runner, wpp_style_runner,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial", type=int, nargs="+", default=[6, 7, 8])
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    args = parser.parse_args()
    with args.panel.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["year"] = int(row["year"])
        row["asfr_15_44"] = float(row["asfr_15_44"])
    models = {
        "naive_trend": fixed_trend_runner("asfr_15_44"),
        "cohort_proxy": wpp_style_runner("asfr_15_44"),
        "reduced_form": reduced_form_runner(),
        "household": household_simulator_runner(),
    }
    reports = {}
    for initial in args.initial:
        reports[str(initial)] = compare_models_rolling(
            rows, models, initial_train_years=initial, horizon=1,
            metric="asfr_15_44", replicates=args.replicates,
            bootstrap_draws=args.bootstrap_draws, baseline="naive_trend",
        )
    result = {
        "panel": str(args.panel),
        "calibration_years": list(range(2010, 2018)),
        "untouched_test_years": [2018, 2019, 2021],
        "excluded_years": [2020],
        "reports": reports,
        "interpretation": "窗口稳健性和预测比较，不是因果估计；不据此增加社会机制",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
