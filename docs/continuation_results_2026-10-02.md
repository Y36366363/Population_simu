# 延续测试与实际修改 · 2026-10-02

## 本轮结论

原研究方向继续保留，但旧rolling结果存在切分、时间尺度、信息集和RMSE口径问题。本轮纠正后，阻尼趋势proxy表现优于家庭适配器，家庭适配器的多年预测和区间稳定性应成为下一项focus。详细平台目标见[全局审计与路线](project_direction_and_audit_2026-10-02.md)。

## 软件和数据检查

| 检查 | 实际结果 |
|---|---|
| 修改前完整Python测试 | 120通过，10.299秒 |
| 修改后完整Python测试 | 134通过，10.966秒 |
| 新浏览器VM回归 | 3组通过：逐帧导出、完成参数与区间、Python CSV |
| JavaScript语法 | `node --check docs/app.js`通过 |
| 静态资源 | 通过；包含新审计报告链接 |
| 主面板 | 550行、50州、2010—2019及2021、键唯一 |
| 固定模型复现输入 | 严格核验完整550州年笛卡尔键、有限且非负结果；拒绝等行数重复替换 |
| 托育/孩次门槛 | 仍未通过：托育0/550，WONDER1/48，ACS仅all-parity |

本轮新增14项Python测试，针对母系继承、末尾窗口和缺年跨度、RMSE、未来信息使用、基线实验参数/复现/统计口径、残差输入严格键及测试结果扰动不影响拟合。测试通过代表这些软件契约成立，不代表模型已获得现实效度。

浏览器检查通过抽取真实函数进入Node VM并模拟DOM/下载环境完成；未运行真实浏览器端到端下载，未部署。CI配置已扩展，云端CI须在之后提交触发时验证，不能把本地测试等同于云端已运行。

## 修复后的六模型滚动回测

输入仍是冻结的可比住房面板；initial=8、每模型每折20次模拟、1000次bootstrap、80%预测区间，开启原有残差层。不使用外部校准或目标年真实住房。

| 折 | 训练年份 | 目标年 | 实际跨度 | 目标州年数 |
|---|---|---:|---:|---:|
| 1 | 2010—2017 | 2018 | 1年 | 50 |
| 2 | 2010—2018 | 2019 | 1年 | 50 |
| 3 | 2010—2019 | 2021 | 2年 | 50 |

这是expanding-window；2018、2019依次进入后续训练，**不是固定2017起点的留出实验**。本轮不再把多个initial的重叠年份混成更多独立证据。

| 模型 | MAPE | pooled RMSE | CRPS | 80%覆盖率 | 平均区间宽度 |
|---|---:|---:|---:|---:|---:|
| naive trend | 1.835% | 1.528 | 0.815 | 58.67% | 2.003 |
| cohort proxy（阻尼趋势） | 1.560% | 1.110 | 0.676 | 53.33% | 2.040 |
| reduced-form | 2.934% | 2.245 | 1.383 | 38.00% | 2.043 |
| household full | 6.529% | 5.530 | 2.832 | 59.33% | 19.441 |
| household no-housing | 6.129% | 5.151 | 2.762 | 58.00% | 18.560 |
| household no-household | 1.874% | 1.548 | 0.818 | 61.33% | 1.992 |

结果指标是旧字段`asfr_15_44`代表的一般生育率GFR，RMSE/宽度单位是每千名15—44岁女性对应的出生数。MAPE、CRPS和coverage在这三个等样本折间平均；RMSE从全部平方误差和样本数计算。区间bootstrap以整折重抽样，仅3折，不能当强独立确认性证据。

2021折尤其值得关注：naive MAPE=2.75%、proxy=1.90%、household full=15.63%、no-housing=14.49%。household该年覆盖率100%伴随宽区间，并不表示预测好。需要检查1200代理的出生计数噪声、首步归一化、年龄结构演化和分母近似；本轮没有针对该测试年调参。

当前残差层仍只按训练期相邻变化估计尺度，尚未按日历跨度校准；不同模型残差seed不同，因此naive和数学等价的no-household存在抽样差异。不能把微小差异解读为机制优劣。artifact的`error_strata`使用未加残差噪声的runner中位数，而主表使用加噪样本中位数；这两者是不同点预测口径，下一轮应从同一逐键score表派生全部分层汇总。

机器结果：[housing_primary_rolling_origin_2026-10-02_corrected.json](artifacts/housing_primary_rolling_origin_2026-10-02_corrected.json)。旧artifact全部保留；新表不与旧表拼接计算“进步幅度”。

## 固定2017起点的残差模型复现

读取9月30日已经选择的`state_shrunk + normal`，每个州年1000抽样，seed=20348930。仅用2010—2017拟合700个残差（跨度1/2/4分别300/250/150），评估150州年。不重新选择方法，不把已检查过的历史数据称为新测试。

MAPE=3.0726%，RMSE=2.9880，CRPS=1.3496，80%区间coverage=84%，宽度6.0103；五项结果与归档值之差均为0。

| 年份/跨度 | 覆盖率 | CRPS | 宽度 |
|---|---:|---:|---:|
| 2018 / 1年 | 90% | 0.5800 | 3.3107 |
| 2019 / 2年 | 88% | 1.0958 | 5.6989 |
| 2021 / 4年 | 74% | 2.3729 | 9.0214 |

该残差模型和上表的滚动研究有不同训练信息和不确定性方法，不能横向比较84%与58.67%作为算法改进。此前候选选择只验证1年跨度；四年跨度每州仅3个训练残差，仍需要独立多跨度检验设计。

机器结果：[frozen_residual_replication_2026-10-02.json](artifacts/frozen_residual_replication_2026-10-02.json)。包含逐州年score、区间、完整输入及源码hash。

## 与原始目标对应的探索基线

21格×5个seed×1000试验=105,000次初始家庭试验，模型方程未改。资源100时，每孩达到预设成功阈值的比例为一孩43.78%、二孩34.93%、三孩28.57%；家庭至少一人达标为43.78%、57.14%、62.90%。四代存续与环境变化表及解释见全局审计第5节。

这些不是现实家庭结论，也没有覆盖生理存活和真实收入代际流动。它们提供了下一轮正式多目标协议的可重复起点。JSON明确区分seed范围/SD与统计置信区间；初代固定孩数不等于每代固定孩数，同seed不等于事件级严格配对。

机器结果：[family_goal_baseline_2026-10-02.json](artifacts/family_goal_baseline_2026-10-02.json)。

## 具体实现变化

- `calibration.py`：最后一个完整rolling窗口不再被丢弃；horizon明确按共同观测年份计数。
- `benchmarks.py`：趋势/proxy/reduced-form/no-household按真实日历跨度推进；每折/跨折/重抽样的RMSE使用SSE/N。
- `run_frozen_cross_validation.py`：默认仅使用各折训练信息；条件住房回放必须显式启用；保存实际fold设计，拒绝超出早期训练期的外部校准，取消错误的untouched声明。
- `family_world.py`：`maternal`正确继承母方家族；先前错误地落入随机继承。父系和随机规则维持原行为。
- `docs/app.js`：批量PNG逐帧等到完成；重跑清除旧区间；浏览器结果/回放和Python CSV分别使用各自完成运行的参数。
- 三个新Python工具：固定残差延续复现、家庭目标基线、完整配置导出；一个Node浏览器回归工具。
- 主README、早期研究协议和四份旧报告加审计入口/勘误；本轮不发布网页、不提交或推送Git。

## 复现命令

在仓库根目录，Python 3.11+；浏览器检查需要Node.js。

```bash
python3 scripts/run_tests.py
node --check docs/app.js
node scripts/check_browser_regressions.js
python3 scripts/check_static_site.py docs

python3 scripts/export_configuration_inventory.py
python3 scripts/run_daily_smoke.py --output docs/artifacts/daily_smoke_2026-10-02.json
python3 scripts/audit_frozen_data_gates.py --output docs/artifacts/frozen_data_gates_2026-10-02.json

PYTHONPATH=src python3 scripts/run_frozen_cross_validation.py \
  data/observed/us_2021/us_research_panel_2010_2021_comparable.csv \
  --output docs/artifacts/housing_primary_rolling_origin_2026-10-02_corrected.json \
  --initial 8 --replicates 20 --bootstrap-draws 1000 --residual-uncertainty

python3 scripts/continue_frozen_residual_validation.py \
  --output docs/artifacts/frozen_residual_replication_2026-10-02.json
python3 scripts/run_family_goal_baseline.py \
  --output docs/artifacts/family_goal_baseline_2026-10-02.json
```

`daily_smoke`主要验证接口、字段和旧artifact可读性；其`ok=true`不是旧研究结论通过科学审核。数据门槛脚本成功执行也不表示门槛已解锁。
