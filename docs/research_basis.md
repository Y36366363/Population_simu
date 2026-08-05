# v3 研究依据与模型映射

本文件记录“研究发现—模型机制—当前参数”的对应关系。引用只用于确定机制方向，除非另行注明，代码里的数值都还是用于敏感性分析的示意参数，并非论文估计值的直接复制。

## 1. 政治权力、任期、派系与家族

### 研究依据

- Dal Bó、Dal Bó 与 Snyder 使用工具变量方法研究美国国会政治家族，结论之一是更长的在位时间会因果性地提高建立或延续政治家族的概率。  
  https://www.nber.org/papers/w13122
- 关于中国精英政治的网络研究强调，派系标签不足以描述全部政治联系， patron-client 网络、中心性和非正式联系会影响晋升及政治风险。  
  https://www.cambridge.org/core/journals/journal-of-east-asian-studies/article/abs/moving-beyond-factions-using-social-network-analysis-to-uncover-patronage-networks-among-chinese-elites/4516226D31EECB62D0E18227CB4ACCD9
- 近期跨代政治代表研究发现，富裕和高地位家庭在政治职位中长期过度代表，家庭背景还能影响政策选择。  
  https://www.nber.org/papers/w35180

### 模型映射

- 政治职业不能在成年时直接获得，通常从公务员入口进入。
- 每名政治人物拥有 `faction_id`、`patron_power`、`political_rank`、`career_tenure`。
- 每个任期结束时按能力、网络与派系资本决定晋升、留任或退出。
- 在位越久，政治与 patron 资本越强；这些资本可以传给子女，但会被 `anti_nepotism_strength` 削弱。
- 输出政治家族占比和派系 HHI 集中度。

## 2. 医生教育、培训和执照

### 研究依据

- 中国《医师法》规定医学学历、实践和资格考试等执业入口。  
  https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313104.html
- 七部门住院医师规范化培训制度把院校医学教育与毕业后临床培训区分开来。  
  https://www.moe.gov.cn/jyb_xxgk/moe_1777/moe_1779/201404/t20140402_166632.html
- 中国多中心医学教育研究讨论了医生家庭背景对医学学习与职业发展的影响，也提醒这种背景不必然带来学业优势。  
  https://link.springer.com/article/10.1186/s12909-025-07053-6

### 模型映射

- 医学职业分为 `medical_trainee` 与取得执照后的 `medical`。
- 进入培训需要教育年限、人力资本和竞争概率。
- 培训持续若干年；达到年限后参加执照概率试验，失败可重试，长期失败会转入其他专业职业。
- 医生家庭提供职业认知和准备优势，但不会绕过教育、培训与执照门槛。

## 3. 公务员、国企与制度冲击

### 研究依据

- 公共部门就业具有代际持续性，稳定性、家庭信息和网络都可能成为传递渠道。  
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2760522
- 关于中国反腐与官僚就业代际传递的研究将反腐视为可能打断家族性公共职位优势的制度冲击。  
  https://www.sciencedirect.com/science/article/pii/S0167268126002246
- 中国 1990 年代国企改革和大规模下岗研究发现，父母就业冲击可能通过教育投入和家庭资源影响下一代。  
  https://preprints.apsanet.org/engage/apsa/article-details/67091d3512ff75c3a12226cb

### 模型映射

- 职业体系区分公务员、政治职位、国企管理人员、国企职工和一般公共服务。
- `state_sector_share` 控制国企/公共部门入口规模。
- 公务员入口包括教育、人力资本、考试选择性和关系资本。
- `soe_reform_year` 与 `soe_reform_shock` 可制造连续数年的国企失业冲击。
- 反裙带参数同时降低政治资本继承和过强 patron 网络。

## 4. 失业、疤痕效应与工伤

### 研究依据

- 失业研究通常区分即时收入损失、再就业困难、长期工资与心理健康疤痕；家庭层面还可能影响子女教育投入。跨代因果结果并非所有研究都一致，因此模型保留可关闭和可调强度。  
  https://www.sciencedirect.com/science/article/pii/S0049089X21001277
- 使用行政数据研究工伤的论文显示，职业伤害可能造成长期收入损失，工伤补偿未必完全覆盖损失。  
  https://pubmed.ncbi.nlm.nih.gov/25223516/

### 模型映射

- 每种职业分别设置失业风险和工伤风险。
- 失业持续时间会降低再就业概率、经济地位和健康资本。
- 再就业可能回到原职业，也可能发生向下或横向流动。
- 工伤降低健康和收入，未被 `worker_compensation` 覆盖的成本进入家庭债务。
- 国企改革冲击只对国企部门额外增加失业风险。

## 5. 房地产、居住分层与继承

### 研究依据

- 美国行政数据研究显示，住房资本具有显著代际持续性，住房供给限制会放大父母与子女之间的住房差距。  
  https://www.nber.org/papers/w35256
- 旧金山联储研究指出，父母住房净值支持能帮助子女更早积累住房财富。  
  https://www.frbsf.org/research-and-insights/publications/economic-letter/2022/11/passing-along-housing-wealth-from-parents-to-children/
- 公共教育和住房捆绑可能让房价、学校质量与代际流动形成空间相关。  
  https://www.aeaweb.org/articles?id=10.1257%2Fmac.20180466

### 模型映射

- 家庭分别记录现金、住房价值和住房份额。
- 成年子女成家时可能获得首付性质的生前住房转移。
- 最后一名成年持有者死亡后，房产按活跃子女分割并扣除遗产税。
- 住房供给弹性影响房价增值和首次购房概率。
- 房产越分越碎时，子女获得的住房保障可能低于成家死线。

## 6. 公共教育质量

### 研究依据

- 高质量学校与更长受教育时间和更高向上流动概率相关。  
  https://www.nber.org/digest/nov18/impact-school-quality-transmission-inequality
- 地方学校质量与住房价格绑定会强化居住分层和代际不平等。  
  https://www.aeaweb.org/articles?id=10.1257%2Fmac.20180466

### 模型映射

- 每个国家有公共教育质量和教育不平等两个参数。
- 每个家庭根据公共质量、社区财富和教育不平等获得 `school_quality`。
- 每年的受教育进度由学校质量、家庭私人投入和个人潜力共同决定。
- 公共教育质量高时，贫困家庭不必完全依赖私人投入；教育不平等高时，住房财富会更多地转换成学校优势。

## 7. 分阶层婚恋市场

### 研究依据

- 大量研究记录了教育和收入上的正向同类婚配；这种匹配会把两个高资源个体聚集到同一家庭，也可能放大家庭间不平等。  
  https://www.nber.org/papers/w20271
- 婚姻市场结果不仅受偏好影响，也受教育分布、就业、可匹配人群结构和搜索摩擦影响。  
  https://www.nber.org/papers/w7510
- OECD 关于移民子代流动的综述也把同类婚配和家庭构成视为代际不平等的重要机制。  
  https://www.oecd.org/en/publications/catching-up-intergenerational-mobility-and-children-of-immigrants_9789264288041-en.html

### 模型映射

- 匹配同时比较经济地位、教育年限、住房保障和派系联系。
- `assortative_mating_strength` 控制同类婚配强度。
- `elite_marriage_closure` 降低精英与非精英跨层匹配权重。
- 低资源群体还会受到动态成家死线影响；这与“偏好同类”是两个不同机制。
- 输出精英—精英婚姻占全部伴侣家庭的比例。

## 当前不能声称的内容

- 不能把职业相似直接解释为遗传。
- 不能把中国、印度、日本和美国当前参数解释为真实比较排名。
- 不能用一次随机运行判断某项政策的净因果效应。
- 不能把模拟中的“死线”理解成自然规律；它是住房、劳动市场和福利制度共同形成的软阈值。
- 政治派系、考试、医生执照和国企制度都只保留了最小结构，后续需要国家和时期校准。
