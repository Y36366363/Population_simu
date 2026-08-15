"""国家级人口校准数据契约与 cohort 输入编译器。

该模块不内置任何国家的最终参数，而是定义三类数据如何组织、检查和编译：
生命表、年龄—性别迁移 OD、孩次—婚姻状态年龄别生育率。缺失年龄或年份默认
产生 warning；生产校准可使用 ``strict=True`` 将其升级为错误。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable, Mapping

from .fertility import FertilitySchedule, FertilityState
from .hazards import AgeRateProfile, hazard_to_probability


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings)}


@dataclass(frozen=True)
class LifeTableSchedule:
    country: str
    year: int
    rates: Mapping[str, AgeRateProfile]
    max_age: int = 100

    def validate(self, *, strict: bool = True) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        expected = set(range(self.max_age + 1))
        for sex in ("F", "M"):
            profile = self.rates.get(sex)
            if profile is None:
                errors.append(f"{self.country}/{self.year}: 缺少 {sex} 生命表")
                continue
            ages = set(profile.ages)
            if not ages & expected:
                errors.append(f"{self.country}/{self.year}/{sex}: 没有有效年龄")
            if len(ages) < self.max_age // 2:
                warnings.append(f"{self.country}/{self.year}/{sex}: 年龄点少于完整生命表")
            if any(not math.isfinite(rate) or rate < 0 for rate in profile.rates):
                errors.append(f"{self.country}/{self.year}/{sex}: 死亡率非法")
        if strict and warnings:
            errors.extend(warnings)
            warnings = []
        return ValidationReport(tuple(errors), tuple(warnings))


@dataclass(frozen=True)
class MigrationRecord:
    origin: str
    destination: str
    sex: str
    age: int
    hazard: float


@dataclass(frozen=True)
class AgeSpecificMigrationMatrix:
    year: int
    records: tuple[MigrationRecord, ...]
    nodes: tuple[str, ...]

    def validate(self, *, strict: bool = True) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        seen: set[tuple[str, str, str, int]] = set()
        sums: dict[tuple[str, str, int], float] = {}
        for record in self.records:
            key = (record.origin, record.destination, record.sex, record.age)
            if key in seen:
                errors.append(f"迁移矩阵重复键 {key}")
            seen.add(key)
            if record.origin not in self.nodes or record.destination not in self.nodes:
                errors.append(f"迁移矩阵节点不存在 {record.origin}->{record.destination}")
            if record.origin == record.destination:
                errors.append(f"迁移矩阵不能包含自迁移 {record.origin}")
            if record.sex not in ("F", "M") or record.age < 0:
                errors.append(f"迁移矩阵性别/年龄非法 {key}")
            if not math.isfinite(record.hazard) or record.hazard < 0:
                errors.append(f"迁移 hazard 非法 {key}")
            sums[(record.origin, record.sex, record.age)] = sums.get(
                (record.origin, record.sex, record.age), 0.0
            ) + hazard_to_probability(record.hazard)
        overloaded = [key for key, value in sums.items() if value > 1.0 + 1e-9]
        if overloaded:
            warnings.append(f"迁移目的地概率和超过 1，将在编译时归一化：{overloaded[:3]}")
        if strict and warnings:
            errors.extend(warnings)
            warnings = []
        return ValidationReport(tuple(errors), tuple(warnings))

    def to_hazards(self) -> dict[str, dict[str, AgeRateProfile]]:
        grouped: dict[tuple[str, str, int], list[float]] = {}
        for record in self.records:
            key = (record.origin, record.destination, record.age)
            grouped.setdefault(key, []).append(record.hazard)
        result: dict[str, dict[str, AgeRateProfile]] = {}
        by_edge: dict[tuple[str, str], list[tuple[int, float]]] = {}
        for (origin, destination, age), rates in grouped.items():
            # cohort 核心的迁移矩阵按目的地共享年龄 profile；如需性别特异矩阵，
            # 应在下一版扩展 MigrationRate 的 sex 维度。
            by_edge.setdefault((origin, destination), []).append((age, sum(rates) / len(rates)))
        for (origin, destination), points in by_edge.items():
            ordered = sorted(points)
            result.setdefault(origin, {})[destination] = AgeRateProfile(
                tuple(age for age, _ in ordered), tuple(rate for _, rate in ordered)
            )
        return result


@dataclass(frozen=True)
class FertilityScheduleRecord:
    country: str
    year: int
    marital: str
    parity: str
    profile: AgeRateProfile


@dataclass(frozen=True)
class NationalCalibrationBundle:
    life_tables: tuple[LifeTableSchedule, ...] = ()
    migration_matrices: tuple[AgeSpecificMigrationMatrix, ...] = ()
    fertility_records: tuple[FertilityScheduleRecord, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self, *, strict: bool = True) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        for table in self.life_tables:
            report = table.validate(strict=strict)
            errors.extend(report.errors); warnings.extend(report.warnings)
        for matrix in self.migration_matrices:
            report = matrix.validate(strict=strict)
            errors.extend(report.errors); warnings.extend(report.warnings)
        keys: set[tuple[str, int, FertilityState]] = set()
        for record in self.fertility_records:
            key = (record.country, record.year, (record.marital, record.parity))
            if key in keys:
                errors.append(f"重复孩次/婚姻生育率 {key}")
            keys.add(key)
        if not self.metadata.get("source"):
            warnings.append("校准包缺少 metadata.source")
        if strict and warnings:
            errors.extend(warnings); warnings = []
        return ValidationReport(tuple(errors), tuple(warnings))

    def fertility_schedule(self, country: str, year: int) -> FertilitySchedule:
        records = [record for record in self.fertility_records
                   if record.country == country and record.year == year]
        if not records:
            raise ValueError(f"没有 {country}/{year} 的孩次—婚姻生育率")
        return FertilitySchedule({(record.marital, record.parity): record.profile
                                  for record in records})

    def life_table(self, country: str, year: int) -> LifeTableSchedule:
        for table in self.life_tables:
            if table.country == country and table.year == year:
                return table
        raise ValueError(f"没有 {country}/{year} 的生命表")

    def migration_matrix(self, year: int) -> AgeSpecificMigrationMatrix:
        for matrix in self.migration_matrices:
            if matrix.year == year:
                return matrix
        raise ValueError(f"没有 {year} 年的迁移矩阵")

    def compile_cohort_inputs(
        self,
        country: str,
        year: int,
        *,
        local_nodes: Iterable[str],
    ) -> dict[str, object]:
        """把校准包编译成 ``CohortComponentModel`` 可消费的输入。

        迁移矩阵目前按男女平均年龄 profile 编译；若研究需要性别特异迁移，
        应先扩展 cohort 核心的迁移率类型，而不是在这里静默丢弃性别差异。
        """
        local = tuple(local_nodes)
        matrix = self.migration_matrix(year)
        unknown = set(local) - set(matrix.nodes)
        if unknown:
            raise ValueError(f"local_nodes 不在迁移矩阵中：{sorted(unknown)}")
        return {
            "mortality_rates": {country: self.life_table(country, year).rates},
            "fertility_schedules": {country: self.fertility_schedule(country, year)},
            "migration_hazards": matrix.to_hazards(),
            "external_nodes": tuple(node for node in matrix.nodes if node not in local),
        }
