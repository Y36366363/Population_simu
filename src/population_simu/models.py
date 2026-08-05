from __future__ import annotations

from dataclasses import dataclass, field


EDUCATION_LEVELS = ("none", "primary", "secondary", "tertiary")


@dataclass
class Person:
    id: int
    age: int
    sex: str
    household_id: int
    region_id: str
    education: int = 0
    income_tier: int = 1
    alive: bool = True
    partnered: bool = False
    mother_id: int | None = None
    father_id: int | None = None


@dataclass
class Household:
    id: int
    region_id: str
    member_ids: list[int] = field(default_factory=list)
    children_ever_born: int = 0
    moves: int = 0


@dataclass(frozen=True)
class YearStats:
    year: int
    population: int
    households: int
    births: int
    deaths: int
    migrations: int
    mean_age: float
    child_share: float
    working_age_share: float
    senior_share: float
    tertiary_share: float
    top_income_share: float
    population_by_region: dict[str, int]

    def flat_dict(self) -> dict[str, int | float]:
        row: dict[str, int | float] = {
            "year": self.year,
            "population": self.population,
            "households": self.households,
            "births": self.births,
            "deaths": self.deaths,
            "migrations": self.migrations,
            "mean_age": round(self.mean_age, 3),
            "child_share": round(self.child_share, 5),
            "working_age_share": round(self.working_age_share, 5),
            "senior_share": round(self.senior_share, 5),
            "tertiary_share": round(self.tertiary_share, 5),
            "top_income_share": round(self.top_income_share, 5),
        }
        row.update({f"region_{key}": value for key, value in self.population_by_region.items()})
        return row

