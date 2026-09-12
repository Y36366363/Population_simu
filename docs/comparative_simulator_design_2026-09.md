# 横向比较与展示设计（2026-09）

## 参考范式

| 范式 | 核心优点 | 对本项目的可借鉴点 | 不应直接复制的部分 |
|---|---|---|---|
| UN World Population Prospects | 以生育、死亡、迁移假设构造多个情景，并报告预测区间 | 把“假设”与“结果”分离；每个情景显示 calibration/prediction 边界和不确定性 | 不能把家庭机制模型伪装成官方人口预测 |
| Our World in Data Population Simulator | 只控制少量高解释度变量：生育率、寿命、迁移率 | 首页用少量核心滑杆快速回答“如果改变 X 会怎样” | 不足以展示家庭分支、住房和代际传递 |
| UrbanSim | 家庭、企业、住房和空间位置的年度微观模拟；强调校准、验证和政策比较 | 将家庭迁移放进住房/机会约束；输出空间分布和政策差异 | 项目范围远大于当前人口研究，不宜一次性加入完整房地产市场 |
| GAMA | 可视化 agent、参数实验、批量实验和空间交互 | 为每个实验保存参数、种子、版本和输出，支持重复实验 | 不需要引入新的 GAMA 运行时 |
| PopSim | 用公开聚合统计生成半合成个体，用于资源分配实验 | 明确区分真实观测、半合成个体和纯合成 smoke fixture | 半合成个体不能被当作真实家庭轨迹 |

来源：[UN WPP](https://population.un.org/wpp/)、[OWID Population Simulator](https://ourworldindata.org/population-simulation-tool)、[UrbanSim 文档](https://cloud.urbansim.com/docs/general/documentation/urbansim.html)、[GAMA](https://gama-platform.org/wiki/next/Home)、[PopSim 论文](https://arxiv.org/abs/2305.02204)。

## 本项目应采用的三层网页结构

### 1. 情景层：控制“想试什么”

只保留高解释度控制项，并按类别分组：

- 人口：生育、死亡、迁移；
- 家庭约束：住房负担、托育、祖辈照护；
- 地区：工资/机会、承载力、城乡迁移；
- 制度：教育、福利、住房政策。

每次运行固定保存 `scenario_id`、随机种子、参数 JSON、代码版本和数据版本。

### 2. 机制层：解释“为什么变”

每个结果卡片都应同时显示：

- 直接结果：人口、家庭数、迁移、出生；
- 中间机制：住房压力、照护缺口、公共服务、财政压力；
- 分布结果：地区、城乡、资源分位数、家庭分支存续；
- 消融对照：full、no-housing、no-household。

这比只显示一条人口曲线更适合本项目的研究问题。

### 3. 证据层：说明“能不能相信”

每个面板必须标记数据状态：

```text
observed：真实观测
calibrated：仅使用 calibration 估计
prediction：untouched test 预测
mechanism：机制解释，不是因果估计
synthetic_smoke：仅用于代码流程测试
blocked：数据不足，不显示正式结论
```

## 与当前项目的差距

当前网页已经具备参数滑杆、世界时间线、家庭子实验和本地 Python 接口；主要缺口不是
更多机制，而是：

1. 缺少场景保存/复现卡片；
2. 缺少 full 与消融的并排结果卡；
3. 缺少预测区间和数据状态标签；
4. 浏览器演示结果与本地 Python 结果需要更明显地区分；
5. 正式历史回放 artifact 尚未完成，不能放入“现实预测”面板。

## 推荐开发顺序

1. 先做情景 JSON 导出和结果 artifact 标签；
2. 再做 full/no-housing/no-household 并排图；
3. 加入中位数和区间，而不是只显示一次随机路径；
4. WONDER/NCHS 分层出生数据完成后，才加入年龄—婚姻—孩次面板；
5. 最后接入正式历史回放和外部观测对照。

核心原则：网页是“可控实验台 + 证据标签”，不是把所有机制堆成一个看似精确的预测游戏。

当前网页已加入情景保存/载入/导出：保存到浏览器的情景可一键恢复，导出的 JSON 也可
通过“载入情景”重新读取。导出的 `result` 是当前浏览器演示路径，仍标记为机制演示，
不会与正式观测 artifact 混用。

网页现已支持 20 次固定种子扰动的 10%—90% 区间、年度时间线播放、逐帧 PNG 导出和
独立 HTML 分享回放。批量 PNG 是浏览器下载队列，若浏览器阻止多文件下载，需要允许
该站点的多次下载；这些帧仍是浏览器机制演示，不是正式实证回放。

Python 三变体 artifact 可由 `scripts/export_household_variants.py` 生成并放入
`docs/artifacts/`；网页点击“加载已验证 JSON”后绘制 full、no-housing、no-household
的同一 ASFR 时间线。GIF/MP4 只在本地生成：

```bash
python3 scripts/render_frames.py frames --output replay.gif
python3 scripts/render_frames.py frames --output replay.mp4
```

需要 GIF 的 Pillow 或 MP4 的 ffmpeg；生成的视频不提交到仓库，避免把大二进制文件混入
研究 artifact。

## 对“AI 自动生成历史动态图/视频”类项目的借鉴

这类项目的强项通常不在于比人口模型更真实，而在于把一组有时间顺序的状态自动转成
可观看的叙事：准备结构化时间线、绘制每个时点的地图/排名/曲线、加入标题和旁白，最后
渲染成视频。它与本项目可以共用同一套版本化结果 artifact，但不能把视频表现力当成
模型证据。

本项目可以形成两种展示出口：

1. **交互沙盘**：用户拖动变量，立即比较 full、消融和不同情景；
2. **自动回放**：给定固定 seed、情景 JSON 和已验证结果，生成“每 5 年一帧”的人口、
   家庭分支、迁移流向和财政状态回放，之后再转成 GIF/MP4 或网页动画。

建议先实现 JSON/PNG 帧序列，而不是直接引入视频生成模型。这样每一帧都可以追溯到：
`scenario_id → seed → model_version → data_artifact → year`。视频只是这些帧的展示层。

因此，三国历史动态图项目可以借鉴“时间线叙事、自动配图、批量渲染、投稿素材”的
工作流；本项目必须额外保留 calibration/test 标签、区间和机制消融，避免漂亮动画
掩盖数据缺口。
