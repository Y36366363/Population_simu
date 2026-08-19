"""冻结期经验数据的纯函数解析器。"""

from __future__ import annotations

VARIABLES = ("NAME", "B25070_001E", "B25070_007E", "B25070_008E",
             "B25070_009E", "B25070_010E")

STATE_NAMES = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa", "20": "Kansas",
    "21": "Kentucky", "22": "Louisiana", "23": "Maine", "24": "Maryland", "25": "Massachusetts",
    "26": "Michigan", "27": "Minnesota", "28": "Mississippi", "29": "Missouri", "30": "Montana",
    "31": "Nebraska", "32": "Nevada", "33": "New Hampshire", "34": "New Jersey",
    "35": "New Mexico", "36": "New York", "37": "North Carolina", "38": "North Dakota",
    "39": "Ohio", "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington", "54": "West Virginia",
    "55": "Wisconsin", "56": "Wyoming", "72": "Puerto Rico",
}


def parse_acs_housing_response(payload: list[list[str]], year: int) -> list[dict[str, object]]:
    if not payload or len(payload) < 2:
        raise ValueError("ACS 响应为空")
    header = payload[0]
    required = set(VARIABLES) | {"state"}
    missing = required - set(header)
    if missing:
        raise ValueError(f"ACS 响应缺少字段：{sorted(missing)}")
    result = []
    for raw in payload[1:]:
        row = dict(zip(header, raw))
        try:
            total = float(row["B25070_001E"])
            burdened = sum(float(row[field]) for field in VARIABLES[2:])
        except (TypeError, ValueError) as exc:
            raise ValueError("ACS B25070 包含非数值估计") from exc
        if total <= 0:
            raise ValueError(f"{row['NAME']} {year} 的 B25070 总数不为正")
        result.append({"entity": row["NAME"], "state": row["state"], "year": year,
                       "housing_cost_burden": burdened / total,
                       "rent_burden_share": burdened / total,
                       "median_gross_rent": None})
    return result


def parse_acs_summary_file(path: str, year: int) -> list[dict[str, object]]:
    """解析 ACS table-based Summary File 的 ``|`` 分隔 B25070 文件。"""
    import csv
    with open(path, encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file, delimiter="|")
        result = []
        for row in rows:
            geo = row.get("GEO_ID", "")
            if not geo.startswith("0400000US"):
                continue
            state = geo[-2:]
            payload_row = [STATE_NAMES.get(state, state), row.get("B25070_E001", ""),
                           row.get("B25070_E007", ""), row.get("B25070_E008", ""),
                           row.get("B25070_E009", ""), row.get("B25070_E010", ""), state]
            result.extend(parse_acs_housing_response(
                [["NAME", "B25070_001E", "B25070_007E", "B25070_008E",
                  "B25070_009E", "B25070_010E", "state"], payload_row], year))
        if not result:
            raise ValueError(f"{path} 没有州级 B25070 行")
        return result


def validate_housing_panel(rows, *, expected_min_states: int = 50) -> dict[str, object]:
    """验证住房子面板；不把它误当作完整 fertility panel。"""
    rows = list(rows)
    required = {"entity", "state", "year", "housing_cost_burden"}
    if not rows:
        raise ValueError("住房面板为空")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"住房面板缺少字段：{missing}")
    keys = [(str(row["state"]), int(row["year"])) for row in rows]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    invalid = []
    for row in rows:
        try:
            value = float(row["housing_cost_burden"])
            if not 0 <= value <= 1:
                invalid.append((row["state"], row["year"], value))
        except (TypeError, ValueError):
            invalid.append((row.get("state"), row.get("year"), row.get("housing_cost_burden")))
    states = {key[0] for key in keys}
    years = sorted({key[1] for key in keys})
    return {"rows": len(rows), "states": len(states), "years": years,
            "duplicate_keys": duplicates, "invalid_values": invalid,
            "complete_state_coverage": len(states) >= expected_min_states,
            "ok": not duplicates and not invalid and len(states) >= expected_min_states}
