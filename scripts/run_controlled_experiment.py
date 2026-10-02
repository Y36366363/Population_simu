"""Run a general control-variable/ablation spec from a source checkout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from population_simu.experiments import run_spec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run_spec(args.spec)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"output": str(args.output), "seeds": len(report["runs"]),
                      "arms": [arm["name"] for arm in report["configuration"]["arms"]],
                      "paired_rows": len(report["paired_differences"]),
                      "all_audits_passed": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
