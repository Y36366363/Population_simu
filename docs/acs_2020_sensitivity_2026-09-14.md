# 2020 住房负担敏感性路径（2026-09-14）

标准 ACS 2020 1-year 产品没有发布，因此主研究面板继续不把 2020 当作与
2010–2019、2021 同口径的年度住房观测。今天新增一条可复现的敏感性路径：

- Census API `2020/acs/acs5` 的 B25070 州级估计；
- 52 个州/地区记录，字段保留 `estimate_type=acs5_B25070`；
- 用它构造独立的 `us_research_panel_2010_2021_with_2020_acs5_sensitivity.csv`；
- 不覆盖主面板，也不改变 2018、2019、2021 untouched test 定义。

这条路径可以回答“把 2020 作为 ACS 5-year 敏感性观测时，模型误差是否明显变化”，
但不能把 2020 的估计解释成标准 ACS 1-year 结果。它也不能解决 WONDER 的年龄—婚姻—孩次
出生分子缺口，因此不会自动开启正式 hazard 校准或因果解释。

可复现命令：

```bash
set -a; source .env; set +a
PYTHONPATH=src python3 scripts/fetch_us_housing_panel.py \
  --start 2020 --end 2020 --key "$CENSUS_API_KEY" \
  --output data/observed/us_2021/us_housing_2020_acs5_sensitivity.csv
PYTHONPATH=src python3 scripts/build_2020_sensitivity_panel.py \
  --housing data/observed/us_2021/us_housing_panel_2010_2021_comparable.csv \
  --housing-2020 data/observed/us_2021/us_housing_2020_acs5_sensitivity.csv \
  --fertility data/observed/us_2021/us_fertility_panel.csv \
  --output data/observed/us_2021/us_research_panel_2010_2021_with_2020_acs5_sensitivity.csv
```
