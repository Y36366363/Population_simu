"""Validate annual compressed ledger partitions against a full in-memory ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from population_simu.family_config import FamilyScenario
from population_simu.simulation_validation import validate_ledger_archiving


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario = FamilyScenario.from_dict(json.loads(args.scenario.read_text(encoding="utf-8")))
    report = validate_ledger_archiving(scenario, years=args.years, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "years": args.years,
        "records": report["full_ledger"]["record_count"],
        "compression_ratio": report["archived_ledger"]["compression_ratio_vs_full_json"],
        "all_checks_passed": report["all_checks_passed"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
