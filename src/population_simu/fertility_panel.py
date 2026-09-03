"""CDC WONDER 出生导出与 Census 女性分母的冻结期面板合并。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


def _field(row: Mapping[str, object], *names: str) -> object:
    for name in names:
        if name in row:
            return row[name]
    raise KeyError(names[0])


def _number(value: object) -> float:
    """Parse numeric exports, including WONDER values formatted with commas."""
    return float(str(value).replace(",", "").strip())


def read_wonder_tsv(path: str | Path) -> list[dict[str, str]]:
    """读取 CDC WONDER 导出的 tab-delimited 文件，跳过空行和说明行。"""
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        rows = []
        for row in csv.DictReader((line for line in file if line.strip()), delimiter="\t"):
            if row and any(value not in (None, "") for value in row.values()):
                rows.append(dict(row))
        if not rows:
            raise ValueError("WONDER 导出为空")
        return rows


def merge_wonder_births_with_denominator(
    birth_rows: Iterable[Mapping[str, object]],
    denominator_rows: Iterable[Mapping[str, object]],
    *,
    country: str = "United States",
) -> list[dict[str, object]]:
    """按州—年合并出生数与女性 15—44 分母，计算 ASFR。

    birth 导出至少需要 ``State,Year,Births``；denominator 至少需要
    ``State,Year,Female15_44``。婚姻状态/孩次若存在会保留，但不能在缺少
    分母时把 WONDER 的 rate 或总人口直接当作 ASFR 分母。
    """
    denominators: dict[tuple[str, int], float] = {}
    for row in denominator_rows:
        try:
            key = (str(_field(row, "State", "state", "entity")), int(_field(row, "Year", "year")))
            value = _number(_field(row, "Female15_44", "female_15_44"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("女性分母必须包含 State/Year/Female15_44") from exc
        if value <= 0:
            raise ValueError(f"女性分母必须为正：{key}")
        if key in denominators:
            raise ValueError(f"女性分母重复州年键：{key}")
        denominators[key] = value
    output = []
    seen: set[tuple[str, int, str, str]] = set()
    for row in birth_rows:
        try:
            state = str(_field(row, "State", "state", "entity"))
            entity = str(row.get("Entity", row.get("entity", state)))
            year = int(_field(row, "Year", "year"))
            births = _number(_field(row, "Births", "births", "Number of Births"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("出生导出必须包含 State/Year/Births") from exc
        if births < 0:
            raise ValueError("出生数不能为负")
        marital = str(row.get("Marital Status", row.get("marital", "all")))
        parity = str(row.get("Live Birth Order", row.get("parity", "all")))
        key = (state, year, marital, parity)
        if key in seen:
            raise ValueError(f"出生导出重复键：{key}")
        seen.add(key)
        denominator = denominators.get((state, year))
        if denominator is None:
            raise ValueError(f"缺少女性分母：{state}/{year}")
        output.append({"country": country, "entity": entity, "state": state,
                       "year": year, "marital": marital, "parity": parity,
                       "births_15_44": births, "female_15_44": denominator,
                       "asfr_15_44": births / denominator * 1000.0})
    if not output:
        raise ValueError("没有可合并的出生观测")
    return output


def merge_stratified_wonder_births(
    birth_rows: Iterable[Mapping[str, object]],
    exposure_rows: Iterable[Mapping[str, object]], *,
    country: str = "United States", strict_parity: bool = True,
) -> list[dict[str, object]]:
    """Merge WONDER births with age×marital (and optionally parity) exposures.

    WONDER supplies state/year/mother-age/marital/live-birth-order counts for
    2007 onward. A valid hazard denominator must use the identical state, year,
    age-group and marital key; if parity-specific exposure is absent, strict
    mode rejects parity-specific births instead of silently reusing an all-parity
    denominator.
    """
    denominators: dict[tuple[str, int, str, str, str], float] = {}
    for row in exposure_rows:
        state = str(_field(row, "State", "state")); year = int(_field(row, "Year", "year"))
        age = str(_field(row, "Age", "age", "Age of Mother", "Age of Mother 9", "age_group"))
        marital = str(row.get("Marital Status", row.get("marital", "all")))
        parity = str(row.get("Live Birth Order", row.get("parity", "all")))
        exposure = _number(_field(row, "Exposure", "exposure", "FemaleExposure"))
        if exposure <= 0: raise ValueError(f"分层暴露必须为正：{state}/{year}/{age}/{marital}/{parity}")
        key = (state, year, age, marital, parity)
        if key in denominators: raise ValueError(f"分层暴露重复键：{key}")
        denominators[key] = exposure
    output = []; seen: set[tuple[str, int, str, str, str]] = set()
    for row in birth_rows:
        state = str(_field(row, "State", "state")); year = int(_field(row, "Year", "year"))
        age = str(_field(row, "Age", "age", "Age of Mother", "Age of Mother 9", "age_group"))
        if age in {"Under 15 years", "Under 15", "45-49 years", "50 years and over", "Unknown or Not Stated"}:
            continue
        marital = str(row.get("Marital Status", row.get("marital", "all")))
        parity = str(row.get("Live Birth Order", row.get("parity", "all")))
        births = _number(_field(row, "Births", "births", "Number of Births"))
        key = (state, year, age, marital, parity)
        if key in seen: raise ValueError(f"出生分层重复键：{key}")
        seen.add(key)
        denominator = denominators.get(key)
        if denominator is None and not strict_parity and parity != "all":
            denominator = denominators.get((state, year, age, marital, "all"))
        if denominator is None:
            raise ValueError(f"缺少同口径年龄—婚姻—孩次暴露：{key}")
        output.append({"country": country, "entity": str(row.get("Entity", row.get("entity", state))),
                       "state": state, "year": year, "age": age, "marital": marital,
                       "parity": parity, "births": births, "exposure": denominator,
                       "rate_per_1000": births / denominator * 1000.0,
                       "denominator_scope": "parity" if key in denominators else "all_parity"})
    if not output: raise ValueError("没有可合并的分层出生观测")
    return output


def aggregate_wonder_to_age_marital(
    birth_rows: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Collapse live-birth-order rows to age×marital total births.

    This is the estimable bridge when the female exposure source (ACS/PUMS or
    registration tables) has age×marital counts but no parity-specific risk
    sets. It deliberately labels parity as ``all``; the resulting rate is an
    age-marital total fertility rate, not a first/second/third-birth hazard.
    """
    totals: dict[tuple[str, int, str, str], dict[str, object]] = {}
    for row in birth_rows:
        # WONDER exports with "Show Totals" include a blank total row; totals
        # are not a state-year observation and must not enter the panel.
        raw_state = row.get("State", row.get("state", ""))
        raw_year = row.get("Year", row.get("year", ""))
        # csv.DictReader stores surplus/malformed fields under a ``None`` key;
        # treat null values as missing rather than attempting int(None).
        if raw_state is None or raw_year is None or not str(raw_state).strip() or not str(raw_year).strip() or str(raw_year).strip().lower() == "none":
            continue
        state = str(_field(row, "State", "state"))
        year = int(_field(row, "Year", "year"))
        age = str(_field(row, "Age", "age", "Age of Mother", "Age of Mother 9", "age_group"))
        if age in {"Under 15 years", "Under 15", "45-49 years", "50 years and over", "Unknown or Not Stated"}:
            continue
        marital = str(row.get("Marital Status", row.get("marital", "all")))
        births = _number(_field(row, "Births", "births", "Number of Births"))
        if births < 0:
            raise ValueError("出生数不能为负")
        key = (state, year, age, marital)
        item = totals.setdefault(key, {"State": state, "Year": year,
                                       "Age": age, "Marital Status": marital,
                                       "Live Birth Order": "all", "Births": 0.0})
        item["Births"] = float(item["Births"]) + births
    if not totals:
        raise ValueError("没有可聚合的出生观测")
    return list(totals.values())
