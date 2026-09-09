"""Check availability of the documented NCHS public-use birth-file fallback."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from urllib.request import Request, urlopen

URLS = {str(y): f"https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/Nat{y}us.zip" for y in range(2018, 2022)}

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    out={}
    for year,url in URLS.items():
        try:
            with urlopen(Request(url, method="HEAD"), timeout=30) as r:
                out[year]={"url":url,"status":r.status,"bytes":int(r.headers.get("Content-Length",0)),"last_modified":r.headers.get("Last-Modified")}
        except Exception as exc:
            out[year]={"url":url,"status":"error","error":str(exc)}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
