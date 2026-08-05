from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass(frozen=True)
class RegionConfig:
    id: str
    name: str
    initial_share: float
    wage_index: float = 1.0
    housing_cost: float = 1.0
    education_access: float = 0.5
    opportunity: float = 0.5


@dataclass(frozen=True)
class PolicyConfig:
    fertility_multiplier: float = 1.0
    childcare_support: float = 0.0
    migration_openness: float = 0.5
    education_investment: float = 0.5
    upward_mobility: float = 0.5


@dataclass(frozen=True)
class SimulationConfig:
    start_year: int = 2025
    years: int = 50
    initial_people: int = 2_000
    random_seed: int = 42
    baseline_tfr: float = 1.8
    pair_formation_rate: float = 0.22
    household_migration_rate: float = 0.025


@dataclass(frozen=True)
class Scenario:
    name: str
    simulation: SimulationConfig
    policy: PolicyConfig
    regions: tuple[RegionConfig, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        return cls(
            name=data["name"],
            simulation=SimulationConfig(**data.get("simulation", {})),
            policy=PolicyConfig(**data.get("policy", {})),
            regions=tuple(RegionConfig(**item) for item in data["regions"]),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "Scenario":
        with Path(path).open(encoding="utf-8") as file:
            return cls.from_dict(json.load(file))

    def validate(self) -> None:
        if not self.regions:
            raise ValueError("情景至少需要一个地区")
        if self.simulation.initial_people < 2:
            raise ValueError("initial_people 至少为 2")
        if self.simulation.years < 1:
            raise ValueError("years 至少为 1")
        if self.simulation.baseline_tfr < 0:
            raise ValueError("baseline_tfr 不能为负")
        if sum(region.initial_share for region in self.regions) <= 0:
            raise ValueError("地区 initial_share 总和必须大于 0")

