# Feature Freeze：首个可证伪 household study

## 决策

冻结所有新机制；只做数据接入、参数估计、历史回放、模型比较、消融和审计。

| 方向 | public data availability | parameter identifiability | current-code coverage | historical holdout | novelty | 8–12周完成 | 总评 |
|---|---:|---:|---:|---:|---:|---:|---|
| housing/childcare burden → fertility | 4 | 3 | 4 | 5 | 4 | 5 | **首选** |
| family resources → intergenerational mobility | 2 | 2 | 4 | 2 | 5 | 2 | 暂缓 |
| household migration → regional inequality | 4 | 2 | 4 | 4 | 3 | 3 | 第二候选 |

首个研究只选择美国州—年面板的 housing burden → fertility。childcare coverage 作为第二
处理变量；如果 2007—2021 年有一致的州级正式托育覆盖序列，就纳入主规格，否则只报告
housing-only 规格，不能用不同年份定义的代理变量拼接。

## Scientific question 和 estimand

**Question:** 在控制女性就业、失业、教育、迁移和州固定效应后，州级住房成本负担与
托育供给能否改善对下一年 15—44 岁年龄别生育率的预测？家庭模拟器是否比简单趋势、
cohort-component 和 reduced-form 模型更能复现 2018—2021 的州级生育动态？

主要预测 estimand 是州—年下一年 `ASFR_15_44` 的条件预测分布；报告 RMSE、MAPE、CRPS
和分层区间覆盖率。机制 estimand 是模型内部“housing/childcare burden 改变生育 hazard
的贡献”，只作为可解释性量，不称为因果效应。只有另行设计识别假设、预处理和敏感性
分析后，才可以报告 causal counterfactual。

## 必须由真实数据估计的参数

- housing burden → first/second/third birth hazard 的系数或非线性曲线；
- childcare coverage → birth hazard 的系数；
- 年龄别基线生育 hazard（15—44）；
- 婚姻状态、孩次和女性就业的分层基线；
- 州固定差异和年份冲击；
- 州级观测误差和 Monte Carlo 初始家庭抽样分布。

住房和托育参数只能在 calibration period 估计。家庭模型中的其他社会机制全部冻结，
不得为了提高 test 期表现临时增加变量。

## 时间设计

- calibration：2007—2017；
- untouched historical test：2018—2021；
- 主报告使用 expanding-window rolling-origin；test 变量、阈值和参数在回测期间不重新调参；
- 另做 2015—2017 的预注册式敏感性窗口，但不能替代主 test。

## 必须比较的模型

1. naive/trend baseline：最近两年趋势外推；
2. cohort-component baseline：真实年龄—性别人口、年龄别死亡率、年龄别生育率，不含家庭机制；
3. reduced-form statistical model：州固定效应 + 年固定效应 + housing/childcare + 预先指定控制变量；
4. household simulator：现有家庭模型，仅启用已经存在的住房、托育、生育 hazard 和人口对账接口。

所有模型必须对同一州—年键给出预测，使用相同 rolling-origin、共同随机数、CRPS、coverage、
RMSE/MAPE。`paired_model_comparison()` 和 `rank_models()` 用于差值区间和排名解释。

## Mechanism ablation

- full：housing + childcare；
- no-housing：将住房处理固定为 calibration 均值；
- no-childcare：将托育处理固定为 calibration 均值；
- no-household：关闭家庭异质性但保持同一宏观输入；
- trend-only：仅保留时间趋势。

消融只能回答“该机制是否改善预测/解释”，不能回答政策造成了多少真实因果变化。

## 数据契约

最小 state-year CSV：

```text
entity,year,asfr_15_44,births_15_44,female_15_44,
housing_cost_burden,median_gross_rent,rent_burden_share,
childcare_supply,under5_formal_care_share,
female_employment,unemployment,education,migration_rate
```

需要下载并固定版本：

- Census ACS 1-year / PUMS：州级租金负担、住房支出、女性就业、教育和家庭结构，2007—2021；
- Census Population Estimates：州—年龄—性别女性分母，2007—2021；
- CDC/NCHS Natality 或 CDC WONDER：州—母亲年龄—孩次—婚姻状态出生数，2007—2021；
- Child Care Aware、HHS ACF 或州行政托育统计：州—年托育价格/容量/覆盖率，只有定义一致时纳入；
- 所有文件记录下载日期、版本、变量定义、权重和缺失处理。

本轮已加入 `scripts/fetch_us_housing_panel.py`，读取 ACS B25070 的 30% 以上租金负担
类别并输出州—年 housing panel。Census API 若返回认证错误，脚本会停止；不能用错误页或
缺失值继续运行。`median_gross_rent` 仍需单独接入 B25064 等表，不能把负担比例当租金。

## 两周最小 empirical milestone

只完成一件事：构造 2007—2021 美国州—年 `ASFR_15_44 + housing_cost_burden` 面板，冻结
2018—2021 test，运行 trend、cohort-component、reduced-form 和 household 四个 runner，
输出第一份 rolling-origin RMSE/MAPE/CRPS/coverage 表，并运行 no-housing 消融。托育变量
若尚未形成一致序列，明确标记为缺失，不用合成值填充。结果只能作为预测验证，不作政策因果结论。
