# 住房主规格三起点 Monte Carlo 汇总 · 2026-09-28

## 固定配置

三个 rolling-origin 起点均使用相同的 20 次 Monte Carlo、1000 次 bootstrap、
相同 calibration/test 划分、六个模型和 residual uncertainty 规则。每个起点
保留独立 artifact，汇总文件只计算跨起点 fold 平均。

## 跨 initial=6/7/8 的 pooled fold 结果

| 模型 | folds | MAPE | CRPS | coverage | 平均区间宽度 |
|---|---:|---:|---:|---:|---:|
| naive trend | 9 | 0.0151 | 0.681 | 0.604 | 1.894 |
| cohort proxy | 9 | 0.0160 | 0.730 | 0.504 | 1.908 |
| reduced-form | 9 | 0.0227 | 1.082 | 0.402 | 1.923 |
| household full | 9 | 0.0210 | 0.974 | 0.402 | 2.181 |
| no-housing | 9 | 0.0209 | 0.956 | 0.356 | 1.824 |
| no-household | 9 | 0.0149 | 0.674 | 0.596 | 1.880 |

这里的区间是 80% 区间。当前 coverage 约为 0.36–0.60，普遍低于 0.80 名义覆盖率，
说明 residual uncertainty 仍偏窄或分布假设过于简单。这是需要优化的预测校准问题，
不是继续添加社会机制的理由；下一步应在 calibration 内进行 scale/分位数校准，
并保留 untouched test 不参与调参。

完整汇总：
`docs/artifacts/housing_primary_monte_carlo_2026-09-28_summary.json`

## 解释

1. 三个起点的 coverage 均为非退化值，说明预测分布已经真正进入评估流程。
2. naive trend 与 no-household 的短期预测表现最好；这进一步支持将 household
   full 定位为机制解释模型，而非短期预测主模型。
3. household full 的区间较宽，但 coverage 没有明显优于简单基准；不能据此声称
   家庭机制更真实或住房具有因果作用。
4. 所有结果仍是 aggregate ASFR 层面的预测诊断；年龄、婚姻、孩次 hazard 仍未
   正式估计，2020 仍未进入主测试期。
