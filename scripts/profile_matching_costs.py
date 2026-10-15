"""Profile read-only matching filters at paired simulation checkpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu.family_config import FamilyScenario
from population_simu.matching_diagnostics import profile_matching_costs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=50)
    parser.add_argument("--checkpoints", type=int, nargs="+", default=[25, 50])
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[20261006, 20261007, 20261008]
    )
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario = FamilyScenario.from_dict(
        json.loads(args.scenario.read_text(encoding="utf-8"))
    )
    report = profile_matching_costs(
        scenario,
        years=args.years,
        checkpoints=args.checkpoints,
        seeds=args.seeds,
        repeats=args.repeats,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "acceptance": report["acceptance"],
        "runs": [
            {
                "seed": run["seed"],
                "population": run["final_population"],
                "households": run["final_households"],
            }
            for run in report["runs"]
        ],
    }, ensure_ascii=False))
    acceptance = report["acceptance"]
    return 0 if acceptance["all_paired_years_equal"] and acceptance["all_audits_read_only"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
