# 网页情景与 aggregate ASFR 机制验证（2026-09-16）

本轮在 Feature Freeze 下暂不处理剩余 47 个 WONDER 批次，专门验证当前可运行部分。

## 网页回归

- 世界流动沙盘：默认 60 年、900 个初始家庭，运行完成；
- 时间线不确定性：20 次固定种子运行，成功显示 10–90% 区间；
- `full / no_housing / no_household` 版本化 JSON：成功加载；
- 家庭资源子命题：一孩、二孩、三孩曲线和资源分配图均正常；
- 未发现浏览器控制台错误。

## Aggregate ASFR 消融

使用 2010–2017 calibration、2018/2019/2021 untouched test 的 50 州面板，
对 150 个州—年测试单元进行独立比较：

| 版本 | 测试 MAPE |
|---|---:|
| full | 4.77% |
| no-housing | 4.51% |
| no-household | 2.49% |

`no-household` 误差更低，说明当前家庭机制适配器更适合做机制解释，而不是短期预测器。
`full` 与 `no-housing` 的差异只能解释为当前模型中住房通道的预测敏感性，不能解释为住房政策的因果效应。

## 边界

- WONDER 当前仍为 1/48 成功批次；
- 年龄—婚姻—孩次 hazard 尚未正式识别；
- aggregate ASFR 结果不进入正式因果反事实；
- 2020 ACS5 仅作为敏感性路径，不改变主测试期。

可复现检查：

```bash
PYTHONPATH=src python3 scripts/run_daily_smoke.py --root . \
  --output data/observed/us_2021/daily_smoke_YYYY-MM-DD.json
PYTHONPATH=src python3 scripts/audit_household_adapter.py \
  data/observed/us_2021/us_research_panel_2010_2021_comparable.csv \
  --output data/observed/us_2021/household_adapter_audit_YYYY-MM-DD.json
```
