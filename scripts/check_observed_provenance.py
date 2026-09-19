"""Check provenance registration and content hashes for data/observed.

The check intentionally excludes source code, README files, the web site, and
data/fixtures. Every observed-data file must be listed in the manifest and its
SHA-256 must match. This catches silent replacement of an input while leaving
the scientific provenance fields to the manifest reviewer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_FIELDS = {"path", "source", "license", "retrieved", "transformation", "sha256"}
EXCLUDED_NAMES = {"README.md", "PROVENANCE_POLICY.md", "provenance_manifest.json"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_files(root: Path) -> set[str]:
    base = root / "data" / "observed"
    return {
        path.relative_to(root).as_posix()
        for path in base.rglob("*")
        if path.is_file() and path.name not in EXCLUDED_NAMES
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=Path("data/observed/provenance_manifest.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = (root / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    by_path = {entry.get("path"): entry for entry in entries}
    files = observed_files(root)
    missing = sorted(files - set(by_path))
    stale = sorted(set(by_path) - files)
    errors: list[str] = []
    if missing:
        errors.append("unregistered=" + ",".join(missing))
    if stale:
        errors.append("stale_manifest_entries=" + ",".join(stale))
    for path in sorted(files & set(by_path)):
        entry = by_path[path]
        missing_fields = sorted(REQUIRED_FIELDS - set(entry))
        if missing_fields:
            errors.append(f"{path}:missing_fields={','.join(missing_fields)}")
            continue
        actual = sha256(root / path)
        if entry["sha256"] != actual:
            errors.append(f"{path}:sha256_mismatch")
        for field in ("source", "license", "retrieved", "transformation"):
            if not str(entry[field]).strip():
                errors.append(f"{path}:empty_{field}")
    if errors:
        print("\n".join(errors))
        return 2
    print(f"observed_provenance_ok files={len(files)} manifest={manifest_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
