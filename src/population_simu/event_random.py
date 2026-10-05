"""Stable event-addressed randomness and replayable exogenous paths.

Keys, rather than call order, select random streams.  This module is limited to
exogenous processes for now; household and person events still use the legacy
sequential stream and must not be described as event-aligned counterfactuals.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import random
from typing import Callable


@dataclass(frozen=True, order=True)
class EventKey:
    process: str
    year: int
    country: str = ""
    region: str = ""
    entity: str = ""
    draw: str = ""

    def __post_init__(self) -> None:
        if not self.process or type(self.year) is not int:
            raise ValueError("event key requires a process and integer year")
        if any(not isinstance(value, str) for value in
               (self.country, self.region, self.entity, self.draw)):
            raise ValueError("event key identifiers must be strings")

    @property
    def token(self) -> str:
        return json.dumps(
            [self.process, self.year, self.country, self.region, self.entity, self.draw],
            ensure_ascii=False, separators=(",", ":"),
        )

    @classmethod
    def from_token(cls, token: str) -> "EventKey":
        try:
            values = json.loads(token)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("invalid event key token") from error
        if not isinstance(values, list) or len(values) != 6:
            raise ValueError("event key token must contain six fields")
        try:
            key = cls(*values)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid event key token fields") from error
        if key.token != token:
            raise ValueError("event key token is not canonical")
        return key


class EventRandom:
    """Create deterministic independent streams from a root seed and EventKey."""

    def __init__(self, seed: int):
        if type(seed) is not int:
            raise ValueError("event random seed must be an integer")
        self.seed = seed

    def stream(self, key: EventKey) -> random.Random:
        payload = json.dumps(
            {"format": "event-random-v1", "seed": self.seed, "key": key.token},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        derived = int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")
        return random.Random(derived)


class ExogenousPath:
    """Record or replay JSON-compatible exogenous values by stable event key."""

    def __init__(self, values: dict[str, object] | None = None, *,
                 record_missing: bool = False, strict: bool = False):
        if record_missing and strict:
            raise ValueError("an exogenous path cannot record and be strict simultaneously")
        self._values = deepcopy(values or {})
        self.record_missing = bool(record_missing)
        self.strict = bool(strict)
        self._validate_values(self._values)

    @staticmethod
    def _validate_values(values: dict[str, object]) -> None:
        if not isinstance(values, dict) or any(not isinstance(key, str) for key in values):
            raise ValueError("exogenous path must be a string-keyed mapping")
        try:
            json.dumps(values, ensure_ascii=False, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("exogenous path values must be finite JSON data") from error

    def resolve(self, key: EventKey, factory: Callable[[], object]) -> object:
        token = key.token
        if token in self._values:
            return deepcopy(self._values[token])
        if self.strict:
            raise KeyError(f"missing frozen exogenous event: {token}")
        value = factory()
        self._validate_values({token: value})
        if self.record_missing:
            self._values[token] = deepcopy(value)
        return deepcopy(value)

    def freeze(self) -> "ExogenousPath":
        return ExogenousPath(self._values, strict=True)

    @property
    def sha256(self) -> str:
        payload = json.dumps(
            {"format": "frozen-exogenous-path-v1", "values": self._values},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def manifest(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        years: list[int] = []
        for token in self._values:
            key = EventKey.from_token(token)
            counts[key.process] = counts.get(key.process, 0) + 1
            years.append(key.year)
        return {
            "sha256": self.sha256,
            "events": len(self._values),
            "counts_by_process": dict(sorted(counts.items())),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        }

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 1, "kind": "frozen_exogenous_path",
                "values": deepcopy(self._values)}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExogenousPath":
        if set(payload) != {"schema_version", "kind", "values"}:
            raise ValueError("invalid exogenous path fields")
        if payload["schema_version"] != 1 or payload["kind"] != "frozen_exogenous_path":
            raise ValueError("unsupported exogenous path schema")
        values = payload["values"]
        if not isinstance(values, dict):
            raise ValueError("exogenous path values must be a mapping")
        path = cls(values, strict=True)
        path.manifest()  # Reject malformed or non-canonical keys at the load boundary.
        return path

    def __len__(self) -> int:
        return len(self._values)
