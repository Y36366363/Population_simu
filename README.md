# 家庭—姓氏家族人口流动与社会晋升模拟沙盘

这是一个以家庭为最小行动单位的无战争世界人口流动与发展沙盘。家庭会形成新分支、积累或损失多维资本，并随工资、住房、教育、福利、婚姻和照护条件在地区与国家之间迁徙；这些微观选择共同改变地区人口、阶层结构和家族延续。

项目的主问题是“家庭如何流动，以及长期累积后世界怎样变化”。一孩、二孩、三孩与资源集中只是其中一个可单独开启的家庭层子实验，不代表整个项目的中心。

交互式网页沙盘（将 `docs/` 设为 GitHub Pages 来源后）：

https://Y36366363.github.io/Population_simu/

> 当前网页版本：世界家庭流动沙盘已作为首页主视角；一孩、二孩、三孩资源配置仍可从顶部“子命题：家庭资源”进入。网页使用固定随机种子，适合比较参数变化，不应被解读为现实国家预测。

## 当前版本定位

当前版本是“机制实验型”的家庭人口微观仿真，不是经过国家数据校准的人口预测器。Python 引擎负责详细年度家庭、个人、职业、婚姻、健康、照护、住房、迁移和政策事件；网页浏览器模型负责快速交互，启动本地应用后可以直接读取 Python 年度结果。

项目当前优先研究：家庭如何在生育数量、子女投资、迁移和代际资本传递之间做选择，以及这些选择如何累积成家族延续、地区分化和阶层流动。一孩/二孩/三孩是其中一个子命题，不是全项目的结论。

## 家庭世界沙盘

- 每个国家从若干姓氏家族开始；中国示例使用 300 个初始姓氏。
- 每个姓氏最初只有一个创始家庭，成年子女结成伴侣后会创建新的家庭分支。
- 姓氏继承现在使用简化的父系规则，可在情景中改为随机继承；女性仍保留自己的出生家族身份。
- 家庭总资源的一部分投入未成年子女，并按子女人数摊薄。
- 家庭资源已拆为九维：金融、人力、社会关系、政治关系、文化、住房、健康、照护时间和债务。
- 子代成年阶层由先天潜力、累计投入、国家教育条件、父母阶层和随机运气共同决定。
- 成年职业包含政治/公共权力、医疗、专业、企业、公共服务、技术、常规劳动与高风险不稳定劳动；父母职业通过知识、执照准备、社会网络和准入壁垒提高同类职业概率。
- 职业生涯进一步区分公务员、政治任期与派系、国企管理/职工、医学培训与执照、失业和再就业；高风险职业可能发生工伤并产生未被补偿覆盖的家庭债务。
- 房地产与现金分开记账，可发生首付支持、房价变化、遗产税和多子女分割；住房所在的资源环境会影响可获得的公共学校质量。
- 婚恋匹配同时考虑教育、收入、住房、职业与派系网络，并允许分别调整同类婚配和精英婚恋封闭程度。
- “成家—繁衍死线”由发展程度、住房压力、养育成本、福利托底和政策支持动态生成；死线以下并非绝对不能生育，而是成家及生育实现率快速下降。
- 经济周期由周期波动和随机冲击组成，同时作用于工资、失业、家庭债务、离婚和城乡迁移。
- 婚姻支持离婚、财产分割、子女监护、丧偶和再婚；同类婚配仍受阶层、教育、住房和派系关系影响。
- 性别参数包括劳动参与、工资差距、母职职业中断和家庭对子女性别不同的投入倾向。
- 每个国家可配置任意数量的城市/乡村地区；家庭按工资、就业、教育、住房成本和衰退压力迁移。
- 地区还可配置 `amenity_supply`：它是教育、托育、公共空间和基础服务的综合供给，会以小权重影响迁移吸引力，并在照护缺口较大时放大生育压力；这是借鉴 4X 游戏可读性的机制抽象，不是现实幸福指数。
- 地区公共服务已可拆为 `school_supply`、`childcare_supply`、`medical_supply`、`transport_access` 和 `safety_level` 五个维度；旧的 `amenity_supply` 仍保留，并与五维平均值共同形成兼容的 `service_index`。
- 地区环境参数包括 `historical_hazard_rate`（历史灾害频率）、`population_exposure`（人口暴露度）和 `recovery_cost`（资源恢复成本）。
- 年度结果新增税收、教育/医疗/养老公共支出、财政结余、地区承载力压力、技术指数、自动化占比和劳动短缺压力。
- 当前快照新增国家—性别—年龄人口矩阵；`FamilyWorld.audit()` 会检查年龄矩阵、国家—地区人口和家庭明细是否闭合。
- 财政现在维护政府基金余额，并记录年度赤字和地区间转移支付，而不只输出一次性收支差额。
- 婚姻、出生、迁移和离婚使用 hazard→年度事件概率转换；家庭分支记录出生间隔和迁移间隔。
- 地区迁移网络和家庭社会网络分别由 `RegionMigrationNetwork` 与 `FamilySocialNetwork` 管理。
- `calibration` 提供按年份/实体分组的历史回放、加权目标函数、可复现网格搜索和随机搜索；它只搜索参数，不把拟合优度误当成政策因果效果。
- `temporal_split()` 和 `evaluate_parameters()` 支持按时间留出验证期；校准参数应只在训练期搜索，再在未来年份报告外推误差。
- `rolling_origin_splits()` 提供 expanding-window 滚动回测，`leave_one_group_out()` 提供跨国家留一验证；Monte Carlo 结果还可用 `interval_metrics()` 检查区间覆盖率和平均宽度。
- `empirical_crps()`/`crps_metrics()` 用多次 Monte Carlo 样本评估概率预测；`stratified_interval_metrics()` 可按国家等维度分层检查覆盖率。
- `benchmarks.compare_models()` 提供统一的模型横向比较接口，仓库内附有透明的固定趋势和阻尼趋势（WPP 风格占位）基准；完整家庭微观模型和年龄—性别 cohort-component 模型可通过 runner 接入。
- `benchmarks.compare_models_rolling()` 用多个 expanding-window 折叠汇总 MAPE、RMSE、CRPS，并用 bootstrap 给出 95% 区间；还可报告相对朴素基准的逐折胜率和误差差值区间。
- 比较器现在要求每个模型完整覆盖测试期的实体—年份键；同时输出 `n_folds`、相对基准改善率和缺失预测错误，避免模型因只预测“容易的国家/年份”而虚假得分。
- 生育社会规范可通过 `social_norm_sources` 拆分为邻居、亲属、同事和媒体四类来源；目前是可解释的网络近似，不是完整社交图。
- 健康不再只是静态分数：慢性病和失能会产生医疗自付、债务与家庭照护负担，并降低劳动收入及生育实现率；医疗可及性和公共长期照护可以缓冲冲击。
- 退休成员按国家养老金替代率获得收入，退休年龄、老年抚养比和灾难性医疗支出均可观察。
- 正式托育和祖辈照护共同形成家庭的年度托育覆盖；祖辈照护受亲属关系、距离、健康和退休状态约束，并消耗提供者的照护时间。
- 子女投资可在“按早期表现追投”和“补偿健康/表现弱势”之间连续调节；输出多子女家庭内部的投资集中度。
- 极贫、中产、富裕家庭使用不同的生育意愿函数：贫困有数量保险倾向，中产受教育与养育成本抑制，富裕家庭允许生育意愿回升。
- 中国政策按 1971、1980、2016、2021 四个阶段切换；其他国家目前是用于对照的简化路径。

运行主要国家时间线：

```bash
PYTHONPATH=src python3 -m population_simu.family_cli \
  scenarios/family_major_countries.json \
  --output outputs/family_major_countries.csv
```

运行家庭引擎的一孩/二孩/三孩情景：

```bash
PYTHONPATH=src python3 -m population_simu.family_cli \
  scenarios/resource_allocation_experiment.json \
  --output outputs/resource_allocation_experiment.csv
```

运行固定资源的微观 Monte Carlo 实验：

```bash
PYTHONPATH=src python3 -m population_simu.resource_experiment \
  --resources 5 100 300 --children 1 2 3 --trials 20000
```

微观实验同时报告两种不同目标：

- `per_child_success_rate`：随机挑一个孩子成功的概率，通常会随资源集中而提高。
- `family_any_success_rate`：一家至少出现一个成功孩子的概率，可能因“多抽几次潜力彩票”而提高。

这两个指标不能混为一谈，也是“一孩是否更好”没有单一答案的核心原因。

运行四代家族延续和动态死线实验：

```bash
PYTHONPATH=src python3 -m population_simu.dynasty_experiment \
  --resources 100 --children 1 2 3 --generations 4 --trials 10000 \
  --material-deadline 58 --housing-pressure 0.75 --welfare-floor 0.08
```

运行制度开关实验：

```bash
PYTHONPATH=src python3 -m population_simu.institution_experiment \
  --resources 100 --children 1 2 3 --generations 4 --trials 5000 \
  --output outputs/institution_switch_experiment.csv
```

制度实验分别只打开公共教育、住房改革、反裙带或高福利，并和基线使用相同随机种子。输出比较四代存续率、末代后代数量和职业同类继承率。

运行共同随机数 Monte Carlo 情景比较：

```bash
PYTHONPATH=src python3 -m population_simu.family_monte_carlo \
  scenarios/family_major_countries.json \
  --years 30 --replicates 20 \
  --output outputs/family_monte_carlo.csv
```

输出包含每个情景/国家/指标的均值、中位数、标准差和 95% 区间。多个情景使用同一组随机种子，适合比较政策差异而不是把随机噪声误当成政策效果。

运行环境冲击单因素敏感性分析：

```bash
PYTHONPATH=src python3 -m population_simu.environment_experiment \
  scenarios/family_major_countries.json \
  --years 30 --replicates 20 --probabilities 0 0.01 0.03 0.06 \
  --output outputs/environment_sensitivity.csv
```

环境事件使用独立随机流；改变灾害概率、历史频率、暴露度或恢复成本时，共同随机数仍保持家庭、经济周期和其他人口事件的抽样一致。

也可以把福利托底提高、住房压力降低，观察资源分散何时重新获得优势：

```bash
PYTHONPATH=src python3 -m population_simu.dynasty_experiment \
  --resources 100 --children 1 2 3 --generations 4 \
  --material-deadline 20 --housing-pressure 0.2 --welfare-floor 0.45
```

## 已有模型

- **个人**：年龄、性别、教育、收入层级、伴侣状态、父母关系。
- **家庭**：成员、所在地区、累计子女数、迁移次数。
- **地区**：工资、住房成本、教育可及性、发展机会。
- **年度事件**：年龄增长、教育升学、收入升降、配对成家、生育、举家迁移、死亡。
- **可替换人口机制**：年龄率表、logit hazard、迁移 softmax、地区迁移矩阵和社会规范强度。
- **政策旋钮**：生育倍率、托育支持、迁移开放、教育投入、向上流动机会、住房改革、反裙带和福利托底。
- **结果指标**：总人口、出生/死亡/迁移、年龄结构、地区人口、大学教育占比、高收入层占比。

当前概率是透明的示意参数，不代表中国、印度或任何真实地区。要回答“人口控制是否造成毁灭性影响”，后续必须用真实生命表、年龄别生育率、迁移矩阵和政策实施时间线校准，并进行不确定性分析；不能只比较一条确定性曲线。

研究依据和每条证据如何映射到模型，见 `docs/research_basis.md`。
理论框架、World3/家庭 ABM/Civilization 对照和下一阶段优先级见 `docs/theory_comparison.md`。
理论方向、方法边界和真实化路线见 `docs/theory_and_validation.md`。

## 政策时间线的事实边界

中国部分只把关键时间点写入开关：1970 年代“晚、稀、少”，1980—2015 年以独生子女为主、2016 年全面两孩、2021 年三孩及配套支持。具体执行强度、城乡与地区例外目前都被压缩成一个 0—1 参数，不是史实还原。

- 联合国对中国与印度人口政策的概览：https://desapublications.un.org/policy-briefs/un-desa-policy-brief-no-153-india-overtakes-china-worlds-most-populous-country
- 中国全面两孩决定：https://www.nhc.gov.cn/jczds/zyjs/201601/73c8db1093a345e794082f3deba32129.shtml
- 中国三孩及配套支持决定：https://www.mee.gov.cn/zcwj/zyygwj/202107/t20210720_849299.shtml

## 运行

项目仅依赖 Python 3.11+ 标准库：

```bash
python3 -m population_simu.cli scenarios/baseline.json --years 50 --output outputs/baseline.csv
python3 -m population_simu.cli scenarios/low_fertility.json --years 50 --output outputs/low_fertility.csv
```

若没有安装包，先临时设置源码目录：

```bash
PYTHONPATH=src python3 -m population_simu.cli scenarios/baseline.json
```

或以可编辑模式安装：

```bash
python3 -m pip install -e .
population-simu scenarios/baseline.json
```

结果是 UTF-8 CSV，可直接用 Excel、Python 或 R 作图比较。

## 交互式网页

`docs/` 默认打开世界人口流动沙盘：用户可以调节初始家庭数量、模拟年份、迁徙开放、区域机会差距、住房、公共教育、福利、照护和经济周期，观察家庭分支、跨区域流向、地区资源差距和阶层变化。

一孩、二孩、三孩与动态子女投资保留为页面中的独立“家庭资源”子实验，不再占据首页主视角。

本地预览：

```bash
python3 -m http.server 8000 --directory docs
```

网页使用轻量 Monte Carlo 模型以保证即时反馈；它和完整 Python 年度模型共享机制方向，但不是同一个计算引擎。

### 本地应用模式

如果需要更详细的家庭、职业、婚姻、健康、政策和家族分支模拟，可在项目根目录启动本地应用：

```bash
PYTHONPATH=src python3 -m population_simu.local_app --port 8000
```

然后打开 `http://127.0.0.1:8000/`。这会提供同一个网页界面，并额外开启只监听本机的 Python 接口：

- `/api/health`：检查完整引擎是否连接
- `/api/scenarios`：列出可运行的 JSON 情景
- `/api/run?scenario=family_major_countries.json&years=60&seed=2026`：运行完整家庭引擎并返回快照与年度 CSV 同构数据
- `/api/run.csv?scenario=family_major_countries.json&years=60&seed=2026`：下载年度国家结果 CSV

网页检测到本地接口后，会出现“运行 Python 情景”按钮，并把年度国家曲线、家庭/分支存量、地区城乡分布、政策阶段和多国对比直接画在页面上；在 GitHub Pages 上没有本地接口时，网页会自动退回浏览器轻量模型，不会因为 API 不存在而白屏。

### GitHub Pages 发布方式

网页采用 GitHub 原生的静态目录发布，不依赖 Actions 构建。把改动合并到 `main` 后，在仓库的 **Settings → Pages → Build and deployment** 中设置：

- **Source**：`Deploy from a branch`
- **Branch**：`main`
- **Folder**：`/docs`

保存后，GitHub 会直接把 `docs/index.html` 发布到上方地址。这样可以避开之前失败的 Pages workflow；旧的失败记录仍会保留在 Actions 历史中，但后续提交不会再触发该工作流。

如果页面没有立即更新，先确认改动已经合并到 `main`，再等待 GitHub Pages 完成发布；浏览器仍显示旧版本时可使用强制刷新。也可以暂时选择 `agent/dynamic-institutions` 分支和 `/docs` 文件夹进行预览，合并后再切回 `main`。

本次网页改动已在本地应用中验证：默认世界视图、Python 年度时间线、国家/地区/政策对比、CSV 下载、迁徙开放度开关和家庭资源子命题均可用；网页新增人口—公共服务—迁移—财政—环境反馈面板。仓库还附有 `data/observed/` 的真实观测快照，可直接用于校准测试。

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

底层情景加载会检查比例范围、资源非负性、地区参数、姓氏规则和政策时期重叠；`FamilyWorld.snapshot()` 提供可序列化的当前年份、国家、地区、家庭数和人口分区结果，供网页/API/批量实验复用。

## 下一步路线

1. 用仓库 `data/observed/` 的 OWID/UN WPP 快照验证管线，再用生命表、人口普查、DHS/MICS/IPUMS 等更细数据校准年龄别生育率、死亡率、迁移年龄结构和地区人口基线。
2. 把婚姻、就业、生育和迁移完全拆成可替换的 hazard/logit 模块，并保留默认示意模型。
3. 用真实省级或城市—乡村迁移矩阵替代默认地区效用，加入迁移网络、住房约束和家庭成员生命周期。
4. 将同一区域的生育规范从“平均子女数”升级为可配置社会网络，区分邻居、亲属、同事和媒体影响。
5. 用历史回放、敏感性分析、共同随机数反事实和中位数/置信区间评估政策，而不是比较单次随机曲线。
6. 继续补充税收、养老金缴费池、医疗融资、托育容量和人口反馈，并让网页展示校准误差和不确定性。
7. 将五维公共服务接入真实地区面板数据，估计滞后效应和异质性。
8. 使用灾害历史和地区暴露数据校准环境模块，并继续扩展资源约束与恢复成本。

### 观测 CSV 与参数搜索快速示例

`data/observed/owid_demography_sample.csv` 是四国 1950—2023 年的固定快照，
含人口、粗出生率、粗死亡率、总和生育率及由率推导的出生/死亡数量。校准
接口不绑定具体引擎，可把任意模拟器包装成 `simulate(parameters)`：

```python
from population_simu.calibration import load_observed_csv, grid_search

observed = load_observed_csv("data/observed/owid_demography_sample.csv")
results = grid_search(
    observed, {"fertility_scale": [0.8, 1.0, 1.2]}, simulate,
    metrics=("population",), group="entity",
)
print(results[0])  # 最佳参数、目标值和各国误差
```

网格搜索适合少量可解释参数；参数较多时使用同模块的 `random_search`
（固定 `seed` 可复现）。下一步可在保持同一 `Simulator` 契约的前提下接入
SciPy 或 Bayesian optimizer，而不改变历史回放和误差定义。

建议的最小验证流程是：按国家分组调用 `temporal_split(..., group="entity")`，
只用训练集调用 `grid_search`/`random_search`，再把最佳参数交给
`evaluate_parameters` 评估验证集。这样可以发现“参数只记住历史、无法外推”
的情况。

对于更严格的横向测试，再报告三类结果：滚动回测的平均误差、留一国家后的
外推误差，以及 Monte Carlo 区间的覆盖率/宽度。覆盖率接近名义水平并不代表
模型正确，但覆盖率明显偏低说明不确定性被低估；区间过宽则说明模型虽安全但
缺乏辨别力。

模型比较示例：

```python
from population_simu.benchmarks import compare_models, fixed_trend_runner, wpp_style_runner

report = compare_models(
    observed, {"fixed_trend": fixed_trend_runner(),
               "wpp_style": wpp_style_runner(),
               "family_micro": family_runner},
    train_years=40, horizon=10, replicates=50,
)
```

这里的 `wpp_style_runner` 是接入真实年龄—性别矩阵前的阻尼趋势基准，不能
冒充联合国 WPP。正式年龄结构模型应由年龄别生育率、死亡率和迁移率推进，
再使用同一 `compare_models` 报告 CRPS、点误差和分层覆盖率。

为提高结论可信度，优先使用 `compare_models_rolling` 而不是单个窗口：它把每个
历史窗口视为一个配对实验，并使用相同随机种子序列比较模型。报告“平均误差 +
95% bootstrap 区间 + 胜率”，只有当模型在多个窗口方向一致且区间不跨越零时，
才适合表述为“相对基准更稳健”；否则应保留为探索性结果。

进阶分析还应做三项稳健性检查：改变训练窗口长度、改变 MAPE/CRPS 的指标权重，
以及把高收入/低收入或高生育/低生育实体分层。若模型排名只在某一组设置下成立，
应报告为敏感性结果，而不是单一确定结论。

## 代码结构

```text
src/population_simu/
  config.py   # 情景参数与校验
  models.py   # 个人、家庭和年度统计
  world.py    # 年度事件引擎
  cli.py      # 命令行与 CSV 导出
  family_config.py       # 国家与政策时期、情景契约和参数校验
  family_models.py       # 姓氏家族、家庭分支与成员
  family_world.py        # 家族繁衍、资源投入、阶层跃迁和 snapshot 接口
  local_app.py            # 本地网页应用与完整 Python 引擎 API
  hazards.py              # 年龄率、logit hazard 和迁移 softmax
  monte_carlo.py          # 共同随机数、区间和敏感性汇总
  family_monte_carlo.py   # 家庭情景批量比较 CLI
  validation.py           # 历史回放误差指标
  calibration.py          # 观测 CSV、分组回放、参数网格和随机搜索
  benchmarks.py           # 固定趋势/WPP风格基准与模型横向比较
  family_cli.py          # 家族模型命令行与年度/家族输出
  resource_experiment.py # 固定资源的一孩/二孩/三孩实验
  capitals.py             # 九维家庭资本与承载力
  occupations.py          # 职业门槛和代际传递渠道
  dynasty_experiment.py   # 多代繁衍死线与绝后实验
  institution_experiment.py # 公共教育/住房/反裙带/高福利开关实验
scenarios/    # 可复制修改的政策情景
tests/        # 可重复性、参数契约、本地应用和基本不变量测试
```
