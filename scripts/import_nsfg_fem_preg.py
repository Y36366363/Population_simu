"""Parse a downloaded NSFG fixed-width pregnancy file into weighted births.

The output is a national validation extract. NSFG does not provide public
state identifiers, so it must not be used as a state-year replacement for ACS
female denominators or CDC state natality totals.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


def dictionary(path: Path) -> dict[str, tuple[int, int]]:
    result = {}
    pattern = re.compile(r"_column\((\d+)\).*?\s([A-Za-z][A-Za-z0-9_]*)\s+%([0-9]+)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            result[match.group(2).lower()] = (int(match.group(1)), int(match.group(3)))
    return result


def value(line: str, spec: tuple[int, int]) -> float | None:
    start, width = spec
    text = line[start - 1:start - 1 + width].strip()
    if not text or text in {".", "98", "99", "999", "9999"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2017)
    args = parser.parse_args()
    spec = dictionary(args.dictionary)
    required = ("pregend1", "agepreg", "fmarout5", "birthord", "datend", "wgt2017_2019")
    missing = [name for name in required if name not in spec]
    if missing:
        raise SystemExit(f"NSFG codebook missing variables: {missing}")
    totals: defaultdict[tuple[int, str, str, int], float] = defaultdict(float)
    lines = 0
    with args.data.open(encoding="ascii", errors="replace") as handle:
        for line in handle:
            lines += 1
            outcome = value(line, spec["pregend1"])
            age = value(line, spec["agepreg"])
            marital_code = value(line, spec["fmarout5"])
            parity_code = value(line, spec["birthord"])
            year = value(line, spec["datend"])
            weight = value(line, spec["wgt2017_2019"])
            if outcome not in {5, 6} or age is None or not 15 <= age <= 44:
                continue
            if marital_code is None or parity_code is None or year is None or weight is None:
                continue
            year_i = int(year)
            if not args.start_year <= year_i <= args.end_year:
                continue
            marital = "married" if int(marital_code) == 1 else "unmarried"
            parity = "first" if int(parity_code) == 1 else "second" if int(parity_code) == 2 else "third_plus"
            totals[(year_i, marital, parity, int(age))] += weight
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country", "year", "age", "marital", "parity", "weight", "source")
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        all_totals: defaultdict[tuple[int, str, int], float] = defaultdict(float)
        for (year, marital, parity, age), births in totals.items():
            all_totals[(year, marital, age)] += births
        output_rows = [(key, births) for key, births in totals.items()]
        output_rows += [((year, marital, "all", age), births)
                        for (year, marital, age), births in all_totals.items()]
        for (year, marital, parity, age), births in sorted(output_rows):
            writer.writerow({"country": "United States", "year": year, "age": age,
                             "marital": marital, "parity": parity, "weight": births,
                             "source": "NSFG 2017-2019 FemPreg weighted"})
    print(f"read {lines} records; wrote {len(totals)} weighted cells to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
