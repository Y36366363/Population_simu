"""年龄—性别 cohort-component 人口核心。

这是一个透明的宏观人口骨架：先按年龄和性别推进存活人口，再生成出生，
最后按地区迁移矩阵重分配。所有数量使用 ``float`` 表示期望人口，便于校准；
家庭微观模型可以把聚合快照与本模块逐年对账，而不需要共享随机状态。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from .hazards import AgeRateProfile, hazard_to_probability
from .fertility import FertilitySchedule, FertilityState


Sex = str
PopulationInput = Mapping[str, Mapping[Sex, Iterable[float]]]
MigrationRate = float | AgeRateProfile | Mapping[str, AgeRateProfile]


@dataclass(frozen=True)
class CohortStep:
    year: int
    births: float
    deaths: float
    internal_migrations: float
    population: float
    population_by_region: dict[str, float]
    external_population_by_node: dict[str, float]
    age_sex: dict[str, dict[str, tuple[float, ...]]]

    def as_dict(self) -> dict[str, object]:
        return {
            "year": self.year,
            "births": self.births,
            "deaths": self.deaths,
            "internal_migrations": self.internal_migrations,
            "population": self.population,
            "population_by_region": dict(self.population_by_region),
            "external_population_by_node": dict(self.external_population_by_node),
            "age_sex": {
                region: {sex: list(values) for sex, values in sexes.items()}
                for region, sexes in self.age_sex.items()
            },
        }


class CohortComponentModel:
    """多地区年龄—性别人口推进器。

    ``fertility_rates`` 的数值是女性每年生育率；``mortality_rates`` 和
    ``migration_hazards`` 是年度 hazard。迁移矩阵只表示模型内地区之间的
    流动，若要表示国际迁移，应增加外部地区节点，而不是把净迁移悄悄塞进人口。
    """

    sexes: tuple[str, str] = ("F", "M")

    def __init__(
        self,
        initial_population: PopulationInput,
        *,
        start_year: int = 2025,
        max_age: int = 100,
        fertility_rates: Mapping[str, AgeRateProfile] | None = None,
        fertility_schedules: Mapping[str, FertilitySchedule] | None = None,
        fertility_state_weights: Mapping[str, Mapping[FertilityState, float]] | None = None,
        mortality_rates: Mapping[str, Mapping[Sex, AgeRateProfile]] | None = None,
        migration_hazards: Mapping[str, Mapping[str, float]] | None = None,
        external_nodes: Iterable[str] = (),
        sex_ratio_at_birth: float = 0.512,
    ) -> None:
        if max_age < 1:
            raise ValueError("max_age 必须至少为 1")
        if not 0 < sex_ratio_at_birth < 1:
            raise ValueError("sex_ratio_at_birth 必须在 0 和 1 之间")
        self.start_year = int(start_year)
        self.year = int(start_year)
        self.max_age = int(max_age)
        self.sex_ratio_at_birth = float(sex_ratio_at_birth)
        self.regions = tuple(initial_population)
        if not self.regions:
            raise ValueError("至少需要一个地区")
        self.external_nodes = tuple(external_nodes)
        if set(self.regions) & set(self.external_nodes) or len(set(self.external_nodes)) != len(self.external_nodes):
            raise ValueError("external_nodes 必须是不同于地区的唯一节点")
        self.nodes = self.regions + self.external_nodes
        self.fertility_rates = dict(fertility_rates or {})
        self.fertility_schedules = dict(fertility_schedules or {})
        self.fertility_state_weights = {
            region: dict(weights)
            for region, weights in (fertility_state_weights or {}).items()
        }
        self.mortality_rates = {
            region: dict(profiles) for region, profiles in (mortality_rates or {}).items()
        }
        self.migration_hazards: dict[str, dict[str, MigrationRate]] = {
            origin: dict(destinations)
            for origin, destinations in (migration_hazards or {}).items()
        }
        self._validate_rates()
        self.population = self._normalise_population(initial_population)

    def _validate_rates(self) -> None:
        for profile in self.fertility_rates.values():
            self._validate_profile(profile)
        for schedule in self.fertility_schedules.values():
            for profile in schedule.profiles.values():
                self._validate_profile(profile)
        for profiles in self.mortality_rates.values():
            for sex in self.sexes:
                if sex in profiles:
                    self._validate_profile(profiles[sex])
        for origin, destinations in self.migration_hazards.items():
            if origin not in self.nodes:
                raise ValueError(f"迁移矩阵包含未知起点 {origin}")
            if any(destination not in self.nodes for destination in destinations):
                raise ValueError("迁移矩阵包含未知目的地")
            for rate in destinations.values():
                if isinstance(rate, AgeRateProfile):
                    self._validate_profile(rate)
                elif isinstance(rate, Mapping):
                    for profile in rate.values():
                        if not isinstance(profile, AgeRateProfile):
                            raise ValueError("性别迁移率必须是 AgeRateProfile")
                        self._validate_profile(profile)
                elif not math.isfinite(float(rate)) or rate < 0:
                    raise ValueError("迁移 hazard 必须为有限非负数")

    @staticmethod
    def _validate_profile(profile: AgeRateProfile) -> None:
        if any(not math.isfinite(float(rate)) or rate < 0 for rate in profile.rates):
            raise ValueError("年龄率必须为有限非负数")

    def _normalise_population(self, source: PopulationInput) -> dict[str, dict[str, list[float]]]:
        result: dict[str, dict[str, list[float]]] = {}
        expected = self.max_age + 1
        for region in self.nodes:
            result[region] = {}
            for sex in self.sexes:
                values = [float(value) for value in source.get(region, {}).get(sex, ())]
                if len(values) > expected:
                    raise ValueError(f"{region}/{sex} 年龄组超过 max_age")
                if any(not math.isfinite(value) or value < 0 for value in values):
                    raise ValueError("初始人口必须为有限非负数")
                result[region][sex] = values + [0.0] * (expected - len(values))
        return result

    def _profile(self, profiles: Mapping[str, AgeRateProfile], region: str, default: float = 0.0) -> AgeRateProfile | None:
        return profiles.get(region) or profiles.get("*")

    def _fertility_rate(self, region: str, age: int) -> float:
        schedule = self.fertility_schedules.get(region) or self.fertility_schedules.get("*")
        if schedule:
            weights = self.fertility_state_weights.get(region, self.fertility_state_weights.get("*", {}))
            return schedule.weighted_rate(age, weights)
        profile = self._profile(self.fertility_rates, region)
        return profile.rate(age) if profile else 0.0

    def _mortality_profile(self, region: str, sex: str) -> AgeRateProfile | None:
        profiles = self.mortality_rates.get(region, self.mortality_rates.get("*", {}))
        return profiles.get(sex) or profiles.get("*")

    def snapshot(self) -> dict[str, dict[str, tuple[float, ...]]]:
        return {
            region: {sex: tuple(values) for sex, values in sexes.items()}
            for region, sexes in self.population.items()
        }

    def total_population(self) -> float:
        return sum(sum(values) for sexes in self.population.values() for values in sexes.values())

    def _assert_nonnegative(self) -> None:
        if any(value < -1e-8 for sexes in self.population.values() for values in sexes.values() for value in values):
            raise AssertionError("年龄—性别人口出现负数")

    def step(self) -> CohortStep:
        previous_total = self.total_population()
        births = 0.0
        births_by_region: dict[str, float] = {region: 0.0 for region in self.regions}
        deaths = 0.0
        next_population: dict[str, dict[str, list[float]]] = {
            region: {sex: [0.0] * (self.max_age + 1) for sex in self.sexes}
            for region in self.nodes
        }
        for region in self.nodes:
            fertility = (self.fertility_schedules.get(region) or self.fertility_schedules.get("*")
                         or self._profile(self.fertility_rates, region)) if region in self.regions else None
            for sex in self.sexes:
                mortality = self._mortality_profile(region, sex)
                for age, count in enumerate(self.population[region][sex]):
                    death_probability = hazard_to_probability(mortality.rate(age) if mortality else 0.0)
                    survived = count * (1.0 - death_probability)
                    deaths += count - survived
                    next_age = min(self.max_age, age + 1)
                    next_population[region][sex][next_age] += survived
            if fertility:
                for age, women in enumerate(self.population[region]["F"]):
                    births_by_region[region] += women * max(0.0, self._fertility_rate(region, age))
        births = sum(births_by_region.values())
        for region in self.regions:
            region_births = births_by_region[region]
            next_population[region]["M"][0] += region_births * self.sex_ratio_at_birth
            next_population[region]["F"][0] += region_births * (1.0 - self.sex_ratio_at_birth)
        self.population = next_population
        internal_migrations = self._apply_migration()
        self._assert_nonnegative()
        self.year += 1
        current_total = self.total_population()
        if abs(current_total - (previous_total + births - deaths)) > 1e-6 * max(1.0, previous_total):
            raise AssertionError("人口守恒失败：出生、死亡和迁移未闭合")
        by_region = {region: sum(sum(values) for values in self.population[region].values())
                     for region in self.regions}
        external = {node: sum(sum(values) for values in self.population[node].values())
                    for node in self.external_nodes}
        return CohortStep(self.year, births, deaths, internal_migrations, current_total,
                          by_region, external, self.snapshot())

    def _apply_migration(self) -> float:
        moves: list[tuple[str, str, str, int, float]] = []
        for origin, destinations in self.migration_hazards.items():
            for sex in self.sexes:
                for age, count in enumerate(self.population[origin][sex]):
                    def rate_at(rate: MigrationRate) -> float:
                        if isinstance(rate, Mapping):
                            profile = rate.get(sex) or rate.get("*")
                            return profile.rate(age) if profile else 0.0
                        return rate if isinstance(rate, (int, float)) else rate.rate(age)

                    age_probabilities = {
                        destination: hazard_to_probability(rate_at(rate))
                        for destination, rate in destinations.items()
                    }
                    total_age_probability = sum(age_probabilities.values())
                    if total_age_probability > 1.0:
                        age_probabilities = {destination: probability / total_age_probability
                                             for destination, probability in age_probabilities.items()}
                    for destination, probability in age_probabilities.items():
                        moves.append((origin, destination, sex, age, count * probability))
        total = 0.0
        for origin, destination, sex, age, amount in moves:
            amount = min(amount, self.population[origin][sex][age])
            self.population[origin][sex][age] -= amount
            self.population[destination][sex][age] += amount
            total += amount
        return total
