"""Download the public 2021 ACS table-based B25070 state file via FTP."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.request import urlopen

from population_simu.empirical_data import parse_acs_summary_file


URL = "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/data/1YRData/acsdt1y{year}-b25070.dat"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2021)
    parser.add_argument("--input", type=Path, help="已下载的 .dat 文件，跳过网络请求")
    parser.add_argument("--output", type=Path, default=Path("data/observed/us_2021/us_housing_panel_2021.csv"))
    args = parser.parse_args()
    url = URL.format(year=args.year)
    raw = args.input or args.output.with_suffix(".raw.dat")
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not args.input:
        with urlopen(url, timeout=120) as response, raw.open("wb") as target:
            target.write(response.read())
    rows = parse_acs_summary_file(str(raw), args.year)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        fields = ("entity", "state", "year", "housing_cost_burden", "rent_burden_share", "median_gross_rent")
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} state rows) from {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
