"""可替换的人口预测基准模型与横向比较。

基准模型只负责产生预测行；评估统一复用 calibration 中的 CRPS、区间覆盖率
和点预测误差。家庭微观模型或真正的年龄—性别 cohort-component 模型可通过
同一个 runner 契约接入，不会被迫伪装成某个简化公式。
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

from .calibration import crps_metrics, replay_errors_by_group, stratified_interval_metrics

Rows = Iterable[Mapping[str, object]]
Runner = Callable[[list[Mapping[str, object]], list[int], int], Iterable[Mapping[str, object]]]


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
        point = samples[0]
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
