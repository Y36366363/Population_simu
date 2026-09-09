# 项目级状态与下一步（2026-09-08）

当前项目处于 Feature Freeze：后续只推进数据验证、模型比较、审计和部署，不新增社会机制。

## 已可用

- GitHub Pages 静态机制网页；
- 本地 Python 家庭引擎与只读 API；
- ACS 州—年住房与女性分母面板；
- 总 ASFR 四模型 rolling-origin、CRPS、coverage、RMSE/MAPE；
- household / no-housing / no-household 机制诊断；
- 114 个自动化测试。

## 当前阻塞

- WONDER 2010—2017 的 48 个年龄×婚姻×孩次批次尚未齐全；
- 2018—2021 独立 test 出生分子尚未齐全；
- 因此正式分层 hazard 校准和分层历史回放仍不能宣称完成。

## 下一步顺序

1. 继续维护静态网页和本地 API 的回归测试；
2. 保存版本化模型结果 JSON，网页只读取这些 artifact；
3. WONDER 解冻后先做字段/总量审计，再做分层校准；
4. 重新运行 household 消融，并分别报告预测误差与机制差异；
5. 最后才把正式历史回放结果接入网页。

当前 aggregate-ASFR 结果已登记在 `data/observed/us_2021/model_artifacts_manifest_2026-09-09.json`；
它明确标记为 validated，但不代表年龄—婚姻—孩次 hazard 已完成。
