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

- primary comparable calibration：2010—2017；
- untouched historical test：2018—2019 和 2021；2020 保留为疫情期间数据缺口，不做插值；
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

## 当前四类 Runner 接入状态

`benchmarks.py` 现在提供四个可比较 runner：`fixed_trend_runner`、`wpp_style_runner`
（cohort proxy）、`reduced_form_runner` 和 `household_simulator_runner`。后两个只消费
校准期传入的数据；reduced-form 使用州内去均值的住房负担斜率，未来处理变量按校准期均值
保持；household adapter 调用现有 `World`，再把出生事件聚合成 ASFR 预测。它们都遵循同一
预测覆盖、CRPS、区间和 rolling-origin 契约，但后两个仍是预测适配器，不是识别后的因果模型。

在 2010–2019、2021 可比面板上的四模型 smoke test 中，trend/cohort proxy 的 MAPE 约 1.38%，
reduced-form 约 2.32%，未校准 household adapter 约 88%。加入现有机制的校准适配器后，
household adapter 的 MAPE 降至约 1.98%，但仍不能把预测改善解释成因果机制成立。

校准器位于 `src/population_simu/household_calibration.py`，只使用 calibration rows：

- 女性 15–44 暴露：直接使用真实 `female_15_44` 分母，暴露缩放固定为 1.0；
- 年龄别生育概率：当前面板没有年龄别出生暴露，因此使用显式年龄 profile 先验；
- 婚配/伴侣暴露：当前没有婚姻分母，使用 0.62 先验并标记 `prior_only`；
- 孩次递进：当前 `parity=all`，使用 `(0.72, 0.48, 0.24)` 先验，不能声称已识别；
- 住房映射：估计州内去均值的住房负担—ASFR 预测弹性。本轮估计值约为 `0.455`，方向为
  正，提示观测混杂/反向因果可能存在；该参数只用于预测，不应解释为住房负担提高生育率。

因此目前家庭模型的真实状态是：分母和住房预测映射已有可复现校准，年龄、婚配、孩次仍需
真实暴露数据才能正式识别。下一步只能接入这些观测分母或做预先登记的敏感性分析，不新增
社会机制。

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

### 生育结果导入路径

由于 2005 年后的 NBER 公共出生微数据不提供可用于本研究的州级细分，当前已固定的首个
可审计路径是使用 CDC/NCHS 每年最终出生报告中的州级表（母亲居住州），再用 Census PEP
单岁年龄—性别估计汇总女性 15—44 岁分母计算 `ASFR_15_44`。该路径覆盖 2007—2021，
不依赖不可批量调用州级地理字段的 WONDER API。导入器为
`src/population_simu/fertility_panel.py`，命令行入口为：

```bash
PYTHONPATH=src python3 scripts/import_wonder_fertility.py \
  data/observed/us_2021/wonder_natality_2007_2021.tsv \
  data/observed/us_2021/us_female_15_44_2007_2021.csv \
  --output data/observed/us_2021/us_fertility_panel.csv
```

输入必须包含 `State,Year,Births` 与 `State,Year,Female15_44`；程序会拒绝重复键、缺失分母、
负出生数和非正分母，并保留可选的 `Marital Status`、`Live Birth Order`。当前仓库尚未放入
当前固定的 outcome 是总出生的一般生育率，尚未加入婚姻状态/孩次分层；真实文件的行数、来源
URL 和 SHA-256 固定在 `data/observed/us_2021/us_fertility_manifest.json`，不使用合成出生数据替代。

本轮已加入 `scripts/fetch_us_housing_panel.py` 和 `scripts/fetch_us_housing_historical.py`。
后者按年份解析 ACS B25070 的 sequence/table-based FTP 格式，并保留 `estimate_type` 与
`source_url`。`median_gross_rent` 仍需单独接入 B25064，不能把负担比例当租金。当前
`us_housing_panel_2010_2021_comparable.csv` 已覆盖 50 州的 2010–2019 和 2021，共 550 行；
manifest 会列出 2007–2009 和 2020 的缺失，不允许静默插值。Census 没有标准 2020 ACS 1-year
Summary File，因此 5-year 或 experimental 值若使用，必须作为单独敏感性规格并标记不可比。

`scripts/validate_frozen_data.py` 已能对当前住房子面板输出 JSON 审计；comparable 切片无重复键、
比例均在 [0,1]；生育结果和女性分母已经接入，`study_readiness()` 已按 2010–2019、2021
主规格通过。2007–2009 与 2020 仍被显式标记为敏感性/缺口，不会进入主规格。

## 两周最小 empirical milestone

只完成一件事：构造 2010—2019、2021 美国州—年 `ASFR_15_44 + housing_cost_burden` 面板，
冻结 2018—2019、2021 test，运行 trend、cohort-component、reduced-form 和 household 四个 runner，
输出第一份 rolling-origin RMSE/MAPE/CRPS/coverage 表，并运行 no-housing 消融。托育变量
若尚未形成一致序列，明确标记为缺失，不用合成值填充。结果只能作为预测验证，不作政策因果结论。

## 后续工作顺序（冻结期）

1. **数据完成**：主规格使用 2010—2019、2021 的 ACS B25070 1-year sequence/table 数据；
   2007—2009 的 ACS 3-year 数据只作为敏感性分析，不能复制成年度值。2020 没有标准 ACS
   1-year Summary File，因此保持缺口。当前已接入 CDC/NVSS 州级总出生数和 Census PEP 女性
   15—44 岁分母。婚姻/孩次分层和托育序列只有在定义和年份一致时加入。
2. **面板锁定**：对所有州年键、缺失、权重、版本和变量定义做审计，生成不可再变的分析 CSV。
3. **参数校准**：只用 2007—2017，估计基线生育 hazard、住房系数和 reduced-form 系数；保存
   参数文件与随机种子。
4. **历史回放**：在 2018—2021 untouched test 上运行四类模型，使用现有 rolling-origin、
   CRPS、coverage、RMSE/MAPE。
5. **机制消融**：只比较 no-housing、no-childcare、no-household 与 full，不添加新机制。
6. **解释边界**：先报告预测和机制贡献；只有未来建立可信识别设计后，才讨论 causal counterfactual。

`study_readiness()` 会自动报告上述阶段是否具备。当前真实状态是 housing slice 已有、完整
住房时期和 fertility outcome 尚未具备，因此下一步唯一阻塞项是生育结果与分母数据。
