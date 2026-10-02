"""Reproduce the original family-size question using the existing toy models.

No model equations are changed here.  Seed ranges and standard deviations
describe Monte Carlo variation; they are not confidence intervals or empirical
estimates of children's survival or educational outcomes.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from population_simu.dynasty_experiment import DynastyParameters, run_cell as run_dynasty_cell
from population_simu.resource_experiment import run_cell as run_resource_cell


DEFAULT_SEEDS = (20261002, 20261003, 20261004, 20261005, 20261006)
RESOURCE_METRICS = (
    "investment_per_child", "mean_child_score", "per_child_success_rate",
    "family_any_success_rate", "mean_best_child_score", "expected_successful_children",
)
DYNASTY_METRICS = (
    "survival_to_final_generation", "extinction_before_final_generation",
    "mean_final_generation_descendants", "median_final_generation_descendants",
    "mean_total_descendants", "occupational_persistence_rate",
)


def dynasty_variants() -> dict[str, DynastyParameters]:
    baseline = DynastyParameters(material_deadline=58.0)
    return {
        "baseline": baseline,
        "lower_housing_pressure": replace(baseline, housing_pressure=0.20),
        "higher_welfare_floor": replace(baseline, welfare_floor=0.45),
        "lower_housing_and_higher_welfare": replace(
            baseline, housing_pressure=0.20, welfare_floor=0.45
        ),
    }


def summarize_replicates(rows: list[dict], metrics: tuple[str, ...]) -> dict[str, dict]:
    """Give equal weight to equally sized seed runs, using sample SD (ddof=1)."""
    if not rows:
        raise ValueError("At least one seed result is required")
    result = {}
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
        result[metric] = {
            "mean": statistics.fmean(values),
            "seed_min": min(values),
            "seed_max": max(values),
            "seed_sample_sd": statistics.stdev(values) if len(values) > 1 else None,
            "n_seeds": len(values),
        }
    return result


def validate_inputs(resources, children, trials, seeds, dynasty_resources, generations) -> None:
    if not resources or any(not math.isfinite(value) or value <= 0 for value in resources):
        raise ValueError("resources must contain finite positive values")
    if not math.isfinite(dynasty_resources) or dynasty_resources <= 0:
        raise ValueError("dynasty_resources must be finite and positive")
    if not children or any(type(value) is not int or value < 1 for value in children):
        raise ValueError("children must contain positive integers")
    if type(trials) is not int or trials < 1:
        raise ValueError("trials must be a positive integer")
    if type(generations) is not int or generations < 1:
        raise ValueError("generations must be a positive integer")
    if not seeds or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain distinct integers")
    if len(set(resources)) != len(resources) or len(set(children)) != len(children):
        raise ValueError("resources and children must not contain duplicate cells")


def source_hashes() -> dict[str, str]:
    paths = (
        "scripts/run_family_goal_baseline.py",
        "src/population_simu/resource_experiment.py",
        "src/population_simu/dynasty_experiment.py",
        "src/population_simu/capitals.py",
        "src/population_simu/occupations.py",
    )
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def run_baseline(
    *, resources=(5.0, 100.0, 300.0), children=(1, 2, 3), trials=1000,
    seeds=DEFAULT_SEEDS, dynasty_resources=100.0, generations=4,
) -> dict:
    resources, children, seeds = tuple(resources), tuple(children), tuple(seeds)
    validate_inputs(resources, children, trials, seeds, dynasty_resources, generations)
    variants = dynasty_variants()
    resource_cells = []
    for resource in resources:
        for count in children:
            runs = [
                {
                    "seed": seed,
                    "result": run_resource_cell(
                        resources=resource, children=count, trials=trials, seed=seed
                    ),
                }
                for seed in seeds
            ]
            resource_cells.append({
                "parameters": {"resources": resource, "children": count, "trials": trials},
                "replicates": runs,
                "summary": summarize_replicates([run["result"] for run in runs], RESOURCE_METRICS),
            })
    dynasty_cells = []
    for name, parameters in variants.items():
        for count in children:
            inputs = {
                "initial_resources": dynasty_resources, "initial_children": count,
                "trials": trials, "generations": generations,
                "founder_occupation": "professional",
            }
            runs = [
                {"seed": seed, "result": run_dynasty_cell(**inputs, seed=seed, parameters=parameters)}
                for seed in seeds
            ]
            dynasty_cells.append({
                "variant": name,
                "parameters": {**inputs, "dynasty_parameters": asdict(parameters)},
                "derived_capital_deadline": parameters.capital_deadline,
                "replicates": runs,
                "summary": summarize_replicates([run["result"] for run in runs], DYNASTY_METRICS),
            })
    cell_count = len(resource_cells) + len(dynasty_cells)
    return {
        "schema_version": 1,
        "kind": "original_family_goal_synthetic_baseline",
        "status": "exploratory_model_conditional_results",
        "model_equations_changed": False,
        "configuration": {
            "resource_levels": list(resources), "initial_child_counts": list(children),
            "dynasty_initial_resources": dynasty_resources, "generations": generations,
            "seeds": list(seeds), "trials_per_seed_per_cell": trials,
            "replicates_per_cell": len(seeds), "trials_per_cell": trials * len(seeds),
            "resource_cells": len(resource_cells), "dynasty_cells": len(dynasty_cells),
            "total_seed_runs": cell_count * len(seeds),
            "total_simulated_founder_family_trials": cell_count * len(seeds) * trials,
            "dynasty_variants": {name: asdict(params) for name, params in variants.items()},
            "dynasty_founder_capitals": {
                "financial": dynasty_resources, "human": 0.68, "social": 0.52,
                "political": 0.18, "cultural": 0.62, "housing": 0.68,
                "health": 0.82, "care_time": 0.78, "debt": 0.12,
            },
            "resource_success_score_threshold": 0.70,
        },
        "reproducibility": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "source_sha256": source_hashes(),
            "source_hash_basis": "Raw checked-out source bytes; includes driver and transitive model modules.",
            "randomness": (
                "The same numeric seed list is reused across cells. Conditional branches and child counts "
                "consume different numbers of draws, so this is NOT strict event-aligned common random numbers."
            ),
        },
        "aggregation": {
            "unit": "One equally sized seed run; arithmetic mean of model-returned rounded metrics.",
            "spread": "seed_min, seed_max, and sample standard deviation across seeds (ddof=1).",
            "single_seed_sd": None,
            "confidence_intervals": False,
            "interpretation": (
                "Seed spread describes Monte Carlo variation only. It excludes parameter, measurement, "
                "structural-model and real-world uncertainty. Means of medians or ratios are means across "
                "seed runs, not pooled medians or pooled occupational-persistence ratios."
            ),
        },
        "interpretation_limits": [
            "These are synthetic, model-conditional scenarios, not empirical estimates or causal policy effects.",
            "The resource model success cutoff of score >= 0.70 is preset; it is not calibrated educational attainment or observed success.",
            "Dynasty survival means at least one modeled descendant exists in the final generation; it is NOT real child or adult biological survival probability.",
            "Only the initial child count is fixed; later generations draw endogenous offspring counts (capped at four).",
            "The four dynasty variants change only housing_pressure and/or welfare_floor; material_deadline remains 58 and all other DynastyParameters stay fixed.",
            "Resource levels are model units. Equal initial resources do not imply equal future income, consumption, or accumulated costs.",
            "These toy models do not execute FamilyWorld, observed population migration, geography, or a monthly/daily simulation.",
        ],
        "resource_experiment": resource_cells,
        "dynasty_experiment": dynasty_cells,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", nargs="+", type=float, default=[5.0, 100.0, 300.0])
    parser.add_argument("--children", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--dynasty-resources", type=float, default=100.0)
    parser.add_argument("--generations", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("outputs/family_goal_baseline.json"))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        report = run_baseline(
            resources=args.resources, children=args.children, trials=args.trials,
            seeds=args.seeds, dynasty_resources=args.dynasty_resources, generations=args.generations,
        )
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "configuration": report["configuration"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
