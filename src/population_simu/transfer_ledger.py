"""Auditable bilateral records for transfers already present in FamilyWorld."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
import math


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


class TransferLedger:
    """Append-only bilateral ledger; it observes transfers and never creates them."""

    def __init__(self) -> None:
        self.records: list[TransferRecord] = []

    def record(self, *, year: int, kind: str, sender: str, receiver: str,
               cash_amount: float = 0.0, resource_kind: str = "none",
               resource_amount: float = 0.0) -> TransferRecord | None:
        if cash_amount == 0 and resource_amount == 0:
            return None
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
            row for row in self.records
            if (year is None or row.year == year)
            and (entity is None or entity in (row.sender, row.receiver))
            and (kind is None or row.kind == kind)
            and (resource_kind is None or row.resource_kind == resource_kind)
        ]

    def audit(self) -> dict[str, object]:
        issues: list[str] = []
        for index, row in enumerate(self.records):
            try:
                TransferRecord(**asdict(row))
            except (TypeError, ValueError) as error:
                issues.append(f"record {index}: {error}")
        return {"ok": not issues, "record_count": len(self.records), "issues": issues}

    def summary(self) -> list[dict[str, object]]:
        """Aggregate only within matching year, mechanism and resource unit."""
        grouped: dict[tuple[int, str, str], dict[str, float | int]] = defaultdict(
            lambda: {"records": 0, "cash_amount": 0.0, "resource_amount": 0.0}
        )
        for row in self.records:
            key = (row.year, row.kind, row.resource_kind)
            grouped[key]["records"] += 1
            grouped[key]["cash_amount"] += row.cash_amount
            grouped[key]["resource_amount"] += row.resource_amount
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
            "units": {
                "cash_amount": "model monetary units",
                "resource_amount": "kind-specific; do not sum across resource kinds",
            },
        }
