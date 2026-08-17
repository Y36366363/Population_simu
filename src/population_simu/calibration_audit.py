"""可审计的国家校准质量报告。"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from .national_calibration import (
    FertilityObservation,
    NationalCalibrationBundle,
)


def audit_calibration_bundle(
    bundle: NationalCalibrationBundle,
    *,
    fertility_observations: Iterable[FertilityObservation] = (),
    max_age: int = 100,
) -> dict[str, object]:
    """输出组件覆盖、权重分母和严格验证状态，不改变模型输入。"""
    report = bundle.validate(strict=False)
    life = []
    for table in bundle.life_tables:
        missing = {}
        for sex, profile in table.rates.items():
            missing[sex] = sorted(set(range(max_age + 1)) - set(profile.ages))
        life.append({"country": table.country, "year": table.year,
                     "complete": all(not values for values in missing.values()),
                     "missing_ages": missing})
    migration = []
    for matrix in bundle.migration_matrices:
        keys = Counter((r.origin, r.destination, r.sex, r.age) for r in matrix.records)
        migration.append({"year": matrix.year, "records": len(matrix.records),
                          "duplicate_keys": sum(v - 1 for v in keys.values() if v > 1),
                          "has_flow_exposure": all(r.flow is not None and r.exposure is not None
                                                    for r in matrix.records)})
    observations = list(fertility_observations)
    fertility = {"records": len(observations),
                 "positive_exposure": all(obs.exposure > 0 for obs in observations),
                 "states": sorted({(obs.marital, obs.parity) for obs in observations})}
    component_status = {
        "life_table": bool(life) and all(item["complete"] for item in life),
        "migration_od": bool(migration) and all(item["records"] and not item["duplicate_keys"]
                                                  for item in migration),
        "fertility_birth_exposure": bool(observations) and fertility["positive_exposure"],
    }
    return {"ok": report.ok and all(component_status.values()),
            "validation": report.as_dict(), "components": component_status,
            "life_tables": life, "migration": migration, "fertility": fertility}
