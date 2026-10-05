"""Run multi-seed structural validation and save a versioned JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from population_simu.simulation_validation import validate_scenario_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261005, 20261006, 20261007])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate_scenario_file(args.scenario, years=args.years, seeds=args.seeds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "runs": len(report["runs"]),
        "years": args.years,
        "all_checks_passed": report["all_checks_passed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
