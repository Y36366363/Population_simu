from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class CapitalBundle:
    """家庭可传递资源；各维度归一化为 0—1，金融资产仍单独保留原始量。"""

    financial: float
    human: float
    social: float
    political: float
    cultural: float
    housing: float
    health: float
    care_time: float
    debt: float = 0.0

    def normalized_financial(self, reference: float) -> float:
        return min(1.0, math.log1p(max(0.0, self.financial)) / math.log1p(max(2.0, reference * 6)))

    def viability(self, reference: float) -> float:
        """成家/繁衍承载力，不等同于人的价值。"""
        return max(
            0.0,
            min(
                1.0,
                0.24 * self.normalized_financial(reference)
                + 0.17 * self.human
                + 0.14 * self.social
                + 0.08 * self.political
                + 0.08 * self.cultural
                + 0.13 * self.housing
                + 0.10 * self.health
                + 0.06 * self.care_time
                - 0.16 * self.debt,
            ),
        )

    def copy(self) -> "CapitalBundle":
        return CapitalBundle(**self.__dict__)


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)

