"""Build the historical state B25070 housing-burden panel from Census ACS FTP.

The 2007--2017 files use sequence format (B25070 sequence 0142), while
2018--2021 use table-based files.  Raw downloads stay outside the repository;
the output records source URLs and estimate type for auditability.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import ssl
import zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote

from population_simu.empirical_data import parse_acs_sequence_state_row, parse_acs_summary_file

STATE_FIPS = {
    "01":"al","02":"ak","04":"az","05":"ar","06":"ca","08":"co","09":"ct","10":"de",
    "12":"fl","13":"ga","15":"hi","16":"id","17":"il","18":"in","19":"ia",
    "20":"ks","21":"ky","22":"la","23":"me","24":"md","25":"ma","26":"mi","27":"mn",
    "28":"ms","29":"mo","30":"mt","31":"ne","32":"nv","33":"nh","34":"nj","35":"nm",
    "36":"ny","37":"nc","38":"nd","39":"oh","40":"ok","41":"or","42":"pa","44":"ri",
    "45":"sc","46":"sd","47":"tn","48":"tx","49":"ut","50":"vt","51":"va","53":"wa",
    "54":"wv","55":"wi","56":"wy",
}

TABLE_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/prototype/1YRData/acsdt1y{year}-b25070.dat"
SEQ_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/data/1_year_seq_by_state/{name}/{year}1{abbr}{sequence:04d}000.zip"
OLD_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/data/1_year/{name}/{year}1{abbr}{sequence:04d}000.zip"
YEAR2009_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/2009/data/1_year_by_state/{name}.zip"
SEQUENCE_CONFIG = {
    2007: (148, 58), 2008: (148, 58), 2009: (148, 58),
    2010: (148, 107), 2011: (155, 107), 2012: (155, 58),
    2013: (146, 162), 2014: (141, 148), 2015: (141, 171),
    2016: (142, 171), 2017: (142, 171),
}

STATE_NAMES = {
    "al":"Alabama","ak":"Alaska","az":"Arizona","ar":"Arkansas","ca":"California","co":"Colorado","ct":"Connecticut","de":"Delaware","dc":"District of Columbia","fl":"Florida","ga":"Georgia","hi":"Hawaii","id":"Idaho","il":"Illinois","in":"Indiana","ia":"Iowa","ks":"Kansas","ky":"Kentucky","la":"Louisiana","me":"Maine","md":"Maryland","ma":"Massachusetts","mi":"Michigan","mn":"Minnesota","ms":"Mississippi","mo":"Missouri","mt":"Montana","ne":"Nebraska","nv":"Nevada","nh":"New Hampshire","nj":"New Jersey","nm":"New Mexico","ny":"New York","nc":"North Carolina","nd":"North Dakota","oh":"Ohio","ok":"Oklahoma","or":"Oregon","pa":"Pennsylvania","ri":"Rhode Island","sc":"South Carolina","sd":"South Dakota","tn":"Tennessee","tx":"Texas","ut":"Utah","vt":"Vermont","va":"Virginia","wa":"Washington","wv":"West Virginia","wi":"Wisconsin","wy":"Wyoming",
}


def _download(url: str, cache: Path) -> bytes:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return cache.read_bytes()
    context = ssl._create_unverified_context()
    with urlopen(url, timeout=180, context=context) as response:
        data = response.read()
    cache.write_bytes(data)
    return data


def _sequence_row(year: int, fips: str, abbr: str, cache: Path) -> dict[str, object]:
    name = STATE_NAMES[abbr]
    sequence, start_position = SEQUENCE_CONFIG[year]
    if year == 2009:
        url = YEAR2009_URL.format(name=quote(name))
        blob = _download(url, cache / f"{year}_{abbr}_{sequence}.zip")
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            wanted = f"e{year}1{abbr}{sequence:04d}000.txt"
            member = next((item for item in archive.namelist() if item.lower().endswith(wanted)), None)
            if member is None:
                raise ValueError(f"{url} 缺少 {wanted}")
            text = archive.read(member).decode("utf-8-sig")
    else:
        url_template = OLD_URL if year in (2007, 2008) else SEQ_URL
        url = url_template.format(year=year, name=quote(name), abbr=abbr, sequence=sequence)
        blob = _download(url, cache / f"{year}_{abbr}_{sequence}.zip")
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            member = next((item for item in archive.namelist() if item.lower().endswith(f"e{year}1{abbr}{sequence:04d}000.txt")), None)
            if member is None:
                raise ValueError(f"{url} 缺少 sequence {sequence:04d}")
            text = archive.read(member).decode("utf-8-sig")
    return parse_acs_sequence_state_row(text, year, state=fips, start_position=start_position, source_url=url)


def fetch_year(year: int, cache: Path) -> list[dict[str, object]]:
    if year in (2018, 2019):
        url = TABLE_URL.format(year=year)
        raw = cache / f"{year}_b25070.dat"
        _download(url, raw)
        rows = parse_acs_summary_file(str(raw), year)
        for row in rows:
            row.update(estimate_type="1yr_table", source_url=url)
        return [row for row in rows if row["state"] in STATE_FIPS]
    rows = []
    for fips, abbr in STATE_FIPS.items():
        try:
            rows.append(_sequence_row(year, fips, abbr, cache))
        except Exception as exc:
            print(f"WARNING {year} {abbr}: {exc}")
    if len(rows) < 45:
        raise ValueError(f"only {len(rows)} states parsed")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2007)
    parser.add_argument("--end", type=int, default=2019)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/population_simu_acs"))
    parser.add_argument("--output", type=Path, default=Path("data/observed/us_2021/us_housing_panel_2007_2019.csv"))
    args = parser.parse_args()
    rows = []
    manifest = {"years": [], "missing_years": [], "sources": {}}
    for year in range(args.start, args.end + 1):
        try:
            year_rows = fetch_year(year, args.cache)
        except Exception as exc:
            manifest["missing_years"].append(year)
            print(f"WARNING {year}: {exc}")
            continue
        rows.extend(year_rows)
        manifest["years"].append(year)
        manifest["sources"][str(year)] = sorted({str(row.get("source_url")) for row in year_rows})
        print(f"{year}: {len(year_rows)} states")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("entity", "state", "year", "housing_cost_burden", "rent_burden_share", "median_gross_rent", "estimate_type", "source_url")
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    manifest["rows"] = len(rows)
    manifest["output"] = str(args.output)
    args.output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(rows)} rows); missing={manifest['missing_years']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
