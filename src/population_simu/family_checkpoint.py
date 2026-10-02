"""Complete, isolated in-memory checkpoints for the current FamilyWorld engine.

The canonical encoding below is a fingerprint format, not a persistence format.
Restoration requires this process and code version; no pickle or JSON loader is
provided. Object graph aliases and dictionary insertion order are significant:
iteration order can change how the engine consumes its sequential random stream.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
import random
from types import CodeType, FunctionType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .family_world import FamilyWorld


class _StateEncoder:
    def __init__(self) -> None:
        self.references: dict[int, int] = {}
        # Keep temporary getstate()/closure tuples alive while encoding. Without
        # this, Python may reuse an ID and falsely identify an unrelated alias.
        self.objects: list[object] = []

    def encode(self, value: object) -> object:
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("World checkpoint cannot contain non-finite numbers")
            return {"float": value.hex()}
        if isinstance(value, bytes):
            return {"bytes": value.hex()}

        identity = id(value)
        if identity in self.references:
            return {"ref": self.references[identity]}
        reference = len(self.references)
        self.references[identity] = reference
        self.objects.append(value)
        type_name = f"{type(value).__module__}.{type(value).__qualname__}"
        result: dict[str, object] = {"id": reference, "type": type_name}

        if isinstance(value, random.Random):
            result["state"] = self.encode(value.getstate())
            result["attributes"] = self.encode(vars(value))
        elif isinstance(value, dict):
            result["items"] = [
                [self.encode(key), self.encode(item)] for key, item in value.items()
            ]
            if isinstance(value, defaultdict):
                result["default_factory"] = self.encode(value.default_factory)
        elif isinstance(value, (tuple, list)):
            result["items"] = [self.encode(item) for item in value]
        elif isinstance(value, (set, frozenset)):
            # Current engine sets contain scalar process names. Independent
            # encoders give deterministic order before assigning graph IDs.
            ordered = sorted(value, key=lambda item: json.dumps(
                _StateEncoder().encode(item), sort_keys=True, separators=(",", ":")
            ))
            result["items"] = [self.encode(item) for item in ordered]
        elif isinstance(value, FunctionType):
            # The occupation totals defaultdict owns a stateless Python factory.
            # Preserve defaults/closures as well so future stateful factories
            # cannot silently disappear from the fingerprint.
            result.update({
                "module": value.__module__,
                "qualname": value.__qualname__,
                "code": self.encode(value.__code__),
                "defaults": self.encode(value.__defaults__),
                "keyword_defaults": self.encode(value.__kwdefaults__),
                "closure": self.encode(tuple(
                    cell.cell_contents for cell in (value.__closure__ or ())
                )),
                "attributes": self.encode(vars(value)),
            })
        elif isinstance(value, CodeType):
            result.update({
                "bytecode": value.co_code.hex(),
                "constants": self.encode(value.co_consts),
                "names": self.encode(value.co_names),
                "variables": self.encode(value.co_varnames),
                "free_variables": self.encode(value.co_freevars),
                "cell_variables": self.encode(value.co_cellvars),
                "arguments": value.co_argcount,
                "positional_only_arguments": value.co_posonlyargcount,
                "keyword_only_arguments": value.co_kwonlyargcount,
                "flags": value.co_flags,
            })
        elif type(value).__module__.startswith("population_simu.") and hasattr(value, "__dict__"):
            result["attributes"] = self.encode(vars(value))
        else:
            raise TypeError(f"Unsupported world checkpoint state type: {type_name}")
        return result


def fingerprint_world(world: "FamilyWorld") -> str:
    """SHA256 of the full current engine state, including RNG and mutable aliases.

    Unsupported state types fail explicitly instead of being omitted. This hash
    identifies a state under this implementation; it is not a cross-version
    compatibility promise or an identifier for observational equivalence.
    """
    payload = {
        "format": "family-world-state-v1",
        "state": _StateEncoder().encode(world),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FamilyCheckpoint:
    """An isolated checkpoint; every restore produces an independent world."""

    _world: "FamilyWorld" = field(repr=False)
    fingerprint: str
    year: int

    @classmethod
    def capture(cls, world: "FamilyWorld") -> "FamilyCheckpoint":
        captured = deepcopy(world)
        return cls(captured, fingerprint_world(captured), captured.year)

    def restore(self) -> "FamilyWorld":
        """Restore without initialization, reseeding, or sharing mutable state."""
        return deepcopy(self._world)
