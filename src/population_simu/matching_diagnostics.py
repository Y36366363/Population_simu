"""Read-only cost diagnostics for the existing household matching mechanism."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import statistics
import time
from typing import Callable

from .family_checkpoint import fingerprint_world
from .family_config import FamilyScenario
from .family_models import FamilyPerson
from .family_world import FamilyWorld


Clock = Callable[[], int]


def _rng_fingerprint(world: FamilyWorld) -> str:
    return hashlib.sha256(repr(world.rng.getstate()).encode("utf-8")).hexdigest()


def _matching_weight(woman: FamilyPerson, man: FamilyPerson, country: object) -> float:
    """Reproduce the current deterministic weight formula without drawing RNG."""
    status_distance = abs(man.economic_status - woman.economic_status)
    education_distance = abs(man.education_years - woman.education_years) / 12
    housing_distance = abs(man.housing_security - woman.housing_security)
    distance = (
        0.52 * status_distance
        + 0.30 * education_distance
        + 0.18 * housing_distance
    )
    weight = 0.08 + math.exp(
        -5.2 * country.assortative_mating_strength * distance
    )
    if (
        man.faction_id is not None
        and woman.faction_id is not None
        and man.faction_id == woman.faction_id
    ):
        weight *= 1.25
    elite_mismatch = (man.economic_status >= 0.72) != (
        woman.economic_status >= 0.72
    )
    if elite_mismatch:
        weight *= 1 - country.elite_marriage_closure
    return max(0.002, weight)


def audit_matching_cost(
    world: FamilyWorld,
    *,
    repeats: int = 9,
    clock_ns: Clock = time.perf_counter_ns,
) -> dict[str, object]:
    """Time dry-run filter stages while proving the world and RNG are untouched.

    The dry run observes a checkpoint, so it cannot reproduce removals caused by
    successful matches within the production phase. It is intended to attribute
    deterministic filtering and weighting cost, not to estimate marriage rates.
    """
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    before_world = fingerprint_world(world)
    before_rng = _rng_fingerprint(world)

    started = clock_ns()
    pools: dict[str, dict[str, list[FamilyPerson]]] = {}
    for person in world.living_people:
        if 22 <= person.age <= 50 and not person.partnered:
            sexes = pools.setdefault(person.country_id, {"F": [], "M": []})
            sexes[person.sex].append(person)
    pool_build_ns = clock_ns() - started

    prepared = []
    started = clock_ns()
    for country_id, sexes in pools.items():
        by_age = world._men_by_woman_age(sexes["M"])
        prepared.append((country_id, sexes["F"], by_age))
    age_index_ns = clock_ns() - started

    stage_samples: dict[str, list[int]] = {
        "active_filter": [],
        "different_household_filter": [],
        "maternal_kin_filter": [],
        "paternal_kin_filter": [],
        "weight_calculation": [],
    }
    counts: dict[str, int] | None = None
    weight_checksum = 0.0
    for repeat in range(repeats):
        active_rows = []
        started = clock_ns()
        for country_id, women, by_age in prepared:
            for woman in women:
                active_rows.append((
                    country_id,
                    woman,
                    [man for man in by_age[woman.age] if not man.partnered],
                ))
        stage_samples["active_filter"].append(clock_ns() - started)

        household_rows = []
        started = clock_ns()
        for country_id, woman, men in active_rows:
            household_rows.append((
                country_id,
                woman,
                [man for man in men if man.household_id != woman.household_id],
            ))
        stage_samples["different_household_filter"].append(clock_ns() - started)

        maternal_rows = []
        started = clock_ns()
        for country_id, woman, men in household_rows:
            maternal_rows.append((
                country_id,
                woman,
                [
                    man for man in men
                    if not (
                        man.mother_id is not None
                        and man.mother_id == woman.mother_id
                    )
                ],
            ))
        stage_samples["maternal_kin_filter"].append(clock_ns() - started)

        paternal_rows = []
        started = clock_ns()
        for country_id, woman, men in maternal_rows:
            paternal_rows.append((
                country_id,
                woman,
                [
                    man for man in men
                    if not (
                        man.father_id is not None
                        and man.father_id == woman.father_id
                    )
                ],
            ))
        stage_samples["paternal_kin_filter"].append(clock_ns() - started)

        started = clock_ns()
        checksum = 0.0
        for country_id, woman, men in paternal_rows:
            country = world.countries[country_id]
            checksum += sum(_matching_weight(woman, man, country) for man in men)
        stage_samples["weight_calculation"].append(clock_ns() - started)
        weight_checksum = checksum

        if repeat == 0:
            age_count = sum(len(by_age[woman.age]) for _, women, by_age in prepared for woman in women)
            active_count = sum(len(men) for _, _, men in active_rows)
            household_count = sum(len(men) for _, _, men in household_rows)
            maternal_count = sum(len(men) for _, _, men in maternal_rows)
            paternal_count = sum(len(men) for _, _, men in paternal_rows)
            counts = {
                "countries": len(prepared),
                "women": sum(len(women) for _, women, _ in prepared),
                "men": sum(len(sexes["M"]) for sexes in pools.values()),
                "age_window_candidates": age_count,
                "active_candidates": active_count,
                "after_household_filter": household_count,
                "after_maternal_filter": maternal_count,
                "after_paternal_filter": paternal_count,
                "rejected_already_partnered": age_count - active_count,
                "rejected_same_household": active_count - household_count,
                "rejected_shared_mother": household_count - maternal_count,
                "rejected_shared_father": maternal_count - paternal_count,
                "weights_evaluated": paternal_count,
            }

    assert counts is not None
    timing = {}
    for name, samples in stage_samples.items():
        median_ns = statistics.median(samples)
        denominator = (
            counts["age_window_candidates"]
            if name == "active_filter"
            else counts["active_candidates"]
            if name == "different_household_filter"
            else counts["after_household_filter"]
            if name == "maternal_kin_filter"
            else counts["after_maternal_filter"]
            if name == "paternal_kin_filter"
            else counts["weights_evaluated"]
        )
        timing[name] = {
            "median_ns": int(median_ns),
            "min_ns": min(samples),
            "max_ns": max(samples),
            "input_candidates": denominator,
            "median_ns_per_input": round(median_ns / denominator, 3)
            if denominator else None,
        }

    after_world = fingerprint_world(world)
    after_rng = _rng_fingerprint(world)
    result = {
        "year": world.year,
        "repeats": repeats,
        "counts": counts,
        "timing": {
            "pool_build_ns": pool_build_ns,
            "age_index_ns": age_index_ns,
            "dry_run_stages": timing,
        },
        "weight_checksum": round(weight_checksum, 12),
        "read_only_checks": {
            "world_fingerprint_unchanged": before_world == after_world,
            "rng_state_unchanged": before_rng == after_rng,
        },
        "interpretation_boundary": [
            "checkpoint dry-runs do not reproduce within-phase successful-match removals",
            "sequential stage timing includes temporary-list allocation and is diagnostic only",
            "no random draw, candidate reorder, weight reorder, or model-state mutation occurs",
        ],
    }
    json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return result


def profile_matching_costs(
    scenario: FamilyScenario,
    *,
    years: int,
    checkpoints: list[int],
    seeds: list[int],
    repeats: int = 9,
) -> dict[str, object]:
    """Run paired control/audited worlds and check every annual fingerprint."""
    if type(years) is not int or years < 1:
        raise ValueError("years must be a positive integer")
    if not checkpoints or checkpoints != sorted(set(checkpoints)):
        raise ValueError("checkpoints must be sorted and distinct")
    if checkpoints[0] < 1 or checkpoints[-1] > years:
        raise ValueError("checkpoints must fall within the simulation horizon")
    if not seeds or len(seeds) != len(set(seeds)) or any(
        type(seed) is not int or seed < 0 for seed in seeds
    ):
        raise ValueError("seeds must be distinct nonnegative integers")
    if scenario.simulation.start_year + years > scenario.simulation.end_year:
        raise ValueError("profiling exceeds scenario end_year")
    scenario.validate()

    runs = []
    checkpoint_set = set(checkpoints)
    for seed in seeds:
        seeded = deepcopy(replace(
            scenario, simulation=replace(scenario.simulation, random_seed=seed)
        ))
        control = FamilyWorld(deepcopy(seeded))
        audited = FamilyWorld(deepcopy(seeded))
        yearly = []
        audits = []
        for elapsed in range(1, years + 1):
            control.step()
            control.transfer_ledger.archive_before(control.year + 1)
            audited.step()
            audited.transfer_ledger.archive_before(audited.year + 1)
            control_fingerprint = fingerprint_world(control)
            audited_fingerprint = fingerprint_world(audited)
            yearly.append({
                "year": audited.year,
                "fingerprint": audited_fingerprint,
                "paired_control_equal": control_fingerprint == audited_fingerprint,
            })
            if elapsed in checkpoint_set:
                audits.append(audit_matching_cost(audited, repeats=repeats))
        runs.append({
            "seed": seed,
            "yearly_fingerprints": yearly,
            "all_paired_years_equal": all(
                row["paired_control_equal"] for row in yearly
            ),
            "audits": audits,
            "final_population": len(audited.living_people),
            "final_households": len(audited.households),
            "final_transfer_records": audited.transfer_ledger.record_count,
        })

    report = {
        "schema_version": 1,
        "kind": "read_only_marriage_matching_cost_profile",
        "scope": "checkpoint filtering and weighting diagnostics; not model validation",
        "configuration": {
            "scenario": scenario.name,
            "years": years,
            "checkpoints": checkpoints,
            "seeds": seeds,
            "repeats": repeats,
            "annual_ledger_archiving": True,
        },
        "runs": runs,
        "acceptance": {
            "all_paired_years_equal": all(run["all_paired_years_equal"] for run in runs),
            "all_audits_read_only": all(
                audit["read_only_checks"]["world_fingerprint_unchanged"]
                and audit["read_only_checks"]["rng_state_unchanged"]
                for run in runs for audit in run["audits"]
            ),
            "timing_is_not_an_acceptance_gate": True,
        },
    }
    json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return report


def summarize_matching_cost_report(report: dict[str, object]) -> dict[str, object]:
    """Aggregate checkpoint counts and timing without changing acceptance claims."""
    if report.get("kind") != "read_only_marriage_matching_cost_profile":
        raise ValueError("input is not a read-only marriage matching cost profile")
    runs = report.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("profile must contain at least one run")
    audit_years = sorted({
        int(audit["year"])
        for run in runs
        for audit in run["audits"]
    })
    if any(
        [int(audit["year"]) for audit in run["audits"]] != audit_years
        for run in runs
    ):
        raise ValueError("every seed must contain the same ordered audit years")

    stages = (
        "active_filter",
        "different_household_filter",
        "maternal_kin_filter",
        "paternal_kin_filter",
        "weight_calculation",
    )
    checkpoints = []
    for year in audit_years:
        audits = [
            next(audit for audit in run["audits"] if int(audit["year"]) == year)
            for run in runs
        ]
        stage_rows = {}
        totals = [
            sum(
                int(audit["timing"]["dry_run_stages"][stage]["median_ns"])
                for stage in stages
            )
            for audit in audits
        ]
        for stage in stages:
            elapsed = [
                int(audit["timing"]["dry_run_stages"][stage]["median_ns"])
                for audit in audits
            ]
            per_input = [
                audit["timing"]["dry_run_stages"][stage]["median_ns_per_input"]
                for audit in audits
                if audit["timing"]["dry_run_stages"][stage]["median_ns_per_input"] is not None
            ]
            stage_rows[stage] = {
                "median_ms": round(statistics.median(elapsed) / 1_000_000, 6),
                "median_ns_per_input": round(statistics.median(per_input), 3)
                if per_input else None,
                "median_share_of_measured_stages": round(statistics.median(
                    value / total if total else 0.0
                    for value, total in zip(elapsed, totals)
                ), 6),
            }
        rejection_specs = {
            "same_household": ("rejected_same_household", "active_candidates"),
            "shared_mother": ("rejected_shared_mother", "after_household_filter"),
            "shared_father": ("rejected_shared_father", "after_maternal_filter"),
        }
        rejection = {}
        for name, (numerator, denominator) in rejection_specs.items():
            values = [int(audit["counts"][numerator]) for audit in audits]
            rates = [
                int(audit["counts"][numerator]) / int(audit["counts"][denominator])
                if int(audit["counts"][denominator]) else 0.0
                for audit in audits
            ]
            rejection[name] = {
                "median_candidates_rejected": statistics.median(values),
                "median_rejection_rate": round(statistics.median(rates), 8),
            }
        checkpoints.append({
            "year": year,
            "seed_count": len(audits),
            "median_counts": {
                key: statistics.median(int(audit["counts"][key]) for audit in audits)
                for key in (
                    "women",
                    "men",
                    "age_window_candidates",
                    "weights_evaluated",
                )
            },
            "rejection": rejection,
            "stages": stage_rows,
        })
    summary = {
        "schema_version": 1,
        "kind": "read_only_marriage_matching_cost_summary",
        "source_configuration": report["configuration"],
        "source_acceptance": report["acceptance"],
        "checkpoints": checkpoints,
        "interpretation_boundary": [
            "timing shares cover only sequential dry-run stages, not the production phase",
            "low rejection rates do not imply kinship checks can be removed",
            "weight timing does not authorize formula, ordering, or RNG changes",
        ],
    }
    json.dumps(summary, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return summary
