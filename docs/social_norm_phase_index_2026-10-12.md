# 社会规范阶段索引的严格等价验证 · 2026-10-12

本轮遵守 feature freeze：没有增加社会机制、政策、职业、国家、UI 或 agent complexity。工作只针对 2026-10-11 三 seed profile 仍显示的既有热点，在不改变迭代顺序、概率规则、随机状态和结果的前提下，为年度生育与汇总阶段建立局部社会规范索引。

## 1. 为什么不能直接做年度结果缓存

`_desired_children` 不只是地区或家族平均值。它还读取当年家庭资源、照护缺口、地区服务、承载力和已出生子女数。更重要的是，`_births` 按家庭顺序运行：较早家庭当年新增的孩子会使其进入后续家庭的社会规范样本。因此，下列做法会改变模型语义：

- 跨年度缓存完整生育意愿；
- 在生育循环开始时冻结“已有子女家庭”集合；
- 在出生后继续复用年初的汇总均值；
- 用无序集合替代家庭字典的既有迭代顺序。

## 2. 实现边界

新增 `_SocialNormIndex` 只存在于方法局部变量，不写入 `FamilyWorld`、checkpoint 或持久 artifact。它保存：

- 按 `country × region` 分组、保持原始插入顺序的家庭序列；
- 按 clan 分组、保持原始插入顺序的家庭序列；
- 当前阶段每个家庭的成年成员职业集合。

索引仍包含尚未生育的家庭。`children_ever_born > 0` 在每次 `_desired_children` 调用时动态判断，所以同一 `_births` 循环中刚发生的出生仍会立即影响后续家庭。索引在生育阶段开始前建立一次；迁移、死亡等事件结束后，在 `_summaries` 前重新建立一次。每年正好两次，不跨事件阶段复用。

直接调用 `_desired_children` 时仍保留完整有序扫描，方便单元诊断和非年度调用；年度主路径才使用阶段索引。

## 3. 逐年完整状态等价

在代码修改前后分别运行四国主情景：

- seed：`20261006`、`20261007`、`20261008`；
- 时长：30 年；
- 每年归档转移账本；
- 每年对完整 `FamilyWorld` 对象图、配置、历史和 RNG 状态编码并计算 SHA-256。

机器可读结果：

- [修改前 fingerprint](artifacts/social_norm_index_fingerprint_baseline_2026-10-12.json)；
- [修改后 fingerprint](artifacts/social_norm_index_fingerprint_candidate_2026-10-12.json)；
- [严格比较](artifacts/social_norm_index_equivalence_2026-10-12.json)。

三个 seed 共 90 个逐年完整 fingerprint 全部相同；期末人口、家庭数、转移记录总数和 RNG 状态也全部相同。源码 SHA-256 从 `8b3c34...ec0e` 变为 `e1c51d...219`，确认比较跨越了真实实现变化。

30 年普通 step 计时下降分别为 `71.76%`、`71.35%` 和 `71.21%`，中位数为 `71.35%`。这组计时与 fingerprint 编码分开记录，编码耗时不计入 step；仍然只代表本机同日运行。

## 4. 50 年三 seed phase profile

候选 profile 见 [social_norm_index_multiseed_profile_2026-10-12.json](artifacts/social_norm_index_multiseed_profile_2026-10-12.json)，与 10 月 11 日同配置基线的比较见 [social_norm_index_profile_comparison_2026-10-12.json](artifacts/social_norm_index_profile_comparison_2026-10-12.json)。六个“seed × 前/后 25 年”全部满足：

- 期末人口、家庭数和转移记录完全一致；
- `_desired_children` 调用次数完全一致；
- 每个 25 年段索引恰好建立 50 次；
- 年度主路径中的 `same_region`、`same_kin` 和 `shares_occupation` 成对调用降为零。

| 指标 | 前 25 年 | 后 25 年 |
|---|---:|---:|
| 候选/基线 step 秒/年中位比 | 0.3598 | 0.2839 |
| 对应中位耗时下降 | 64.0% | 71.6% |
| `_summaries` 候选/基线中位比 | 0.2322 | 0.1959 |
| `_births` 候选/基线中位比 | 0.2349 | 0.2075 |
| 索引建立中位秒/年 | 0.0054 | 0.0111 |

重构后，后 25 年/前 25 年 step 秒数中位比由约 `2.15` 降为 `1.71`。这说明索引显著削弱了家庭总数增长带来的二次扫描成本，但没有消除长期增长：`_summaries`、`_births` 之外的资源、职业、成家和人口位置扫描仍随实体数增加。

## 5. 测试与证据边界

专项测试覆盖：

- 逐家庭“直接扫描值 = 索引值”；
- 索引建立后某家庭首次拥有子女，后续查询仍与直接扫描相同；
- 每个正常年度恰好重建两次；
- profile 比较器会拒绝终态漂移、调用次数变化或错误的索引建立次数。

完整结果：`204 tests passed`；浏览器回归、静态站点、本地 API、daily smoke 和 53 个观测数据 provenance 均通过。

[frozen_data_gates_2026-10-12.json](artifacts/frozen_data_gates_2026-10-12.json) 与前一天字节级相同：WONDER 仍为 `1/48`，ACS 暴露仍只有 `all` parity，托育 exposure 仍未满足定义、来源、分母与覆盖要求。正式 hazard、托育主规格和因果政策反事实继续冻结。本轮提高的是计算可扩展性和内部等价证据，不是历史预测准确率或因果可信度。

## 6. 下一步边界

若没有新外部历史数据，下一步不应扩张机制。可以做的内部工作只有：

1. 重新分析索引后剩余的后 25 年热点；
2. 对 `_summaries` 内其他稳定聚合探索同样的阶段局部缓存；
3. 每次候选都继续要求多 seed、逐年完整 fingerprint 完全相同；
4. 任何近似、重排随机调用或改变浮点聚合顺序的优化均不接受。
