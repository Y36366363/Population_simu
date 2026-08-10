"""历史回放校准骨架：只比较观测与模拟，不自动修改参数。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping

from .validation import series_error


def load_observed_csv(path: str | Path) -> list[dict[str, float | int | str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        rows = []
        for row in csv.DictReader(file):
            parsed: dict[str, float | int | str] = dict(row)
            if "year" in row:
                parsed["year"] = int(row["year"])
            for key, value in row.items():
                if key != "year" and value not in (None, ""):
                    try:
                        parsed[key] = float(value)
                    except ValueError:
                        pass
            rows.append(parsed)
        return rows


def replay_errors(
    observed_rows: Iterable[Mapping[str, object]],
    simulated_rows: Iterable[Mapping[str, object]],
    metrics: tuple[str, ...] = ("population", "births", "deaths"),
) -> dict[str, dict[str, float]]:
    observed = list(observed_rows)
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

