"""Longer-horizon structural validation without adding or calibrating mechanisms."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import time

from .experiments import audit_experiment_world, source_hashes
from .family_config import FamilyScenario
from .family_world import FamilyWorld


def _advance(world: FamilyWorld, years: int, *, budgets: dict[str, float | int]) -> tuple[
        list[dict[str, object]], list[dict[str, object]]]:
    audits = []
    trajectory = []
    started = time.perf_counter()
    for _ in range(years):
        step_started = time.perf_counter()
        before = len(world.living_people)
        stats = world.step()
        audit = audit_experiment_world(world, previous_population=before, stats=stats)
        if not audit["ok"]:
            raise ValueError(f"structural validation failed in {world.year}: {audit['issues'][:8]}")
        audits.append(audit)
        elapsed = time.perf_counter() - started
        row = {
            "year": world.year,
            "population": len(world.living_people),
            "households": len(world.households),
            "registered_ledger_entities": len(world.transfer_ledger.entities),
            "transfer_records": world.transfer_ledger.record_count,
            "resident_transfer_records": len(world.transfer_ledger.records),
            "transfer_archive_bytes": world.transfer_ledger.archive_bytes,
            "step_seconds": round(time.perf_counter() - step_started, 6),
            "cumulative_seconds": round(elapsed, 6),
        }
        trajectory.append(row)
        checks = {
            "population": budgets["max_population"],
            "households": budgets["max_households"],
            "transfer_records": budgets["max_transfer_records"],
            "cumulative_seconds": budgets["max_seconds_per_run"],
        }
        exceeded = [name for name, limit in checks.items() if row[name] > limit]
        if exceeded:
            raise ValueError(
                f"structural validation budget exceeded in {world.year}: {', '.join(exceeded)}"
            )
    return audits, trajectory


def validate_scenario(scenario: FamilyScenario, *, years: int,
                      seeds: list[int], max_population: int = 20_000,
                      max_households: int = 10_000,
                      max_transfer_records: int = 200_000,
                      max_seconds_per_run: float = 120.0) -> dict[str, object]:
    if type(years) is not int or years < 2:
        raise ValueError("validation years must be an integer of at least two")
    if not seeds or len(set(seeds)) != len(seeds) or any(
            type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError("validation seeds must be distinct nonnegative integers")
    if scenario.simulation.start_year + years > scenario.simulation.end_year:
        raise ValueError("validation exceeds scenario end_year")
    budgets = {
        "max_population": max_population,
        "max_households": max_households,
        "max_transfer_records": max_transfer_records,
        "max_seconds_per_run": max_seconds_per_run,
    }
    if any(type(budgets[name]) is not int or budgets[name] < 1 for name in
           ("max_population", "max_households", "max_transfer_records")):
        raise ValueError("count budgets must be positive integers")
    if type(max_seconds_per_run) not in (int, float) or max_seconds_per_run <= 0:
        raise ValueError("runtime budget must be a positive number")
    scenario.validate()

    runs = []
    for seed in seeds:
        seeded = deepcopy(replace(
            scenario,
            simulation=replace(scenario.simulation, random_seed=seed),
        ))
        world = FamilyWorld(seeded)
        world.begin_exogenous_path_recording()
        audits, trajectory = _advance(world, years, budgets=budgets)
        path_manifest = world.freeze_exogenous_path().manifest()
        expected_events = years * (
            len(world.countries) + sum(len(regions) for regions in world.regions.values())
        )
        if path_manifest["events"] != expected_events:
            raise ValueError("exogenous path is incomplete")
        genealogy_audit = world.genealogy(next(iter(world.people)))
        transfer_summary = world.transfer_ledger.summary()
        floor_rows = [
            row for row in transfer_summary if row["kind"] == "minimum_resource_floor"
        ]
        runs.append({
            "seed": seed,
            "start_year": scenario.simulation.start_year,
            "end_year": world.year,
            "final_population": len(world.living_people),
            "final_households": len(world.households),
            "path_manifest": path_manifest,
            "expected_path_events": expected_events,
            "transfer_records": world.transfer_ledger.audit()["record_count"],
            "transfer_summary_rows": len(transfer_summary),
            "transfer_kinds": sorted({str(row["kind"]) for row in transfer_summary}),
            "minimum_resource_floor": {
                "records": sum(int(row["records"]) for row in floor_rows),
                "cash_amount": sum(float(row["cash_amount"]) for row in floor_rows),
                "interpretation": "explicit accounting of existing model floor; not household-origin cash",
            },
            "genealogy_people": audits[-1]["genealogy"]["people"],
            "sample_genealogy_query_json_safe": bool(
                json.dumps(genealogy_audit, allow_nan=False)
            ),
            "annual_audits": len(audits),
            "resource_trajectory": trajectory,
            "runtime_seconds": trajectory[-1]["cumulative_seconds"],
            "max_population_observed": max(row["population"] for row in trajectory),
            "max_households_observed": max(row["households"] for row in trajectory),
            "max_transfer_records_observed": max(
                row["transfer_records"] for row in trajectory
            ),
            "all_population_balances_closed": all(
                audit["population_balance"]["balanced"] for audit in audits
            ),
            "all_regional_balances_closed": all(
                audit["regional_population_balance"]["all_regions_balanced"]
                for audit in audits
            ),
            "all_transfer_audits_passed": all(
                audit["transfer_ledger"]["ok"] for audit in audits
            ),
            "all_genealogy_audits_passed": all(
                audit["genealogy"]["ok"] for audit in audits
            ),
        })

    # A separate split-run contract verifies that checkpoint restoration does not
    # change the continuation. This is deterministic replay, not empirical fit.
    split = years // 2
    seeded = deepcopy(replace(
        scenario,
        simulation=replace(scenario.simulation, random_seed=seeds[0]),
    ))
    prefix = FamilyWorld(seeded)
    prefix.begin_exogenous_path_recording()
    _advance(prefix, split, budgets=budgets)
    checkpoint = prefix.checkpoint()
    left, right = checkpoint.restore(), checkpoint.restore()
    _advance(left, years - split, budgets=budgets)
    _advance(right, years - split, budgets=budgets)
    left_fingerprint = left.checkpoint().fingerprint
    right_fingerprint = right.checkpoint().fingerprint
    continuation = {
        "split_year": checkpoint.year,
        "left_fingerprint": left_fingerprint,
        "right_fingerprint": right_fingerprint,
        "identical": left_fingerprint == right_fingerprint,
    }
    if not continuation["identical"]:
        raise ValueError("checkpoint continuations diverged")

    report = {
        "schema_version": 1,
        "kind": "simulation_structural_validation",
        "scope": "internal consistency and reproducibility; not empirical accuracy",
        "configuration": {
            "scenario": asdict(scenario),
            "years": years,
            "seeds": list(seeds),
            "budgets": budgets,
        },
        "source_sha256": source_hashes(),
        "runs": runs,
        "checkpoint_continuation": continuation,
        "all_checks_passed": all(
            run[flag]
            for run in runs
            for flag in (
                "all_population_balances_closed",
                "all_regional_balances_closed",
                "all_transfer_audits_passed",
                "all_genealogy_audits_passed",
            )
        ) and continuation["identical"],
        "accuracy_boundary": {
            "supports": [
                "deterministic implementation checks",
                "population and regional flow conservation",
                "external-path completeness",
                "transfer and genealogy referential integrity",
            ],
            "does_not_support": [
                "historical predictive accuracy",
                "parameter identification",
                "causal policy effects",
                "real-world forecast validity",
            ],
        },
    }
    # Fail before export if a future change introduces NaN or Infinity.
    json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return report


def validate_scenario_file(path: Path, *, years: int, seeds: list[int],
                           **budgets: float | int) -> dict[str, object]:
    scenario = FamilyScenario.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return validate_scenario(scenario, years=years, seeds=seeds, **budgets)


def validate_ledger_archiving(scenario: FamilyScenario, *, years: int, seed: int) -> dict[str, object]:
    """Compare full and annually archived ledgers under identical simulation paths."""
    if type(years) is not int or years < 2 or type(seed) is not int or seed < 0:
        raise ValueError("archiving validation requires years >= 2 and a nonnegative seed")
    if scenario.simulation.start_year + years > scenario.simulation.end_year:
        raise ValueError("archiving validation exceeds scenario end_year")
    seeded = deepcopy(replace(
        scenario, simulation=replace(scenario.simulation, random_seed=seed)
    ))
    full = FamilyWorld(seeded)
    compact = FamilyWorld(deepcopy(seeded))
    full.begin_exogenous_path_recording()
    compact.begin_exogenous_path_recording()
    archive_manifests = []
    checkpoints = []
    full_step_seconds = 0.0
    compact_step_seconds = 0.0
    milestone_years = {max(2, years // 4), max(2, years // 2), years}
    for elapsed_years in range(1, years + 1):
        started = time.perf_counter()
        full.step()
        full_step_seconds += time.perf_counter() - started
        started = time.perf_counter()
        compact.step()
        compact_step_seconds += time.perf_counter() - started
        manifest = compact.transfer_ledger.archive_before(compact.year + 1)
        if manifest is not None:
            archive_manifests.append(manifest)
        if [asdict(row) for row in full.history] != [asdict(row) for row in compact.history]:
            raise ValueError(f"ledger archiving changed model history in {compact.year}")
        if elapsed_years in milestone_years:
            full_bytes = full.transfer_ledger.resident_json_bytes
            compact_bytes = compact.transfer_ledger.storage_bytes
            checkpoints.append({
                "elapsed_years": elapsed_years,
                "year": full.year,
                "population": len(full.living_people),
                "households": len(full.households),
                "transfer_records": full.transfer_ledger.record_count,
                "full_canonical_json_bytes": full_bytes,
                "archived_payload_bytes": compact_bytes,
                "archived_to_full_storage_ratio": compact_bytes / full_bytes if full_bytes else 0.0,
                "full_cumulative_step_seconds": round(full_step_seconds, 6),
                "archived_cumulative_step_seconds": round(compact_step_seconds, 6),
            })
    full_summary = full.transfer_ledger.summary()
    compact_summary = compact.transfer_ledger.summary()
    same_people = {key: asdict(value) for key, value in full.people.items()} == {
        key: asdict(value) for key, value in compact.people.items()
    }
    same_households = {key: asdict(value) for key, value in full.households.items()} == {
        key: asdict(value) for key, value in compact.households.items()
    }
    same_paths = full.freeze_exogenous_path().as_dict() == compact.freeze_exogenous_path().as_dict()
    same_summaries = full_summary == compact_summary
    same_rng = full.rng.getstate() == compact.rng.getstate()
    same_internal_drivers = all(
        getattr(full, name) == getattr(compact, name)
        for name in (
            "_shock_residual", "_economic_cycle", "_technology",
            "_environmental_stress", "_government_funds", "_regional_transfers",
        )
    )
    sample_entity = next(iter(full.transfer_ledger.entities))
    same_entity_query = [asdict(row) for row in full.transfer_ledger.query(entity=sample_entity)] == [
        asdict(row) for row in compact.transfer_ledger.query(entity=sample_entity)
    ]
    full_payload_bytes = full.transfer_ledger.resident_json_bytes
    report = {
        "schema_version": 1,
        "kind": "transfer_ledger_archiving_validation",
        "scope": "storage representation equivalence; not empirical validation",
        "configuration": {"scenario": scenario.name, "years": years, "seed": seed},
        "source_sha256": source_hashes(),
        "equivalence": {
            "history": True,
            "people": same_people,
            "households": same_households,
            "exogenous_path": same_paths,
            "transfer_summary": same_summaries,
            "legacy_rng_state": same_rng,
            "internal_driver_state": same_internal_drivers,
            "sample_entity_query": same_entity_query,
        },
        "full_ledger": {
            "record_count": full.transfer_ledger.record_count,
            "resident_records": len(full.transfer_ledger.records),
            "estimated_canonical_json_bytes": full_payload_bytes,
            "audit_ok": full.transfer_ledger.audit()["ok"],
        },
        "archived_ledger": {
            "record_count": compact.transfer_ledger.record_count,
            "resident_records": len(compact.transfer_ledger.records),
            "archive_count": len(compact.transfer_ledger.archives),
            "compressed_bytes": compact.transfer_ledger.archive_bytes,
            "estimated_payload_bytes": compact.transfer_ledger.storage_bytes,
            "compression_ratio_vs_full_json": (
                compact.transfer_ledger.storage_bytes / full_payload_bytes
                if full_payload_bytes else 0.0
            ),
            "audit_ok": compact.transfer_ledger.audit()["ok"],
            "archive_manifests": archive_manifests,
        },
        "scaling_checkpoints": checkpoints,
        "runtime_note": "wall-clock measurements are machine-specific and are not accuracy evidence",
    }
    report["all_checks_passed"] = (
        all(report["equivalence"].values())
        and report["full_ledger"]["audit_ok"]
        and report["archived_ledger"]["audit_ok"]
        and report["full_ledger"]["record_count"] == report["archived_ledger"]["record_count"]
    )
    if not report["all_checks_passed"]:
        raise ValueError("ledger archiving equivalence failed")
    json.dumps(report, ensure_ascii=False, allow_nan=False)
    return report
