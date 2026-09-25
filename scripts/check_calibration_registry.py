"""Validate the versioned calibration-target registry used by daily smoke tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {"target_id", "role", "variable", "geography", "years", "source_artifact", "priority", "status"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    args = parser.parse_args()
    data = json.loads(args.registry.read_text(encoding="utf-8"))
    targets = data.get("targets", [])
    if not targets:
        raise SystemExit("registry_has_no_targets")
    ids = [row.get("target_id") for row in targets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate_target_id")
    for row in targets:
        missing = sorted(REQUIRED - set(row))
        if missing:
            raise SystemExit(f"{row.get('target_id', '<unknown>')}:missing={','.join(missing)}")
        if not row["years"] or sorted(row["years"]) != row["years"]:
            raise SystemExit(f"{row['target_id']}:invalid_years")
    print(f"calibration_registry_ok targets={len(targets)} blocked={len(data.get('blocked_targets', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
