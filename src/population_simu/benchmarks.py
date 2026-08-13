"""可替换的人口预测基准模型与横向比较。

基准模型只负责产生预测行；评估统一复用 calibration 中的 CRPS、区间覆盖率
和点预测误差。家庭微观模型或真正的年龄—性别 cohort-component 模型可通过
同一个 runner 契约接入，不会被迫伪装成某个简化公式。
"""

from __future__ import annotations

from random import Random
from statistics import median
from typing import Callable, Iterable, Mapping

from .calibration import (
    crps_metrics,
    replay_errors_by_group,
    rolling_origin_splits,
    stratified_interval_metrics,
)

Rows = Iterable[Mapping[str, object]]
Runner = Callable[[list[Mapping[str, object]], list[int], int], Iterable[Mapping[str, object]]]


def _median_forecast(replicates: list[list[Mapping[str, object]]], metric: str) -> list[dict[str, object]]:
    """把多个随机重复压缩为按 key 的中位数点预测。"""
    values: dict[tuple[str, int], list[float]] = {}
    for replica in replicates:
        for row in replica:
            if "year" not in row or metric not in row:
                continue
            key = (str(row.get("entity", "all")), int(row["year"]))
            values.setdefault(key, []).append(float(row[metric]))
    return [{"entity": entity, "year": year, metric: median(samples)}
            for (entity, year), samples in sorted(values.items())]


def _mean_error(errors: Mapping[str, Mapping[str, float]], metric: str = "mape") -> float:
    values: list[float] = []
    for row in errors.values():
        if metric in row:
            values.append(float(row[metric]))
        else:
            for nested in row.values():
                if isinstance(nested, Mapping) and metric in nested:
                    values.append(float(nested[metric]))
    if not values:
        raise ValueError("没有可汇总的模型误差")
    return sum(values) / len(values)


def _bootstrap_mean(values: list[float], seed: int, draws: int = 2000) -> dict[str, float | int]:
    if not values:
        raise ValueError("bootstrap 至少需要一个折叠分数")
    if draws < 100:
        raise ValueError("bootstrap draws 至少为 100")
    rng = Random(seed)
    means = []
    for _ in range(draws):
        means.append(sum(values[rng.randrange(len(values))] for _ in values) / len(values))
    means.sort()
    return {
        "n_folds": len(values),
        "draws": draws,
        "mean": sum(values) / len(values),
        "lower_95": means[min(len(means) - 1, int(0.025 * draws))],
        "upper_95": means[min(len(means) - 1, int(0.975 * draws))],
    }


def fixed_trend_runner(metric: str = "population") -> Runner:
    """固定趋势基准：按实体最近两点的线性增量外推。"""
    def run(train: list[Mapping[str, object]], years: list[int], seed: int) -> list[dict[str, object]]:
        entities = sorted({str(row.get("entity", "all")) for row in train})
        output: list[dict[str, object]] = []
        for entity in entities:
            rows = sorted((row for row in train if str(row.get("entity", "all")) == entity),
                          key=lambda row: int(row["year"]))
            if not rows or metric not in rows[-1]:
                continue
            last = float(rows[-1][metric])
            previous = float(rows[-2][metric]) if len(rows) > 1 and metric in rows[-2] else last
            increment = last - previous
            for offset, year in enumerate(years, start=1):
                output.append({"entity": entity, "year": year, metric: max(0.0, last + increment * offset)})
        return output
    return run


def wpp_style_runner(metric: str = "population", damping: float = 0.85) -> Runner:
    """WPP 风格的轻量基准：阻尼近期趋势并保持非负。

    这不是联合国 WPP 的复制品；真正的 WPP 风格模型应由年龄—性别矩阵、
    年龄别生育率、死亡率和迁移率驱动。该 runner 只用于在接入完整 cohort-
    component 模型前提供一个透明、可回归测试的基准。
    """
    if not 0 <= damping <= 1:
        raise ValueError("damping 必须在 0 和 1 之间")
    def run(train: list[Mapping[str, object]], years: list[int], seed: int) -> list[dict[str, object]]:
        entities = sorted({str(row.get("entity", "all")) for row in train})
        output: list[dict[str, object]] = []
        for entity in entities:
            rows = sorted((row for row in train if str(row.get("entity", "all")) == entity),
                          key=lambda row: int(row["year"]))
            if not rows or metric not in rows[-1]:
                continue
            history = [float(row[metric]) for row in rows[-6:] if metric in row]
            increment = (history[-1] - history[0]) / max(1, len(history) - 1)
            level = history[-1]
            for year in years:
                level = max(0.0, level + damping * increment)
                output.append({"entity": entity, "year": year, metric: level})
        return output
    return run


def compare_models(
    observed_rows: Rows,
    models: Mapping[str, Runner],
    *,
    train_years: int,
    horizon: int,
    metric: str = "population",
    replicates: int = 1,
    seed: int = 0,
) -> dict[str, dict[str, object]]:
    """在同一留出窗口比较多个模型，返回点误差、CRPS 和区间诊断。"""
    if train_years < 1 or horizon < 1 or replicates < 1:
        raise ValueError("train_years、horizon 和 replicates 必须为正数")
    observed = list(observed_rows)
    years = sorted({int(row["year"]) for row in observed if "year" in row})
    if len(years) <= train_years or len(years) < train_years + horizon:
        raise ValueError("观测年份不足以进行模型比较")
    train_cutoff = years[train_years]
    forecast_years = years[train_years:train_years + horizon]
    train = [row for row in observed if int(row["year"]) < train_cutoff]
    test = [row for row in observed if int(row["year"]) in forecast_years]
    result: dict[str, dict[str, object]] = {}
    for name, runner in models.items():
        samples = [list(runner(train, forecast_years, seed + index)) for index in range(replicates)]
        point = _median_forecast(samples, metric)
        errors = replay_errors_by_group(test, point, group="entity", metrics=(metric,))
        entry: dict[str, object] = {
            "point_errors": errors,
            "crps": crps_metrics(test, samples, metrics=(metric,), group="entity"),
        }
        if replicates > 1:
            entry["intervals"] = stratified_interval_metrics(
                test, samples, strata=("entity",), metrics=(metric,))
        result[name] = entry
    return result


def compare_models_rolling(
    observed_rows: Rows,
    models: Mapping[str, Runner],
    *,
    initial_train_years: int,
    horizon: int = 1,
    step: int = 1,
    metric: str = "population",
    replicates: int = 20,
    seed: int = 0,
    bootstrap_draws: int = 2000,
    baseline: str | None = None,
) -> dict[str, dict[str, object]]:
    """多窗口滚动回测，并给出 bootstrap 置信区间和相对基准胜率。

    每个窗口、每个模型使用相同的 seed 序列（common random numbers），使模型
    差异更少受随机噪声影响。误差按实体先计算 MAPE 再平均，避免人口大国完全
    支配跨国比较；CRPS 仍保留原始量纲并单独报告。
    """
    if replicates < 1:
        raise ValueError("replicates 必须至少为 1")
    observed = list(observed_rows)
    folds = rolling_origin_splits(observed, initial_train_years=initial_train_years,
                                  horizon=horizon, step=step, group="entity")
    if baseline is not None and baseline not in models:
        raise ValueError("baseline 必须是 models 中的模型名")
    fold_scores: dict[str, list[dict[str, float | int]]] = {name: [] for name in models}
    for fold_index, (train, test) in enumerate(folds):
        years = sorted({int(row["year"]) for row in test})
        for name, runner in models.items():
            # 每个模型共享同一组 replicate seeds；不同折叠使用不重叠的偏移。
            samples = [list(runner(train, years, seed + fold_index * replicates + index))
                       for index in range(replicates)]
            point = _median_forecast(samples, metric)
            errors = replay_errors_by_group(test, point, group="entity", metrics=(metric,))
            crps = crps_metrics(test, samples, metrics=(metric,), group="entity")[metric]["mean_crps"]
            fold_scores[name].append({
                "origin_year": min(years),
                "mape": _mean_error(errors, "mape"),
                "rmse": _mean_error(errors, "rmse"),
                "crps": float(crps),
            })
    result: dict[str, dict[str, object]] = {}
    for name, scores in fold_scores.items():
        mape = [float(row["mape"]) for row in scores]
        rmse = [float(row["rmse"]) for row in scores]
        crps = [float(row["crps"]) for row in scores]
        result[name] = {
            "folds": scores,
            "summary": {
                "mape": _bootstrap_mean(mape, seed + 11, bootstrap_draws),
                "rmse": _bootstrap_mean(rmse, seed + 17, bootstrap_draws),
                "crps": _bootstrap_mean(crps, seed + 23, bootstrap_draws),
            },
        }
    if baseline is not None:
        baseline_mape = [float(row["mape"]) for row in fold_scores[baseline]]
        for name, scores in fold_scores.items():
            if name == baseline:
                result[name]["vs_baseline"] = {"win_rate": 0.5, "mean_delta": 0.0}
                continue
            deltas = [float(row["mape"]) - base
                      for row, base in zip(scores, baseline_mape)]
            wins = sum(delta < 0 for delta in deltas)
            result[name]["vs_baseline"] = {
                "win_rate": wins / len(deltas),
                "mean_delta": sum(deltas) / len(deltas),
                "delta_95": _bootstrap_mean(deltas, seed + 31, bootstrap_draws),
            }
    return result
