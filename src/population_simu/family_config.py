from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass(frozen=True)
class PolicyEra:
    start_year: int
    end_year: int | None
    name: str
    max_children: int | None = None
    enforcement: float = 0.0
    fertility_multiplier: float = 1.0
    child_support: float = 0.0

    def active(self, year: int) -> bool:
        return self.start_year <= year and (self.end_year is None or year <= self.end_year)


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    urban: bool
    initial_share: float = 0.5
    wage_multiplier: float = 1.0
    housing_cost: float = 1.0
    education_quality: float = 0.5
    job_opportunity: float = 0.5


@dataclass(frozen=True)
class Country:
    id: str
    name: str
    initial_clans: int
    initial_development: float
    annual_development_gain: float
    initial_urbanization: float
    annual_urbanization_gain: float
    education_access: float
    cost_of_children: float
    baseline_family_resources: float
    initial_children_per_family: float
    rich_fertility_rebound: float = 0.5
    institutional_openness: float = 0.5
    welfare_floor: float = 0.15
    housing_pressure: float = 0.5
    occupational_inheritance: float = 0.45
    public_education_quality: float = 0.55
    education_inequality: float = 0.35
    medical_training_years: int = 7
    medical_license_pass_rate: float = 0.70
    civil_service_selectivity: float = 0.18
    state_sector_share: float = 0.22
    base_unemployment_rate: float = 0.055
    worker_compensation: float = 0.45
    property_inheritance_tax: float = 0.05
    housing_supply_elasticity: float = 0.45
    political_term_years: int = 5
    faction_count: int = 4
    anti_nepotism_strength: float = 0.35
    assortative_mating_strength: float = 0.65
    elite_marriage_closure: float = 0.45
    soe_reform_year: int | None = None
    soe_reform_shock: float = 0.0
    cycle_years: float = 9.0
    cycle_amplitude: float = 0.10
    shock_probability: float = 0.025
    shock_severity: float = 0.18
    base_divorce_rate: float = 0.012
    remarriage_rate: float = 0.16
    female_labor_access: float = 0.76
    gender_pay_gap: float = 0.12
    maternal_career_penalty: float = 0.10
    son_preference: float = 0.0
    public_education_reform: float = 0.0
    housing_reform_strength: float = 0.0
    high_welfare_strength: float = 0.0
    healthcare_access: float = 0.65
    medical_cost_burden: float = 0.35
    chronic_disease_base_rate: float = 0.006
    public_long_term_care: float = 0.15
    pension_replacement_rate: float = 0.30
    retirement_age: int = 65
    childcare_capacity: float = 0.35
    childcare_subsidy: float = 0.20
    grandparent_care_availability: float = 0.45
    dynamic_investment_strength: float = 0.35
    investment_need_weight: float = 0.20
    regions: tuple[Region, ...] = field(default_factory=tuple)
    policies: tuple[PolicyEra, ...] = field(default_factory=tuple)

    def development_at(self, year: int, start_year: int) -> float:
        return min(1.0, self.initial_development + self.annual_development_gain * (year - start_year))

    def urbanization_at(self, year: int, start_year: int) -> float:
        return min(0.98, self.initial_urbanization + self.annual_urbanization_gain * (year - start_year))

    def policy_at(self, year: int) -> PolicyEra:
        active = [policy for policy in self.policies if policy.active(year)]
        if not active:
            return PolicyEra(start_year=-10_000, end_year=None, name="无专项生育限制")
        return max(active, key=lambda policy: policy.start_year)


@dataclass(frozen=True)
class FamilySimulation:
    start_year: int = 1970
    end_year: int = 2100
    random_seed: int = 42
    adult_pairing_rate: float = 0.30
    international_migration_rate: float = 0.0015
    resource_investment_share: float = 0.32
    inheritance_share: float = 0.25
    surname_rule: str = "paternal"


@dataclass(frozen=True)
class FamilyScenario:
    name: str
    simulation: FamilySimulation
    countries: tuple[Country, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "FamilyScenario":
        countries = []
        for item in data["countries"]:
            country_data = dict(item)
            country_data["policies"] = tuple(PolicyEra(**policy) for policy in item.get("policies", []))
            country_data["regions"] = tuple(Region(**region) for region in item.get("regions", []))
            countries.append(Country(**country_data))
        return cls(
            name=data["name"],
            simulation=FamilySimulation(**data.get("simulation", {})),
            countries=tuple(countries),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "FamilyScenario":
        with Path(path).open(encoding="utf-8") as file:
            return cls.from_dict(json.load(file))

    def validate(self) -> None:
        if self.simulation.end_year <= self.simulation.start_year:
            raise ValueError("end_year 必须晚于 start_year")
        if self.simulation.random_seed < 0:
            raise ValueError("random_seed 必须为非负整数")
        for name in ("adult_pairing_rate", "international_migration_rate", "resource_investment_share", "inheritance_share"):
            value = getattr(self.simulation, name)
            if not 0 <= value <= 1:
                raise ValueError(f"simulation.{name} 必须在 0—1 之间")
        if self.simulation.surname_rule not in {"paternal", "random", "maternal"}:
            raise ValueError("surname_rule 必须是 paternal、maternal 或 random")
        if not self.countries:
            raise ValueError("至少需要一个国家")
        ids = [country.id for country in self.countries]
        if len(ids) != len(set(ids)):
            raise ValueError("国家 id 必须唯一")
        for country in self.countries:
            if country.initial_clans < 1:
                raise ValueError(f"{country.name} 至少需要一个初始姓氏家族")
            for name in (
                "initial_development",
                "initial_urbanization",
                "education_access",
                "rich_fertility_rebound",
                "institutional_openness",
                "welfare_floor",
                "housing_pressure",
                "occupational_inheritance",
                "public_education_quality",
                "education_inequality",
                "medical_license_pass_rate",
                "civil_service_selectivity",
                "state_sector_share",
                "base_unemployment_rate",
                "worker_compensation",
                "property_inheritance_tax",
                "housing_supply_elasticity",
                "anti_nepotism_strength",
                "assortative_mating_strength",
                "elite_marriage_closure",
                "shock_probability",
                "base_divorce_rate",
                "remarriage_rate",
                "female_labor_access",
                "gender_pay_gap",
                "maternal_career_penalty",
                "son_preference",
                "public_education_reform",
                "housing_reform_strength",
                "high_welfare_strength",
            ):
                value = getattr(country, name)
                if not 0 <= value <= 1:
                    raise ValueError(f"{country.name} 的 {name} 必须在 0—1 之间")
            for name in ("baseline_family_resources", "cost_of_children", "initial_children_per_family"):
                if getattr(country, name) < 0:
                    raise ValueError(f"{country.name} 的 {name} 不能为负数")
            if country.annual_development_gain < 0 or country.annual_urbanization_gain < 0:
                raise ValueError(f"{country.name} 的年度发展/城市化增速不能为负数")
            if country.regions:
                region_ids = [region.id for region in country.regions]
                if len(region_ids) != len(set(region_ids)):
                    raise ValueError(f"{country.name} 的地区 id 必须唯一")
                if sum(region.initial_share for region in country.regions) <= 0:
                    raise ValueError(f"{country.name} 的地区 initial_share 总和必须大于 0")
                for region in country.regions:
                    if region.initial_share < 0 or region.wage_multiplier < 0 or region.housing_cost <= 0:
                        raise ValueError(f"{country.name}/{region.name} 的地区基础参数无效")
                    for name in ("education_quality", "job_opportunity"):
                        if not 0 <= getattr(region, name) <= 1:
                            raise ValueError(f"{country.name}/{region.name} 的 {name} 必须在 0—1 之间")
            policies = sorted(country.policies, key=lambda policy: policy.start_year)
            for index, policy in enumerate(policies):
                if policy.end_year is not None and policy.end_year < policy.start_year:
                    raise ValueError(f"{country.name} 的政策 {policy.name} 年份范围无效")
                if not 0 <= policy.enforcement <= 1 or policy.fertility_multiplier < 0 or policy.child_support < 0:
                    raise ValueError(f"{country.name} 的政策 {policy.name} 参数无效")
                if index and policies[index - 1].end_year is not None and policy.start_year <= policies[index - 1].end_year:
                    raise ValueError(f"{country.name} 的政策时期不能重叠")
            for name in (
                "healthcare_access",
                "medical_cost_burden",
                "chronic_disease_base_rate",
                "public_long_term_care",
                "pension_replacement_rate",
                "childcare_capacity",
                "childcare_subsidy",
                "grandparent_care_availability",
                "dynamic_investment_strength",
                "investment_need_weight",
            ):
                value = getattr(country, name)
                if not 0 <= value <= 1:
                    raise ValueError(f"{country.name} 的 {name} 必须在 0—1 之间")
            if not 50 <= country.retirement_age <= 80:
                raise ValueError(f"{country.name} 的 retirement_age 必须在 50—80 之间")
