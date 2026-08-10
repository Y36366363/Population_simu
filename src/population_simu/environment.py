"""可复现、可替换的环境冲击过程。

环境事件使用独立随机流，避免改变气候参数时连带改变家庭和经济周期的抽样。
"""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class EnvironmentalConfig:
    baseline_pressure: float = 0.10
    event_probability: float = 0.02
    event_severity: float = 0.20
    recovery_years: float = 5.0
    resource_constraint: float = 0.10


@dataclass(frozen=True)
class ClimateEvent:
    year: int
    region_id: str
    kind: str
    severity: float


class EnvironmentalProcess:
    """按国家—地区产生年度灾害事件，事件过程与主模拟 RNG 隔离。"""

    _KINDS = ("drought", "flood", "heat")

    def __init__(self, seed: int):
        self.seed = int(seed)

    def events_for_year(
        self,
        year: int,
        country_id: str,
        region_ids: tuple[str, ...],
        config: EnvironmentalConfig,
        *,
        hazard_history: dict[str, float] | None = None,
        population_exposure: dict[str, float] | None = None,
    ) -> dict[str, ClimateEvent]:
        events: dict[str, ClimateEvent] = {}
        for index, region_id in enumerate(region_ids):
            # 不使用 Python hash，确保跨进程、跨平台复现。
            stream_seed = (
                self.seed
                + 1009 * year
                + 10007 * index
                + 7919 * sum(ord(char) for char in f"{country_id}:{region_id}")
            )
            rng = random.Random(stream_seed)
            history_multiplier = 0.5 + 1.0 * max(
                0.0, min(1.0, (hazard_history or {}).get(region_id, 0.5))
            )
            probability = max(0.0, min(1.0, config.event_probability * history_multiplier))
            if rng.random() >= probability:
                continue
            exposure = max(
                0.0,
                min(1.0, (population_exposure or {}).get(region_id, 0.5)),
            )
            severity = max(
                0.0,
                min(1.0, config.event_severity * (0.70 + 0.60 * rng.random())),
            )
            severity = min(1.0, severity * (0.60 + 0.80 * exposure))
            events[region_id] = ClimateEvent(
                year=year,
                region_id=region_id,
                kind=self._KINDS[int(rng.random() * len(self._KINDS))],
                severity=severity,
            )
        return events

    @staticmethod
    def next_stress(
        previous: float,
        event: ClimateEvent | None,
        config: EnvironmentalConfig,
        recovery_cost: float = 0.0,
    ) -> float:
        recovery = max(1.0, config.recovery_years * (1.0 + max(0.0, recovery_cost)))
        baseline = max(0.0, min(1.0, config.baseline_pressure))
        decayed = max(0.0, previous - baseline) * (1.0 - 1.0 / recovery)
        shock = event.severity if event is not None else 0.0
        return max(0.0, min(1.0, baseline + decayed + shock))
