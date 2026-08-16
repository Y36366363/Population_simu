"""真实年龄—性别数据与 cohort-component 快照的历史回放工具。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping

from .hazards import AgeRateProfile

WB_AGE_INDICATORS: dict[str, tuple[str, int, int]] = {
    "SP.POP.0014.FE.IN": ("F", 0, 14),
    "SP.POP.0014.MA.IN": ("M", 0, 14),
    "SP.POP.1564.FE.IN": ("F", 15, 64),
    "SP.POP.1564.MA.IN": ("M", 15, 64),
    "SP.POP.65UP.FE.IN": ("F", 65, 100),
    "SP.POP.65UP.MA.IN": ("M", 65, 100),
}


def load_world_bank_age_sex_groups(path: str | Path) -> list[dict[str, object]]:
    """读取世界银行 WDI 0—14/15—64/65+ 年龄组—性别 CSV 快照。"""
    rows: list[dict[str, object]] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        for line, row in enumerate(csv.DictReader(file), start=2):
            indicator = row.get("indicator", "")
            if indicator not in WB_AGE_INDICATORS:
                raise ValueError(f"第 {line} 行包含未知年龄指标 {indicator}")
            try:
                value = float(row["value"])
                year = int(row["year"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第 {line} 行年份或人口数无效") from exc
            sex, age_min, age_max = WB_AGE_INDICATORS[indicator]
            rows.append({
                "entity": row["entity"], "code": row.get("code", ""), "year": year,
                "sex": sex, "age_min": age_min, "age_max": age_max,
                "population": value, "source_indicator": indicator,
            })
    return rows


def expand_age_groups_uniformly(rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """将年龄组均匀拆成单岁输入，并明确标记为 derived/synthetic。

    这只是历史回放的可运行初始化，不是观测单岁年龄；严格校准应替换为
    census/register 的 single-age 文件。
    """
    expanded: list[dict[str, object]] = []
    for row in rows:
        lo, hi = int(row["age_min"]), int(row["age_max"])
        width = hi - lo + 1
        if width <= 0:
            raise ValueError("年龄组范围无效")
        per_age = float(row["population"]) / width
        for age in range(lo, hi + 1):
            item = dict(row)
            item.update({"age": age, "population": per_age, "derived": True,
                         "derivation": "uniform_age_group_split"})
            expanded.append(item)
    return expanded


def age_coverage_report(rows: Iterable[Mapping[str, object]], *, max_age: int = 100) -> dict[str, object]:
    """报告输入是否覆盖完整单岁年龄，避免把年龄组资料误标为生命表级数据。"""
    rows = list(rows)
    ages = {int(row["age"]) for row in rows if "age" in row}
    missing = sorted(set(range(max_age + 1)) - ages)
    return {"single_age": not missing, "n_ages": len(ages), "missing_ages": missing,
            "derived_rows": sum(bool(row.get("derived", False)) for row in rows)}


def load_age_sex_death_rates(path: str | Path) -> list[dict[str, object]]:
    """读取 OWID/HMD/UN WPP 风格的年龄—性别死亡率长表。"""
    rows: list[dict[str, object]] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        for line, row in enumerate(csv.DictReader(file), start=2):
            try:
                rows.append({
                    "entity": row["entity"], "code": row.get("code", ""),
                    "year": int(row["year"]), "age": int(row["age"]),
                    "sex": row["sex"], "death_rate_per_1000": float(row["death_rate_per_1000"]),
                })
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"第 {line} 行死亡率字段无效") from exc
    return rows


def death_rate_profiles(
    rows: Iterable[Mapping[str, object]],
    *,
    entity: str,
    year: int,
) -> dict[str, AgeRateProfile]:
    """把年龄点死亡率（每千人）转换成 cohort 核心的年度 hazard profile。

    线性插值只用于把公开数据中的年龄点接入接口；它不是完整生命表的替代品。
    """
    selected = [row for row in rows if str(row.get("entity")) == entity
                and int(row["year"]) == year]
    profiles: dict[str, AgeRateProfile] = {}
    for sex in ("F", "M"):
        points = sorted((int(row["age"]), float(row["death_rate_per_1000"]) / 1000.0)
                        for row in selected if str(row.get("sex")) == sex)
        if points:
            profiles[sex] = AgeRateProfile(tuple(age for age, _ in points),
                                            tuple(rate for _, rate in points))
    if not profiles:
        raise ValueError(f"没有 {entity}/{year} 的年龄—性别死亡率")
    return profiles


def _snapshot_value(snapshot: Mapping[str, Mapping[str, Iterable[float]]], sex: str,
                    age_min: int, age_max: int) -> float:
    values = list(snapshot.get(sex, ()))
    if not values:
        return 0.0
    return sum(float(values[age]) for age in range(max(0, age_min), min(age_max, len(values) - 1) + 1))


def replay_age_sex_groups(
    observed_rows: Iterable[Mapping[str, object]],
    simulated_snapshots: Mapping[int, Mapping[str, Mapping[str, Iterable[float]]]],
) -> dict[str, object]:
    """将真实年龄组—性别观测与模型单岁年龄快照逐年对账。

    ``simulated_snapshots`` 的结构为 ``year -> entity -> sex -> age counts``。
    返回总体 MAE/MAPE 和按实体、性别、年龄组的误差，缺失年份会报错。
    """
    rows = list(observed_rows)
    errors: list[float] = []
    percentages: list[float] = []
    by_stratum: dict[str, list[float]] = {}
    for row in rows:
        year = int(row["year"])
        entity = str(row["entity"])
        if year not in simulated_snapshots or entity not in simulated_snapshots[year]:
            raise ValueError(f"缺少 {entity}/{year} 的 cohort-component 快照")
        predicted = _snapshot_value(
            simulated_snapshots[year][entity], str(row["sex"]),
            int(row["age_min"]), int(row["age_max"]),
        )
        actual = float(row["population"])
        error = predicted - actual
        errors.append(error)
        if actual:
            percentages.append(abs(error) / abs(actual))
        label = f"{entity}|{row['sex']}|{row['age_min']}-{row['age_max']}"
        by_stratum.setdefault(label, []).append(abs(error))
    if not errors:
        raise ValueError("没有可回放的年龄—性别观测")
    return {
        "n": len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "bias": sum(errors) / len(errors),
        "mape": sum(percentages) / len(percentages) if percentages else 0.0,
        "by_stratum": {
            label: {"n": len(values), "mae": sum(values) / len(values)}
            for label, values in sorted(by_stratum.items())
        },
    }


def reconcile_age_sex_snapshots(
    family_snapshot: Mapping[str, Mapping[str, Mapping[int, int] | Iterable[float]]],
    cohort_snapshot: Mapping[str, Mapping[str, Iterable[float]]],
) -> dict[str, object]:
    """比较家庭明细聚合与 cohort 核心的同年年龄—性别矩阵。"""
    errors: list[float] = []
    by_entity: dict[str, list[float]] = {}
    entities = set(family_snapshot) | set(cohort_snapshot)
    for entity in entities:
        entity_errors: list[float] = []
        for sex in ("F", "M"):
            family_values = family_snapshot.get(entity, {}).get(sex, {})
            if isinstance(family_values, Mapping):
                family_array = [float(family_values.get(age, 0)) for age in range(101)]
            else:
                family_array = [float(value) for value in family_values]
            cohort_values = [float(value) for value in cohort_snapshot.get(entity, {}).get(sex, ())]
            max_age = max(len(family_array), len(cohort_values))
            for age in range(max_age):
                difference = (family_array[age] if age < len(family_array) else 0.0) - (
                    cohort_values[age] if age < len(cohort_values) else 0.0
                )
                entity_errors.append(abs(difference))
        if entity_errors:
            by_entity[entity] = entity_errors
            errors.extend(entity_errors)
    if not errors:
        raise ValueError("两个快照没有可比较的年龄—性别数据")
    return {
        "n": len(errors),
        "mae": sum(errors) / len(errors),
        "by_entity": {
            entity: {"n": len(values), "mae": sum(values) / len(values)}
            for entity, values in sorted(by_entity.items())
        },
    }
