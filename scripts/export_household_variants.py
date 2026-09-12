"""Export versioned Python household full/ablation forecasts for the Pages UI."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from population_simu.benchmarks import household_simulator_runner
from population_simu.household_calibration import calibrate_household_parameters

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("panel",type=Path); p.add_argument("--output",type=Path,required=True); p.add_argument("--seed",type=int,default=2026); a=p.parse_args()
    with a.panel.open(encoding="utf-8-sig",newline="") as h: rows=list(csv.DictReader(h))
    for r in rows:
        r["year"]=int(r["year"]); r["asfr_15_44"]=float(r["asfr_15_44"]); r["housing_cost_burden"]=float(r.get("housing_cost_burden") or .35)
    train=[r for r in rows if 2010<=r["year"]<=2017]; years=[2018,2019,2021]
    calibration=calibrate_household_parameters(train)
    housing={(r["entity"],r["year"]):r["housing_cost_burden"] for r in rows}
    specs={
      "full": household_simulator_runner(calibration=calibration,use_housing=True,future_housing=housing),
      "no_housing": household_simulator_runner(calibration=calibration,use_housing=False,future_housing=housing),
      "no_household": household_simulator_runner(calibration=calibration,use_household_mechanisms=False),
    }
    forecasts=[]
    for name,runner in specs.items():
        for row in runner(train,years,a.seed):
            row["variant"]=name; forecasts.append(row)
    payload={"version":"2026-09-12","kind":"aggregate_asfr_mechanism_artifact","status":"validated_for_predictive_interface","panel":str(a.panel),"calibration_years":[2010,2011,2012,2013,2014,2015,2016,2017],"test_years":years,"seed":a.seed,"variants":["full","no_housing","no_household"],"calibration":calibration.as_dict(),"formal_hazard_replay_ready":False,"rows":forecasts,"interpretation":"Aggregate ASFR mechanism comparison only; not age-marital-parity calibration or causal counterfactual."}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print(f"wrote {a.output} rows={len(forecasts)} variants={len(specs)}"); return 0
if __name__=="__main__": raise SystemExit(main())
