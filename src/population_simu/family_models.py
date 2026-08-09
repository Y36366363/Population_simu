from __future__ import annotations

from dataclasses import dataclass, field

from .capitals import CapitalBundle


@dataclass
class Clan:
    id: int
    surname: str
    origin_country_id: str
    founder_household_id: int
    founder_resources: float
    branch_ids: list[int] = field(default_factory=list)
    total_births: int = 0
    peak_living_members: int = 0


@dataclass
class FamilyPerson:
    id: int
    clan_id: int
    surname: str
    country_id: str
    household_id: int
    age: int
    sex: str
    innate_potential: float
    region_id: str = ""
    human_capital: float = 0.0
    economic_status: float = 0.0
    cumulative_investment: float = 0.0
    annual_investment: float = 0.0
    observed_achievement: float = 0.0
    occupation: str = "dependent"
    social_capital: float = 0.0
    political_capital: float = 0.0
    cultural_capital: float = 0.0
    housing_security: float = 0.0
    health_capital: float = 0.8
    debt_burden: float = 0.0
    adult_viability: float = 0.0
    education_years: float = 0.0
    training_years: int = 0
    licensed: bool = False
    career_tenure: int = 0
    unemployment_years: int = 0
    injury_level: float = 0.0
    political_rank: int = 0
    faction_id: int | None = None
    patron_power: float = 0.0
    parent_occupation: str | None = None
    previous_occupation: str | None = None
    spouse_id: int | None = None
    marriage_count: int = 0
    divorce_count: int = 0
    career_interruption: float = 0.0
    chronic_condition: bool = False
    disability_level: float = 0.0
    partnered: bool = False
    alive: bool = True
    mother_id: int | None = None
    father_id: int | None = None


@dataclass
class FamilyBranch:
    id: int
    clan_id: int
    surname: str
    country_id: str
    generation: int
    resources: float
    permanent_income: float
    capitals: CapitalBundle
    region_id: str = ""
    member_ids: list[int] = field(default_factory=list)
    children_ever_born: int = 0
    parent_household_ids: tuple[int, ...] = field(default_factory=tuple)
    migration_count: int = 0
    property_value: float = 0.0
    property_count: float = 0.0
    school_quality: float = 0.5
    internal_migration_count: int = 0
    divorce_count: int = 0
    annual_medical_spending: float = 0.0
    care_burden: float = 0.0
    catastrophic_medical_expense: bool = False
    formal_childcare_coverage: float = 0.0
    grandparent_care_coverage: float = 0.0
    childcare_gap: float = 0.0
    investment_concentration: float = 0.0


@dataclass(frozen=True)
class FamilyYearStats:
    year: int
    country_id: str
    policy: str
    population: int
    households: int
    living_clans: int
    births: int
    deaths: int
    migrants: int
    mean_children_per_completed_family: float
    mean_child_investment: float
    upward_mobility_rate: float
    high_status_share: float
    median_household_resources: float
    bottom_clan_extinction_share: float
    below_deadline_share: float
    occupational_persistence_rate: float
    precarious_inheritance_rate: float
    fertility_realization_gap: float
    political_occupation_share: float
    medical_occupation_share: float
    precarious_occupation_share: float
    unemployment_rate: float
    injury_rate: float
    homeownership_rate: float
    licensed_physician_share: float
    state_sector_share: float
    political_dynasty_share: float
    faction_concentration: float
    elite_marriage_share: float
    economic_cycle_index: float
    unemployment_pressure: float
    divorces: int
    remarriages: int
    internal_migrants: int
    rural_population_share: float
    female_high_status_share: float
    gender_status_gap: float
    chronic_illness_share: float
    elder_dependency_ratio: float
    mean_household_care_burden: float
    catastrophic_medical_expense_share: float
    formal_childcare_coverage: float
    grandparent_care_coverage: float
    mean_childcare_gap: float
    sibling_investment_concentration: float
    tax_revenue: float
    public_spending: float
    fiscal_balance: float
    capacity_pressure: float
    technology_index: float
    automation_share: float
    labor_shortage_index: float

    def flat_dict(self) -> dict[str, int | float | str]:
        return {
            "year": self.year,
            "country": self.country_id,
            "policy": self.policy,
            "population": self.population,
            "households": self.households,
            "living_clans": self.living_clans,
            "births": self.births,
            "deaths": self.deaths,
            "migrants": self.migrants,
            "mean_children_per_completed_family": round(self.mean_children_per_completed_family, 4),
            "mean_child_investment": round(self.mean_child_investment, 4),
            "upward_mobility_rate": round(self.upward_mobility_rate, 5),
            "high_status_share": round(self.high_status_share, 5),
            "median_household_resources": round(self.median_household_resources, 4),
            "bottom_clan_extinction_share": round(self.bottom_clan_extinction_share, 5),
            "below_deadline_share": round(self.below_deadline_share, 5),
            "occupational_persistence_rate": round(self.occupational_persistence_rate, 5),
            "precarious_inheritance_rate": round(self.precarious_inheritance_rate, 5),
            "fertility_realization_gap": round(self.fertility_realization_gap, 5),
            "political_occupation_share": round(self.political_occupation_share, 5),
            "medical_occupation_share": round(self.medical_occupation_share, 5),
            "precarious_occupation_share": round(self.precarious_occupation_share, 5),
            "unemployment_rate": round(self.unemployment_rate, 5),
            "injury_rate": round(self.injury_rate, 5),
            "homeownership_rate": round(self.homeownership_rate, 5),
            "licensed_physician_share": round(self.licensed_physician_share, 5),
            "state_sector_share": round(self.state_sector_share, 5),
            "political_dynasty_share": round(self.political_dynasty_share, 5),
            "faction_concentration": round(self.faction_concentration, 5),
            "elite_marriage_share": round(self.elite_marriage_share, 5),
            "economic_cycle_index": round(self.economic_cycle_index, 5),
            "unemployment_pressure": round(self.unemployment_pressure, 5),
            "divorces": self.divorces,
            "remarriages": self.remarriages,
            "internal_migrants": self.internal_migrants,
            "rural_population_share": round(self.rural_population_share, 5),
            "female_high_status_share": round(self.female_high_status_share, 5),
            "gender_status_gap": round(self.gender_status_gap, 5),
            "chronic_illness_share": round(self.chronic_illness_share, 5),
            "elder_dependency_ratio": round(self.elder_dependency_ratio, 5),
            "mean_household_care_burden": round(self.mean_household_care_burden, 5),
            "catastrophic_medical_expense_share": round(
                self.catastrophic_medical_expense_share, 5
            ),
            "formal_childcare_coverage": round(self.formal_childcare_coverage, 5),
            "grandparent_care_coverage": round(self.grandparent_care_coverage, 5),
            "mean_childcare_gap": round(self.mean_childcare_gap, 5),
            "sibling_investment_concentration": round(
                self.sibling_investment_concentration, 5
            ),
            "tax_revenue": round(self.tax_revenue, 4),
            "public_spending": round(self.public_spending, 4),
            "fiscal_balance": round(self.fiscal_balance, 4),
            "capacity_pressure": round(self.capacity_pressure, 5),
            "technology_index": round(self.technology_index, 5),
            "automation_share": round(self.automation_share, 5),
            "labor_shortage_index": round(self.labor_shortage_index, 5),
        }
