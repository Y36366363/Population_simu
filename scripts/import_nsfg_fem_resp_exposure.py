"""Extract a weighted national female exposure snapshot from NSFG respondents."""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


def dictionary(path: Path) -> dict[str, tuple[int, int]]:
    pattern = re.compile(r"_column\((\d+)\).*?\s([A-Za-z][A-Za-z0-9_]*)\s+%([0-9]+)")
    return {m.group(2).lower(): (int(m.group(1)), int(m.group(3)))
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if (m := pattern.search(line))}


def value(line: str, spec: tuple[int, int]) -> float | None:
    start, width = spec; text = line[start - 1:start - 1 + width].strip()
    if not text or text in {".", "98", "99", "999", "9999"}: return None
    try: return float(text)
    except ValueError: return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--year", type=int, default=2018)
    args = parser.parse_args(); spec = dictionary(args.dictionary)
    required = ("age_a", "fmarital", "wgt2017_2019")
    missing = [name for name in required if name not in spec]
    if missing: raise SystemExit(f"NSFG codebook missing variables: {missing}")
    totals: defaultdict[tuple[str, int], float] = defaultdict(float)
    with args.data.open(encoding="ascii", errors="replace") as handle:
        for line in handle:
            age, marital_code, weight = (value(line, spec[name]) for name in required)
            if age is None or marital_code is None or weight is None or not 15 <= age <= 44: continue
            marital = "married" if int(marital_code) == 1 else "unmarried"
            totals[(marital, int(age))] += weight
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country", "year", "age", "marital", "parity", "weight", "source")
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for (marital, age), weight in sorted(totals.items()):
            writer.writerow({"country": "United States", "year": args.year, "age": age,
                             "marital": marital, "parity": "all", "weight": weight,
                             "source": "NSFG 2017-2019 FemResp weighted snapshot"})
    print(f"wrote {len(totals)} weighted exposure cells to {args.output}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
