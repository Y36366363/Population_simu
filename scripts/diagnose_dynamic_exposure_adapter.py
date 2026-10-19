"""Compare fixed sex-share denominators with annual female 15--44 exposure.

This synthetic diagnostic reuses the frozen target paths from 2026-10-18 and
re-runs only independent calibration paths.  Production adapters are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu.config import PolicyConfig, RegionConfig, Scenario, SimulationConfig
from population_simu.household_calibration import HouseholdCalibration
from population_simu.world import World


SEX_SHARE_ASSUMPTIONS = (100 / 205, 0.5, 105 / 205)


def _distribution(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": statistics.mean(ordered),
        "sd": statistics.pstdev(ordered),
        "minimum": ordered[0],
        "median": statistics.median(ordered),
        "maximum": ordered[-1],
    }


def _metrics(errors: list[float]) -> dict[str, float | int]:
    return {
        "n": len(errors),
        "bias": statistics.mean(errors),
        "mae": statistics.mean(abs(error) for error in errors),
        "rmse": math.sqrt(statistics.mean(error * error for error in errors)),
    }


def _summary(rows: list[dict[str, float | int]]) -> dict[str, object]:
    return {
        metric: _distribution([float(row[metric]) for row in rows])
        for metric in ("bias", "mae", "rmse")
    }


def _first_exposure_rate(seed: int, size: int, burden: float,
                         calibration: HouseholdCalibration) -> tuple[float, float]:
    baseline_tfr = max(
        0.2,
        min(
            4.0,
            60.0 * calibration.tfr_conversion_years
            / (1000.0 * max(0.1, calibration.partnership_exposure)),
        ),
    )
    scenario = Scenario(
        name="dynamic_exposure_calibration",
        simulation=SimulationConfig(
            start_year=2017,
            years=1,
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
    world = World(scenario)
    stat = world.step()
    scan_start = perf_counter()
    female_15_44 = sum(
        person.sex == "F" and 15 <= person.age <= 44
        for person in world.living_people
    )
    scan_seconds = perf_counter() - scan_start
    return stat.births / max(1, female_15_44) * 1000.0, scan_seconds


def diagnose(source: dict[str, object], source_path: Path) -> dict[str, object]:
    design = source["design"]
    calibration = HouseholdCalibration(housing_elasticity=float(design["housing_elasticity"]))
    report_horizons = [int(value) for value in design["reported_horizons"]]
    repetitions = int(design["calibration_repetitions"])
    paths_per_repetition = int(design["independent_calibration_paths"])
    reference_burden = float(design["reference_burden"])
    by_size: dict[str, object] = {}

    for size_text, previous in source["by_size"].items():
        size = int(size_text)
        calibration_start, calibration_end = previous["calibration_seed_range"]
        expected_end = int(calibration_start) + repetitions * paths_per_repetition - 1
        if int(calibration_end) != expected_end:
            raise ValueError("source calibration seed range does not match design")

        dynamic_scales = []
        exposure_scan_seconds = 0.0
        calibration_start_time = perf_counter()
        for repetition in range(repetitions):
            start = int(calibration_start) + repetition * paths_per_repetition
            rates = []
            for offset in range(paths_per_repetition):
                rate, scan_seconds = _first_exposure_rate(
                    start + offset, size, reference_burden, calibration
                )
                rates.append(rate)
                exposure_scan_seconds += scan_seconds
            dynamic_scales.append(60.0 / statistics.mean(rates))
        calibration_elapsed = perf_counter() - calibration_start_time

        oracle_exposure_scale = float(previous["oracle"]["exposure_scale"])
        target_lookup = {
            (int(row["seed"]), float(row["burden"])): row["path"]
            for row in previous["target_records"]
        }
        target_seeds = sorted({key[0] for key in target_lookup})
        burdens = sorted({key[1] for key in target_lookup})

        # A constant sex-share change is only a units change if its scale is
        # independently recalibrated. Verify this directly on all frozen paths.
        fixed_scales = [float(value) for value in previous["calibration_scale_estimates"]]
        ratio_invariance_errors = []
        for sex_share in SEX_SHARE_ASSUMPTIONS:
            for base_scale in fixed_scales:
                recalibrated_scale = base_scale * sex_share / 0.5
                for path in target_lookup.values():
                    for row in path:
                        alternative_rate = (
                            float(row["births"]) / (size * sex_share) * 1000.0
                        )
                        base_prediction = base_scale * float(row["fixed_denominator_rate"])
                        ratio_invariance_errors.append(
                            recalibrated_scale * alternative_rate - base_prediction
                        )

        horizons = {}
        for horizon in report_horizons:
            index = horizon - 1
            dynamic_errors_by_rep = []
            dynamic_contrast_errors_by_rep = []
            for scale in dynamic_scales:
                errors = []
                contrast_errors = []
                for seed in target_seeds:
                    for burden in burdens:
                        row = target_lookup[(seed, burden)][index]
                        truth = oracle_exposure_scale * float(row["exposure_rate"])
                        errors.append(scale * float(row["exposure_rate"]) - truth)
                    low = target_lookup[(seed, burdens[0])][index]
                    high = target_lookup[(seed, burdens[-1])][index]
                    contrast = float(high["exposure_rate"]) - float(low["exposure_rate"])
                    contrast_errors.append((scale - oracle_exposure_scale) * contrast)
                dynamic_errors_by_rep.append(_metrics(errors))
                dynamic_contrast_errors_by_rep.append(_metrics(contrast_errors))

            previous_horizon = previous["horizons"][str(horizon)]
            horizons[str(horizon)] = {
                "dynamic_exposure_error": _summary(dynamic_errors_by_rep),
                "dynamic_exposure_contrast_error": _summary(
                    dynamic_contrast_errors_by_rep
                ),
                "fixed_denominator_exposure_error": previous_horizon[
                    "independent_exposure_aware_error"
                ],
                "fixed_denominator_contrast_error": previous_horizon[
                    "independent_exposure_contrast_error"
                ],
                "female_exposure_over_fixed_denominator": previous_horizon[
                    "female_exposure_over_fixed_denominator"
                ],
            }

        by_size[size_text] = {
            "oracle_exposure_scale": oracle_exposure_scale,
            "dynamic_exposure_scale": _distribution(dynamic_scales),
            "relative_dynamic_scale_bias": (
                statistics.mean(dynamic_scales) / oracle_exposure_scale - 1.0
            ),
            "constant_sex_share_check": {
                "assumptions": list(SEX_SHARE_ASSUMPTIONS),
                "female_to_male_interpretation": [
                    "100 females / 105 males",
                    "equal female and male shares",
                    "105 females / 100 males",
                ],
                "max_abs_prediction_difference_after_recalibration": max(
                    abs(value) for value in ratio_invariance_errors
                ),
                "unrecalibrated_level_change_relative_to_0_5": {
                    str(value): 0.5 / value - 1.0 for value in SEX_SHARE_ASSUMPTIONS
                },
            },
            "diagnostic_cost": {
                "calibration_elapsed_seconds": calibration_elapsed,
                "exposure_scan_seconds": exposure_scan_seconds,
                "exposure_scan_share_of_elapsed": (
                    exposure_scan_seconds / calibration_elapsed
                    if calibration_elapsed else 0.0
                ),
                "paths": repetitions * paths_per_repetition,
                "note": "machine-specific timing; a production implementation could fold the count into annual summarization",
            },
            "horizons": horizons,
            "calibration_scale_estimates": dynamic_scales,
        }

    source_files = [
        "scripts/diagnose_dynamic_exposure_adapter.py",
        "scripts/diagnose_scale_size_horizon.py",
        "src/population_simu/world.py",
        "src/population_simu/config.py",
        "src/population_simu/household_calibration.py",
        "src/population_simu/benchmarks.py",
    ]
    result = {
        "kind": "synthetic_dynamic_exposure_adapter_diagnostic",
        "source_artifact": str(source_path),
        "source_artifact_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "question": (
            "whether constant female-share assumptions matter after recalibration, "
            "and whether annual women-15-44 exposure removes long-horizon drift"
        ),
        "design": {
            "sizes": design["sizes"],
            "maximum_horizon": design["maximum_horizon"],
            "reported_horizons": report_horizons,
            "calibration_repetitions": repetitions,
            "independent_calibration_paths": paths_per_repetition,
            "strict_same_target_paths": True,
        },
        "by_size": by_size,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in source_files
        },
        "limits": [
            "synthetic World DGP, not historical or causal validation",
            "dynamic exposure is internal simulated women aged 15-44, not observed state exposure",
            "15 calibration repetitions give a coarse uncertainty distribution",
            "timing is machine-specific and not a production benchmark",
            "sex-share invariance assumes each denominator convention is recalibrated consistently",
            "the experiment does not validate the simulated age-sex structure against reality",
        ],
    }

    for row in by_size.values():
        assert row["constant_sex_share_check"][
            "max_abs_prediction_difference_after_recalibration"
        ] < 1e-9
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    result = diagnose(source, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n")
    compact = {}
    for size, row in result["by_size"].items():
        compact[size] = {
            "dynamic_scale_sd": row["dynamic_exposure_scale"]["sd"],
            "relative_scale_bias": row["relative_dynamic_scale_bias"],
            "ratio_invariance_max_error": row["constant_sex_share_check"][
                "max_abs_prediction_difference_after_recalibration"
            ],
            "scan_share_of_runtime": row["diagnostic_cost"][
                "exposure_scan_share_of_elapsed"
            ],
            "horizons": {
                horizon: {
                    "dynamic_rmse_median": values["dynamic_exposure_error"][
                        "rmse"
                    ]["median"],
                    "fixed_rmse_median": values[
                        "fixed_denominator_exposure_error"
                    ]["rmse"]["median"],
                    "dynamic_bias_median": values["dynamic_exposure_error"][
                        "bias"
                    ]["median"],
                }
                for horizon, values in row["horizons"].items()
            },
        }
    print(json.dumps(compact, indent=2))
