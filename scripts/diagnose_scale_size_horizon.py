"""Diagnose scale noise and denominator drift across population size and horizon.

The experiment is synthetic and leaves the production adapter unchanged.  It
separates finite-simulation scale error from an exposure-denominator mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu.config import PolicyConfig, RegionConfig, Scenario, SimulationConfig
from population_simu.household_calibration import HouseholdCalibration
from population_simu.world import World


LAST_GFR = 60.0
SIZES = (1200, 4800)
BURDENS = (0.20, 0.35, 0.50)
REFERENCE_BURDEN = 0.35
HORIZON = 10
REPORT_HORIZONS = (1, 2, 5, 10)
ORACLE_SEEDS = tuple(range(100_000, 100_800))
TARGET_SEEDS = tuple(range(0, 60))
CALIBRATION_REPETITIONS = 15
CALIBRATION_PATHS = 100
CALIBRATION_SEED_BASE = 200_000


def _scenario(seed: int, burden: float, size: int,
              calibration: HouseholdCalibration, years: int) -> Scenario:
    baseline_tfr = max(
        0.2,
        min(
            4.0,
            LAST_GFR * calibration.tfr_conversion_years
            / (1000.0 * max(0.1, calibration.partnership_exposure)),
        ),
    )
    return Scenario(
        name="scale_size_horizon_dgp",
        simulation=SimulationConfig(
            start_year=2017,
            years=years,
            initial_people=size,
            random_seed=seed,
            baseline_tfr=baseline_tfr,
        ),
        policy=PolicyConfig(
            childcare_support=max(0.0, min(1.0, 1.0 - burden)),
            fertility_multiplier=calibration.housing_multiplier(burden),
        ),
        regions=(RegionConfig("state", "state", 1.0),),
    )


def _path(seed: int, burden: float, size: int,
          calibration: HouseholdCalibration, years: int) -> list[dict[str, float | int]]:
    world = World(_scenario(seed, burden, size, calibration, years))
    records = []
    for horizon in range(1, years + 1):
        stat = world.step()
        female_exposure = sum(
            person.sex == "F" and 15 <= person.age <= 44
            for person in world.living_people
        )
        records.append({
            "horizon": horizon,
            "year": stat.year,
            "births": stat.births,
            "population": stat.population,
            "female_15_44": female_exposure,
            "fixed_denominator_rate": stat.births / (size * 0.5) * 1000.0,
            "exposure_rate": stat.births / max(1, female_exposure) * 1000.0,
        })
    return records


def _distribution(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": statistics.mean(ordered),
        "sd": statistics.pstdev(ordered),
        "minimum": ordered[0],
        "q025": ordered[min(len(ordered) - 1, int(0.025 * len(ordered)))],
        "median": statistics.median(ordered),
        "q975": ordered[min(len(ordered) - 1, int(0.975 * len(ordered)))],
        "maximum": ordered[-1],
    }


def _metrics(errors: list[float]) -> dict[str, float | int]:
    return {
        "n": len(errors),
        "bias": statistics.mean(errors),
        "mae": statistics.mean(abs(error) for error in errors),
        "rmse": math.sqrt(statistics.mean(error * error for error in errors)),
    }


def _summarize_repetitions(rows: list[dict[str, float | int]]) -> dict[str, object]:
    return {
        metric: _distribution([float(row[metric]) for row in rows])
        for metric in ("bias", "mae", "rmse")
    }


def diagnose() -> dict[str, object]:
    calibration = HouseholdCalibration(housing_elasticity=-1.0)
    by_size: dict[str, object] = {}

    for size_index, size in enumerate(SIZES):
        oracle_paths = [
            _path(seed, REFERENCE_BURDEN, size, calibration, 1)[0]
            for seed in ORACLE_SEEDS
        ]
        oracle_fixed_mean = statistics.mean(
            float(row["fixed_denominator_rate"]) for row in oracle_paths
        )
        oracle_exposure_mean = statistics.mean(
            float(row["exposure_rate"]) for row in oracle_paths
        )
        oracle_fixed_scale = LAST_GFR / oracle_fixed_mean
        oracle_exposure_scale = LAST_GFR / oracle_exposure_mean

        target_paths: dict[tuple[int, float], list[dict[str, float | int]]] = {}
        target_records: list[dict[str, object]] = []
        for seed in TARGET_SEEDS:
            for burden in BURDENS:
                path = _path(seed, burden, size, calibration, HORIZON)
                if float(path[0]["fixed_denominator_rate"]) <= 0:
                    raise RuntimeError("same-trajectory scale undefined for zero first-year births")
                target_paths[(seed, burden)] = path
                target_records.append({"seed": seed, "burden": burden, "path": path})

        scale_estimates = []
        size_seed_base = CALIBRATION_SEED_BASE + size_index * 100_000
        for repetition in range(CALIBRATION_REPETITIONS):
            start = size_seed_base + repetition * CALIBRATION_PATHS
            rates = [
                float(_path(start + offset, REFERENCE_BURDEN, size, calibration, 1)[0][
                    "fixed_denominator_rate"
                ])
                for offset in range(CALIBRATION_PATHS)
            ]
            scale_estimates.append(LAST_GFR / statistics.mean(rates))

        horizon_summary: dict[str, object] = {}
        for horizon in REPORT_HORIZONS:
            idx = horizon - 1
            scale_only_by_rep = []
            exposure_aware_by_rep = []
            contrast_by_rep = []
            for scale in scale_estimates:
                scale_errors = []
                exposure_errors = []
                contrast_errors = []
                for seed in TARGET_SEEDS:
                    for burden in BURDENS:
                        row = target_paths[(seed, burden)][idx]
                        prediction = scale * float(row["fixed_denominator_rate"])
                        scale_truth = oracle_fixed_scale * float(row["fixed_denominator_rate"])
                        exposure_truth = oracle_exposure_scale * float(row["exposure_rate"])
                        scale_errors.append(prediction - scale_truth)
                        exposure_errors.append(prediction - exposure_truth)
                    low = target_paths[(seed, BURDENS[0])][idx]
                    high = target_paths[(seed, BURDENS[-1])][idx]
                    prediction_delta = scale * (
                        float(high["fixed_denominator_rate"])
                        - float(low["fixed_denominator_rate"])
                    )
                    truth_delta = oracle_exposure_scale * (
                        float(high["exposure_rate"]) - float(low["exposure_rate"])
                    )
                    contrast_errors.append(prediction_delta - truth_delta)
                scale_only_by_rep.append(_metrics(scale_errors))
                exposure_aware_by_rep.append(_metrics(exposure_errors))
                contrast_by_rep.append(_metrics(contrast_errors))

            same_exposure_errors = []
            same_contrast_errors = []
            for seed in TARGET_SEEDS:
                for burden in BURDENS:
                    path = target_paths[(seed, burden)]
                    same_scale = LAST_GFR / float(path[0]["fixed_denominator_rate"])
                    prediction = same_scale * float(path[idx]["fixed_denominator_rate"])
                    truth = oracle_exposure_scale * float(path[idx]["exposure_rate"])
                    same_exposure_errors.append(prediction - truth)
                low = target_paths[(seed, BURDENS[0])]
                high = target_paths[(seed, BURDENS[-1])]
                predicted_delta = (
                    LAST_GFR * float(high[idx]["fixed_denominator_rate"])
                    / float(high[0]["fixed_denominator_rate"])
                    - LAST_GFR * float(low[idx]["fixed_denominator_rate"])
                    / float(low[0]["fixed_denominator_rate"])
                )
                truth_delta = oracle_exposure_scale * (
                    float(high[idx]["exposure_rate"])
                    - float(low[idx]["exposure_rate"])
                )
                same_contrast_errors.append(predicted_delta - truth_delta)

            exposure_ratios = [
                float(target_paths[(seed, burden)][idx]["female_15_44"]) / (size * 0.5)
                for seed in TARGET_SEEDS for burden in BURDENS
            ]
            horizon_summary[str(horizon)] = {
                "female_exposure_over_fixed_denominator": _distribution(exposure_ratios),
                "independent_scale_only_error": _summarize_repetitions(scale_only_by_rep),
                "independent_exposure_aware_error": _summarize_repetitions(exposure_aware_by_rep),
                "independent_exposure_contrast_error": _summarize_repetitions(contrast_by_rep),
                "same_trajectory_exposure_aware_error": _metrics(same_exposure_errors),
                "same_trajectory_exposure_contrast_error": _metrics(same_contrast_errors),
            }

        by_size[str(size)] = {
            "oracle": {
                "fixed_rate_mean": oracle_fixed_mean,
                "fixed_scale": oracle_fixed_scale,
                "exposure_rate_mean": oracle_exposure_mean,
                "exposure_scale": oracle_exposure_scale,
                "fixed_rate_se": statistics.pstdev(
                    float(row["fixed_denominator_rate"]) for row in oracle_paths
                ) / math.sqrt(len(oracle_paths)),
                "exposure_rate_se": statistics.pstdev(
                    float(row["exposure_rate"]) for row in oracle_paths
                ) / math.sqrt(len(oracle_paths)),
            },
            "independent_scale": _distribution(scale_estimates),
            "relative_scale_bias": statistics.mean(scale_estimates) / oracle_fixed_scale - 1.0,
            "horizons": horizon_summary,
            "target_records": target_records,
            "calibration_scale_estimates": scale_estimates,
            "calibration_seed_range": [
                size_seed_base,
                size_seed_base + CALIBRATION_REPETITIONS * CALIBRATION_PATHS - 1,
            ],
        }

    source_files = [
        "scripts/diagnose_scale_size_horizon.py",
        "src/population_simu/world.py",
        "src/population_simu/config.py",
        "src/population_simu/household_calibration.py",
        "src/population_simu/benchmarks.py",
    ]
    result = {
        "kind": "synthetic_scale_size_horizon_diagnostic",
        "estimands": {
            "scale_only": "recovery of oracle mapping using the same fixed denominator",
            "exposure_aware": "prediction relative to births per actual simulated women aged 15-44",
            "contrast": "high-minus-low housing burden response under exposure-aware mapping",
        },
        "design": {
            "last_gfr": LAST_GFR,
            "sizes": list(SIZES),
            "burdens": list(BURDENS),
            "reference_burden": REFERENCE_BURDEN,
            "housing_elasticity": -1.0,
            "maximum_horizon": HORIZON,
            "reported_horizons": list(REPORT_HORIZONS),
            "oracle_paths_per_size": len(ORACLE_SEEDS),
            "target_paths_per_burden_and_size": len(TARGET_SEEDS),
            "calibration_repetitions": CALIBRATION_REPETITIONS,
            "independent_calibration_paths": CALIBRATION_PATHS,
            "target_seed_range": [min(TARGET_SEEDS), max(TARGET_SEEDS)],
            "oracle_seed_range": [min(ORACLE_SEEDS), max(ORACLE_SEEDS)],
        },
        "by_size": by_size,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in source_files
        },
        "limits": [
            "synthetic World DGP, not historical or causal validation",
            "oracle values are finite Monte Carlo approximations",
            "15 calibration repetitions provide a coarse uncertainty distribution",
            "housing changes both fertility_multiplier and childcare_support",
            "exposure-aware target is an internal diagnostic, not observed state GFR",
            "the experiment isolates denominator and Monte Carlo effects, not all structural errors",
        ],
    }

    assert set(TARGET_SEEDS).isdisjoint(ORACLE_SEEDS)
    calibration_ranges = [
        set(range(int(row["calibration_seed_range"][0]),
                  int(row["calibration_seed_range"][1]) + 1))
        for row in by_size.values()
    ]
    assert all(set(TARGET_SEEDS).isdisjoint(values) for values in calibration_ranges)
    assert calibration_ranges[0].isdisjoint(calibration_ranges[1])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n")
    compact = {}
    for size, row in result["by_size"].items():
        compact[size] = {
            "scale_sd": row["independent_scale"]["sd"],
            "relative_scale_bias": row["relative_scale_bias"],
            "horizons": {
                horizon: {
                    "scale_only_rmse_median": values[
                        "independent_scale_only_error"
                    ]["rmse"]["median"],
                    "exposure_rmse_median": values[
                        "independent_exposure_aware_error"
                    ]["rmse"]["median"],
                    "exposure_bias_median": values[
                        "independent_exposure_aware_error"
                    ]["bias"]["median"],
                    "same_exposure_rmse": values[
                        "same_trajectory_exposure_aware_error"
                    ]["rmse"],
                }
                for horizon, values in row["horizons"].items()
            },
        }
    print(json.dumps(compact, indent=2))
