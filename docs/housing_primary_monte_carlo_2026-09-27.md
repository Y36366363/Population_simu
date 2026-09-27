# 住房主规格 Monte Carlo 预测区间 · 2026-09-27

## 配置

- 面板：`us_research_panel_2010_2021_comparable.csv`
- calibration：2010–2017
- untouched test：2018、2019、2021
- 2020：排除，仅作 ACS5 敏感性年份
- rolling-origin：initial=6，四个一年期 folds
- 模型：naive trend、cohort proxy、reduced-form、household full、
  no-housing、no-household
- Monte Carlo：20 次；bootstrap：1000 次

## 非退化结果

| 模型 | MAPE | CRPS | coverage | 平均区间宽度 |
|---|---:|---:|---:|---:|
| naive trend | 0.0153 | 0.704 | 0.590 | 1.849 |
| cohort proxy | 0.0160 | 0.737 | 0.525 | 1.850 |
| reduced-form | 0.0219 | 1.057 | 0.385 | 1.841 |
| household full | 0.0205 | 0.956 | 0.420 | 2.018 |
| household no-housing | 0.0204 | 0.954 | 0.385 | 1.789 |
| household no-household | 0.0151 | 0.695 | 0.560 | 1.816 |

完整 JSON：
`docs/artifacts/housing_primary_monte_carlo_2026-09-27_residual.json`

## 不确定性定义

原始确定性 runner 重复运行时可能产生相同预测，因此仅增加 Monte Carlo 次数
不能自动产生有效区间。本次通过 `--residual-uncertainty` 启用一个明确的
预测不确定性层：从 calibration 期每州的一步变化误差估计尺度，对每个预测
样本加入零均值误差。

这个层：

- 不改变点预测的期望；
- 不改变住房、生育、家庭或迁移机制；
- 不使用 untouched test 的观测值；
- 不是因果冲击，也不是年龄—婚姻—孩次 hazard；
- 只用于让确定性预测基准具有可评估的预测分布。

因此 coverage 和 CRPS 现在可解释为预测区间诊断，但不能解释为结构机制的
置信区间。正式报告仍应在主要 rolling-origin 起点 6、7、8 全部运行后汇总。
