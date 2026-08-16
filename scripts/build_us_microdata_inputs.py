"""Convert prepared ACS PUMS/NSFG or natality CSV extracts to calibration CSVs.

This intentionally accepts local extracts rather than bypassing Census/CDC
terms of use.  Example:

``python scripts/build_us_microdata_inputs.py --pums pums.csv --births births.csv
--exposure female_exposure.csv --year 2021``
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from population_simu.microdata import (
    fertility_observations_from_weighted_rows,
    migration_records_from_pums,
    read_csv_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pums", type=Path)
    parser.add_argument("--births", type=Path)
    parser.add_argument("--exposure", type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--country", default="United States")
    parser.add_argument("--out-dir", type=Path, default=Path("data/observed/us_2021"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.pums:
        records = migration_records_from_pums(read_csv_rows(args.pums), year=args.year)
        target = args.out_dir / f"us_migration_od_age_sex_{args.year}.csv"
        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=("year", "origin", "destination", "sex", "age", "hazard", "flow", "exposure"))
            writer.writeheader()
            for record in records:
                writer.writerow({"year": args.year, "origin": record.origin,
                                 "destination": record.destination, "sex": record.sex,
                                 "age": record.age, "hazard": record.hazard,
                                 "flow": record.flow, "exposure": record.exposure})
        print(f"wrote {target} ({len(records)} records)")
    if args.births or args.exposure:
        if not (args.births and args.exposure):
            parser.error("--births 与 --exposure 必须同时提供")
        observations = fertility_observations_from_weighted_rows(
            read_csv_rows(args.births), read_csv_rows(args.exposure),
            country=args.country, year=args.year,
        )
        target = args.out_dir / f"us_fertility_observations_{args.year}.csv"
        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=("country", "year", "marital", "parity", "age", "births", "exposure"))
            writer.writeheader()
            for obs in observations:
                writer.writerow({"country": obs.country, "year": obs.year,
                                 "marital": obs.marital, "parity": obs.parity,
                                 "age": obs.age, "births": obs.births,
                                 "exposure": obs.exposure})
        print(f"wrote {target} ({len(observations)} records)")
    if not args.pums and not args.births:
        parser.error("至少提供 --pums 或 --births/--exposure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
