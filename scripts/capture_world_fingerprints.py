"""Capture yearly complete-state fingerprints for strict refactor equivalence."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu.family_checkpoint import fingerprint_world
from population_simu.family_config import FamilyScenario
from population_simu.family_world import FamilyWorld


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario_bytes = args.scenario.read_bytes()
    scenario = FamilyScenario.from_dict(json.loads(scenario_bytes))
    if args.years < 1 or scenario.simulation.start_year + args.years > scenario.simulation.end_year:
        raise SystemExit("invalid fingerprint horizon")
    if not args.seeds or len(args.seeds) != len(set(args.seeds)):
        raise SystemExit("fingerprint seeds must be distinct")
    runs = []
    for seed in args.seeds:
        seeded = deepcopy(replace(
            scenario, simulation=replace(scenario.simulation, random_seed=seed)
        ))
        world = FamilyWorld(seeded)
        yearly = []
        step_seconds = []
        for _ in range(args.years):
            started = time.perf_counter()
            world.step()
            step_seconds.append(time.perf_counter() - started)
            world.transfer_ledger.archive_before(world.year + 1)
            yearly.append({"year": world.year, "fingerprint": fingerprint_world(world)})
        runs.append({
            "seed": seed,
            "yearly_fingerprints": yearly,
            "final_population": len(world.living_people),
            "final_households": len(world.households),
            "transfer_records": world.transfer_ledger.record_count,
            "rng_state_sha256": hashlib.sha256(
                repr(world.rng.getstate()).encode("utf-8")
            ).hexdigest(),
            "step_seconds": round(sum(step_seconds), 6),
            "step_seconds_per_year": round(sum(step_seconds) / args.years, 6),
        })
    family_world_path = ROOT / "src/population_simu/family_world.py"
    report = {
        "schema_version": 1,
        "kind": "world_fingerprint_capture",
        "label": args.label,
        "scope": "strict implementation equivalence; timings are machine-specific",
        "configuration": {
            "scenario": scenario.name,
            "scenario_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
            "years": args.years,
            "seeds": args.seeds,
            "annual_ledger_archiving": True,
        },
        "family_world_sha256": hashlib.sha256(family_world_path.read_bytes()).hexdigest(),
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "label": args.label,
        "family_world_sha256": report["family_world_sha256"],
        "runs": [{"seed": run["seed"], "step_seconds": run["step_seconds"]}
                 for run in runs],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
