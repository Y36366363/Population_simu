"""Create small, reproducible CDC WONDER query batches.

The output is a manifest for manual/API-assisted WONDER exports. Keeping one
year and a small state chunk per request reduces timeouts and makes failures
retriable without changing the estimand.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=2010)
    p.add_argument("--end", type=int, default=2017)
    p.add_argument("--states-per-batch", type=int, default=10)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.start > args.end or args.states_per_batch < 1:
        raise SystemExit("invalid batch range")
    states = [f"{i:02d}" for i in
              (1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18,
               19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
               33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47,
               48, 49, 50, 51, 53, 54, 55, 56)]
    batches = []
    for year in range(args.start, args.end + 1):
        for offset in range(0, len(states), args.states_per_batch):
            batches.append({"id": f"{year}-{offset // args.states_per_batch:02d}",
                            "year": year,
                            "state_fips": states[offset:offset + args.states_per_batch],
                            "group_by": ["State", "Year", "Age of Mother 9",
                                          "Marital Status", "Live Birth Order"],
                            "export": "TSV", "status": "pending"})
    manifest = {"source": "CDC WONDER Natality 2007-2024",
                "estimand": "state-year-age-marital-parity birth counts",
                "batches": batches}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {args.output} ({len(batches)} batches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
