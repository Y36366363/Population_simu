# 真实观测校准样例

`owid_demography_sample.csv` 是用于测试历史回放与参数搜索的小型、可提交
到仓库的样例，包含中国、印度、日本和美国 1950—2023 年的年度观测：

- `population`：年中人口（人）；
- `birth_rate_per_1000`、`death_rate_per_1000`：每千人粗出生率和粗死亡率；
- `tfr`：总和生育率（每名女性的平均生育数）；
- `births_estimated`、`deaths_estimated`：用人口 × 粗率 / 1000 推导的数量，
  仅用于把观测接入现有 `population/births/deaths` 接口，不应当当作独立统计。

数据来源是 Our World in Data 的 Grapher CSV，底层主要来自联合国
World Population Prospects 2024：

- [Population](https://ourworldindata.org/grapher/population)
- [Crude birth rate](https://ourworldindata.org/grapher/crude-birth-rate)
- [Crude death rate](https://ourworldindata.org/grapher/crude-death-rate)
- [Total fertility rate](https://ourworldindata.org/grapher/children-born-per-woman)

下载日期：2026-08-12。OWID 数据通常按 CC BY 4.0 发布；使用时请保留
来源和底层提供者署名。该文件是固定快照，后续更新数据时应在这里记录
新的下载日期和版本，避免校准结果因数据漂移而无法复现。

## 年龄—性别与死亡率样例

- `wb_age_sex_groups_sample.csv`：世界银行 WDI 的中国、印度、日本、美国
  1990—2023 年人口年龄组—性别数据（0—14、15—64、65+），由 WDI 指标
  `SP.POP.0014.*.IN`、`SP.POP.1564.*.IN` 和 `SP.POP.65UP.*.IN` 组成。
  这是公开的分组观测，不是单岁年龄；回放时由模型单岁年龄聚合到同样的年龄组。
  来源：[World Bank Indicators API](https://api.worldbank.org/)。
- `owid_age_sex_death_rates_sample.csv`：中国、印度、日本、美国 1990—2023
  年的若干年龄点（0、10、15、25、45、65、80）男女死亡率，来源为
  Human Mortality Database 与 UN WPP，经 OWID Grapher 整理。它用于测试
  年龄—性别死亡率接口，不等同于完整生命表；完整生命表应使用 HMD 的逐年
  年龄文件或 WPP 的生命表输出。
  来源：[OWID 年龄—性别死亡率图表](https://ourworldindata.org/grapher/annual-death-rates-in-different-age-groups-by-sex)。

这些文件由 `population_simu.cohort_replay` 读取；年龄组观测与模型单岁年龄
快照的对账结果会按国家、性别和年龄组分层输出。

## 可替换的正式校准 CSV 契约

正式数据可以不提交到仓库，只需按以下长表接入：

```text
# 单岁生命表
country,year,sex,age,death_rate
# 年龄—性别 OD（hazard，不是人数）
year,origin,destination,sex,age,hazard
# 婚姻—孩次生育率分母
country,year,marital,parity,age,births,exposure
```

`exposure` 应是同口径的女性人年（或调查权重后的暴露量），不能用总人口替代。
如果只有 0—14/15—64/65+ 年龄组，工具可以做均匀拆分来启动回放，但会标记为
`derived=True`，严格校准会要求真实单岁年龄覆盖。迁移 OD 也必须保留性别与年龄，
否则只能作为兼容旧模型的平均 profile。
