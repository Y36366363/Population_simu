# 理论与类似沙盘对照

## 结论先行

本项目最适合保持“微观家庭 ABM + 宏观 cohort-component 审计 + 少量系统动力学库存”的混合结构。家庭是决策单位，但人口年龄结构、出生—死亡—迁移和财政资源必须在宏观层闭合；环境、技术和公共服务则以库存/流量方式反馈到家庭。

## 与成熟框架的对照

| 框架 | 擅长的问题 | 对本项目的启发 | 不应直接照搬 |
|---|---|---|---|
| UN cohort-component | 年龄—性别人口、出生、死亡、迁移的总量一致性 | 每年检查年龄结构和人口流量闭合 | 不能表达家庭网络、职业继承和资源分配 |
| 家庭政策 ABM | 异质家庭、社会网络、政策作用机制 | 把邻居/亲属/同事/媒体从平均规范逐步变成网络 | 不能只凭模拟结果声称政策因果 |
| FPsim 类生命历程 ABM | 生物、行为和家庭计划的联动 | 婚姻、避孕、生育间隔应成为生命周期 hazard | 需要更细的生殖健康数据，不能用总和生育率替代 |
| World3/系统动力学 | 人口、资源、产出、污染的长期反馈 | 把财政、环境恢复、技术和资源当作库存—流量 | 不能用宏观平均变量替代家庭异质性 |
| Civilization VI | 可读的住房、公共服务、忠诚/压力反馈 | 用少量可解释旋钮表达承载力和地方压力 | 游戏的离散惩罚和胜利条件不是现实证据 |
| 城市/地区家庭微观模拟 | 家庭迁移、空间分布、地区差异 | 将地区矩阵、住房、学校、就业和暴露度放在同一空间层 | 需要真实地区基线和迁移矩阵校准 |

## 近期应优先补的结构

1. **年龄结构闭合**：增加按年龄、性别的国家和地区人口表，与家庭明细定期对账；现有 `FamilyWorld.audit()` 先检查国家—地区分区和年度指标的结构合法性。
2. **库存—流量财政**：把税收、教育、医疗、养老和灾害恢复支出从年度指标升级为政府基金余额，允许赤字、借贷和跨地区转移。
3. **生命周期事件**：婚姻、首次生育、二次生育、迁移和就业使用可替换 hazard，并记录事件间隔，而不是只看年度概率。
4. **空间网络**：地区迁移矩阵与家庭社会网络分离；迁移网络决定信息和机会传播，交通与房价决定迁移成本。
5. **验证优先于扩张**：每加入一个机制，都要有历史回放、极端情景、敏感性分析和共同随机数测试。

## 资料与边界

- 联合国人口投影使用 fertility、mortality、migration 假设和 cohort-component 方法：
  https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/files/documents/2024/Jul/undesa_pd_2024_wpp2024_methodology-report_web.pdf
- 家庭政策与社会结构的 agent-based 研究：
  https://www.demographic-research.org/articles/volume/29/37
- FPsim 家庭计划生命历程 ABM：
  https://www.nature.com/articles/s44294-023-00001-z
- World3/系统动力学的交互说明：
  https://limits.world/
- Civilization VI 官方机制介绍及官方手册：
  https://civilization.2k.com/en-GB/civ-vi/
  https://cdn.cloudflare.steamstatic.com/steam/apps/289070/manuals/CIV_VI_25TH_ONLINE_MANUAL_ENG.pdf?t=1663263035

这些资料用于决定机制方向和验证方法，不代表本项目已经完成现实国家校准。
