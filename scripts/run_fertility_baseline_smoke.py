"""Smoke-test the frozen fertility outcome against the currently available baselines.

This intentionally does not run the final four-model study: housing coverage is
incomplete, so the result is a pipeline check rather than a study estimate.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from population_simu.benchmarks import (compare_models_rolling, fixed_trend_runner,
                                         household_simulator_runner, rank_models,
                                         reduced_form_runner, wpp_style_runner)

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("csv", type=Path); p.add_argument("--output", type=Path); a=p.parse_args()
    with a.csv.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    for row in rows:
        row["year"]=int(row["year"]); row["asfr_15_44"]=float(row["asfr_15_44"])
    models={"naive_trend":fixed_trend_runner("asfr_15_44"),"cohort_proxy":wpp_style_runner("asfr_15_44")}
    scope="fertility-only smoke test"
    if rows and "housing_cost_burden" in rows[0]:
        models.update({"reduced_form":reduced_form_runner(),"household":household_simulator_runner()})
        scope="comparable-panel four-model smoke test"
    report=compare_models_rolling(rows,models,initial_train_years=8,horizon=1,metric="asfr_15_44",replicates=20,bootstrap_draws=1000,baseline="naive_trend")
    result={"scope":scope,"rows":len(rows),"models":rank_models(report),"report":report,"final_four_model_ready":len(models)==4,"note":"预测比较，不是因果估计；2020 缺口不插值"}
    rendered=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(rendered+"\n",encoding="utf-8")
    print(rendered); return 0
if __name__ == "__main__": raise SystemExit(main())
