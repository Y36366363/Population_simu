# 成家候选年龄窗口索引与严格等价验证 · 2026-10-14

本轮继续遵守 feature freeze：没有增加社会机制、政策、国家、职业、UI 或 agent complexity。目标是处理 2026-10-13 识别出的成家匹配热点，但把候选顺序、权重顺序、随机调用次数和逐年完整状态不变设为硬约束。

## 1. 风险边界与修改前基线

`_form_family_branches` 会先分别打乱男女候选，然后按女性顺序构造兼容男性列表、按该列表顺序计算权重、调用 `rng.choices`，最后再调用一次成家 hazard 随机数。任何排序、集合化、近似最近邻或提前随机抽样都会改变轨迹。

因此本轮先保存修改前的三 seed、50 年 profile：[`matching_baseline_multiseed_profile_2026-10-14.json`](artifacts/matching_baseline_multiseed_profile_2026-10-14.json)。修改前 `family_world.py` SHA-256 为 `c92f14569914a492029ea865463fa35e4b3ca66fc0f43a46ed1169bce1c3eaa8`。

## 2. 严格等价的年龄窗口索引

新实现对每个国家已经打乱的男性序列建立女性年龄 22—50 岁的候选元组，只预先排除绝不可能满足的 `abs(man.age - woman.age) > 9`。元组保留原全局男性顺序；每位女性仍按原顺序过滤：

- 男性尚未配对；
- 不在同一家庭；
- 不共享已知母亲或父亲。

成功成家后，男性的 `partnered` 状态在原有位置立即设为真。旧实现同时从列表删除该男性；新实现不再做线性删除，而由下一次过滤排除。失败的 hazard 不改变其状态。由此得到与旧“剩余男性列表”完全相同的活动候选序列，权重顺序和随机调用保持不变。

单元测试 `test_age_window_index_preserves_active_male_candidate_order` 逐位比较旧全扫描与新索引在连续移除候选后的完整 ID 顺序。profile 比较器另外要求每个国家每年恰好构建一次窗口索引；当前四国情景的每个 25 年分段均记录 100 次构建。

## 3. 完整 fingerprint 验收

候选 fingerprint 为 [`marriage_age_window_fingerprint_candidate_2026-10-14.json`](artifacts/marriage_age_window_fingerprint_candidate_2026-10-14.json)，严格比较为 [`marriage_age_window_equivalence_2026-10-14.json`](artifacts/marriage_age_window_equivalence_2026-10-14.json)。候选 `family_world.py` SHA-256 为 `48786db8d46fcc6b7048dc3b2fb43857a57c52f0c73e9b67a33ab8eb6a48dfc9`，确认比较跨越了真实源码变化。

三个 seed（`20261006`、`20261007`、`20261008`）各运行30年，共90个逐年完整世界 fingerprint 全部一致，同时满足：

- 期末人口完全一致；
- 期末家庭数完全一致；
- 转移账本记录数完全一致；
- RNG 状态 SHA-256 完全一致。

这是本轮接受代码修改的主要证据。artifact 中跨日普通计时受机器负载影响，不作为性能结论或验收门槛。

## 4. 同日多 seed 性能结果

候选 profile 为 [`marriage_age_window_multiseed_profile_2026-10-14.json`](artifacts/marriage_age_window_multiseed_profile_2026-10-14.json)，结构与计时比较为 [`marriage_age_window_profile_comparison_2026-10-14.json`](artifacts/marriage_age_window_profile_comparison_2026-10-14.json)。它与修改前 profile 使用相同情景、三个 seed、50 年、25 年分段和 cProfile 口径。

| 同日 cProfile 指标 | 前25年候选/基线中位比 | 后25年候选/基线中位比 |
|---|---:|---:|
| `_form_family_branches` 秒/年 | 0.847 | 0.874 |
| 总 step 秒/年 | 0.953 | 0.960 |

成家阶段的中位改善约为前25年15.3%、后25年12.6%；后25年三个 seed 均改善。总 step 的中位改善约为4.7%和4.0%。候选实现的后半程/前半程 step 比为 `1.363`，基线为 `1.385`，长期增长形状仅小幅改善。所有计时都是本机诊断，不是正确性门槛，也不证明成家行为符合现实观测。

## 5. 回归、数据边界与下一步

- 完整 Python：211 项测试通过；
- 静态网页、本地 API 冒烟和浏览器回归：通过；
- data provenance：53 个观测文件通过；
- [`frozen_data_gates_2026-10-14.json`](artifacts/frozen_data_gates_2026-10-14.json) 与 10 月 13 日字节级相同。

WONDER 仍为 `1/48`，ACS 暴露仍只有 `all` parity，托育主 exposure 仍未解锁。因此今天提高的是内部模拟可扩展性与可审计性，不提高历史预测、正式年龄—婚姻—孩次 hazard 或因果反事实的证据等级。

成家匹配的安全优化空间已明显缩小。后续不得把候选列表改为集合、按分数重排或使用近似最近邻；若继续研究匹配性能，应先做只读诊断，量化年龄窗口之后同户/近亲过滤和权重计算各自成本。任何候选仍须从修改前源码建立基线，并通过多 seed、逐年完整 fingerprint 和 RNG 状态完全一致的门槛。若取得新的外部历史数据，应优先恢复历史验证，而不是继续内部扩张。
