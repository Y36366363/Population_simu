"""Calibration contract for the frozen household fertility adapter.

The current state-year panel identifies the female 15--44 denominator and a
reduced-form housing association. It does *not* identify age-specific,
marital-exposure, or parity-transition hazards. Those parameters therefore
remain explicit priors until a marriage/parity exposure file is added.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from statistics import median
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class HouseholdCalibration:
    female_exposure_scale: float = 1.0
    age_profile: tuple[float, ...] = (0.35, 0.65, 0.9, 1.0, 0.95, 0.75, 0.45)
    age_profile_ages: tuple[int, ...] = (18, 22, 26, 30, 34, 38, 42)
    partnership_exposure: float = 0.62
    parity_progression: tuple[float, float, float] = (0.72, 0.48, 0.24)
    housing_elasticity: float = 0.0
    tfr_conversion_years: float = 30.0
    reference_housing_burden: float = 0.35
    identified: tuple[str, ...] = ("female_exposure_scale", "housing_elasticity")
    prior_only: tuple[str, ...] = ("age_profile", "partnership_exposure", "parity_progression")

    def housing_multiplier(self, burden: float) -> float:
        """Map burden to the existing fertility probability, not a new mechanism."""
        return math.exp(self.housing_elasticity * (float(burden) - self.reference_housing_burden))

    def as_dict(self) -> dict[str, object]:
        return {
            "female_exposure_scale": self.female_exposure_scale,
            "age_profile": list(self.age_profile),
            "age_profile_ages": list(self.age_profile_ages),
            "partnership_exposure": self.partnership_exposure,
            "parity_progression": list(self.parity_progression),
            "housing_elasticity": self.housing_elasticity,
            "tfr_conversion_years": self.tfr_conversion_years,
            "reference_housing_burden": self.reference_housing_burden,
            "identified": list(self.identified),
            "prior_only": list(self.prior_only),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "HouseholdCalibration":
        """Load a frozen calibration artifact without silently filling fields."""
        values = dict(payload.get("calibration", payload))
        required = {"age_profile", "age_profile_ages", "parity_progression",
                    "partnership_exposure", "housing_elasticity"}
        missing = sorted(required - set(values))
        if missing:
            raise ValueError(f"校准 artifact 缺少字段：{missing}")
        return cls(
            female_exposure_scale=float(values.get("female_exposure_scale", 1.0)),
            age_profile=tuple(float(x) for x in values["age_profile"]),
            age_profile_ages=tuple(int(x) for x in values["age_profile_ages"]),
            partnership_exposure=float(values["partnership_exposure"]),
            parity_progression=tuple(float(x) for x in values["parity_progression"]),
            housing_elasticity=float(values["housing_elasticity"]),
            tfr_conversion_years=float(values.get("tfr_conversion_years", 30.0)),
            reference_housing_burden=float(values.get("reference_housing_burden", 0.35)),
            identified=tuple(str(x) for x in values.get("identified", ())),
            prior_only=tuple(str(x) for x in values.get("prior_only", ())),
        )


def calibrate_household_parameters(rows: Iterable[Mapping[str, object]]) -> HouseholdCalibration:
    """Estimate identifiable parameters from calibration rows only.

    ``rows`` must exclude the untouched test period. Missing marital/parity
    denominators do not trigger imputation; the corresponding values remain
    documented priors.
    """
    source = [r for r in rows if _number(r.get("asfr_15_44")) is not None
              and _number(r.get("housing_cost_burden")) is not None]
    if not source:
        raise ValueError("需要 asfr_15_44 和 housing_cost_burden 才能校准")
    burdens = [float(r["housing_cost_burden"]) for r in source]
    reference = median(burdens)
    by_entity: dict[str, list[Mapping[str, object]]] = {}
    for row in source:
        by_entity.setdefault(str(row.get("entity", "all")), []).append(row)
    pairs: list[tuple[float, float]] = []
    for entity, entity_rows in by_entity.items():
        xbar = sum(float(r["housing_cost_burden"]) for r in entity_rows) / len(entity_rows)
        ybar = sum(float(r["asfr_15_44"]) for r in entity_rows) / len(entity_rows)
        pairs.extend((float(r["housing_cost_burden"]) - xbar,
                      float(r["asfr_15_44"]) - ybar) for r in entity_rows)
    denom = sum(x * x for x, _ in pairs)
    slope_asfr = sum(x * y for x, y in pairs) / denom if denom > 1e-12 else 0.0
    mean_asfr = sum(float(r["asfr_15_44"]) for r in source) / len(source)
    # Convert a one-unit housing burden change into a log fertility multiplier.
    elasticity = slope_asfr / max(1.0, mean_asfr)
    elasticity = max(-5.0, min(5.0, elasticity))
    return HouseholdCalibration(
        female_exposure_scale=1.0,
        housing_elasticity=elasticity,
        reference_housing_burden=reference,
    )


def calibrate_fertility_observations(
    observations: Iterable[Any], *, prior: HouseholdCalibration | None = None,
    min_age_cells: int = 3,
) -> HouseholdCalibration:
    """Identify age, partnership and parity inputs from weighted observations.

    The observations must contain ``age``, ``marital``, ``parity``, ``births``
    and ``exposure`` (either :class:`FertilityObservation` objects or mappings).
    This is deliberately a separate calibration step: the state-year housing
    panel cannot identify these denominators.  Partnership exposure is only
    identified when rows with ``parity=all`` are supplied, preventing accidental
    double-counting of parity-specific denominators.
    """
    base = prior or HouseholdCalibration()
    records = [_observation_dict(obs) for obs in observations]
    valid = [r for r in records if _number(r.get("age")) is not None
             and _number(r.get("births")) is not None
             and _number(r.get("exposure")) is not None
             and float(r["exposure"]) > 0]
    if not valid:
        return base

    identified = set(base.identified)
    prior_only = set(base.prior_only)
    # Prefer an explicit all-parity exposure table for age and partnership.
    all_rows = [r for r in valid if _norm_parity(r.get("parity")) == "all"]
    # A separate all-parity exposure table may be paired with parity-specific
    # births. If its births are all zero after the key join, fall back to the
    # detailed rows rather than incorrectly concluding the age profile is flat.
    age_rows = all_rows if any(float(r["births"]) > 0 for r in all_rows) else valid
    by_age: dict[int, list[float]] = {}
    for row in age_rows:
        age = int(float(row["age"]))
        if 15 <= age <= 44:
            by_age.setdefault(age, [0.0, 0.0])
            by_age[age][0] += float(row["births"])
            by_age[age][1] += float(row["exposure"])
    age_rates = {age: b / e for age, (b, e) in by_age.items() if e > 0}
    if len(age_rates) >= min_age_cells and max(age_rates.values(), default=0) > 0:
        peak = max(age_rates.values())
        ages = base.age_profile_ages
        profile = tuple(_linear_profile(age_rates, age) / peak for age in ages)
        base = replace(base, age_profile=profile)
        identified.add("age_profile"); prior_only.discard("age_profile")

    if all_rows:
        married = sum(float(r["exposure"]) for r in all_rows
                      if _norm_marital(r.get("marital")) == "married")
        total = sum(float(r["exposure"]) for r in all_rows)
        if total > 0 and married >= 0:
            base = replace(base, partnership_exposure=max(0.0, min(1.0, married / total)))
            identified.add("partnership_exposure"); prior_only.discard("partnership_exposure")

    rates: dict[str, float] = {}
    for parity in ("first", "second", "third_plus"):
        subset = [r for r in valid if _norm_marital(r.get("marital")) == "married"
                  and _norm_parity(r.get("parity")) == parity]
        exposure = sum(float(r["exposure"]) for r in subset)
        births = sum(float(r["births"]) for r in subset)
        if exposure > 0:
            rates[parity] = births / exposure
    if "first" in rates and rates["first"] > 0 and len(rates) >= 2:
        first = rates["first"]
        progression = tuple(max(0.0, min(1.0, rates.get(p, first) / first))
                            for p in ("first", "second", "third_plus"))
        base = replace(base, parity_progression=progression)
        identified.add("parity_progression"); prior_only.discard("parity_progression")
    return replace(base, identified=tuple(sorted(identified)), prior_only=tuple(sorted(prior_only)))


def _observation_dict(obs: Any) -> dict[str, object]:
    if isinstance(obs, Mapping):
        return dict(obs)
    return {name: getattr(obs, name, None)
            for name in ("age", "marital", "parity", "births", "exposure")}


def _norm_marital(value: object) -> str:
    text = str(value).strip().lower()
    return "married" if text in {"married", "1", "m", "spouse"} else "unmarried"


def _norm_parity(value: object) -> str:
    text = str(value).strip().lower().replace(" ", "_")
    if text in {"all", "total", "any"}:
        return "all"
    if text in {"first", "1", "0"}:
        return "first"
    if text in {"second", "2"}:
        return "second"
    if text in {"third", "third_plus", "3", "3+", "fourth_plus"}:
        return "third_plus"
    return text


def _linear_profile(points: Mapping[int, float], age: int) -> float:
    ordered = sorted(points.items())
    if age <= ordered[0][0]:
        return ordered[0][1]
    if age >= ordered[-1][0]:
        return ordered[-1][1]
    for (left_age, left), (right_age, right) in zip(ordered, ordered[1:]):
        if left_age <= age <= right_age:
            fraction = (age - left_age) / (right_age - left_age)
            return left + fraction * (right - left)
    return ordered[-1][1]


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
