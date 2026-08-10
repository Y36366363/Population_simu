"""地区迁移网络与家庭社会网络的独立接口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .family_config import Country, Region


@dataclass(frozen=True)
class RegionMigrationNetwork:
    """只负责地区—地区可达性，不读取家庭成员或社会规范。"""

    def destinations(self, country: Country, origin: Region, regions: Iterable[Region]) -> tuple[Region, ...]:
        matrix = country.migration_matrix.get(origin.id, {})
        return tuple(
            region for region in regions
            if region.id != origin.id and (not matrix or matrix.get(region.id, 0.0) > 0)
        )

    def edge_weight(self, country: Country, origin: Region, destination: Region) -> float:
        return country.migration_matrix.get(origin.id, {}).get(destination.id, 1.0)


@dataclass(frozen=True)
class FamilySocialNetwork:
    """只负责家庭间规范来源，不决定地区迁移路径。"""

    def same_region(self, household, other) -> bool:
        return household.country_id == other.country_id and household.region_id == other.region_id

    def same_kin(self, household, other) -> bool:
        return household.clan_id == other.clan_id and household.id != other.id

    def shares_occupation(self, occupations: set[str], other_people: Iterable[object]) -> bool:
        return bool(occupations.intersection(
            getattr(person, "occupation", "") for person in other_people
        ))

