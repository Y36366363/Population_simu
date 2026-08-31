"""Align merged WONDER births with ACS age×marital exposures.

Because ACS has no parity risk set, WONDER live-birth-order rows are aggregated
to parity=all before the strict merge. The script writes separate calibration
(2010–2017) and untouched test (2018–2021) files and refuses missing years.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path
from population_simu.fertility_panel import aggregate_wonder_to_age_marital, merge_stratified_wonder_births

def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country","entity","state","year","age","marital","parity","births","exposure","rate_per_1000","denominator_scope")
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    p=argparse.ArgumentParser(); p.add_argument("births",type=Path); p.add_argument("acs_calibration",type=Path); p.add_argument("acs_test",type=Path); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    births=aggregate_wonder_to_age_marital(read_csv(a.births))
    cal=merge_stratified_wonder_births([r for r in births if 2010<=int(r["Year"])<=2017],read_csv(a.acs_calibration))
    test=merge_stratified_wonder_births([r for r in births if 2018<=int(r["Year"])<=2021],read_csv(a.acs_test))
    if {int(r["year"]) for r in cal} != set(range(2010,2018)): raise SystemExit("calibration 年份不完整")
    if {int(r["year"]) for r in test} != set(range(2018,2022)): raise SystemExit("test 年份不完整")
    # Formal statewide calibration requires the same 52 state/territory keys
    # represented by the ACS panel for every year; partial batches are smoke
    # tests only and must not silently become the headline panel.
    expected_cal = {(r["state"], int(r["year"])) for r in read_csv(a.acs_calibration)}
    expected_test = {(r["state"], int(r["year"])) for r in read_csv(a.acs_test)}
    observed_cal = {(str(r.get("State", r.get("state"))), int(r["Year"])) for r in births if 2010 <= int(r["Year"]) <= 2017}
    observed_test = {(str(r.get("State", r.get("state"))), int(r["Year"])) for r in births if 2018 <= int(r["Year"]) <= 2021}
    if not expected_cal.issubset(observed_cal): raise SystemExit("calibration 州覆盖不完整；不能进入正式结果")
    if not expected_test.issubset(observed_test): raise SystemExit("test 州覆盖不完整；不能进入正式结果")
    write(a.output_dir/"wonder_acs_age_marital_calibration_2010_2017.csv",cal); write(a.output_dir/"wonder_acs_age_marital_test_2018_2021.csv",test)
    print(f"calibration_rows={len(cal)} test_rows={len(test)}")
if __name__=="__main__": main()
