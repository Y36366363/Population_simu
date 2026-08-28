"""Fetch official ACS B12002 female age-by-marital exposure counts.

This is an aggregate-table alternative to downloading very large ACS PUMS
files. Counts are split uniformly within the published age bands and retain
the original ``age_band`` so the allocation is auditable; it is not claimed to
be single-year observed data.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
from datetime import date


AGE_BANDS = {
    "15_17": (15, 16, 17), "18_19": (18, 19), "20_24": (20, 21, 22, 23, 24),
    "25_29": (25, 26, 27, 28, 29), "30_34": (30, 31, 32, 33, 34),
    "35_39": (35, 36, 37, 38, 39), "40_44": (40, 41, 42, 43, 44),
}


def _get_json(url: str):
    # curl uses the platform certificate store; this also works on macOS
    # installations where Python's bundled urllib lacks the system CA chain.
    api_key = os.environ.get("CENSUS_API_KEY")
    if api_key:
        url += ("&" if "?" in url else "?") + f"key={api_key}"
    completed = subprocess.run(["curl", "--fail", "--silent", "--show-error",
                                "--location", "--max-time", "120", url],
                               check=True, capture_output=True, text=True)
    payload = completed.stdout.lstrip()
    if payload.startswith("<"):
        if "Invalid Key" in payload:
            raise RuntimeError("Census API 返回 Invalid Key；请重新申请/确认邮箱验证后的 key")
        if "Missing Key" in payload:
            raise RuntimeError("Census API 返回 Missing Key；请检查 CENSUS_API_KEY 是否已导出")
        raise RuntimeError("Census API 返回 HTML 错误页，而非 JSON")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Census API 返回不可解析响应") from exc


def _variables(year: int) -> tuple[dict[str, str], dict[str, list[str]]]:
    metadata = _get_json(f"https://api.census.gov/data/{year}/acs/acs1/groups/B12002.json")["variables"]
    selected: dict[str, list[str]] = {band: [] for band in AGE_BANDS}
    labels: dict[str, str] = {}
    for name, item in metadata.items():
        if not name.endswith("E"):
            continue
        label = item.get("label", "")
        if "Female" not in label:
            continue
        for band in AGE_BANDS:
            if f"{band.split('_')[0]} to {band.split('_')[1]} years" in label or (
                band == "18_19" and "18 and 19 years" in label
            ) or (band == "15_17" and "15 to 17 years" in label):
                selected[band].append(name); labels[name] = label
    if any(not values for values in selected.values()):
        raise ValueError(f"ACS B12002 age variables missing for {year}")
    return labels, selected


def fetch(year: int) -> list[dict[str, object]]:
    labels, selected = _variables(year)
    variables = ["NAME", *sorted(labels)]
    url = f"https://api.census.gov/data/{year}/acs/acs1?get={','.join(variables)}&for=state:*"
    table = _get_json(url)
    header, *body = table
    index = {name: i for i, name in enumerate(header)}
    rows: list[dict[str, object]] = []
    for record in body:
        state, name = record[index["state"]], record[index["NAME"]]
        for band, ages in AGE_BANDS.items():
            married = unmarried = 0.0
            for variable in selected[band]:
                value = float(record[index[variable]] or 0)
                label = labels[variable]
                if "Now married" in label:
                    married += value
                elif any(status in label for status in ("Never married", "Widowed", "Divorced")):
                    unmarried += value
            divisor = len(ages)
            for age in ages:
                rows.extend((
                    {"country": "United States", "state": state, "entity": name,
                     "year": year, "age": age, "age_band": band,
                     "marital": "married", "parity": "all", "exposure": married / divisor,
                     "source": "Census ACS1 B12002", "allocation": "uniform_within_band"},
                    {"country": "United States", "state": state, "entity": name,
                     "year": year, "age": age, "age_band": band,
                     "marital": "unmarried", "parity": "all", "exposure": unmarried / divisor,
                     "source": "Census ACS1 B12002", "allocation": "uniform_within_band"},
                ))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2010)
    parser.add_argument("--end", type=int, default=2017)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = [row for year in range(args.start, args.end + 1) for row in fetch(year)]
    except Exception as exc:
        raise SystemExit("Census API 下载失败；请设置 CENSUS_API_KEY，或提供本地 ACS 导出。"
                         f" 原始错误: {exc}") from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        fields = tuple(rows[0])
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    metadata = {
        "source": "https://api.census.gov/data/{}/acs/acs1/groups/B12002.json".format(args.start),
        "years": [args.start, args.end], "table": "B12002",
        "weighting": "published ACS table estimates (not PUMS microdata)",
        "age_allocation": "uniform_within_band", "retrieved": date.today().isoformat(),
        "rows": len(rows),
    }
    args.output.with_suffix(args.output.suffix + ".metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"wrote {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
