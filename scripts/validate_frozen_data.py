"""Validate currently available frozen-study data without fitting models."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from population_simu.empirical_data import validate_housing_panel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("housing_csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.housing_csv.open(encoding="utf-8-sig", newline="") as file:
        report = {"housing": validate_housing_panel(list(csv.DictReader(file))),
                  "fertility_panel": {"available": False,
                                      "reason": "等待 CDC/NVSS 年龄—孩次出生和女性分母文件"},
                  "study_ready": False}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
