"""从加权微数据构造迁移 OD 与婚姻—孩次生育观测。

本模块只做加权汇总和口径检查，不下载受协议约束的 PUMS/NSFG 文件。
ACS PUMS 行通常需要 ``AGEP,SEX,ST,MIGSP,PWGTP``；出生登记行需要
``age,marital,parity,weight``，女性暴露行需要 ``age,marital,parity,weight``。
"""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
from typing import Iterable, Mapping

from .national_calibration import FertilityObservation, MigrationRecord


def _weighted(row: Mapping[str, object], weight_key: str) -> float:
    value = float(row[weight_key])
    if value < 0:
        raise ValueError("微数据权重不能为负")
    return value


def migration_records_from_pums(
    rows: Iterable[Mapping[str, object]], *, year: int,
    age_max: int = 100, weight_key: str = "PWGTP",
) -> tuple[MigrationRecord, ...]:
    """由 ACS PUMS 当前州 ST 与一年前州 MIGSP 生成年龄—性别 OD hazard。

    MIGSP 缺失、非州代码或当前州与原州相同的行不形成内部迁移；权重先汇总
    为 flow，再以原州同年龄—性别的加权人口作为 exposure。输出保留 flow 和
    exposure，便于审计抽样权重与 hazard 的分母。
    """
    flows: defaultdict[tuple[str, str, str, int], float] = defaultdict(float)
    exposure: defaultdict[tuple[str, str, int], float] = defaultdict(float)
    for row in rows:
        try:
            age, sex = int(row["AGEP"]), str(row["SEX"])
            origin, destination = str(row["MIGSP"]), str(row["ST"])
            weight = _weighted(row, weight_key)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("ACS PUMS 行缺少 AGEP/SEX/ST/MIGSP/权重") from exc
        if sex in {"1", "M"}:
            sex = "M"
        elif sex in {"2", "F"}:
            sex = "F"
        else:
            continue
        if not 0 <= age <= age_max or origin in {"000", "999", ""} or destination in {"", "999"}:
            continue
        exposure[(origin, sex, age)] += weight
        if origin != destination:
            flows[(origin, destination, sex, age)] += weight
    records: list[MigrationRecord] = []
    for (origin, destination, sex, age), flow in sorted(flows.items()):
        denominator = exposure[(origin, sex, age)]
        if denominator <= 0:
            continue
        records.append(MigrationRecord(origin, destination, sex, age,
                                       flow / denominator, flow, denominator))
    if not records:
        raise ValueError("ACS PUMS 没有可构造的年龄—性别迁移 OD")
    return tuple(records)


def fertility_observations_from_weighted_rows(
    birth_rows: Iterable[Mapping[str, object]],
    exposure_rows: Iterable[Mapping[str, object]], *,
    country: str, year: int, weight_key: str = "weight",
) -> tuple[FertilityObservation, ...]:
    """由出生登记/NSFG 加权行计算 births、exposure 和孩次 hazard 分母。"""
    births: defaultdict[tuple[str, str, str, int], float] = defaultdict(float)
    exposure: defaultdict[tuple[str, str, str, int], float] = defaultdict(float)
    for row in birth_rows:
        try:
            key = (country, str(row["marital"]), str(row["parity"]), int(row["age"]))
            births[key] += _weighted(row, weight_key)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("出生行需要 age/marital/parity/weight") from exc
    for row in exposure_rows:
        try:
            key = (country, str(row["marital"]), str(row["parity"]), int(row["age"]))
            exposure[key] += _weighted(row, weight_key)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("暴露行需要 age/marital/parity/weight") from exc
    observations: list[FertilityObservation] = []
    for (entity, marital, parity, age), denominator in sorted(exposure.items()):
        if denominator <= 0:
            continue
        observations.append(FertilityObservation(entity, year, marital, parity, age,
                                                 births[(entity, marital, parity, age)],
                                                 denominator))
    if not observations:
        raise ValueError("没有可构造的婚姻—孩次生育暴露")
    return tuple(observations)


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))
