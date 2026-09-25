"""Run the lightweight, dependency-free daily regression checks.

This intentionally does not run the expensive rolling-origin study.  It checks
the contracts that can silently break the web demo or invalidate a published
artifact: static assets, panel keys, artifact status and local API payloads.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    checks: dict[str, object] = {}

    # Reuse the static checker so the daily report has one source of truth.
    import subprocess, sys
    completed = subprocess.run(
        [sys.executable, str(root / "scripts/check_static_site.py"), str(root / "docs")],
        capture_output=True, text=True,
    )
    checks["static_site"] = completed.returncode == 0
    checks["static_site_output"] = completed.stdout.strip()

    registry = subprocess.run(
        [sys.executable, str(root / "scripts/check_calibration_registry.py"),
         str(root / "data/fixtures/calibration_target_registry.json")],
        capture_output=True, text=True,
    )
    checks["calibration_registry"] = {
        "ok": registry.returncode == 0,
        "output": registry.stdout.strip(),
    }

    panel_path = root / "data/observed/us_2021/us_research_panel_2010_2021_comparable.csv"
    rows = read_csv(panel_path)
    keys = [(row["state"], row["year"]) for row in rows]
    checks["primary_panel"] = {
        "rows": len(rows), "states": len({row["state"] for row in rows}),
        "years": sorted({int(row["year"]) for row in rows}),
        "duplicate_keys": len(keys) != len(set(keys)),
    }

    sensitivity = root / "data/observed/us_2021/us_research_panel_2010_2021_with_2020_acs5_sensitivity.csv"
    sensitivity_rows = read_csv(sensitivity)
    checks["2020_sensitivity_panel"] = {
        "rows": len(sensitivity_rows),
        "states": len({row["state"] for row in sensitivity_rows}),
        "has_acs5_label": any(row.get("housing_estimate_type") == "acs5_B25070" for row in sensitivity_rows),
        "years": sorted({int(row["year"]) for row in sensitivity_rows}),
    }

    artifact = root / "data/observed/us_2021/frozen_cross_validation_2026-09-14_2020_sensitivity.json"
    artifact_data = json.loads(artifact.read_text(encoding="utf-8"))
    checks["cross_validation_artifact"] = {
        "models": sorted(artifact_data.get("reports", {} ).get("6", {}).keys()),
        "untouched_test_years": artifact_data.get("untouched_test_years", []),
        "sensitivity_test_years": artifact_data.get("sensitivity_test_years", []),
    }

    from population_simu.local_app import run_scenario
    api_checks = {}
    for scenario in ("family_major_countries.json", "resource_allocation_experiment.json"):
        result = run_scenario(scenario, years=2, seed=2026)
        api_checks[scenario] = {
            "history_rows": len(result["history"]),
            "snapshot_year": result["snapshot"]["year"],
            "region_history": bool(result["region_history"]),
        }
    checks["local_api_contract"] = api_checks

    checks["ok"] = (
        checks["static_site"]
        and checks["calibration_registry"]["ok"]
        and not checks["primary_panel"]["duplicate_keys"]
        and checks["2020_sensitivity_panel"]["has_acs5_label"]
        and len(checks["cross_validation_artifact"]["models"]) == 6
        and all(item["history_rows"] > 0 for item in api_checks.values())
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
