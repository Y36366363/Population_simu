"""Profile early versus late costs of existing FamilyWorld event phases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from population_simu.family_config import FamilyScenario
from population_simu.performance_profiling import profile_simulation_phases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=50)
    parser.add_argument("--split-after", type=int, default=25)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261006, 20261007, 20261008])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario = FamilyScenario.from_dict(json.loads(args.scenario.read_text(encoding="utf-8")))
    report = profile_simulation_phases(
        scenario, years=args.years, seeds=args.seeds, split_after_years=args.split_after,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "median_step_late_to_early_ratio": report["median_step_late_to_early_ratio"],
        "top_growth_phases": report["phase_growth_ranking"][:5],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
