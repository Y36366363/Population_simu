"""按婚姻状态和孩次拆分的年龄别生育率。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .hazards import AgeRateProfile


FertilityState = tuple[str, str]


@dataclass(frozen=True)
class FertilitySchedule:
    """首胎、二胎、三胎及以上 × 婚姻状态的年龄别率表。

    ``weights`` 是某地区某年度处于各状态的育龄女性权重；动态家庭模型应
    每年从婚姻和孩次状态重新计算它，而不是永久使用一组静态权重。
    """

    profiles: Mapping[FertilityState, AgeRateProfile]

    def __post_init__(self) -> None:
        allowed_marital = {"married", "unmarried"}
        allowed_parity = {"first", "second", "third_plus"}
        for (marital, parity), profile in self.profiles.items():
            if marital not in allowed_marital or parity not in allowed_parity:
                raise ValueError("生育状态必须是 married/unmarried × first/second/third_plus")
            if not isinstance(profile, AgeRateProfile):
                raise TypeError("生育 profile 必须是 AgeRateProfile")

    def rate(self, age: int, marital: str, parity: str) -> float:
        profile = self.profiles.get((marital, parity))
        return profile.rate(age) if profile else 0.0

    def weighted_rate(self, age: int, weights: Mapping[FertilityState, float]) -> float:
        if any(value < 0 for value in weights.values()):
            raise ValueError("生育状态权重不能为负")
        total = sum(float(value) for value in weights.values())
        if total <= 0:
            return 0.0
        return sum(float(weight) * self.rate(age, marital, parity)
                   for (marital, parity), weight in weights.items()) / total

