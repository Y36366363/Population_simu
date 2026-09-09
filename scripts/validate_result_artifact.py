"""Validate versioned model-result artifacts before they are published."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED = {"panel", "calibration_years", "untouched_test_years", "reports", "interpretation"}

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("artifact", type=Path); a = p.parse_args()
    d = json.loads(a.artifact.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED - set(d))
    if missing: raise SystemExit("missing_fields=" + ",".join(missing))
    if set(d["calibration_years"]) & set(d["untouched_test_years"]):
        raise SystemExit("calibration_test_overlap")
    if not d["reports"]: raise SystemExit("empty_reports")
    print(f"artifact_ok models={len(next(iter(d['reports'].values())))} test_years={d['untouched_test_years']}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
