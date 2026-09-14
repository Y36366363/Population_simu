"""Fetch ACS state-year housing cost burden for the frozen fertility study.

The Census API now commonly requires an API key. Set ``CENSUS_API_KEY`` or pass
``--key``; the script refuses to continue on an authentication/error response.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode

from population_simu.empirical_data import VARIABLES, parse_acs_housing_response


def fetch_year(year: int, api_key: str | None = None) -> list[dict[str, object]]:
    params = {"get": ",".join(VARIABLES), "for": "state:*"}
    if api_key:
        params["key"] = api_key
    # The Census Bureau did not release the standard 2020 ACS 1-year product.
    # Use the official ACS 5-year product only for that year and retain the
    # dataset choice in every row so downstream calibration can stratify or
    # exclude the sensitivity year explicitly.
    dataset = "acs5" if year == 2020 else "acs1"
    url = f"https://api.census.gov/data/{year}/acs/{dataset}?{urlencode(params)}"
    # Use curl's platform certificate store.  Python installations on macOS
    # often lack the system CA bundle even though the same HTTPS endpoint is
    # reachable from the browser and command line.
    try:
        completed = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "120", url],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads(completed.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise RuntimeError("Census API 请求失败；请检查 CENSUS_API_KEY 和网络连接") from exc
    rows = parse_acs_housing_response(payload, year)
    for row in rows:
        row["estimate_type"] = f"{dataset}_B25070"
        row["source_url"] = url.split("&key=", 1)[0]
    return rows


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
    fields = ("entity", "state", "year", "housing_cost_burden", "rent_burden_share", "median_gross_rent", "estimate_type", "source_url")
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} state-year rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
