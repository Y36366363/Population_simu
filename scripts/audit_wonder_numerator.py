"""Audit WONDER batch files and reconcile 15–44 births to the frozen panel."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from collections import defaultdict
from population_simu.fertility_panel import read_wonder_tsv

AGES={"15-19 years","20-24 years","25-29 years","30-34 years","35-39 years","40-44 years"}
def main():
 p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--input-dir",type=Path,required=True); p.add_argument("--baseline",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
 m=json.loads(a.manifest.read_text(encoding="utf-8")); base={(r['state'],int(r['year'])):float(r['births_15_44']) for r in csv.DictReader(a.baseline.open(encoding='utf-8-sig'))}; reports=[]; totals=defaultdict(float)
 for b in m['batches']:
  f=a.input_dir/f"{b['id']}.tsv"; rep={"id":b['id'],"year":b['year'],"status":"missing"}
  try:
   rows=[r for r in read_wonder_tsv(f) if r.get('State') and r.get('Year')]
   codes={str(r.get('State Code','')) for r in rows}; expected=set(b['state_fips']); rep.update(status='success',rows=len(rows),missing_state_fips=sorted(expected-codes),suppressed=sum(str(r.get('Births','')).lower().startswith('supp') for r in rows))
   for r in rows:
    if r.get('Age of Mother 9') in AGES and r.get('Births','').replace(',','').replace('.','',1).isdigit() and r.get('Live Birth Order')!='Unknown or not stated': totals[(r['State Code'],int(r['Year']))]+=float(r['Births'].replace(',',''))
  except Exception as e: rep['error']=str(e)
  reports.append(rep)
 reconciliation=[]
 for k,v in sorted(totals.items()):
  if k in base: reconciliation.append({"state":k[0],"year":k[1],"wonder_births_15_44":v,"baseline_births_15_44":base[k],"relative_difference":(v/base[k]-1) if base[k] else None})
 out={"batches":reports,"complete_batches":sum(r['status']=='success' and not r.get('missing_state_fips') for r in reports),"total_batches":len(reports),"reconciliation":reconciliation}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps({k:out[k] for k in ('complete_batches','total_batches')},indent=2)); return 0 if out['complete_batches']==len(reports) else 2
if __name__=='__main__': raise SystemExit(main())
