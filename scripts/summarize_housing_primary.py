"""Create the human-readable frozen housing-primary results note."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.artifact.read_text(encoding="utf-8"))
    lines = [
        "# Housing-primary rolling-origin results · 2026-09-21",
        "",
        "This is a predictive replication report, not a causal estimate. The primary outcome is state-year `ASFR_15_44`; calibration uses 2010–2017 and the untouched test years are 2018, 2019 and 2021. 2020 is excluded from the primary specification.",
        "",
        "## Overall rolling-origin diagnostics",
        "",
        "Each expanding-window origin uses 20 common-random Monte Carlo repetitions and 1,000 bootstrap draws over fold scores. CRPS is in ASFR-per-1,000 units. Coverage is the nominal 10–90% interval coverage.",
        "",
        "| origin window | model | MAPE | RMSE | CRPS | coverage | interval width |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for initial, report in data["reports"].items():
        for name, details in report.items():
            summary = details["summary"]
            lines.append(
                f"| {initial} years | `{name}` | {pct(summary['mape']['mean'])} | "
                f"{summary['rmse']['mean']:.3f} | {summary['crps']['mean']:.3f} | "
                f"{pct(summary['coverage']['mean'])} | {summary['mean_interval_width']['mean']:.3f} |"
            )
    lines += [
        "",
        "## Regional MAPE (initial window = 6 years)",
        "",
        "| model | Northeast | Midwest | South | West |",
        "|---|---:|---:|---:|---:|",
    ]
    regional = data["error_strata"]["6"]
    for model, groups in regional.items():
        lines.append(
            f"| `{model}` | {pct(groups['Northeast']['mean_mape'])} | {pct(groups['Midwest']['mean_mape'])} | "
            f"{pct(groups['South']['mean_mape'])} | {pct(groups['West']['mean_mape'])} |"
        )
    lines += [
        "",
        "## Interpretation of the household ablation",
        "",
        "1. `household_no_household` currently bypasses household formation, marriage, fertility and migration events and uses the recent two-year trend. It is therefore mathematically equivalent to the `naive_trend` control under this forecast contract. Its lower error is evidence that the full stochastic adapter adds predictive noise in this implementation, not evidence that household mechanisms are false or causally harmful.",
        "2. `household` is worse than the trend control in the rolling-origin table. The plausible, testable explanations are the seeded World process, the proxy female exposure, and the calibration-to-ASFR scaling; these are model limitations to audit, not substantive demographic conclusions.",
        "3. `household_no_housing` is identical to `household` in these rolling folds. This means the current one-year aggregate adapter does not transmit enough variation from the exogenous housing series to change the forecast path. Housing sensitivity should therefore be described as unresolved rather than as a measured fertility effect.",
        "4. Deterministic baselines have zero-width intervals, so their 10–90% coverage is mechanically zero. A calibrated predictive interval for those baselines requires a pre-specified residual or bootstrap construction; the current coverage values must not be read as probabilistic model failure.",
        "",
        "## Scope gates",
        "",
        "- Childcare remains outside the primary specification until one documented state-year series has a stable definition, denominator, source and full calibration/test coverage.",
        "- Age–marital-status–parity hazards remain prior-only until state-year births and matching exposure denominators pass the strict five-dimensional key audit.",
        "- No causal counterfactual is reported from this artifact.",
        "",
        f"Source artifact: `{args.artifact}`.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
