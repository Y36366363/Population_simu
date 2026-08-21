"""Merge the frozen fertility outcome with the available housing burden slice."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--housing", type=Path, required=True); p.add_argument("--fertility", type=Path, required=True); p.add_argument("--output", type=Path, required=True); a=p.parse_args()
    housing=read(a.housing); fertility=read(a.fertility)
    h={(r["state"],int(r["year"])):r for r in housing}; rows=[]; unmatched=0
    for f in fertility:
        key=(f["state"],int(f["year"])); r=h.get(key)
        if r is None: unmatched+=1; continue
        rows.append({**f, "housing_cost_burden":r["housing_cost_burden"], "rent_burden_share":r.get("rent_burden_share",""), "median_gross_rent":r.get("median_gross_rent",""), "housing_estimate_type":r.get("estimate_type",""), "housing_source_url":r.get("source_url","")})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else []
    with a.output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    years=sorted({int(r["year"]) for r in rows}); states=sorted({r["state"] for r in rows})
    manifest={"rows":len(rows),"states":len(states),"years":years,"unmatched_fertility_rows":unmatched,"missing_years":sorted(set(range(2007,2022))-set(years)),"note":"2020 standard ACS 1-year housing estimate is not available; no imputation applied."}
    a.output.with_suffix(".manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))
if __name__ == "__main__": main()
