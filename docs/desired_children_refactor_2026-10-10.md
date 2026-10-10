# 生育社会规范扫描的严格等价重构 · 2026-10-10

本轮继续遵守 feature freeze，没有增加社会机制、政策、国家、职业或 UI。目标是处理 2026-10-09 已定位的现有性能热点：`_desired_children` 为邻居、亲属和同事规范分别扫描家庭，其中邻居和同事重复判断地区关系。

## 1. 重构内容

旧实现按当前 `dict` 顺序完成三次家庭扫描：

1. 同地区且有子女的家庭；
2. 同宗族且有子女的其他家庭；
3. 同地区、有子女、非自身且共享职业的家庭。

新实现只遍历一次 `self.households.values()`，在同一循环中分别追加到三个列表。三个列表各自的顺序、筛选条件、`statistics.fmean` 输入顺序、权重和默认回退值保持不变。它不缓存跨阶段结果：生育阶段和年末汇总之间仍会重新计算，因为期间可能发生出生、迁移和死亡。

## 2. 严格等价门槛

修改前后分别在四国主情景运行20年×3 seed，并每年归档账本和保存完整 `FamilyWorld` fingerprint。基线和候选结果见：

- [`desired_children_fingerprint_baseline_2026-10-10.json`](artifacts/desired_children_fingerprint_baseline_2026-10-10.json)；
- [`desired_children_fingerprint_candidate_2026-10-10.json`](artifacts/desired_children_fingerprint_candidate_2026-10-10.json)；
- [`desired_children_refactor_equivalence_2026-10-10.json`](artifacts/desired_children_refactor_equivalence_2026-10-10.json)。

比较器要求以下字段逐 seed 一致：

- 20个逐年完整世界 fingerprint；
- 期末人口和家庭；
- 累计转移记录；
- legacy RNG 状态 SHA-256。

三个 seed 共60个逐年 fingerprint 全部完全相同。旧 `family_world.py` SHA-256 为 `00669c...13d3`，新实现为 `8b3c34...ec0e`，证明比较的确跨越了源码变化，而不是对同一文件重复运行。

## 3. 性能结果

20年无 profiler 的同日顺序运行没有稳定收益：三个 seed 的候选相对基线运行时间变化约为 `+0.5%`、`+4.3%`、`-1.1%`。因此不能根据短周期 wall-clock 宣称整体加速。

热点主要发生在后25年，所以另用与前日相同的 `cProfile` 口径对 seed `20261007` 运行50年。候选结果见 [`desired_children_candidate_profile_2026-10-10.json`](artifacts/desired_children_candidate_profile_2026-10-10.json)。与旧实现相同 seed 比较：

| 指标 | 旧实现 | 合并扫描 | 变化 |
|---|---:|---:|---:|
| 后25年 `same_region` 调用 | 266,733,589 | 133,391,838 | -50.0% |
| 后25年 `_desired_children` 秒/年 | 3.221 | 3.068 | -4.7% |
| 后25年 `_summaries` 秒/年 | 2.344 | 2.229 | -4.9% |
| 后25年 `_births` 秒/年 | 0.935 | 0.905 | -3.2% |
| 后25年总 step 秒/年 | 3.508 | 3.385 | -3.5% |
| 前25年总 step 秒/年 | 1.643 | 1.652 | +0.5% |

结论是：重构确定性地删除了半数地区关系重复调用，在家庭较多的后半程观察到小幅改善，但不是数量级优化，也没有稳定改善短周期总时间。绝对秒数依赖机器和当时负载。

## 4. 测试与解释边界

新增测试明确要求单次 `_desired_children` 中 `same_region` 和 `same_kin` 均只调用“当前家庭数”次。完整回归继续检查人口、地区流量、checkpoint、归档账本、网页和 API。

这次重构只改变计算方式，不改变生育规范机制。严格 fingerprint 相同支持“实现等价”，但不提高历史预测准确率，不识别参数，也不支持因果政策解释。

## 5. 外部数据状态

[`frozen_data_gates_2026-10-10.json`](artifacts/frozen_data_gates_2026-10-10.json) 与前一日字节级相同：托育主 exposure 仍不完整，WONDER 仍为1/48，ACS 暴露仍只有 `all` parity。正式年龄—婚姻—孩次 hazard、托育主规格和因果反事实继续冻结。

下一步若继续做性能工作，应先考虑建立年度社会规范索引或只优化年末统计，但任何方案仍必须通过相同的逐年 fingerprint 门槛；不能以“结果近似”为理由改变模型语义。
