# 家庭—姓氏家族人口流动与社会晋升模拟沙盘

这是一个以家庭为最小行动单位的无战争世界人口流动与发展沙盘。家庭会形成新分支、积累或损失多维资本，并随工资、住房、教育、福利、婚姻和照护条件在地区与国家之间迁徙；这些微观选择共同改变地区人口、阶层结构和家族延续。

项目的主问题是“家庭如何流动，以及长期累积后世界怎样变化”。一孩、二孩、三孩与资源集中只是其中一个可单独开启的家庭层子实验，不代表整个项目的中心。

交互式网页沙盘（将 `docs/` 设为 GitHub Pages 来源后）：

https://Y36366363.github.io/Population_simu/

> 当前网页版本：世界家庭流动沙盘已作为首页主视角；一孩、二孩、三孩资源配置仍可从顶部“子命题：家庭资源”进入。网页使用固定随机种子，适合比较参数变化，不应被解读为现实国家预测。

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

运行宏观一孩/二孩/三孩情景：

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
- **政策旋钮**：生育倍率、托育支持、迁移开放、教育投入、向上流动机会。
- **结果指标**：总人口、出生/死亡/迁移、年龄结构、地区人口、大学教育占比、高收入层占比。

当前概率是透明的示意参数，不代表中国、印度或任何真实地区。要回答“人口控制是否造成毁灭性影响”，后续必须用真实生命表、年龄别生育率、迁移矩阵和政策实施时间线校准，并进行不确定性分析；不能只比较一条确定性曲线。

第三版研究依据和每条证据如何映射到模型，见 `docs/research_basis.md`。

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

### GitHub Pages 发布方式

网页采用 GitHub 原生的静态目录发布，不依赖 Actions 构建。把改动合并到 `main` 后，在仓库的 **Settings → Pages → Build and deployment** 中设置：

- **Source**：`Deploy from a branch`
- **Branch**：`main`
- **Folder**：`/docs`

保存后，GitHub 会直接把 `docs/index.html` 发布到上方地址。这样可以避开之前失败的 Pages workflow；旧的失败记录仍会保留在 Actions 历史中，但后续提交不会再触发该工作流。

如果页面没有立即更新，先确认改动已经合并到 `main`，再等待 GitHub Pages 完成发布；浏览器仍显示旧版本时可使用强制刷新。也可以暂时选择 `agent/dynamic-institutions` 分支和 `/docs` 文件夹进行预览，合并后再切回 `main`。

本次网页改动已在本地静态服务器中验证：默认世界视图、区域节点、时间线、迁徙开放度开关和家庭资源子命题均可用，浏览器控制台无错误；Python 回归测试为 28 项全部通过。

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

底层情景加载会检查比例范围、资源非负性、地区参数、姓氏规则和政策时期重叠；`FamilyWorld.snapshot()` 提供可序列化的当前年份、国家、地区、家庭数和人口分区结果，供网页/API/批量实验复用。

## 下一步路线

1. 接入联合国 WPP、各国生命表和年龄别生育率，建立国家/省级校准层。
2. 加入结婚、离婚、跨国家庭、二孩/三孩生育意愿与性别中性的家庭结构。
3. 加入税收、养老账户可持续性、托育供给容量和照护服务劳动力市场。
4. 用 Monte Carlo 批量运行，展示中位数与置信区间，而不是单次随机结果。
5. 让网页沙盘逐步读取 Python 批量情景结果，并加入地区时间线、家庭追踪和政策情景对照。

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
  family_cli.py          # 家族模型命令行与年度/家族输出
  resource_experiment.py # 固定资源的一孩/二孩/三孩实验
  capitals.py             # 九维家庭资本与承载力
  occupations.py          # 职业门槛和代际传递渠道
  dynasty_experiment.py   # 多代繁衍死线与绝后实验
  institution_experiment.py # 公共教育/住房/反裙带/高福利开关实验
scenarios/    # 可复制修改的政策情景
tests/        # 可重复性与基本不变量测试
```
