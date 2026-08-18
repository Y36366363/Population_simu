"""Fetch ACS state-year housing cost burden for the frozen fertility study.

The Census API now commonly requires an API key. Set ``CENSUS_API_KEY`` or pass
``--key``; the script refuses to continue on an authentication/error response.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from population_simu.empirical_data import VARIABLES, parse_acs_housing_response


def fetch_year(year: int, api_key: str | None = None) -> list[dict[str, object]]:
    params = {"get": ",".join(VARIABLES), "for": "state:*"}
    if api_key:
        params["key"] = api_key
    url = f"https://api.census.gov/data/{year}/acs/acs1?{urlencode(params)}"
    with urlopen(url, timeout=60) as response:
        payload = json.load(response)
    return parse_acs_housing_response(payload, year)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2007)
    parser.add_argument("--end", type=int, default=2021)
    parser.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"))
    parser.add_argument("--output", type=Path, default=Path("data/observed/us_2021/us_housing_panel.csv"))
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start 不能晚于 --end")
    rows = []
    for year in range(args.start, args.end + 1):
        rows.extend(fetch_year(year, args.key))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("entity", "state", "year", "housing_cost_burden", "rent_burden_share", "median_gross_rent")
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} state-year rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
