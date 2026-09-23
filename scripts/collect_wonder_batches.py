"""Validate local WONDER batch TSVs, update manifest status, and merge successes.

The actual CDC WONDER export is intentionally manual/browser-assisted. For each
manifest batch, save the TSV as ``<batch-id>.tsv`` in the input directory, then
run this script. Missing/empty/malformed files are marked failed and never
silently enter the merged panel.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from population_simu.fertility_panel import read_wonder_tsv


REQUIRED = {
    "State", "State Code", "Year", "Age of Mother 9",
    "Marital Status", "Live Birth Order", "Births",
}


def validate_batch_rows(rows: list[dict[str, str]]) -> None:
    """Reject structurally incomplete exports before marking a batch success."""
    if not rows:
        raise ValueError("empty WONDER batch")
    missing = sorted(REQUIRED - set(rows[0]))
    if missing:
        raise ValueError(f"missing WONDER columns: {missing}")
    for index, row in enumerate(rows, start=2):
        if not str(row.get("State Code", "")).strip() or not str(row.get("Year", "")).strip():
            raise ValueError(f"missing state/year at row {index}")
        births = str(row.get("Births", "")).strip().replace(",", "")
        if births and not births.lower().startswith(("suppressed", "missing", "unknown")):
            try:
                if float(births) < 0:
                    raise ValueError
            except ValueError as exc:
                raise ValueError(f"invalid Births at row {index}: {row.get('Births')!r}") from exc


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mark-missing-failed", action="store_true",
                   help="将尚未下载的文件标记 failed；默认保留 pending 以区分未尝试批次")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    merged: list[dict[str, str]] = []
    for batch in manifest.get("batches", []):
        path = args.input_dir / f"{batch['id']}.tsv"
        try:
            rows = read_wonder_tsv(path)
            validate_batch_rows(rows)
            batch.update({"status": "success", "rows": len(rows), "file": str(path)})
            merged.extend(rows)
        except Exception as exc:
            if path.exists() or args.mark_missing_failed:
                batch.update({"status": "failed", "error": str(exc), "file": str(path)})
            else:
                batch.update({"status": "pending", "file": str(path)})
    manifest["updated"] = True
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if merged:
        fields = list(dict.fromkeys(k for row in merged for k in row))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader(); writer.writerows(merged)
    success = sum(b.get("status") == "success" for b in manifest["batches"])
    failed = sum(b.get("status") == "failed" for b in manifest["batches"])
    pending = sum(b.get("status") == "pending" for b in manifest["batches"])
    print(f"success={success} failed={failed} pending={pending} merged_rows={len(merged)}")
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
