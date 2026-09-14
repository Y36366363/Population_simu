"""Build the explicitly labelled 2020 ACS-5 sensitivity panel.

The frozen primary study excludes 2020 because the standard ACS 1-year
housing product was not released.  This helper adds only the official ACS
5-year B25070 estimate for 2020 and writes a separate panel/manifest; it does
not overwrite the primary panel or silently turn a 5-year estimate into a
1-year observation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--housing", type=Path, required=True)
    parser.add_argument("--housing-2020", type=Path, required=True)
    parser.add_argument("--fertility", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    primary_housing = read(args.housing)
    primary_states = {row["state"] for row in primary_housing}
    # Keep the same 50-state universe as the frozen primary panel.  ACS5 also
    # returns DC/Puerto Rico, but adding them only in 2020 would create an
    # unbalanced entity and break common-year rolling-origin folds.
    housing = primary_housing + [
        row for row in read(args.housing_2020) if row["state"] in primary_states
    ]
    fertility = read(args.fertility)
    by_key = {(row["state"], int(row["year"])): row for row in housing}
    rows: list[dict[str, str]] = []
    unmatched = 0
    for birth in fertility:
        row = by_key.get((birth["state"], int(birth["year"])))
        if row is None:
            unmatched += 1
            continue
        rows.append({
            **birth,
            "housing_cost_burden": row["housing_cost_burden"],
            "rent_burden_share": row.get("rent_burden_share", ""),
            "median_gross_rent": row.get("median_gross_rent", ""),
            "housing_estimate_type": row.get("estimate_type", "acs1_B25070"),
            "housing_source_url": row.get("source_url", ""),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    years = sorted({int(row["year"]) for row in rows})
    states = sorted({row["state"] for row in rows})
    manifest = {
        "rows": len(rows), "states": len(states), "years": years,
        "unmatched_fertility_rows": unmatched,
        "primary_panel": "data/observed/us_2021/us_research_panel_2010_2021_comparable.csv",
        "sensitivity_year": 2020,
        "sensitivity_source": "Census ACS 5-year B25070",
        "interpretation": "2020 is a sensitivity observation, not comparable to ACS 1-year years without qualification.",
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
