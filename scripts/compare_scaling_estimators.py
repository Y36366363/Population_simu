"""Compare same-trajectory and independent scaling under a known simulator DGP.

This is a synthetic measurement-mapping experiment.  It does not fit or alter
the production household adapter and it does not estimate a real housing effect.
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
INITIAL_PEOPLE = 1200
BURDENS = (0.20, 0.35, 0.50)
REFERENCE_BURDEN = 0.35
ORACLE_SEEDS = tuple(range(100_000, 100_800))
TARGET_SEEDS = tuple(range(0, 120))
CALIBRATION_REPETITIONS = 50
CALIBRATION_POOL_SIZES = (1, 5, 20, 100)
CALIBRATION_SEED_BASE = 200_000


def _raw_rates(seed: int, burden: float, calibration: HouseholdCalibration) -> tuple[float, float]:
    baseline_tfr = max(
        0.2,
        min(
            4.0,
            LAST_GFR * calibration.tfr_conversion_years
            / (1000.0 * max(0.1, calibration.partnership_exposure)),
        ),
    )
    scenario = Scenario(
        name="scaling_estimator_dgp",
        simulation=SimulationConfig(
            start_year=2017,
            years=2,
            initial_people=INITIAL_PEOPLE,
            random_seed=seed,
            baseline_tfr=baseline_tfr,
        ),
        policy=PolicyConfig(
            childcare_support=max(0.0, min(1.0, 1.0 - burden)),
            fertility_multiplier=calibration.housing_multiplier(burden),
        ),
        regions=(RegionConfig("state", "state", 1.0),),
    )
    history = {row.year: row for row in World(scenario).run()}
    denominator = INITIAL_PEOPLE * 0.5
    return tuple(history[year].births / denominator * 1000.0 for year in (2018, 2019))


def _rmse(errors: list[float]) -> float:
    return math.sqrt(statistics.mean(error * error for error in errors))


def _metrics(errors: list[float]) -> dict[str, float | int]:
    return {
        "n": len(errors),
        "bias": statistics.mean(errors),
        "mae": statistics.mean(abs(error) for error in errors),
        "rmse": _rmse(errors),
    }


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


def diagnose() -> dict[str, object]:
    calibration = HouseholdCalibration(housing_elasticity=-1.0)

    # The large, disjoint reference sample approximates the DGP expectation.
    oracle_first = [_raw_rates(seed, REFERENCE_BURDEN, calibration)[0]
                    for seed in ORACLE_SEEDS]
    oracle_mean = statistics.mean(oracle_first)
    oracle_se = statistics.pstdev(oracle_first) / math.sqrt(len(oracle_first))
    oracle_scale = LAST_GFR / oracle_mean
    oracle_halves = [oracle_first[: len(oracle_first) // 2],
                     oracle_first[len(oracle_first) // 2 :]]

    target_rows: list[dict[str, object]] = []
    target_lookup: dict[tuple[int, float], tuple[float, float]] = {}
    for seed in TARGET_SEEDS:
        for burden in BURDENS:
            raw = _raw_rates(seed, burden, calibration)
            if raw[0] <= 0:
                raise RuntimeError("same-trajectory scale is undefined for zero first-year births")
            target_lookup[(seed, burden)] = raw
            target_rows.append({
                "seed": seed,
                "burden": burden,
                "raw_rates": list(raw),
                "oracle_mapped": [oracle_scale * value for value in raw],
                "same_trajectory_mapped": [LAST_GFR * value / raw[0] for value in raw],
            })

    same_summary: dict[str, object] = {}
    for year_index, year in enumerate((2018, 2019)):
        errors = [
            float(row["same_trajectory_mapped"][year_index])
            - float(row["oracle_mapped"][year_index])
            for row in target_rows
        ]
        same_summary[str(year)] = _metrics(errors)

    # Each repetition uses one independent pool; prefix means make K nested
    # without re-running trajectories. Pools and target/oracle seeds are disjoint.
    scale_estimates: dict[int, list[float]] = {size: [] for size in CALIBRATION_POOL_SIZES}
    independent_metrics: dict[int, list[dict[str, object]]] = {
        size: [] for size in CALIBRATION_POOL_SIZES
    }
    for repetition in range(CALIBRATION_REPETITIONS):
        start = CALIBRATION_SEED_BASE + repetition * max(CALIBRATION_POOL_SIZES)
        pool = [_raw_rates(start + offset, REFERENCE_BURDEN, calibration)[0]
                for offset in range(max(CALIBRATION_POOL_SIZES))]
        for size in CALIBRATION_POOL_SIZES:
            scale = LAST_GFR / statistics.mean(pool[:size])
            scale_estimates[size].append(scale)
            by_year = {}
            for year_index, year in enumerate((2018, 2019)):
                errors = [
                    scale * float(row["raw_rates"][year_index])
                    - float(row["oracle_mapped"][year_index])
                    for row in target_rows
                ]
                by_year[str(year)] = _metrics(errors)
            independent_metrics[size].append({"repetition": repetition, "by_year": by_year})

    independent_summary: dict[str, object] = {}
    for size in CALIBRATION_POOL_SIZES:
        independent_summary[str(size)] = {
            "scale": _distribution(scale_estimates[size]),
            "relative_scale_bias": (
                statistics.mean(scale_estimates[size]) / oracle_scale - 1.0
            ),
            "by_year": {
                str(year): {
                    metric: _distribution([
                        float(row["by_year"][str(year)][metric])
                        for row in independent_metrics[size]
                    ])
                    for metric in ("bias", "mae", "rmse")
                }
                for year in (2018, 2019)
            },
        }

    # Housing contrast is high burden minus low burden using paired target seeds.
    oracle_contrasts: dict[int, list[float]] = {0: [], 1: []}
    same_contrasts: dict[int, list[float]] = {0: [], 1: []}
    raw_contrasts: dict[int, list[float]] = {0: [], 1: []}
    for seed in TARGET_SEEDS:
        low = target_lookup[(seed, BURDENS[0])]
        high = target_lookup[(seed, BURDENS[-1])]
        for year_index in (0, 1):
            raw_delta = high[year_index] - low[year_index]
            raw_contrasts[year_index].append(raw_delta)
            oracle_contrasts[year_index].append(oracle_scale * raw_delta)
        same_contrasts[0].append(0.0)
        same_contrasts[1].append(
            LAST_GFR * high[1] / high[0] - LAST_GFR * low[1] / low[0]
        )

    contrast_summary: dict[str, object] = {}
    for year_index, year in enumerate((2018, 2019)):
        same_errors = [estimate - truth for estimate, truth in zip(
            same_contrasts[year_index], oracle_contrasts[year_index]
        )]
        entry: dict[str, object] = {
            "oracle_contrast": _distribution(oracle_contrasts[year_index]),
            "same_trajectory_contrast": _distribution(same_contrasts[year_index]),
            "same_trajectory_error": _metrics(same_errors),
            "independent": {},
        }
        for size in CALIBRATION_POOL_SIZES:
            rmses = []
            biases = []
            for scale in scale_estimates[size]:
                errors = [scale * raw - truth for raw, truth in zip(
                    raw_contrasts[year_index], oracle_contrasts[year_index]
                )]
                rmses.append(_rmse(errors))
                biases.append(statistics.mean(errors))
            entry["independent"][str(size)] = {
                "rmse": _distribution(rmses),
                "bias": _distribution(biases),
            }
        contrast_summary[str(year)] = entry

    source_files = [
        "scripts/compare_scaling_estimators.py",
        "src/population_simu/world.py",
        "src/population_simu/config.py",
        "src/population_simu/household_calibration.py",
        "src/population_simu/benchmarks.py",
    ]
    result = {
        "kind": "synthetic_scaling_estimator_comparison",
        "estimand": (
            "recovery of an oracle population mapping from raw simulator rates; "
            "not real-world forecast accuracy"
        ),
        "design": {
            "last_gfr": LAST_GFR,
            "initial_people": INITIAL_PEOPLE,
            "burdens": list(BURDENS),
            "reference_burden": REFERENCE_BURDEN,
            "housing_elasticity": -1.0,
            "years": [2018, 2019],
            "oracle_seed_count": len(ORACLE_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "calibration_repetitions": CALIBRATION_REPETITIONS,
            "calibration_pool_sizes": list(CALIBRATION_POOL_SIZES),
            "seed_ranges": {
                "target": [min(TARGET_SEEDS), max(TARGET_SEEDS)],
                "oracle": [min(ORACLE_SEEDS), max(ORACLE_SEEDS)],
                "calibration": [CALIBRATION_SEED_BASE,
                                CALIBRATION_SEED_BASE
                                + CALIBRATION_REPETITIONS * max(CALIBRATION_POOL_SIZES) - 1],
            },
        },
        "oracle": {
            "mean_raw_first_rate": oracle_mean,
            "monte_carlo_se_of_mean": oracle_se,
            "scale": oracle_scale,
            "half_sample_means": [statistics.mean(values) for values in oracle_halves],
            "half_sample_scales": [LAST_GFR / statistics.mean(values)
                                    for values in oracle_halves],
        },
        "same_trajectory": same_summary,
        "independent": independent_summary,
        "housing_contrast": contrast_summary,
        "target_rows": target_rows,
        "scale_estimates": {str(size): values for size, values in scale_estimates.items()},
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in source_files
        },
        "limits": [
            "synthetic World DGP, not historical or causal validation",
            "oracle is a finite Monte Carlo approximation rather than an analytic expectation",
            "housing simultaneously changes fertility_multiplier and childcare_support",
            "raw denominator is initial population times 0.5, not observed women aged 15-44",
            "target evaluates measurement mapping, not prediction of an unseen stochastic realization",
            "two simulated years cannot establish long-horizon stability",
        ],
    }

    assert set(TARGET_SEEDS).isdisjoint(ORACLE_SEEDS)
    assert set(TARGET_SEEDS).isdisjoint(range(
        CALIBRATION_SEED_BASE,
        CALIBRATION_SEED_BASE + CALIBRATION_REPETITIONS * max(CALIBRATION_POOL_SIZES),
    ))
    assert max(abs(float(row["same_trajectory_mapped"][0]) - LAST_GFR)
               for row in target_rows) < 1e-12
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n")
    compact = {
        "oracle": result["oracle"],
        "same_trajectory": result["same_trajectory"],
        "independent_scale": {
            size: {
                "relative_scale_bias": row["relative_scale_bias"],
                "scale_sd": row["scale"]["sd"],
                "2018_rmse_median": row["by_year"]["2018"]["rmse"]["median"],
                "2019_rmse_median": row["by_year"]["2019"]["rmse"]["median"],
            }
            for size, row in result["independent"].items()
        },
    }
    print(json.dumps(compact, indent=2))
