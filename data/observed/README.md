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
