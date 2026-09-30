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

## 2026-09-30 后续诊断：跨度与抽样稳定性

本次不更改候选、不重选方法，也不使用留出期调整参数。固定采用校准期验证选出的
`state-shrunk + normal`，重新生成带完整选择记录的 artifact，并把留出结果按年份
拆分。可见 coverage 从 2018 的 0.90、2019 的 0.88 降至 2021 的 0.74；区间宽度
虽随跨度从 3.31 增至 9.02，四年外推的不确定性仍偏低。留出期总体 coverage 0.84
因此掩盖了长跨度覆盖不足；不能据此在测试期调大区间。

| 测试年 / 距校准末年跨度 | 州数 | CRPS | 80%区间 coverage | 平均宽度 |
|---|---:|---:|---:|---:|
| 2018 / 1 年 | 50 | 0.580 | 0.900 | 3.311 |
| 2019 / 2 年 | 50 | 1.096 | 0.880 | 5.699 |
| 2021 / 4 年 | 50 | 2.373 | 0.740 | 9.021 |

另以相同校准拟合、同一已选方法、每州—年 1,000 个预测抽样，重复 10 个随机种子。
CRPS 均值 1.343（SD 0.0034，范围 1.340–1.352）；平均区间宽度 6.022（SD 0.0104，
范围 6.007–6.038）；coverage 均值 0.837（SD 0.0134，范围 0.820–0.867）。因此
CRPS 和区间宽度的数值很稳定，coverage 因有限样本/边界跨越呈现更明显的离散波动；
主要问题不是 Monte Carlo 噪声，而是预测跨度和区域间的校准差异。西部 coverage
仍为 0.718，是可报告的诊断信号，但该测试集只能指出失配，不能用于修正模型。

此轮生成的详细诊断：
`docs/artifacts/residual_uncertainty_comparison_2026-09-30.json`
