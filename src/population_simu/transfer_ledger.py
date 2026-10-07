"""Auditable bilateral records for transfers already present in FamilyWorld."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
import hashlib
import json
import math
import zlib


@dataclass(frozen=True)
class TransferRecord:
    year: int
    kind: str
    sender: str
    receiver: str
    cash_amount: float = 0.0
    resource_kind: str = "none"
    resource_amount: float = 0.0

    def __post_init__(self) -> None:
        if type(self.year) is not int or not self.kind:
            raise ValueError("transfer requires an integer year and nonempty kind")
        if not self.sender or not self.receiver or self.sender == self.receiver:
            raise ValueError("transfer requires two distinct explicit counterparties")
        for name, value in (("cash_amount", self.cash_amount),
                            ("resource_amount", self.resource_amount)):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative number")
        if self.cash_amount == 0 and self.resource_amount == 0:
            raise ValueError("transfer must contain cash or a noncash resource")
        if self.resource_amount > 0 and self.resource_kind == "none":
            raise ValueError("noncash transfer requires a resource_kind")
        if self.resource_amount == 0 and self.resource_kind != "none":
            raise ValueError("resource_kind requires a positive resource_amount")


@dataclass(frozen=True)
class TransferArchive:
    min_year: int
    max_year: int
    record_count: int
    compressed_payload: bytes
    compressed_sha256: str
    summary_rows: tuple[tuple[int, str, str, int, float, float], ...]

    @property
    def compressed_bytes(self) -> int:
        return len(self.compressed_payload)

    def manifest(self) -> dict[str, object]:
        return {
            "min_year": self.min_year,
            "max_year": self.max_year,
            "record_count": self.record_count,
            "compressed_bytes": self.compressed_bytes,
            "compressed_sha256": self.compressed_sha256,
        }


class TransferLedger:
    """Append-only bilateral ledger; it observes transfers and never creates them."""

    def __init__(self, *, strict_entities: bool = False) -> None:
        self.records: list[TransferRecord] = []
        self.archives: list[TransferArchive] = []
        self.entities: set[str] = set()
        self.strict_entities = bool(strict_entities)

    def register_entity(self, entity: str) -> None:
        if not isinstance(entity, str) or not entity or ":" not in entity:
            raise ValueError("ledger entity must be a typed nonempty identifier")
        self.entities.add(entity)

    def record(self, *, year: int, kind: str, sender: str, receiver: str,
               cash_amount: float = 0.0, resource_kind: str = "none",
               resource_amount: float = 0.0) -> TransferRecord | None:
        if cash_amount == 0 and resource_amount == 0:
            return None
        if self.strict_entities:
            missing = {sender, receiver} - self.entities
            if missing:
                raise ValueError(f"unregistered transfer counterparties: {sorted(missing)}")
        entry = TransferRecord(
            year=year,
            kind=kind,
            sender=sender,
            receiver=receiver,
            cash_amount=float(cash_amount),
            resource_kind=resource_kind,
            resource_amount=float(resource_amount),
        )
        self.records.append(entry)
        return entry

    def query(self, *, year: int | None = None, entity: str | None = None,
              kind: str | None = None, resource_kind: str | None = None) -> list[TransferRecord]:
        return [
            row for row in self._all_records()
            if (year is None or row.year == year)
            and (entity is None or entity in (row.sender, row.receiver))
            and (kind is None or row.kind == kind)
            and (resource_kind is None or row.resource_kind == resource_kind)
        ]

    @staticmethod
    def _encode_records(records: list[TransferRecord]) -> bytes:
        return json.dumps(
            [asdict(row) for row in records],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @staticmethod
    def _decode_archive(archive: TransferArchive) -> list[TransferRecord]:
        if hashlib.sha256(archive.compressed_payload).hexdigest() != archive.compressed_sha256:
            raise ValueError("transfer archive checksum mismatch")
        try:
            payload = json.loads(zlib.decompress(archive.compressed_payload))
        except (zlib.error, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("invalid compressed transfer archive") from error
        if not isinstance(payload, list):
            raise ValueError("transfer archive payload must be a list")
        try:
            records = [TransferRecord(**item) for item in payload]
        except (TypeError, ValueError) as error:
            raise ValueError("invalid transfer archive record") from error
        if len(records) != archive.record_count:
            raise ValueError("transfer archive record count mismatch")
        return records

    def _all_records(self) -> list[TransferRecord]:
        archived = [row for archive in self.archives for row in self._decode_archive(archive)]
        return archived + list(self.records)

    @staticmethod
    def _summarize(records: list[TransferRecord]) -> list[dict[str, object]]:
        grouped: dict[tuple[int, str, str], dict[str, float | int]] = defaultdict(
            lambda: {"records": 0, "cash_amount": 0.0, "resource_amount": 0.0}
        )
        for row in records:
            key = (row.year, row.kind, row.resource_kind)
            grouped[key]["records"] += 1
            grouped[key]["cash_amount"] += row.cash_amount
            grouped[key]["resource_amount"] += row.resource_amount
        return [
            {"year": year, "kind": kind, "resource_kind": resource_kind,
             **grouped[(year, kind, resource_kind)]}
            for year, kind, resource_kind in sorted(grouped)
        ]

    def archive_before(self, before_year: int) -> dict[str, object] | None:
        """Compress live records older than before_year without changing totals."""
        if type(before_year) is not int:
            raise ValueError("archive boundary must be an integer year")
        selected = [row for row in self.records if row.year < before_year]
        if not selected:
            return None
        raw = self._encode_records(selected)
        compressed = zlib.compress(raw, level=9)
        summary = self._summarize(selected)
        archive = TransferArchive(
            min_year=min(row.year for row in selected),
            max_year=max(row.year for row in selected),
            record_count=len(selected),
            compressed_payload=compressed,
            compressed_sha256=hashlib.sha256(compressed).hexdigest(),
            summary_rows=tuple(
                (int(row["year"]), str(row["kind"]), str(row["resource_kind"]),
                 int(row["records"]), float(row["cash_amount"]),
                 float(row["resource_amount"]))
                for row in summary
            ),
        )
        self.archives.append(archive)
        self.records = [row for row in self.records if row.year >= before_year]
        return archive.manifest()

    def audit(self, *, valid_entities: set[str] | None = None,
              year_range: tuple[int, int] | None = None) -> dict[str, object]:
        issues: list[str] = []
        archived_records: list[tuple[str, TransferRecord]] = []
        for index, archive in enumerate(self.archives):
            if hashlib.sha256(archive.compressed_payload).hexdigest() != archive.compressed_sha256:
                issues.append(f"archive {index}: checksum mismatch")
            if archive.record_count < 1 or archive.min_year > archive.max_year:
                issues.append(f"archive {index}: invalid bounds or count")
            try:
                decoded = self._decode_archive(archive)
            except ValueError as error:
                issues.append(f"archive {index}: {error}")
                continue
            if decoded and (
                    min(row.year for row in decoded) != archive.min_year
                    or max(row.year for row in decoded) != archive.max_year):
                issues.append(f"archive {index}: year bounds mismatch")
            expected_summary = tuple(
                (int(row["year"]), str(row["kind"]), str(row["resource_kind"]),
                 int(row["records"]), float(row["cash_amount"]),
                 float(row["resource_amount"]))
                for row in self._summarize(decoded)
            )
            if expected_summary != archive.summary_rows:
                issues.append(f"archive {index}: summary mismatch")
            archived_records.extend((f"archive {index} record {offset}", row)
                                    for offset, row in enumerate(decoded))
        labeled_records = archived_records + [
            (f"resident record {index}", row) for index, row in enumerate(self.records)
        ]
        for label, row in labeled_records:
            try:
                TransferRecord(**asdict(row))
            except (TypeError, ValueError) as error:
                issues.append(f"{label}: {error}")
                continue
            if valid_entities is not None:
                for role, entity in (("sender", row.sender), ("receiver", row.receiver)):
                    if entity not in valid_entities:
                        issues.append(f"{label}: unknown {role} {entity}")
            if year_range is not None and not year_range[0] <= row.year <= year_range[1]:
                issues.append(
                    f"{label}: year {row.year} outside {year_range[0]}..{year_range[1]}"
                )
            if self.strict_entities:
                for role, entity in (("sender", row.sender), ("receiver", row.receiver)):
                    if entity not in self.entities:
                        issues.append(f"{label}: unregistered {role} {entity}")
        return {"ok": not issues, "record_count": self.record_count,
                "resident_record_count": len(self.records),
                "archive_count": len(self.archives), "issues": issues}

    @property
    def record_count(self) -> int:
        return len(self.records) + sum(archive.record_count for archive in self.archives)

    @property
    def archive_bytes(self) -> int:
        return sum(archive.compressed_bytes for archive in self.archives)

    @property
    def resident_json_bytes(self) -> int:
        return len(self._encode_records(self.records))

    @property
    def storage_bytes(self) -> int:
        """Approximate payload bytes, excluding small Python/index overhead."""
        return self.archive_bytes + self.resident_json_bytes

    def summary(self) -> list[dict[str, object]]:
        """Aggregate only within matching year, mechanism and resource unit."""
        grouped: dict[tuple[int, str, str], dict[str, float | int]] = defaultdict(
            lambda: {"records": 0, "cash_amount": 0.0, "resource_amount": 0.0}
        )
        rows = self._summarize(self.records)
        for archive in self.archives:
            rows.extend({"year": year, "kind": kind, "resource_kind": resource_kind,
                         "records": records, "cash_amount": cash, "resource_amount": resource}
                        for year, kind, resource_kind, records, cash, resource
                        in archive.summary_rows)
        for row in rows:
            key = (int(row["year"]), str(row["kind"]), str(row["resource_kind"]))
            grouped[key]["records"] += int(row["records"])
            grouped[key]["cash_amount"] += float(row["cash_amount"])
            grouped[key]["resource_amount"] += float(row["resource_amount"])
        return [
            {
                "year": year,
                "kind": kind,
                "resource_kind": resource_kind,
                **grouped[(year, kind, resource_kind)],
            }
            for year, kind, resource_kind in sorted(grouped)
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "kind": "bilateral_transfer_ledger",
            "records": [asdict(row) for row in self.records],
            "archives": [archive.manifest() for archive in self.archives],
            "entities": sorted(self.entities),
            "units": {
                "cash_amount": "model monetary units",
                "resource_amount": "kind-specific; do not sum across resource kinds",
            },
        }
