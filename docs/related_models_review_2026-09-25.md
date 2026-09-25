# 横向研究与开源项目复核 · 2026-09-25

## 复核对象

- [nismod/microsimulation](https://github.com/nismod/microsimulation)：用配置文件区分静态微合成、动态微模拟和准动态投影。
- [MPIDR/rsocsim](https://github.com/MPIDR/rsocsim)：以月度年龄别率驱动出生、死亡和婚姻等竞争事件，并保存亲属关系。
- [SimPaths](https://github.com/centreformicrosimulation/SimPaths)：把生命周期模块、家庭关系、财政过程和年度人口对齐分层组织。
- [FPOP geospatial dynamic microsimulation](https://www.microsimulation.pub/articles/00102)：强调家庭与个人事件、地理位置和外部人口控制总量的结合。
- [APPSIM validation study](https://www.microsimulation.pub/articles/00038)：区分 individual equation、meso 和 macro alignment，并强调逐年与长期结果都要验证。
- [PolicyEngine calibration targets](https://github.com/PolicyEngine/microcosm-dynamics/blob/master/docs/calibration-targets.md)：使用版本化 target registry，把来源、优先级和不确定性写入校准目标。

## 与本项目的匹配结果

### 现在可以采用

1. **版本化 target registry**：本次新增
   `data/fixtures/calibration_target_registry.json`，只登记当前住房主规格真正可用的
   outcome/exposure；年龄—婚姻—孩次和托育仍是显式 blocked target。
2. **模块级验证边界**：保留 naive、cohort-component proxy、reduced-form 作为短期预测比较；
   household full/no-housing/no-household 继续作为机制诊断。
3. **宏观对账的独立记录**：target registry 只描述外部目标，不把对账调整误写成参数估计。

### 暂不采用

- 把 agent 的自由行为或 LLM 决策引入生育和迁移 hazard。
- 在真实年龄—婚姻—孩次分层分子与暴露分母缺失时进行正式 hazard 校准。
- 用 alignment 强行改善 untouched test 表现；alignment 只能在预先定义的目标和报告中出现。

## 解释

相关研究普遍显示，微观模型的优势在于保存家庭关系和异质性；但若问题只是年龄、性别、地区总量预测，宏观 cohort-component 模型通常更直接。对本项目而言，合理的结构是：

`外部 target registry → 简单预测基准 → household 机制模拟 → 同一 holdout 指标 → 分层误差与消融`。

这条链条能吸收成熟项目的工程优点，同时保持当前研究问题可证伪、可复现、非因果的边界。
