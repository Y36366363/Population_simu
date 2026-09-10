"""Create a tiny deterministic fixture for pipeline tests only.

This is explicitly synthetic and must never be used as an empirical estimate.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    fields=("country","year","age","marital","parity","weight","source")
    birth=[]; exposure=[]
    for year in (2010,2011,2012):
        for age in (20,30):
            for marital in ("married","unmarried"):
                for parity in ("first","second"):
                    exp=10000.0 + 100*age + 50*(year-2010)
                    rate=(0.08 if marital=="married" else 0.02) * (1.0 if age==20 else .85)
                    rate *= (1.0 if parity=="first" else .55)
                    exposure.append({"country":"US","year":year,"age":age,"marital":marital,"parity":parity,"weight":exp,"source":"synthetic smoke fixture"})
                    birth.append({"country":"US","year":year,"age":age,"marital":marital,"parity":parity,"weight":round(exp*rate,3),"source":"synthetic smoke fixture"})
    for name,rows in (("births",birth),("exposure",exposure)):
        with (a.output_dir/f"{name}.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"wrote smoke fixture rows={len(birth)}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
