"""Deterministic profiling of existing simulation phases; no model mechanisms."""

from __future__ import annotations

import cProfile
from copy import deepcopy
from dataclasses import replace
import json
import math
import statistics
import time

from .experiments import source_hashes
from .family_config import FamilyScenario
from .family_world import FamilyWorld


STEP_PHASES = (
    "_update_environment",
    "_update_economic_cycle",
    "_health_and_care",
    "_update_childcare_support",
    "_allocate_resources",
    "_mature_young_adults",
    "_career_transitions",
    "_earn_resources",
    "_divorces",
    "_form_family_branches",
    "_births",
    "_internal_migration",
    "_international_migration",
    "_deaths",
    "_population_locations",
    "_update_clan_peaks",
    "_update_government_funds",
    "_summaries",
    "_region_snapshot",
)

# These are reported for diagnosis but excluded from the additive phase total:
# population-flow accounting contains a nested population-location scan, while
# the other helpers are called inside one or more direct step phases.
NESTED_DIAGNOSTICS = (
    "_population_flow_ledger",
    "_desired_children",
    "_region_capacity_pressure",
    "living_people",
    "same_region",
    "same_kin",
    "shares_occupation",
)


def _profile_entries(profile: cProfile.Profile) -> dict[str, dict[str, float | int]]:
    wanted = {"step", "archive_before", *STEP_PHASES, *NESTED_DIAGNOSTICS}
    rows = {name: {"calls": 0, "self_seconds": 0.0, "cumulative_seconds": 0.0}
            for name in wanted}
    for entry in profile.getstats():
        code = entry.code
        name = getattr(code, "co_name", "")
        if name not in wanted:
            continue
        row = rows[name]
        row["calls"] += int(entry.callcount)
        row["self_seconds"] += float(entry.inlinetime)
        row["cumulative_seconds"] += float(entry.totaltime)
    return rows


def _profile_segment(world: FamilyWorld, years: int) -> dict[str, object]:
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    for _ in range(years):
        world.step()
        world.transfer_ledger.archive_before(world.year + 1)
    profiler.disable()
    wall_seconds = time.perf_counter() - started
    entries = _profile_entries(profiler)
    step_seconds = float(entries["step"]["cumulative_seconds"])
    phases = {}
    for name in STEP_PHASES:
        entry = entries[name]
        cumulative = float(entry["cumulative_seconds"])
        phases[name] = {
            "calls": int(entry["calls"]),
            "self_seconds": round(float(entry["self_seconds"]), 6),
            "cumulative_seconds": round(cumulative, 6),
            "seconds_per_year": round(cumulative / years, 6),
            "share_of_step": round(cumulative / step_seconds, 6) if step_seconds else 0.0,
        }
    attributed = sum(float(entries[name]["cumulative_seconds"]) for name in STEP_PHASES)
    diagnostics = {
        name: {
            "calls": int(entries[name]["calls"]),
            "self_seconds": round(float(entries[name]["self_seconds"]), 6),
            "cumulative_seconds": round(float(entries[name]["cumulative_seconds"]), 6),
            "seconds_per_year": round(
                float(entries[name]["cumulative_seconds"]) / years, 6
            ),
        }
        for name in NESTED_DIAGNOSTICS
    }
    return {
        "years": years,
        "start_year": world.year - years,
        "end_year": world.year,
        "end_population": len(world.living_people),
        "end_households": len(world.households),
        "end_transfer_records": world.transfer_ledger.record_count,
        "wall_seconds": round(wall_seconds, 6),
        "step_cumulative_seconds": round(step_seconds, 6),
        "step_seconds_per_year": round(step_seconds / years, 6),
        "archive_cumulative_seconds": round(
            float(entries["archive_before"]["cumulative_seconds"]), 6
        ),
        "archive_seconds_per_year": round(
            float(entries["archive_before"]["cumulative_seconds"]) / years, 6
        ),
        "unattributed_step_seconds": round(max(0.0, step_seconds - attributed), 6),
        "phases": phases,
        "nested_diagnostics": diagnostics,
    }


def profile_simulation_phases(
    scenario: FamilyScenario,
    *,
    years: int,
    seeds: list[int],
    split_after_years: int | None = None,
) -> dict[str, object]:
    """Compare direct step-phase costs before and after a fixed time split."""
    if type(years) is not int or years < 4:
        raise ValueError("profiling years must be an integer of at least four")
    split = years // 2 if split_after_years is None else split_after_years
    if type(split) is not int or not 1 <= split < years:
        raise ValueError("split_after_years must fall within the simulated interval")
    if not seeds or len(set(seeds)) != len(seeds) or any(
            type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError("profiling seeds must be distinct nonnegative integers")
    if scenario.simulation.start_year + years > scenario.simulation.end_year:
        raise ValueError("profiling exceeds scenario end_year")
    scenario.validate()
    runs = []
    for seed in seeds:
        seeded = deepcopy(replace(
            scenario, simulation=replace(scenario.simulation, random_seed=seed)
        ))
        world = FamilyWorld(seeded)
        early = _profile_segment(world, split)
        late = _profile_segment(world, years - split)
        phase_growth = {}
        for name in STEP_PHASES:
            early_rate = float(early["phases"][name]["seconds_per_year"])
            late_rate = float(late["phases"][name]["seconds_per_year"])
            phase_growth[name] = {
                "early_seconds_per_year": early_rate,
                "late_seconds_per_year": late_rate,
                "absolute_increase_seconds_per_year": round(late_rate - early_rate, 6),
                "late_to_early_ratio": round(late_rate / early_rate, 6)
                if early_rate > 0 else None,
            }
        runs.append({
            "seed": seed,
            "early": early,
            "late": late,
            "step_late_to_early_ratio": round(
                float(late["step_seconds_per_year"]) / float(early["step_seconds_per_year"]), 6
            ),
            "population_late_to_early_endpoint_ratio": round(
                int(late["end_population"]) / int(early["end_population"]), 6
            ),
            "households_late_to_early_endpoint_ratio": round(
                int(late["end_households"]) / int(early["end_households"]), 6
            ),
            "phase_growth": phase_growth,
        })

    aggregate = []
    for name in STEP_PHASES:
        increases = [float(run["phase_growth"][name]["absolute_increase_seconds_per_year"])
                     for run in runs]
        ratios = [run["phase_growth"][name]["late_to_early_ratio"] for run in runs]
        finite_ratios = [float(value) for value in ratios
                         if value is not None and math.isfinite(float(value))]
        aggregate.append({
            "phase": name,
            "median_absolute_increase_seconds_per_year": round(statistics.median(increases), 6),
            "median_late_to_early_ratio": round(statistics.median(finite_ratios), 6)
            if finite_ratios else None,
        })
    aggregate.sort(
        key=lambda row: float(row["median_absolute_increase_seconds_per_year"]), reverse=True
    )
    report = {
        "schema_version": 1,
        "kind": "family_world_phase_profile",
        "scope": "runtime attribution for existing phases; not empirical or causal validation",
        "configuration": {
            "scenario": scenario.name,
            "years": years,
            "split_after_years": split,
            "seeds": list(seeds),
            "annual_ledger_archiving": True,
            "profiler": "cProfile deterministic instrumentation",
        },
        "source_sha256": source_hashes(),
        "runs": runs,
        "phase_growth_ranking": aggregate,
        "median_step_late_to_early_ratio": round(statistics.median(
            float(run["step_late_to_early_ratio"]) for run in runs
        ), 6),
        "interpretation_boundary": [
            "profiler timings are machine- and load-specific",
            "ranked direct step phases are additive; nested diagnostics are excluded from ranking",
            "association with entity growth does not identify causal model effects",
            "runtime profiling does not improve historical predictive validity",
        ],
    }
    json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return report
