"""历史回放、参数搜索与可复现校准工具。

校准器不假定具体的模拟器实现：调用方提供一个 ``simulate(parameters)``
函数，返回和观测 CSV 相同结构的年度行。这让家庭沙盘、聚合模型和网页
演示可以共享同一套误差与搜索逻辑。
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from itertools import product
from random import Random
from typing import Callable, Iterable, Mapping, Sequence

from .validation import series_error

ParameterSet = Mapping[str, float]
Simulator = Callable[[ParameterSet], Iterable[Mapping[str, object]]]


def load_observed_csv(path: str | Path) -> list[dict[str, float | int | str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        rows = []
        reader = csv.DictReader(file)
        if not reader.fieldnames or "year" not in reader.fieldnames:
            raise ValueError("观测 CSV 必须包含 year 列")
        for line_number, row in enumerate(reader, start=2):
            parsed: dict[str, float | int | str] = dict(row)
            try:
                parsed["year"] = int(row["year"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第 {line_number} 行 year 不是整数") from exc
            for key, value in row.items():
                if key != "year" and value not in (None, ""):
                    try:
                        number = float(value)
                        if not math.isfinite(number):
                            raise ValueError
                        parsed[key] = number
                    except ValueError:
                        pass
            rows.append(parsed)
        return rows


def temporal_split(
    rows: Iterable[Mapping[str, object]],
    *,
    validation_fraction: float = 0.2,
    group: str | None = None,
    min_train_years: int = 3,
) -> tuple[list[Mapping[str, object]], list[Mapping[str, object]]]:
    """按时间切分训练/验证期，防止用未来数据挑参数。

    多实体数据按各实体的年份共同切分；若实体年份不齐，仍保持每个实体
    至少 ``min_train_years`` 个训练年份。
    """
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction 必须在 0 和 1 之间")
    if min_train_years < 1:
        raise ValueError("min_train_years 必须为正数")
    source = list(rows)
    groups: dict[str, list[Mapping[str, object]]] = {}
    for row in source:
        name = str(row.get(group, "all")) if group else "all"
        groups.setdefault(name, []).append(row)
    train: list[Mapping[str, object]] = []
    validation: list[Mapping[str, object]] = []
    for group_rows in groups.values():
        years = sorted({int(row["year"]) for row in group_rows if "year" in row})
        if len(years) <= min_train_years:
            raise ValueError("每个实体的年份不足以进行训练/验证切分")
        holdout = max(1, math.ceil(len(years) * validation_fraction))
        cutoff = years[-holdout]
        if sum(year < cutoff for year in years) < min_train_years:
            cutoff = years[min_train_years]
        train.extend(row for row in group_rows if int(row["year"]) < cutoff)
        validation.extend(row for row in group_rows if int(row["year"]) >= cutoff)
    return train, validation


def evaluate_parameters(
    observed_rows: Iterable[Mapping[str, object]],
    parameters: ParameterSet,
    simulate: Simulator,
    *,
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
    weights: Mapping[str, float] | None = None,
    objective_metric: str = "rmse",
    group: str | None = None,
) -> dict[str, object]:
    """在未参与搜索的观测期评估一组参数，返回可序列化报告。"""
    observed = list(observed_rows)
    simulated = list(simulate(parameters))
    errors = (replay_errors_by_group(observed, simulated, group=group, metrics=metrics)
              if group else replay_errors(observed, simulated, metrics))
    return {
        "parameters": dict(parameters),
        "objective": _objective_for_errors(errors, weights, objective_metric),
        "errors": errors,
    }


def replay_errors(
    observed_rows: Iterable[Mapping[str, object]],
    simulated_rows: Iterable[Mapping[str, object]],
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
) -> dict[str, dict[str, float]]:
    observed = list(observed_rows)
    if not parameter_grid or any(not values for values in parameter_grid.values()):
        raise ValueError("parameter_grid 及其每个候选值列表都不能为空")
    simulated = list(simulated_rows)
    result: dict[str, dict[str, float]] = {}
    for metric in metrics:
        observed_series = {
            int(row["year"]): float(row[metric])
            for row in observed if "year" in row and metric in row
        }
        simulated_series = {
            int(row["year"]): float(row[metric])
            for row in simulated if "year" in row and metric in row
        }
        result[metric] = series_error(observed_series, simulated_series)
    return result


def replay_errors_by_group(
    observed_rows: Iterable[Mapping[str, object]],
    simulated_rows: Iterable[Mapping[str, object]],
    *,
    group: str = "entity",
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
) -> dict[str, dict[str, dict[str, float]]]:
    """按国家/地区等分组后回放，避免不同实体相同年份互相覆盖。"""
    observed_groups: dict[str, list[Mapping[str, object]]] = {}
    simulated_groups: dict[str, list[Mapping[str, object]]] = {}
    for row in observed_rows:
        observed_groups.setdefault(str(row.get(group, "all")), []).append(row)
    for row in simulated_rows:
        simulated_groups.setdefault(str(row.get(group, "all")), []).append(row)
    result: dict[str, dict[str, dict[str, float]]] = {}
    for name in sorted(set(observed_groups) & set(simulated_groups)):
        result[name] = replay_errors(observed_groups[name], simulated_groups[name], metrics)
    if not result:
        raise ValueError(f"观测和模拟没有共同的 {group}")
    return result


def weighted_objective(
    errors: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float] | None = None,
    metric: str = "rmse",
) -> float:
    """将多个观测指标汇总为一个可比较的目标值。

    默认使用各指标的相对 RMSE（``mape``），避免人口规模大的国家压过
    生育率等小量纲指标；调用方可显式选择 ``mae``/``rmse``/``mape``。
    """
    weights = weights or {name: 1.0 for name in errors}
    total = sum(float(weights.get(name, 0.0)) * float(values[metric])
                for name, values in errors.items())
    scale = sum(float(weights.get(name, 0.0)) for name in errors)
    if scale <= 0:
        raise ValueError("至少需要一个正权重指标")
    return total / scale


def _objective_for_errors(errors, weights, objective_metric):
    if errors and isinstance(next(iter(errors.values())), dict) and "mae" not in next(iter(errors.values())):
        by_metric: dict[str, list[float]] = {}
        for group_errors in errors.values():
            for metric, values in group_errors.items():
                by_metric.setdefault(metric, []).append(float(values[objective_metric]))
        aggregated = {
            metric: {objective_metric: sum(values) / len(values)}
            for metric, values in by_metric.items()
        }
        return weighted_objective(aggregated, weights, objective_metric)
    return weighted_objective(errors, weights, objective_metric)


def grid_search(
    observed_rows: Iterable[Mapping[str, object]],
    parameter_grid: Mapping[str, Sequence[float]],
    simulate: Simulator,
    *,
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
    weights: Mapping[str, float] | None = None,
    objective_metric: str = "rmse",
    group: str | None = None,
) -> list[dict[str, object]]:
    """穷举参数网格，返回按目标值升序排列的候选结果。"""
    observed = list(observed_rows)
    names = list(parameter_grid)
    candidates: list[dict[str, object]] = []
    for values in product(*(parameter_grid[name] for name in names)):
        parameters = {name: float(value) for name, value in zip(names, values)}
        simulated = list(simulate(parameters))
        errors = (replay_errors_by_group(observed, simulated, group=group, metrics=metrics)
                  if group else replay_errors(observed, simulated, metrics))
        candidates.append({
            "parameters": parameters,
            "objective": _objective_for_errors(errors, weights, objective_metric),
            "errors": errors,
        })
    return sorted(candidates, key=lambda candidate: float(candidate["objective"]))


def random_search(
    observed_rows: Iterable[Mapping[str, object]],
    bounds: Mapping[str, tuple[float, float]],
    simulate: Simulator,
    *,
    trials: int = 32,
    seed: int = 0,
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
    weights: Mapping[str, float] | None = None,
    objective_metric: str = "rmse",
    group: str | None = None,
) -> list[dict[str, object]]:
    """在连续边界内做可复现的随机搜索，便于后续替换 Bayesian optimizer。"""
    if trials <= 0:
        raise ValueError("trials 必须为正数")
    observed = list(observed_rows)
    rng = Random(seed)
    if not bounds:
        raise ValueError("bounds 不能为空")
    for name, (low, high) in bounds.items():
        if not math.isfinite(float(low)) or not math.isfinite(float(high)) or low > high:
            raise ValueError(f"参数 {name} 的边界无效")
    candidates: list[dict[str, object]] = []
    for _ in range(trials):
        parameters = {
            name: rng.uniform(float(low), float(high))
            for name, (low, high) in bounds.items()
        }
        simulated = list(simulate(parameters))
        errors = (replay_errors_by_group(observed, simulated, group=group, metrics=metrics)
                  if group else replay_errors(observed, simulated, metrics))
        candidates.append({
            "parameters": parameters,
            "objective": _objective_for_errors(errors, weights, objective_metric),
            "errors": errors,
        })
    return sorted(candidates, key=lambda candidate: float(candidate["objective"]))
