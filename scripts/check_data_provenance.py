#!/usr/bin/env python3
"""Validate provenance coverage and integrity for data/observed files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_PATH = Path("data/observed/PROVENANCE.json")
OBSERVED_DIR = Path("data/observed")
DATE_BASES = {"downloaded", "generated", "first_committed"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATASET_FIELDS = ("provider", "source_urls", "license", "redistribution", "citation")
FILE_FIELDS = ("dataset", "recorded_on", "date_basis", "transformation", "sha256")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _sha256(path: Path) -> str:
    # Git normalizes tracked text files to LF.  macOS checkouts may expose
    # CRLF in the working tree via core.autocrlf, so hash the canonical bytes
    # used by the repository rather than a platform-specific line ending.
    raw = path.read_bytes()
    if path.suffix.lower() in {".csv", ".tsv", ".json", ".txt"}:
        raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    digest = hashlib.sha256()
    digest.update(raw)
    return digest.hexdigest()


def _observed_files(root: Path) -> set[str]:
    base = root / OBSERVED_DIR
    git_dir = root / ".git"
    if git_dir.exists():
        tracked = subprocess.run(
            ["git", "ls-files", "data/observed"], cwd=root,
            check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        return {
            path for path in tracked
            if Path(path).name != "README.md" and Path(path) != MANIFEST_PATH
        }
    return {
        path.relative_to(root).as_posix()
        for path in base.rglob("*")
        if path.is_file()
        and path.relative_to(root) != MANIFEST_PATH
        and path.name != "README.md"
    }


def validate(root: Path) -> list[str]:
    """Return human-readable validation errors; an empty list means success."""
    errors: list[str] = []
    manifest_file = root / MANIFEST_PATH
    if not manifest_file.is_file():
        return [f"missing manifest: {MANIFEST_PATH.as_posix()}"]

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read {MANIFEST_PATH.as_posix()}: {exc}"]

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    datasets = manifest.get("datasets")
    files = manifest.get("files")
    if not isinstance(datasets, dict):
        errors.append("datasets must be an object")
        datasets = {}
    if not isinstance(files, dict):
        errors.append("files must be an object")
        files = {}

    for dataset_id, record in datasets.items():
        prefix = f"dataset {dataset_id!r}"
        if not _nonempty_string(dataset_id) or not isinstance(record, dict):
            errors.append(f"{prefix} must be a named object")
            continue
        for field in DATASET_FIELDS:
            value = record.get(field)
            if field == "source_urls":
                if not isinstance(value, list) or not value or not all(
                    _nonempty_string(item) for item in value
                ):
                    errors.append(f"{prefix}.{field} must be a non-empty string list")
            elif not _nonempty_string(value):
                errors.append(f"{prefix}.{field} must be a non-empty string")

    actual_paths = _observed_files(root)
    recorded_paths = set(files)
    for path in sorted(actual_paths - recorded_paths):
        errors.append(f"unregistered observed file: {path}")
    for path in sorted(recorded_paths - actual_paths):
        errors.append(f"manifest entry has no file: {path}")

    for relative_path, record in files.items():
        prefix = f"file {relative_path!r}"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or ".." in pure_path.parts or not relative_path.startswith(
            f"{OBSERVED_DIR.as_posix()}/"
        ):
            errors.append(f"{prefix} is not a safe path under data/observed")
            continue
        for field in FILE_FIELDS:
            value = record.get(field)
            if not _nonempty_string(value):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        dataset_id = record.get("dataset")
        if _nonempty_string(dataset_id) and dataset_id not in datasets:
            errors.append(f"{prefix}.dataset references unknown dataset {dataset_id!r}")
        if not _valid_date(record.get("recorded_on")):
            errors.append(f"{prefix}.recorded_on must be an ISO date (YYYY-MM-DD)")
        date_basis = record.get("date_basis")
        if date_basis not in DATE_BASES:
            errors.append(
                f"{prefix}.date_basis must be one of {', '.join(sorted(DATE_BASES))}"
            )
        if date_basis == "first_committed" and not _nonempty_string(record.get("notes")):
            errors.append(f"{prefix}.notes is required when the download date is unknown")
        expected_hash = record.get("sha256")
        if _nonempty_string(expected_hash) and not SHA256_RE.fullmatch(expected_hash):
            errors.append(f"{prefix}.sha256 must be 64 lowercase hexadecimal characters")
        full_path = root / relative_path
        if full_path.is_file() and SHA256_RE.fullmatch(str(expected_hash or "")):
            actual_hash = _sha256(full_path)
            if actual_hash != expected_hash:
                errors.append(
                    f"checksum mismatch for {relative_path}: expected {expected_hash}, got {actual_hash}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        print("data_provenance_check=failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = len(_observed_files(args.root.resolve()))
    print(f"data_provenance_check=ok files={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
