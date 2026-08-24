"""Calibrate frozen household fertility inputs from weighted public-data extracts.

The script intentionally accepts prepared birth and female-exposure extracts;
it does not download restricted microdata or silently impute missing denominators.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from population_simu.household_calibration import (
    calibrate_fertility_observations,
    calibrate_household_parameters,
)
from population_simu.microdata import fertility_observations_from_weighted_rows


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--births", type=Path, required=True,
                        help="weighted birth rows: year,age,marital,parity,weight")
    parser.add_argument("--exposure", type=Path, required=True,
                        help="weighted female exposure rows with the same keys")
    parser.add_argument("--panel", type=Path,
                        help="optional housing/state-year calibration panel")
    parser.add_argument("--country", default="US")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    births, exposure = _read(args.births), _read(args.exposure)
    years = sorted({int(row["year"]) for row in births + exposure})
    observations = []
    for year in years:
        b = [row for row in births if int(row["year"]) == year]
        e = [row for row in exposure if int(row["year"]) == year]
        if b and e:
            observations.extend(fertility_observations_from_weighted_rows(
                b, e, country=args.country, year=year))
    if not observations:
        raise SystemExit("没有同时存在出生和女性暴露的年份；拒绝无分母校准")
    prior = calibrate_household_parameters(_read(args.panel)) if args.panel else None
    calibration = calibrate_fertility_observations(observations, prior=prior)
    result = {
        "calibration": calibration.as_dict(),
        "source_files": {"births": str(args.births), "exposure": str(args.exposure),
                          "panel": str(args.panel) if args.panel else None},
        "years": years,
        "observation_rows": len(observations),
        "interpretation": "预测校准，不是因果估计；所有 prior_only 参数仍需敏感性分析",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
