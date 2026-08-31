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

def normalise_births(rows):
    """Use WONDER State Code as the join key while retaining State as entity."""
    out=[]
    for r in rows:
        x=dict(r)
        if r.get("State Code") or r.get("state_code"):
            x["State"] = r.get("State Code", r.get("state_code"))
            x["Entity"] = r.get("State", r.get("entity", x["State"]))
        out.append(x)
    return out

def write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country","entity","state","year","age","marital","parity","births","exposure","rate_per_1000","denominator_scope")
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def collapse_acs_to_wonder_age(rows):
    bands={"15-19":(15,19),"20-24":(20,24),"25-29":(25,29),"30-34":(30,34),"35-39":(35,39),"40-44":(40,44)}
    out={}
    for r in rows:
        age=int(r["age"]); band=next((b for b,(lo,hi) in bands.items() if lo<=age<=hi),None)
        if band is None: continue
        key=(r["state"],int(r["year"]),band,r["marital"],r["parity"])
        item=out.setdefault(key,{**r,"age":band,"age_band":band,"exposure":0.0})
        item["exposure"] += float(r["exposure"])
    return list(out.values())

def main():
    p=argparse.ArgumentParser(); p.add_argument("births",type=Path); p.add_argument("acs_calibration",type=Path); p.add_argument("acs_test",type=Path); p.add_argument("--births-test",type=Path, help="2018–2021 WONDER 合并文件；未提供则明确拒绝 test 输出"); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    births=aggregate_wonder_to_age_marital(normalise_births(read_csv(a.births)))
    for r in births:
        r["Age"] = str(r["Age"]).replace(" years", "")
        r["Marital Status"] = str(r["Marital Status"]).lower()
    by_year={int(r["Year"]) for r in births}
    if not set(range(2010,2018)).issubset(by_year): raise SystemExit("calibration 年份不完整")
    test_births = births if a.births_test is None else aggregate_wonder_to_age_marital(normalise_births(read_csv(a.births_test)))
    if a.births_test is None: raise SystemExit("缺少 --births-test：2018–2021 test 出生分子不能从 calibration 文件推断")
    for r in test_births:
        r["Age"] = str(r["Age"]).replace(" years", ""); r["Marital Status"] = str(r["Marital Status"]).lower()
    if not set(range(2018,2022)).issubset({int(r["Year"]) for r in test_births}): raise SystemExit("test 年份不完整")
    cal=merge_stratified_wonder_births([r for r in births if 2010<=int(r["Year"])<=2017],collapse_acs_to_wonder_age(read_csv(a.acs_calibration)))
    test=merge_stratified_wonder_births([r for r in test_births if 2018<=int(r["Year"])<=2021],collapse_acs_to_wonder_age(read_csv(a.acs_test)))
    if {int(r["year"]) for r in cal} != set(range(2010,2018)): raise SystemExit("calibration 年份不完整")
    if {int(r["year"]) for r in test} != set(range(2018,2022)): raise SystemExit("test 年份不完整")
    # Formal statewide calibration requires the same 52 state/territory keys
    # represented by the ACS panel for every year; partial batches are smoke
    # tests only and must not silently become the headline panel.
    expected_cal = {(r["state"], int(r["year"])) for r in read_csv(a.acs_calibration)}
    expected_test = {(r["state"], int(r["year"])) for r in read_csv(a.acs_test)}
    observed_cal = {(str(r.get("State", r.get("state"))), int(r["Year"])) for r in births if 2010 <= int(r["Year"]) <= 2017}
    observed_test = {(str(r.get("State", r.get("state"))), int(r["Year"])) for r in test_births if 2018 <= int(r["Year"]) <= 2021}
    if not expected_cal.issubset(observed_cal): raise SystemExit("calibration 州覆盖不完整；不能进入正式结果")
    if not expected_test.issubset(observed_test): raise SystemExit("test 州覆盖不完整；不能进入正式结果")
    write(a.output_dir/"wonder_acs_age_marital_calibration_2010_2017.csv",cal); write(a.output_dir/"wonder_acs_age_marital_test_2018_2021.csv",test)
    print(f"calibration_rows={len(cal)} test_rows={len(test)}")
if __name__=="__main__": main()
