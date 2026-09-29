# Calibration-only 残差尺度与分布比较 · 2026-09-29

## 设计

点预测使用州级最近两年 ASFR 线性外推。残差从 expanding-window 伪预测中产生：
训练窗口和误差目标全部限制在 2010–2017，并分别覆盖 1、2、4 年 horizon。

方法选择只在 calibration 内进行：用截至 2015 年拟合并验证 2016；用截至
2016 年拟合并验证 2017。比较 3 种尺度估计与 3 种残差分布，共 9 个候选。
选定方法后，使用完整 2010–2017 重估，再对 2018、2019、2021 作一次最终
评估。留出期没有参与残差池、方差估计或方法选择。

## 校准期内部方法比较

候选选择规则：coverage 与名义 80% 相差不超过 10 个百分点时，选择 CRPS 最低者；
否则先选 coverage gap 最小者，再比较 CRPS。

| 尺度 | 分布 | CRPS | coverage | 区间宽度 |
|---|---|---:|---:|---:|
| state-shrunk | normal | 0.715 | 0.820 | 3.283 |
| region | empirical quantile | 0.716 | 0.700 | 2.848 |
| state-shrunk | bootstrap residual | 0.716 | 0.760 | 3.349 |
| region | bootstrap residual | 0.717 | 0.720 | 2.931 |
| state-shrunk | empirical quantile | 0.718 | 0.700 | 2.747 |
| pooled | empirical quantile | 0.726 | 0.750 | 2.946 |
| region | normal | 0.727 | 0.830 | 3.343 |
| pooled | bootstrap residual | 0.728 | 0.760 | 2.999 |
| pooled | normal | 0.732 | 0.840 | 3.405 |

按预先设定的规则，选择 `state-shrunk + normal`。州级方差按
`n/(n+10)` 向 Census region 方差收缩，减少每州残差样本有限带来的尺度抖动。

## Untouched test 最终评估

| 州—年样本 | MAPE | RMSE | CRPS | 80%区间 coverage | 平均宽度 |
|---:|---:|---:|---:|---:|---:|
| 150 | 0.0307 | 2.988 | 1.350 | 0.840 | 6.010 |

州聚类 bootstrap 95% 区间：

- CRPS：1.044–1.692
- coverage：0.753–0.913
- 平均区间宽度：5.624–6.413

区域 coverage：Midwest 0.861，Northeast 0.926，South 0.875，West 0.718。
West 区间覆盖偏低，应作为后续预注册的校准诊断记录；当前留出期不再用于调参。

## 方法判断

- pooled、region、state-shrunk 三种尺度层级均已比较。部分汇聚州级尺度在
  calibration validation 中 CRPS 最低，最终 coverage 为 0.84。
- 正态分布和 bootstrap residual 在内部 CRPS 接近；经验分位数区间较窄，
  但内部 coverage 偏低。
- 最终 coverage 达到 80% 附近，但 bootstrap 区间仍较宽，且区域表现不均；
  不应把单次 holdout 结果解释成普遍校准保证。
- 这次点预测是短期 naive linear trend 基准，因此 MAPE/RMSE 不与 household
  机制模拟 artifact 直接等同比较。此试验只回答预测残差分布和尺度问题。

机器可读完整结果：
`docs/artifacts/residual_uncertainty_comparison_2026-09-29.json`
