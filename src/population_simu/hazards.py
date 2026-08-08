"""可替换的人口事件 hazard/logit 基础函数。"""

from __future__ import annotations

from dataclasses import dataclass
import math


def clamp_probability(value: float) -> float:
    return min(1.0, max(0.0, value))


def logit_probability(linear_predictor: float) -> float:
    if linear_predictor >= 0:
        exponent = math.exp(-linear_predictor)
        return 1.0 / (1.0 + exponent)
    exponent = math.exp(linear_predictor)
    return exponent / (1.0 + exponent)


def softmax_weights(scores: list[float], temperature: float = 1.0) -> list[float]:
    """将目的地效用转换为可抽样权重，避免永远选择单一最高分地区。"""
    if not scores:
        return []
    scale = max(1e-6, temperature)
    peak = max(scores)
    weights = [math.exp((score - peak) / scale) for score in scores]
    return [weight if math.isfinite(weight) else 0.0 for weight in weights]


@dataclass(frozen=True)
class AgeRateProfile:
    """按年龄线性插值的年度率表；超出端点使用端点值。"""

    ages: tuple[int, ...]
    rates: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.ages) != len(self.rates) or not self.ages:
            raise ValueError("年龄率表必须有相同长度且至少包含一个年龄点")
        if tuple(sorted(self.ages)) != self.ages or len(set(self.ages)) != len(self.ages):
            raise ValueError("年龄率表的年龄必须严格递增")
        if any(rate < 0 for rate in self.rates):
            raise ValueError("年龄率不能为负数")

    def rate(self, age: int) -> float:
        if age <= self.ages[0]:
            return self.rates[0]
        if age >= self.ages[-1]:
            return self.rates[-1]
        for index in range(len(self.ages) - 1):
            age0, age1 = self.ages[index], self.ages[index + 1]
            if age0 <= age <= age1:
                fraction = (age - age0) / (age1 - age0)
                return self.rates[index] + fraction * (self.rates[index + 1] - self.rates[index])
        return self.rates[-1]

    @classmethod
    def from_pairs(cls, pairs: tuple[tuple[int, float], ...]) -> "AgeRateProfile | None":
        return cls(tuple(age for age, _ in pairs), tuple(rate for _, rate in pairs)) if pairs else None
