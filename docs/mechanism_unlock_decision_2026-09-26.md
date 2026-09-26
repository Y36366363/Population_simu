# 高风险机制解锁审查 · 2026-09-26

## 结论

今天不解锁以下四项：

1. LLM 自主决定生育、婚姻或迁移；
2. 自动进化 agent 规则；
3. 正式年龄—婚姻—孩次 hazard；
4. 为改善测试期拟合而强行 alignment。

这不是永久否决，而是因为它们目前会改变 estimand、增加不可识别随机性，或
掩盖 untouched test 的真实误差。

## 分项判断

| 机制 | 当前状态 | 解锁前必须完成 | 解锁后的安全实施 |
| --- | --- | --- | --- |
| LLM 自主决策 | 暂缓 | 明确行为变量、可重复提示/模型版本、人工基线、无 LLM 对照、成本和失败率报告 | 只做 scenario authoring 或解释层；核心 hazard 仍由固定参数模块执行 |
| 自动进化 agent | 暂缓 | 预注册变异规则、停止条件、版本化状态迁移、固定种子可复现、历史 holdout 不参与进化 | 仅在独立探索分支运行，不进入主结果或校准期 |
| 年龄—婚姻—孩次 hazard | blocked | 48 个 WONDER 批次完成；州—年—年龄—婚姻—孩次键审计；匹配女性暴露分母；独立 calibration/test | 先估计首胎/递进 hazard，再与 aggregate ASFR 对账；不得用 NSFG 全国数据冒充州级分母 |
| alignment | 仅可作为预注册校准工具 | 目标总量来源、调整层级、被调整变量、未调整对照、调整量上限和测试期隔离 | 只在 calibration 或独立 benchmark 中使用；不得用测试期目标反向修正预测 |

## 为什么现阶段不应加入 LLM 或自动进化

成熟动态微模拟项目通常强调事件率、年度状态转移、外部控制总量和可重复
校准，而不是让自由生成 agent 改写行为规则。[SimPaths](https://github.com/centreformicrosimulation/SimPaths)
将生命周期模块和人口对齐分开；[rsocsim](https://github.com/MPIDR/rsocsim)
以年龄别事件率和竞争风险推进人口过程。对于验证而言，APPSIM 的经验也表明
需要区分 individual、meso、macro alignment，并分别检查逐年和长期结果。
[APPSIM validation study](https://www.microsimulation.pub/articles/00038)

因此，LLM 目前最多适合作为“场景说明生成器”或网页解释助手，不能成为生育
或迁移概率的隐式来源。自动进化也只能在独立探索分支中测试，否则无法判断
性能变化来自机制、提示词、随机种子还是训练状态。

## 当前实际闸门状态

- 主住房面板：550 行、50 州、2010–2019 与 2021；2020 仅敏感性年份。
- 托育：0/550 个可审计州—年 exposure，继续 blocked。
- WONDER：1/48 批次成功，47 批待完成。
- 当前允许：住房主规格 rolling-origin、aggregate ASFR 模型比较、网页/API 回归。

## 最小解锁顺序

1. 先完成现有四类模型和 untouched test 报告，不添加新机制。
2. 完成 48 批出生分子与匹配暴露分母的严格键审计。
3. 在独立分支估计正式 hazard，并与 cohort-component 总量逐年对账。
4. 只有在上述结果稳定后，才做预注册 alignment 敏感性分析。
5. LLM/自动进化最后单独做 sandbox，不进入主研究结果。
