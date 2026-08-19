"""Feature-freeze 下的首个可证伪 household study 协议。

本模块只负责研究设计与时间切分，不新增社会机制。所有模型必须消费同一
state-year 面板和同一 untouched test period。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class StudyDesign:
    name: str
    outcome: str
    treatment: tuple[str, ...]
    entity: str = "entity"
    year: str = "year"
    calibration_start: int = 2007
    calibration_end: int = 2017
    test_start: int = 2018
    test_end: int = 2021

    def validate(self) -> None:
        if self.calibration_start > self.calibration_end:
            raise ValueError("calibration period 无效")
        if self.test_start <= self.calibration_end or self.test_start > self.test_end:
            raise ValueError("test period 必须严格晚于 calibration period")
        if not self.outcome or not self.treatment:
            raise ValueError("必须指定 outcome 和 treatment")


FERTILITY_STUDY = StudyDesign(
    name="US state housing-childcare burden and fertility",
    outcome="asfr_15_44",
    treatment=("housing_cost_burden", "childcare_supply"),
    calibration_start=2007,
    calibration_end=2017,
    test_start=2018,
    test_end=2021,
)


def split_study_panel(
    rows: Iterable[Mapping[str, object]], design: StudyDesign = FERTILITY_STUDY,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """严格按年份切分面板；禁止 test 行进入 calibration。"""
    design.validate()
    calibration: list[dict[str, object]] = []
    test: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        year = int(row[design.year])
        if design.entity not in row or design.outcome not in row:
            raise ValueError(f"缺少研究字段：{design.entity}/{design.outcome}")
        missing = [field for field in design.treatment if field not in row]
        if missing:
            raise ValueError(f"缺少处理变量：{missing}")
        if design.calibration_start <= year <= design.calibration_end:
            calibration.append(row)
        elif design.test_start <= year <= design.test_end:
            test.append(row)
    if not calibration or not test:
        raise ValueError("calibration 或 untouched test 为空")
    if {int(row[design.year]) for row in calibration} & {int(row[design.year]) for row in test}:
        raise AssertionError("calibration/test 年份发生泄漏")
    return calibration, test


def required_empirical_columns() -> dict[str, tuple[str, ...]]:
    return {
        "outcome": ("entity", "year", "asfr_15_44", "births_15_44", "female_15_44"),
        "housing": ("housing_cost_burden", "median_gross_rent", "rent_burden_share"),
        "childcare": ("childcare_supply", "under5_formal_care_share"),
        "controls": ("female_employment", "unemployment", "education", "migration_rate"),
    }


def validate_empirical_panel(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """检查最小面板字段、重复州年键和数值可用性。"""
    rows = list(rows)
    required = {field for fields in required_empirical_columns().values() for field in fields}
    if not rows:
        raise ValueError("经验面板为空")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"经验面板缺少字段：{missing}")
    keys = [(str(row["entity"]), int(row["year"])) for row in rows]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    numeric = ["asfr_15_44", "births_15_44", "female_15_44",
               "housing_cost_burden", "childcare_supply"]
    invalid = sum(1 for row in rows for field in numeric
                  if row.get(field) in (None, "") or not _is_finite(row[field]))
    return {"rows": len(rows), "entities": len({key[0] for key in keys}),
            "years": sorted({key[1] for key in keys}),
            "duplicate_keys": duplicates, "invalid_core_values": invalid,
            "ok": not duplicates and invalid == 0}


def _is_finite(value: object) -> bool:
    try:
        return float(value) == float(value) and abs(float(value)) != float("inf")
    except (TypeError, ValueError):
        return False


def study_readiness(
    housing_rows: Iterable[Mapping[str, object]],
    fertility_rows: Iterable[Mapping[str, object]] = (),
    *,
    design: StudyDesign = FERTILITY_STUDY,
    min_entities: int = 50,
) -> dict[str, object]:
    """给出进入校准、回放和模型比较前的最小就绪状态。"""
    housing = list(housing_rows)
    fertility = list(fertility_rows)
    housing_years = {int(row["year"]) for row in housing if "year" in row}
    housing_entities = {str(row.get("state", row.get("entity", ""))) for row in housing}
    fertility_years = {int(row["year"]) for row in fertility if "year" in row}
    fertility_entities = {str(row.get("state", row.get("entity", ""))) for row in fertility}
    required_years = set(range(design.calibration_start, design.test_end + 1))
    housing_full = len(housing_entities) >= min_entities and required_years <= housing_years
    fertility_full = len(fertility_entities) >= min_entities and required_years <= fertility_years
    return {
        "housing_slice_valid": bool(housing),
        "housing_full_period": housing_full,
        "fertility_full_period": fertility_full,
        "panel_merge_ready": housing_full and fertility_full,
        "model_comparison_ready": housing_full and fertility_full,
        "missing_housing_years": sorted(required_years - housing_years),
        "missing_fertility_years": sorted(required_years - fertility_years),
        "next_required": ("download fertility outcome and denominator data"
                           if not fertility_full else
                           "merge panel and run calibration-only model checks"),
    }
