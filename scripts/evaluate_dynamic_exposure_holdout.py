"""Compare legacy and dynamic-exposure household adapters on fixed historical years.

The 2018, 2019 and 2021 outcomes have been inspected previously, so this is a
diagnostic replay rather than a fresh untouched test or causal evaluation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from random import Random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu.benchmarks import (
    fixed_trend_runner,
    household_simulator_runner,
    reduced_form_runner,
    wpp_style_runner,
)
from population_simu.calibration import crps_metrics, interval_metrics


TRAIN_YEARS = tuple(range(2010, 2018))
TEST_YEARS = (2018, 2019, 2021)


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean, right_mean = statistics.mean(left), statistics.mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - left_mean) ** 2 for x in left)
        * sum((y - right_mean) ** 2 for y in right)
    )
    return numerator / denominator if denominator > 0 else None


def _median_predictions(samples: list[list[dict[str, object]]]) -> dict[tuple[str, int], float]:
    values: dict[tuple[str, int], list[float]] = {}
    for sample in samples:
        for row in sample:
            key = (str(row["entity"]), int(row["year"]))
            values.setdefault(key, []).append(float(row["asfr_15_44"]))
    return {key: statistics.median(items) for key, items in values.items()}


def _error_summary(observed: list[dict[str, object]],
                   predictions: dict[tuple[str, int], float]) -> dict[str, float | int]:
    errors = []
    apes = []
    for row in observed:
        actual = float(row["asfr_15_44"])
        predicted = predictions[(str(row["entity"]), int(row["year"]))]
        errors.append(predicted - actual)
        if abs(actual) > 1e-12:
            apes.append(abs(predicted - actual) / abs(actual) * 100.0)
    return {
        "n": len(errors),
        "bias": statistics.mean(errors),
        "mae": statistics.mean(abs(error) for error in errors),
        "rmse": math.sqrt(statistics.mean(error * error for error in errors)),
        "mape_percent": statistics.mean(apes),
    }


def _cluster_bootstrap_delta(observed: list[dict[str, object]],
                             legacy: dict[tuple[str, int], float],
                             candidate: dict[tuple[str, int], float],
                             draws: int, seed: int, *, reference_name: str) -> dict[str, object]:
    states = sorted({str(row["entity"]) for row in observed})
    rows_by_state = {state: [row for row in observed if str(row["entity"]) == state]
                     for state in states}
    rng = Random(seed)
    deltas = []
    for _ in range(draws):
        selected = [states[rng.randrange(len(states))] for _ in states]
        legacy_apes = []
        candidate_apes = []
        for state in selected:
            for row in rows_by_state[state]:
                key = (state, int(row["year"]))
                actual = float(row["asfr_15_44"])
                legacy_apes.append(abs(legacy[key] - actual) / abs(actual) * 100.0)
                candidate_apes.append(abs(candidate[key] - actual) / abs(actual) * 100.0)
        deltas.append(statistics.mean(candidate_apes) - statistics.mean(legacy_apes))
    ordered = sorted(deltas)
    return {
        "delta_definition": f"dynamic candidate MAPE - {reference_name} MAPE; negative favors dynamic",
        "draws": draws,
        "cluster": "state, preserving all three evaluation years",
        "mean": statistics.mean(deltas),
        "lower_95": ordered[int(0.025 * draws)],
        "upper_95": ordered[min(draws - 1, int(0.975 * draws))],
        "candidate_better_probability": sum(value < 0 for value in deltas) / draws,
    }


def load_panel(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        raw = list(csv.DictReader(handle))
    rows = []
    for row in raw:
        year = int(row["year"])
        if year not in TRAIN_YEARS + TEST_YEARS:
            continue
        rows.append({
            **row,
            "year": year,
            "asfr_15_44": float(row["asfr_15_44"]),
            "births_15_44": float(row["births_15_44"]),
            "female_15_44": float(row["female_15_44"]),
            "housing_cost_burden": float(row["housing_cost_burden"]),
        })
    states = sorted({str(row["entity"]) for row in rows})
    expected = {(state, year) for state in states for year in TRAIN_YEARS + TEST_YEARS}
    keys = {(str(row["entity"]), int(row["year"])) for row in rows}
    if len(states) != 50 or keys != expected or len(rows) != len(keys):
        raise ValueError("panel must contain unique 50-state rows for 2010-2019 and 2021")
    return rows


def evaluate(rows: list[dict[str, object]], replicates: int,
             scale_paths: int, bootstrap_draws: int, seed: int) -> dict[str, object]:
    train = [row for row in rows if int(row["year"]) in TRAIN_YEARS]
    test = [row for row in rows if int(row["year"]) in TEST_YEARS]
    models = {
        "naive_trend": fixed_trend_runner("asfr_15_44"),
        "damped_trend_proxy": wpp_style_runner("asfr_15_44"),
        "reduced_form": reduced_form_runner(),
        "household_legacy_same_path_fixed_denominator": household_simulator_runner(),
        "household_fixed_denominator_independent_scale": household_simulator_runner(
            independent_scale_paths=scale_paths,
        ),
        "household_dynamic_exposure_independent_scale": household_simulator_runner(
            exposure_denominator="dynamic_female_15_44",
            independent_scale_paths=scale_paths,
        ),
    }
    reports = {}
    point_predictions = {}
    for name, runner in models.items():
        samples = [list(runner(train, list(TEST_YEARS), seed + index))
                   for index in range(replicates)]
        point = _median_predictions(samples)
        if set(point) != {(str(row["entity"]), int(row["year"])) for row in test}:
            raise ValueError(f"{name} forecast keys do not match held-out panel")
        point_predictions[name] = point
        sample_rows = [[{"entity": str(item["entity"]), "year": int(item["year"]),
                         "asfr_15_44": float(item["asfr_15_44"])}
                        for item in sample] for sample in samples]
        overall = _error_summary(test, point)
        by_year = {
            str(year): _error_summary(
                [row for row in test if int(row["year"]) == year], point
            ) for year in TEST_YEARS
        }
        last_train = {str(row["entity"]): row for row in train if int(row["year"]) == 2017}
        predicted_levels, observed_levels = [], []
        predicted_changes, observed_changes, exposure_changes, errors = [], [], [], []
        for row in test:
            key = (str(row["entity"]), int(row["year"]))
            baseline = last_train[str(row["entity"])]
            predicted = point[key]
            observed = float(row["asfr_15_44"])
            predicted_levels.append(predicted)
            observed_levels.append(observed)
            predicted_changes.append(predicted - float(baseline["asfr_15_44"]))
            observed_changes.append(observed - float(baseline["asfr_15_44"]))
            exposure_changes.append(
                float(row["female_15_44"]) / float(baseline["female_15_44"]) - 1.0
            )
            errors.append(predicted - observed)
        reports[name] = {
            "overall": overall,
            "by_year": by_year,
            "crps": crps_metrics(test, sample_rows, metrics=("asfr_15_44",),
                                 group="entity")["asfr_15_44"]["mean_crps"],
            "interval": interval_metrics(test, sample_rows, metrics=("asfr_15_44",),
                                         group="entity")["asfr_15_44"],
            "descriptive_association": {
                "prediction_observation_level_correlation": _correlation(
                    predicted_levels, observed_levels
                ),
                "prediction_observation_change_from_2017_correlation": _correlation(
                    predicted_changes, observed_changes
                ),
                "forecast_error_observed_exposure_growth_correlation": _correlation(
                    errors, exposure_changes
                ),
                "note": "descriptive predictive association, not a causal relationship",
            },
        }

    legacy_name = "household_legacy_same_path_fixed_denominator"
    fixed_independent_name = "household_fixed_denominator_independent_scale"
    dynamic_name = "household_dynamic_exposure_independent_scale"
    return {
        "kind": "fixed_2017_dynamic_exposure_candidate_diagnostic",
        "evaluation_design": "fixed 2010-2017 calibration; previously inspected 2018, 2019, 2021 evaluation",
        "calibration_years": list(TRAIN_YEARS),
        "evaluation_years": list(TEST_YEARS),
        "calendar_horizons": [1, 2, 4],
        "replicates": replicates,
        "independent_scale_paths": scale_paths,
        "future_observed_housing_used": False,
        "future_observed_female_exposure_used_by_models": False,
        "observed_female_exposure_role": "constructs observed GFR and is used only in post-prediction diagnostics",
        "reports": reports,
        "paired_dynamic_vs_legacy": _cluster_bootstrap_delta(
            test, point_predictions[legacy_name], point_predictions[dynamic_name],
            bootstrap_draws, seed + 99_001, reference_name=legacy_name,
        ),
        "paired_dynamic_vs_fixed_independent": _cluster_bootstrap_delta(
            test, point_predictions[fixed_independent_name], point_predictions[dynamic_name],
            bootstrap_draws, seed + 99_002, reference_name=fixed_independent_name,
        ),
        "limitations": [
            "evaluation outcomes have been inspected previously; not a fresh untouched test",
            "only three historical target years and overlapping national shocks",
            "household adapter is simplified World, not full FamilyWorld",
            "dynamic exposure is generated internally and is not calibrated to state age-sex structure",
            "association diagnostics are descriptive and not causal",
            "dynamic-versus-fixed-independent comparison isolates denominator choice within the candidate scaling design",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--scale-paths", type=int, default=100)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    report = evaluate(load_panel(args.panel), args.replicates, args.scale_paths,
                      args.bootstrap_draws, args.seed)
    sources = [args.panel, Path(__file__), ROOT / "src/population_simu/benchmarks.py",
               ROOT / "src/population_simu/world.py"]
    report["source_sha256"] = {
        str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
        hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n")
    compact = {
        name: {
            "mape": row["overall"]["mape_percent"],
            "rmse": row["overall"]["rmse"],
            "change_correlation": row["descriptive_association"][
                "prediction_observation_change_from_2017_correlation"
            ],
        } for name, row in report["reports"].items()
    }
    compact["paired_dynamic_vs_legacy"] = report["paired_dynamic_vs_legacy"]
    compact["paired_dynamic_vs_fixed_independent"] = report[
        "paired_dynamic_vs_fixed_independent"
    ]
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
