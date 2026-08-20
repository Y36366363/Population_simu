"""Import CDC WONDER natality TSV plus Census female denominator CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from population_simu.fertility_panel import merge_wonder_births_with_denominator, read_wonder_tsv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("births_tsv", type=Path,
                        help="CDC WONDER export grouped by State/Year (and optionally marital/parity)")
    parser.add_argument("denominator_csv", type=Path,
                        help="Census PEP CSV with State,Year,Female15_44")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    births = read_wonder_tsv(args.births_tsv)
    with args.denominator_csv.open(encoding="utf-8-sig", newline="") as file:
        denominators = list(csv.DictReader(file))
    rows = merge_wonder_births_with_denominator(births, denominators)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country", "entity", "state", "year", "marital", "parity",
              "births_15_44", "female_15_44", "asfr_15_44")
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
