"""Run multi-seed long-horizon archive and checkpoint resource validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from population_simu.family_config import FamilyScenario
from population_simu.simulation_validation import validate_archived_resource_budget


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=50)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261006, 20261007, 20261008])
    parser.add_argument("--restore-after", type=int, default=25)
    parser.add_argument("--max-population", type=int, default=20_000)
    parser.add_argument("--max-households", type=int, default=10_000)
    parser.add_argument("--max-transfer-records", type=int, default=300_000)
    parser.add_argument("--max-archived-payload-bytes", type=int, default=10_000_000)
    parser.add_argument("--max-seconds-per-seed", type=float, default=180.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario = FamilyScenario.from_dict(json.loads(args.scenario.read_text(encoding="utf-8")))
    report = validate_archived_resource_budget(
        scenario,
        years=args.years,
        seeds=args.seeds,
        restore_after_years=args.restore_after,
        max_population=args.max_population,
        max_households=args.max_households,
        max_transfer_records=args.max_transfer_records,
        max_archived_payload_bytes=args.max_archived_payload_bytes,
        max_seconds_per_seed=args.max_seconds_per_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "years": args.years,
        "seeds": args.seeds,
        "all_checks_passed": report["all_checks_passed"],
        "runs": [
            {
                "seed": run["seed"],
                "population": run["final_population"],
                "households": run["final_households"],
                "records": run["transfer_records"],
                "payload_bytes": run["archived_payload_bytes"],
                "seconds": run["runtime_seconds"],
            }
            for run in report["runs"]
        ],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
