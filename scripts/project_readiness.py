"""Produce a reproducible project-level readiness snapshot during Feature Freeze."""
from __future__ import annotations

import argparse, json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); root = a.root
    manifest = root / "data/observed/us_2021/wonder_batches_2010_2017.json"
    batches = json.loads(manifest.read_text()) if manifest.exists() else {"batches": []}
    statuses = {}
    for row in batches.get("batches", []): statuses[row.get("status", "missing")] = statuses.get(row.get("status", "missing"), 0) + 1
    required = {
        "static_index": (root / "docs/index.html").exists(),
        "pages_workflow": (root / ".github/workflows/pages.yml").exists(),
        "acs_calibration": (root / "data/observed/us_2021/acs_exposure_age_marital_2010_2017.csv").exists(),
        "acs_test": (root / "data/observed/us_2021/acs_exposure_age_marital_2018_2021.csv").exists(),
        "aggregate_fertility_panel": (root / "data/observed/us_2021/us_fertility_panel.csv").exists(),
        "household_audit": (root / "data/observed/us_2021/household_adapter_audit_2026-09-05.json").exists(),
    }
    report = {
        "feature_freeze": True,
        "required_artifacts": required,
        "wonder_2010_2017_batches": {"statuses": statuses, "complete": statuses.get("success", 0) == 48},
        "formal_stratified_replay_ready": False,
        "web_static_ready": required["static_index"] and required["pages_workflow"],
        "local_python_engine": True,
        "interpretation": {
            "ready_now": ["static Pages demo", "local Python engine", "aggregate ASFR model comparison"],
            "blocked": ["formal age-marital-parity calibration", "stratified historical replay"],
            "reason": "WONDER stratified numerator batches and separate test numerator are incomplete",
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
