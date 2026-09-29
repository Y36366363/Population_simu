"""Pool frozen rolling-origin artifacts without hiding their fold structure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    args = parser.parse_args()
    loaded = [(path.name, json.loads(path.read_text(encoding="utf-8"))) for path in args.artifacts]
    models = sorted({model for _, data in loaded for model in data.get("reports", {}).get(next(iter(data.get("reports", {})), ""), {})})
    pooled = {}
    for model in models:
        folds = []
        by_origin = {}
        for filename, data in loaded:
            report = next(iter(data.get("reports", {}).values()), {}).get(model)
            if not report:
                continue
            by_origin[filename] = report["summary"]
            folds.extend(report.get("folds", []))
        pooled[model] = {
            "n_folds": len(folds),
            "mape_mean": mean(float(row["mape"]) for row in folds),
            "rmse_mean": mean(float(row["rmse"]) for row in folds),
            "crps_mean": mean(float(row["crps"]) for row in folds),
            "coverage_mean": mean(float(row["coverage"]) for row in folds),
            "nominal_coverage": 0.8,
            "coverage_gap_to_nominal": mean(float(row["coverage"]) for row in folds) - 0.8,
            "mean_interval_width": mean(float(row["mean_interval_width"]) for row in folds),
            "by_origin": by_origin,
        }
    result = {
        "version": "2026-09-28",
        "kind": "housing_primary_rolling_origin_summary",
        "panel": loaded[0][1].get("panel") if loaded else None,
        "calibration_years": list(range(2010, 2018)),
        "untouched_test_years": [2018, 2019, 2021],
        "origins": [int(next(iter(data.get("reports", {})))) for _, data in loaded],
        "monte_carlo_replicates": args.replicates,
        "bootstrap_draws": args.bootstrap_draws,
        "residual_uncertainty": True,
        "source_artifacts": [str(path) for path in args.artifacts],
        "pooled_fold_summary": pooled,
        "interpretation": "跨 initial=6/7/8 的 rolling-origin 汇总；每个起点的原始 fold 和 bootstrap 结果保留在 source_artifacts 中。不是因果估计。",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "models": len(pooled), "folds": sum(x["n_folds"] for x in pooled.values())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
