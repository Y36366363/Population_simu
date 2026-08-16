"""Build a small, reproducible US 2021 calibration bundle from public files.

The script converts Census single-age population estimates and CDC life-table
workbooks into the project's long CSV contracts.  It deliberately does not
invent an age-sex OD matrix or parity exposure: those must be supplied from
ACS PUMS/NSFG or a protected statistical extract.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "observed" / "us_2021"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    return ["".join(item.itertext()) for item in root.findall("m:si", NS)]


def convert_cdc_life_table(source: Path, target: Path, sex: str) -> int:
    with zipfile.ZipFile(source) as book:
        strings = _shared_strings(book)
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
    rows = sheet.findall(".//m:row", NS)
    # CDC Table 2/3 has age rows beginning at row 4 and qx in column B.
    output = []
    for row in rows[3:]:
        cells = row.findall("m:c", NS)
        if len(cells) < 2:
            continue
        age_cell, qx_cell = cells[0], cells[1]
        age_raw = age_cell.findtext("m:v", default="", namespaces=NS)
        qx_raw = qx_cell.findtext("m:v", default="", namespaces=NS)
        if age_cell.attrib.get("t") == "s":
            label = strings[int(age_raw)]
            if "100 and older" in label:
                age = 100
            elif "–" in label:
                age = int(label.split("–", 1)[0])
            else:
                continue
        else:
            continue
        try:
            qx = float(qx_raw)
        except ValueError:
            continue
        output.append({"country": "United States", "year": 2021, "sex": sex,
                       "age": age, "death_rate": qx})
    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=output[0].keys())
        writer.writeheader(); writer.writerows(output)
    return len(output)


def convert_census_population(source: Path, target: Path) -> int:
    output = []
    with source.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row["AGE"] == "999":
                continue
            sex = "M" if row["SEX"] == "0" else "F"
            output.append({"country": "United States", "year": 2021, "sex": sex,
                           "age": int(row["AGE"]),
                           "population": float(row["POPESTIMATE2021"])})
    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=output[0].keys())
        writer.writeheader(); writer.writerows(output)
    return len(output)


def main() -> int:
    required = [
        DATA / "census_single_age_sex_2025.csv",
        DATA / "cdc_us_life_table_male.xlsx",
        DATA / "cdc_us_life_table_female.xlsx",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Missing public input files:", *missing, sep="\n", file=sys.stderr)
        return 2
    n_pop = convert_census_population(required[0], DATA / "us_population_single_age_sex_2021.csv")
    n_m = convert_cdc_life_table(required[1], DATA / "us_life_table_male_2021.csv", "M")
    n_f = convert_cdc_life_table(required[2], DATA / "us_life_table_female_2021.csv", "F")
    print(f"population_rows={n_pop} male_life_rows={n_m} female_life_rows={n_f}")
    print("OD and parity exposure remain required inputs; no synthetic values were created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
