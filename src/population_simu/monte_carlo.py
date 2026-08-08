"""共同随机数 Monte Carlo、敏感性和区间汇总工具。"""

from __future__ import annotations

from dataclasses import dataclass
import random
import statistics
from typing import Callable, Iterable


def common_random_seeds(base_seed: int, replicates: int) -> list[int]:
    if replicates < 1:
        raise ValueError("replicates 必须至少为 1")
    rng = random.Random(base_seed)
    return [rng.randrange(1, 2**31 - 1) for _ in range(replicates)]


def quantile(values: Iterable[float], probability: float) -> float:
    data = sorted(float(value) for value in values)
    if not data:
        raise ValueError("至少需要一个观测值")
    if not 0 <= probability <= 1:
        raise ValueError("probability 必须在 0—1 之间")
    position = (len(data) - 1) * probability
    lower = int(position)
    upper = min(len(data) - 1, lower + 1)
    return data[lower] + (data[upper] - data[lower]) * (position - lower)


@dataclass(frozen=True)
class IntervalSummary:
    n: int
    mean: float
    median: float
    ci_low: float
    ci_high: float
    sd: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "n": self.n,
            "mean": round(self.mean, 6),
            "median": round(self.median, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "sd": round(self.sd, 6),
        }


def summarize(values: Iterable[float], confidence: float = 0.95) -> IntervalSummary:
    data = [float(value) for value in values]
    if not data:
        raise ValueError("至少需要一个观测值")
    if not 0 < confidence < 1:
        raise ValueError("confidence 必须在 0—1 之间")
    tail = (1 - confidence) / 2
    return IntervalSummary(
        n=len(data),
        mean=statistics.fmean(data),
        median=quantile(data, 0.5),
        ci_low=quantile(data, tail),
        ci_high=quantile(data, 1 - tail),
        sd=statistics.stdev(data) if len(data) > 1 else 0.0,
    )


def paired_sensitivity(
    runner: Callable[[str, int], float],
    scenarios: Iterable[str],
    seeds: Iterable[int],
) -> dict[str, IntervalSummary]:
    """用同一组种子运行多个情景，减少政策比较中的随机噪声。"""
    seed_list = list(seeds)
    if not seed_list:
        raise ValueError("seeds 不能为空")
    return {
        scenario: summarize(runner(scenario, seed) for seed in seed_list)
        for scenario in scenarios
    }
