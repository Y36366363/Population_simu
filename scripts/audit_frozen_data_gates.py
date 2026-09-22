"""Audit the two frozen data gates without fabricating missing observations."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_YEARS = set(range(2010, 2020)) | {2021}
REQUIRED_CHILDCARE_FIELDS = {
    "childcare_supply", "under5_formal_care_share", "childcare_definition",
    "childcare_source_url", "childcare_denominator",
}
REQUIRED_WONDER_FIELDS = {
    "State Code", "Year", "Age of Mother 9 Code", "Marital Status Code",
    "Live Birth Order Code", "Births",
}


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def finite(value: object) -> bool:
    try:
        number = float(value)
        return number == number and abs(number) != float("inf")
    except (TypeError, ValueError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    panel_path = root / "data/observed/us_2021/us_research_panel_2010_2021_comparable.csv"
    panel, panel_fields = read_csv(panel_path)
    panel_years = {int(r["year"]) for r in panel}
    panel_states = {r["state"] for r in panel}
    childcare_fields = sorted(REQUIRED_CHILDCARE_FIELDS & set(panel_fields))
    childcare_missing_fields = sorted(REQUIRED_CHILDCARE_FIELDS - set(panel_fields))
    childcare_rows = ([r for r in panel if all(r.get(f, "") != "" for f in REQUIRED_CHILDCARE_FIELDS)]
                      if not childcare_missing_fields else [])
    childcare_keys = {(r["state"], int(r["year"])) for r in childcare_rows}
    expected_keys = {(state, year) for state in panel_states for year in REQUIRED_YEARS}

    manifest_path = root / "data/observed/us_2021/wonder_batches_2010_2017.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    statuses = {}
    for batch in manifest.get("batches", []):
        status = batch.get("status", "missing")
        statuses[status] = statuses.get(status, 0) + 1

    partial_path = root / "data/observed/us_2021/wonder_births_partial_2010_2017.csv"
    partial_rows, partial_fields = read_csv(partial_path) if partial_path.exists() else ([], [])
    partial_key_fields = sorted(REQUIRED_WONDER_FIELDS & set(partial_fields))
    partial_has_all_parity = any(str(r.get("Live Birth Order Code", "")).lower() in {"00", "all", "total"}
                                for r in partial_rows)
    exposure_path = root / "data/observed/us_2021/acs_exposure_age_marital_2010_2017.csv"
    exposure_rows, exposure_fields = read_csv(exposure_path)
    exposure_parity_values = sorted({r.get("parity", "") for r in exposure_rows})
    exposure_years = sorted({int(r["year"]) for r in exposure_rows})
    exposure_has_state = "state" in exposure_fields
    hazard_ready = (
        statuses.get("success", 0) == 48
        and bool(partial_rows)
        and set(REQUIRED_WONDER_FIELDS) <= set(partial_fields)
        and exposure_has_state
        and any(value not in {"", "all", "total"} for value in exposure_parity_values)
    )
    report = {
        "version": "2026-09-22",
        "feature_freeze": True,
        "panel": {
            "rows": len(panel), "states": len(panel_states),
            "years": sorted(panel_years), "fields": panel_fields,
        },
        "childcare_gate": {
            "status": "blocked",
            "ready_for_primary": False,
            "required_fields": sorted(REQUIRED_CHILDCARE_FIELDS),
            "present_fields": childcare_fields,
            "missing_fields": childcare_missing_fields,
            "complete_state_year_keys": len(childcare_keys),
            "expected_state_year_keys": len(expected_keys),
            "missing_years": sorted(REQUIRED_YEARS - panel_years),
            "reason": "主面板没有可审计的托育定义、来源和分母字段；不得用网页旋钮或综合 amenity 代替观测 exposure。",
        },
        "age_marital_parity_gate": {
            "status": "blocked",
            "formal_hazard_ready": hazard_ready,
            "wonder_batch_statuses": statuses,
            "wonder_success_batches": statuses.get("success", 0),
            "wonder_required_batches": 48,
            "partial_birth_rows": len(partial_rows),
            "partial_birth_key_fields": partial_key_fields,
            "partial_contains_all_parity": partial_has_all_parity,
            "acs_exposure_years": exposure_years,
            "acs_exposure_parity_values": exposure_parity_values,
            "acs_exposure_has_state": exposure_has_state,
            "reason": "WONDER 州级年龄×婚姻×孩次分子未完成 48 批；ACS 暴露当前只有 all-parity，NSFG 全国文件不能替代州级分母。",
        },
        "allowed_now": [
            "housing-primary rolling-origin and mechanism diagnostics",
            "aggregate ASFR predictive comparison",
            "网页和本地 API 回归测试",
        ],
        "not_allowed_yet": [
            "childcare as a primary exposure",
            "formal age-marital-parity hazard calibration",
            "causal counterfactual claims",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
