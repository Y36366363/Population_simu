# 住房主规格验证更新 · 2026-09-26

## 本次完成

### Rolling-origin 流程验证

使用 `us_research_panel_2010_2021_comparable.csv`，校准期为 2010–2017，
留出年份为 2018、2019、2021，2020 排除。比较六个模型：

- naive trend
- cohort-component proxy
- reduced-form
- household full
- household no-housing
- household no-household

输出已包含每个 rolling fold 的 RMSE、MAPE、CRPS、coverage 和平均区间宽度，
并包含州与 Census region 的 MAPE 分层。

快速验证 artifact：
`docs/artifacts/housing_primary_rolling_origin_2026-09-26_smoke.json`

该次运行使用 1 个 Monte Carlo replicate，目的只是验证流程、字段和严格键，
因此 coverage=0、区间宽度=0 是预期的退化结果，不能当作最终预测区间。
正式报告仍需在资源允许时使用预注册的多次 replicate 配置。

### Household 机制消融

`docs/artifacts/household_ablation_report_2026-09-26.json` 使用 2018、2019、2021
的 150 个州—年观测，分别比较 full、no-housing 和 no-household，共 450 个
严格键匹配的预测单元，并对同一州—年差值做 1000 次 paired bootstrap。

当前结果摘要：

| variant | MAPE | RMSE |
|---|---:|---:|
| full | 0.0477 | 3.458 |
| no-housing | 0.0451 | 3.194 |
| no-household | 0.0249 | 2.146 |

相对 full 的 paired MAPE 差值：

- no-housing − full：−0.00256，95% bootstrap 区间 [−0.00511, −0.00085]
- no-household − full：−0.02276，95% bootstrap 区间 [−0.02840, −0.01793]

这说明当前 household adapter 在短期预测上不占优，尤其是 no-household 更好；
它只能支持“机制模型与预测基准存在差异”的解释，不能支持住房的因果结论。

## 下一步

1. 保留当前快速 artifact 作为接口回归记录，不把它当正式置信区间。
2. 在同一配置下完成多 replicate rolling-origin，确保 coverage 有非退化区间。
3. 固定后再做区域/州配对区间汇总。
4. 年龄—婚姻—孩次 hazard 仍等待 48 个 WONDER 批次和匹配暴露分母，暂不进入主规格。
