"""Calibration contract for the frozen household fertility adapter.

The current state-year panel identifies the female 15--44 denominator and a
reduced-form housing association. It does *not* identify age-specific,
marital-exposure, or parity-transition hazards. Those parameters therefore
remain explicit priors until a marriage/parity exposure file is added.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median
from typing import Iterable, Mapping


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


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
