# 生育规范扫描重构的三 seed 长周期验证 · 2026-10-11

本轮继续遵守 feature freeze，不增加社会机制、政策、国家、职业、UI 或 agent complexity。目标是把 2026-10-10 只对一个 seed 做过的 50 年性能剖析扩展为同配置三 seed 对照，并把正确性门槛与机器相关计时明确分离。

## 1. 验证设计

基线是重构前的 [`simulation_phase_profile_2026-10-09.json`](artifacts/simulation_phase_profile_2026-10-09.json)，候选是当前实现的 [`desired_children_multiseed_profile_2026-10-11.json`](artifacts/desired_children_multiseed_profile_2026-10-11.json)。两者均使用：

- `family_major_countries.json` 四国主情景；
- seed `20261006`、`20261007`、`20261008`；
- 50 年模拟，按前 25 年和后 25 年分段；
- 每年归档资源/现金转移账本；
- 同一组 `cProfile` 事件阶段与嵌套诊断口径。

新增的 `scripts/compare_phase_profiles.py` 要求配置和 seed 集合完全相同，并逐个“seed × 时段”检查：

1. 期末人口、家庭数和累计转移记录完全一致；
2. `_desired_children`、`same_kin` 和 `shares_occupation` 调用数完全一致；
3. 合并扫描满足精确关系 `2 × candidate_same_region = baseline_same_region + desired_children_calls`；
4. 计时只报告，不作为正确性验收门槛。

机器可读对照见 [`desired_children_multiseed_comparison_2026-10-11.json`](artifacts/desired_children_multiseed_comparison_2026-10-11.json)。比较器确认两份 profile 之间唯一变化的 `src/` 文件是 `family_world.py`。

## 2. 严格结果

六个“seed × 时段”均通过三项正确性门槛。三 seed 汇总调用量如下：

| 时段 | 旧 `same_region` 调用 | 新调用 | 减少 |
|---|---:|---:|---:|
| 前 25 年 | 334,884,261 | 167,504,060 | 49.9815% |
| 后 25 年 | 794,899,991 | 397,525,092 | 49.9906% |

减少幅度略低于整齐的 50%，是因为旧的同事扫描会先排除自身，再调用 `same_region`；精确等式已逐 seed、逐时段验证，而不是用约数判断。

10 月 10 日另有更强的轨迹证据：三 seed × 20 年共 60 个逐年完整世界 fingerprint、RNG 和账本完全相同。本轮 50 年 profile 的终态相等不能替代逐年 fingerprint，但它把相同实现扩展到了更长时段，并对调用结构做了独立验证。

## 3. 跨 seed 性能结果

候选相对旧实现的 step 秒/年比值如下；小于 1 表示候选更快：

| seed | 前 25 年 | 后 25 年 |
|---:|---:|---:|
| 20261006 | 0.9177 | 0.9219 |
| 20261007 | 0.8794 | 0.8697 |
| 20261008 | 0.9108 | 0.9703 |
| **中位数** | **0.9108** | **0.9219** |

三 seed 中位数对应前半段约 `8.9%`、后半段约 `7.8%` 的 cProfile step 耗时下降。阶段中位比值为：

- 前 25 年：`_summaries` 下降约 `10.6%`，`_births` 下降约 `9.4%`；
- 后 25 年：`_summaries` 下降约 `9.1%`，`_births` 下降约 `7.9%`。

所有 seed 的方向一致，但幅度并不一致，尤其 seed `20261008` 后半段只有约 `3.0%`。因此稳妥结论是：调用复杂度确定下降，在本机三次配对运行中观察到小幅至中等的 cProfile 改善；不能把 `7.8%` 当成跨机器保证，也不能从中推断人口机制更真实。

重构后后 25 年每年 step 仍为前 25 年的中位 `2.153` 倍。增长排名仍由 `_summaries` 和 `_births` 主导，说明这次重构降低了常数成本，但没有改变家庭增长导致的长期复杂度形状。下一次性能工作若开展，应先设计可严格等价的年度索引或汇总缓存，并继续使用完整 fingerprint 门槛；不应为性能引入新的社会机制。

## 4. 外部有效性与门禁

[`frozen_data_gates_2026-10-11.json`](artifacts/frozen_data_gates_2026-10-11.json) 与 10 月 10 日快照字节级相同：

- WONDER 分层出生分子仍为 `1/48` 批；
- ACS 暴露仍只有 `all` parity；
- 托育主 exposure 的定义、来源、分母和全州—年覆盖仍缺失。

因此正式年龄—婚姻—孩次 hazard、托育主规格和因果政策反事实继续冻结。本轮只提高内部实现证据，不提高历史预测或因果证据等级。

## 5. 回归结果与复现

- 全套 Python 测试：`199 passed`；
- profile 对照专项测试：`5 passed`；
- 浏览器回归：`browser_regressions_ok groups=3`；
- 静态网页检查：`static_site_ok assets=6`；
- 观测数据来源与 SHA-256：`data_provenance_check=ok files=53`；
- daily smoke：`ok=true`。

```bash
python scripts/profile_simulation_phases.py scenarios/family_major_countries.json \
  --years 50 --split-after 25 \
  --seeds 20261006 20261007 20261008 \
  --output docs/artifacts/desired_children_multiseed_profile_2026-10-11.json

python scripts/compare_phase_profiles.py \
  docs/artifacts/simulation_phase_profile_2026-10-09.json \
  docs/artifacts/desired_children_multiseed_profile_2026-10-11.json \
  --output docs/artifacts/desired_children_multiseed_comparison_2026-10-11.json
```
