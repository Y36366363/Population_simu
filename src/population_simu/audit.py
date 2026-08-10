"""人口沙盘的微观—宏观一致性审计。"""

from __future__ import annotations

import math
from typing import Iterable, Mapping


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def audit_snapshot(snapshot: Mapping[str, object]) -> list[str]:
    """检查当前快照的非负性和国家—地区分区闭合。"""
    issues: list[str] = []
    population = snapshot.get("population", 0)
    households = snapshot.get("households", 0)
    if not isinstance(population, int) or population < 0:
        issues.append("snapshot.population 必须是非负整数")
    if not isinstance(households, int) or households < 0:
        issues.append("snapshot.households 必须是非负整数")
    countries = snapshot.get("countries", {})
    if not isinstance(countries, Mapping):
        return issues + ["snapshot.countries 必须是映射"]
    country_population = 0
    country_households = 0
    for country_id, country in countries.items():
        if not isinstance(country, Mapping):
            issues.append(f"{country_id} 必须是映射")
            continue
        c_population = country.get("population", 0)
        c_households = country.get("households", 0)
        country_population += c_population if isinstance(c_population, int) else 0
        country_households += c_households if isinstance(c_households, int) else 0
        regions = country.get("regions", [])
        region_population = sum(
            row.get("population", 0) for row in regions if isinstance(row, Mapping)
        )
        region_households = sum(
            row.get("households", 0) for row in regions if isinstance(row, Mapping)
        )
        if region_population != c_population:
            issues.append(f"{country_id} 的地区人口没有闭合")
        if region_households != c_households:
            issues.append(f"{country_id} 的地区家庭数没有闭合")
        for row in regions:
            if not isinstance(row, Mapping):
                issues.append(f"{country_id} 含有非法地区记录")
                continue
            for key in ("population", "households", "median_resources"):
                value = row.get(key, 0)
                if not _finite(value) or float(value) < 0:
                    issues.append(f"{country_id}/{row.get('id')} 的 {key} 非法")
    if country_population != population:
        issues.append("国家人口合计没有闭合")
    if country_households != households:
        issues.append("国家家庭合计没有闭合")
    return issues


def audit_history(rows: Iterable[Mapping[str, object]]) -> list[str]:
    """检查年度结果的基本范围，不替代历史数据校准。"""
    issues: list[str] = []
    previous: dict[str, int] = {}
    for row in rows:
        country = str(row.get("country", row.get("country_id", "?")))
        year = row.get("year")
        if not isinstance(year, int):
            issues.append(f"{country} 年份非法")
        population = row.get("population", 0)
        if not isinstance(population, int) or population < 0:
            issues.append(f"{country} 人口非法")
        if isinstance(population, int) and country in previous and year == row.get("year"):
            if population < 0:
                issues.append(f"{country} 出现负人口")
        previous[country] = population if isinstance(population, int) else 0
        for key in ("births", "deaths", "migrants", "environmental_stress", "capacity_pressure"):
            value = row.get(key, 0)
            if not _finite(value) or float(value) < 0:
                issues.append(f"{country}/{key} 非法")
    return issues

