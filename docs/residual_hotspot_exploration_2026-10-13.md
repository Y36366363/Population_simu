# 剩余热点探索与严格等价优化 · 2026-10-13

本轮继续遵守 feature freeze，没有增加社会机制、政策、国家、职业、UI 或 agent complexity。目标是在 2026-10-12 阶段索引之后，重新定位 `_summaries`、资源、职业、成家与人口位置扫描的真实成本，并只保留严格等价且有稳定证据的重构。

## 1. 完整调用图重新归因

在四国主情景、seed `20261007`、50 年且年度归档条件下保存完整 cProfile 调用图。索引优化后的单次运行约有 1.57 亿次函数调用；主要累计时间为：

| 函数/阶段 | 50 年累计时间 | 主要来源 |
|---|---:|---|
| `_desired_children` | 34.34 s | 仍展开地区、家族和职业样本 |
| `_summaries` | 28.09 s | 包含大量生育意愿汇总 |
| `_births` | 13.47 s | 同样调用生育意愿 |
| `_form_family_branches` | 5.96 s | 配对候选与权重 |
| `_earn_resources` | 4.94 s | 家庭成员和职业收入计算 |
| `_population_locations` | 1.44 s | 每年九次人口位置快照 |

更细的调用量显示：`statistics.fmean` 约 50.8 万次、职业集合交集约 1,727 万次、列表追加约 2,785 万次。由此可知，上轮虽然把全世界扫描缩成地区索引，但主路径仍是“每个待评估家庭遍历同地区家庭”，热点尚未真正消失。职业事件自身只有约 0.81 秒，不应因名称直觉而优先改写。

## 2. 接受：精确整数聚合与出生增量更新

阶段索引现保存以下精确聚合：

- 地区内已有子女家庭的 `count` 与 `children_sum`；
- 家族内对应的 `count` 与 `children_sum`；
- 每个地区、每种成年职业签名对应的相交职业家庭 `count` 与 `children_sum`。

子女数是当前模型中的小整数，因此 `children_sum / count` 与原先对整数序列使用 `statistics.fmean` 得到相同浮点结果。亲属和同事规范仍扣除家庭自身。更重要的是，每次实际出生后立即调用 `record_birth`：第一次生育会同时增加 count 和 sum，后续生育只增加 sum。因此年内较早出生对后续家庭的即时反馈没有被冻结。

严格证据：

- [聚合候选 fingerprint](artifacts/social_norm_aggregate_fingerprint_candidate_2026-10-13.json)；
- [与 10 月 12 日索引实现的逐年比较](artifacts/social_norm_aggregate_equivalence_2026-10-13.json)；
- [三 seed、50 年 profile](artifacts/social_norm_aggregate_multiseed_profile_2026-10-13.json)；
- [profile 结构与计时比较](artifacts/social_norm_aggregate_profile_comparison_2026-10-13.json)。

三个 seed × 30 年的 90 个逐年完整 fingerprint、期末人口/家庭、账本和 RNG 全部一致。六个 profile 分段中：

- `_desired_children` 调用次数完全一致；
- 索引建立次数完全一致；
- `record_birth` 调用次数逐段精确等于实际出生数；
- 期末人口、家庭和转移记录完全一致。

相对 10 月 12 日地区索引实现：

| 指标 | 前 25 年中位比 | 后 25 年中位比 |
|---|---:|---:|
| 总 step 秒/年 | 0.972 | 0.721 |
| `_summaries` | 0.557 | 0.366 |
| `_births` | 0.571 | 0.500 |

后25年三个 seed 的总 step 均改善，中位约下降 `27.9%`。前25年系统噪声较明显，中位只下降约 `2.8%`，不能声称所有区间都有同等收益。重构后后半程/前半程的 step 增长比由约 `1.71` 降至 `1.30`。

## 3. 接受：人口位置扫描去除中间列表

`_population_locations` 原先先构造 `living_people` 列表，再构造位置字典；现在直接按相同的 `self.people` 插入顺序过滤存活者并构造字典。它不改变键顺序和输出。

- [最终候选 fingerprint](artifacts/population_locations_fingerprint_candidate_2026-10-13.json)；
- [与聚合候选的严格比较](artifacts/population_locations_equivalence_2026-10-13.json)。

再次运行的 90 个逐年完整 fingerprint 全部一致。含下一节已撤回资源候选的 phase profile 中，人口位置阶段前后半段的三-seed 中位比为 `0.782` 和 `0.854`；最终 5,818 人世界上的交替顺序微基准中，新方法单次中位比约为 `0.647`。这些都是机器相关性能诊断，不是模型有效性证据。

## 4. 拒绝：收入资源成员扫描合并

曾尝试在 `_earn_resources` 中先构造一次存活成员列表，再由其派生劳动者、退休者、幼儿数和家庭人口。逻辑与 fingerprint 均保持一致，但 profile 证据不足：

- 前25年 `_earn_resources` 三-seed 中位比约 `0.973`；
- 后25年中位比约 `1.019`，没有改善；
- 总 step 后25年中位比约 `1.026`。

因此该改动已从最终代码撤回。探索 artifact 保留用于审计：

- [被拒候选 fingerprint](artifacts/residual_scan_fingerprint_candidate_2026-10-13.json)；
- [被拒候选等价检查](artifacts/residual_scan_equivalence_2026-10-13.json)；
- [被拒候选 profile](artifacts/residual_scan_multiseed_profile_2026-10-13.json)；
- [被拒候选 profile 比较](artifacts/residual_scan_profile_comparison_2026-10-13.json)。

严格等价是保留候选的必要条件，不是充分条件；没有稳定收益的复杂化不应进入主实现。

## 5. 新的剩余热点与下一步

聚合优化后，后25年阶段份额不再由单一平方扫描支配。三个 seed 中主要阶段大致为：

- `_summaries`：约 23%–24%；
- `_form_family_branches`：约 14%–15%；
- `_births`：约 14%；
- `_earn_resources`：约 14%；
- 死亡、资源分配、健康、财政和地区快照各约 3%–4%。

这意味着继续优化的收益上限已明显分散。下一步若没有外部历史数据，最值得研究的是成家匹配候选索引，但该阶段包含 shuffle、`rng.choices`、候选顺序与权重顺序，风险高于本轮整数聚合。任何方案必须保持候选列表顺序、随机调用次数和权重顺序，并先生成修改前 fingerprint；不能为了速度使用近似最近邻或改变配对机制。

## 6. 回归与外部证据边界

- 完整 Python：`207 tests passed`；
- 浏览器回归：通过；
- 静态网页与本地 API：通过；
- data provenance：53 个观测文件通过；
- [10 月 13 日数据门禁](artifacts/frozen_data_gates_2026-10-13.json)与前一天字节级相同。

WONDER 仍为 `1/48`，ACS 暴露仍只有 `all` parity，托育主 exposure 仍未解锁。因此今天提高的是内部模拟可扩展性与实现审计能力，不提高历史预测、正式 hazard 或因果反事实的证据等级。
