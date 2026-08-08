"""历史回放和模拟结果误差指标。"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

from .monte_carlo import summarize


def series_error(
    observed: Mapping[int, float],
    simulated: Mapping[int, float],
) -> dict[str, float | int]:
    years = sorted(set(observed) & set(simulated))
    if not years:
        raise ValueError("观测和模拟没有共同年份")
    errors = [float(simulated[year]) - float(observed[year]) for year in years]
    absolute = [abs(error) for error in errors]
    squared = [error**2 for error in errors]
    percentage = [abs(error) / abs(float(observed[year])) for year, error in zip(years, errors) if observed[year]]
    return {
        "n": len(years),
        "mae": sum(absolute) / len(absolute),
        "rmse": math.sqrt(sum(squared) / len(squared)),
        "bias": sum(errors) / len(errors),
        "mape": sum(percentage) / len(percentage) if percentage else 0.0,
    }


def interval_error(
    observed: Mapping[int, float],
    simulated_replicates: Iterable[Mapping[int, float]],
) -> dict[str, float | int]:
    """对每个模拟重复先计算年度 MAE，再汇总中位数和区间。"""
    errors = [series_error(observed, simulated)["mae"] for simulated in simulated_replicates]
    return summarize(errors).as_dict()
