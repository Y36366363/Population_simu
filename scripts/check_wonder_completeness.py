"""Report whether the local WONDER batch directory is complete."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from population_simu.fertility_panel import read_wonder_tsv

def main():
    p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--input-dir",type=Path,required=True); a=p.parse_args()
    m=json.loads(a.manifest.read_text(encoding="utf-8")); ok=0; missing=[]; bad=[]
    for b in m["batches"]:
        f=a.input_dir/f"{b['id']}.tsv"
        try:
            rows=read_wonder_tsv(f)
            states={str(r.get("State Code", r.get("state_code", r.get("State",r.get("state"))))) for r in rows}
            expected=set(b["state_fips"])
            if not expected.issubset(states): bad.append((b["id"],sorted(expected-states)))
            else: ok+=1
        except Exception as e: missing.append((b["id"],str(e)))
    print(f"complete_batches={ok}/{len(m['batches'])} missing_or_invalid={len(missing)} incomplete={len(bad)}")
    if missing: print("missing:", ", ".join(x[0] for x in missing))
    if bad: print("incomplete:", ", ".join(x[0] for x in bad))
    return 0 if ok==len(m["batches"]) and not bad else 2
if __name__=="__main__": raise SystemExit(main())
