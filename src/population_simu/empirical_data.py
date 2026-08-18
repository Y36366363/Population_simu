"""冻结期经验数据的纯函数解析器。"""

from __future__ import annotations

VARIABLES = ("NAME", "B25070_001E", "B25070_007E", "B25070_008E",
             "B25070_009E", "B25070_010E")


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
