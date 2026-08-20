"""Validate currently available frozen-study data without fitting models."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from population_simu.empirical_data import validate_housing_panel
from population_simu.study_protocol import study_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("housing_csv", type=Path)
    parser.add_argument("--fertility", type=Path,
                        help="可选的真实州级生育面板 CSV")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.housing_csv.open(encoding="utf-8-sig", newline="") as file:
        housing_rows = list(csv.DictReader(file))
    fertility_rows = []
    if args.fertility:
        with args.fertility.open(encoding="utf-8-sig", newline="") as file:
            fertility_rows = list(csv.DictReader(file))
    readiness = study_readiness(housing_rows, fertility_rows)
    report = {"housing": validate_housing_panel(housing_rows),
              "fertility_panel": {"available": bool(fertility_rows),
                                  "rows": len(fertility_rows),
                                  "years": sorted({int(r["year"]) for r in fertility_rows})},
              "study_readiness": readiness,
              "study_ready": readiness["model_comparison_ready"]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
