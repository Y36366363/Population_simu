"""家庭模型机制卡片：把规则、数据和验证责任写在同一处。

这些卡片不是参数值，也不会改变模拟逻辑；它们是模型审计和后续校准的
契约。每个机制都必须能回答“它想解释什么、观测什么、何时失效”。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MechanismCard:
    name: str
    purpose: str
    inputs: tuple[str, ...]
    parameters: tuple[str, ...]
    probability_rule: str
    observables: tuple[str, ...]
    validation_metrics: tuple[str, ...]
    failure_scope: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


MECHANISM_CARDS: tuple[MechanismCard, ...] = (
    MechanismCard(
        "marriage_and_union", "解释成家机会和婚姻持续时间如何影响家庭形成",
        ("年龄", "性别", "教育", "收入", "住房", "社会网络"),
        ("pair_formation_hazard", "assortative_matching", "divorce_hazard"),
        "duration_hazard + matching logit + hazard_to_probability",
        ("首次婚姻年龄", "婚姻率", "离婚率", "再婚率"),
        ("年龄别婚姻率 MAE", "婚姻持续期分布", "离婚/再婚 hazard 校准"),
        ("未婚比例极端的国家", "非婚生育占比较高的地区", "登记制度不完整时期"),
    ),
    MechanismCard(
        "fertility", "解释生育时机、子女数量和资源约束的共同作用",
        ("女性年龄", "伴侣状态", "已有子女", "资源", "托育", "住房", "政策"),
        ("age_fertility_profile", "fertility_multiplier", "birth_spacing", "child_cost"),
        "duration_hazard(age_rate × policy × care × resources)",
        ("年龄别生育率", "总和生育率", "首胎/二胎间隔", "按孩次生育率"),
        ("ASFR MAE", "TFR RMSE", "出生间隔分位数误差", "孩次 hazard"),
        ("辅助生殖普及快速变化", "生育登记漏报", "战争/重大灾害等非平稳时期"),
    ),
    MechanismCard(
        "mortality_and_health", "让人口年龄结构和健康资本共同决定死亡与劳动能力",
        ("年龄", "性别", "地区", "健康资本", "医疗可及性", "灾害暴露"),
        ("age_sex_mortality", "health_shock", "medical_access", "hazard_multiplier"),
        "hazard_to_probability(age_sex_hazard × health/environment multipliers)",
        ("年龄别死亡率", "预期寿命", "婴儿死亡率", "慢病/失能率"),
        ("生命表误差", "年龄别死亡率 RMSE", "寿命差距", "死亡总量误差"),
        ("极端灾害年份", "死因结构快速变化", "高龄组小样本"),
    ),
    MechanismCard(
        "migration", "解释家庭和个人在地区/国家之间的流动及其年龄结构",
        ("工资", "住房", "公共服务", "迁移网络", "家庭成员", "地区容量"),
        ("migration_hazard", "destination_temperature", "capacity_penalty", "network_weight"),
        "hazard_to_probability + destination softmax + capacity constraint",
        ("年龄别迁移率", "OD 流量矩阵", "净迁移", "迁入地人口"),
        ("OD 矩阵 MAE", "年龄结构误差", "目的地排序", "迁移守恒"),
        ("边界政策突变", "登记口径变化", "没有可靠 OD 数据的地区"),
    ),
    MechanismCard(
        "employment_and_income", "把教育、就业和经济周期连接到家庭资源与生育/迁移",
        ("教育", "年龄", "性别", "职业", "经济周期", "地区工资"),
        ("employment_logit", "wage_gap", "automation", "job_loss_hazard"),
        "logit(employment utility) + income transition hazards",
        ("劳动参与率", "失业率", "工资分布", "职业转换率", "性别工资差"),
        ("年龄性别就业率", "收入分位数误差", "转岗率", "失业持续期"),
        ("非正规就业占主导的地区", "重大制度断点", "收入观测严重缺失"),
    ),
    MechanismCard(
        "intergenerational_transmission", "表达家庭资本、职业和社会网络对子代机会的影响",
        ("父母职业", "教育", "财富", "关系网络", "子代能力", "反裙带政策"),
        ("transmission_strength", "meritocracy", "investment_rule", "luck_variance"),
        "bounded probability/logit with capital and network channels",
        ("父子职业相关", "教育代际相关", "收入代际弹性", "向上流动率"),
        ("职业转移矩阵", "教育流动矩阵", "收入 rank-rank slope", "相关性校准"),
        ("精英职位定义不同", "代际关系不可观测", "制度更替期"),
    ),
    MechanismCard(
        "childcare_and_grandparent_care", "解释照护供给如何改变生育实现和女性就业约束",
        ("托位供给", "祖辈年龄健康", "距离", "工作时间", "子女年龄"),
        ("formal_care_capacity", "kin_care_capacity", "care_cost", "distance_decay"),
        "coverage logistic × availability × kin capacity",
        ("托育使用率", "祖辈照护小时", "二胎间隔", "母亲就业率"),
        ("照护覆盖率", "小时误差", "二胎 hazard", "就业率差异"),
        ("祖辈不共同居住", "照护服务统计缺失", "多代家庭定义不一致"),
    ),
    MechanismCard(
        "public_finance_and_services", "让人口、税收和公共服务形成可追踪的反馈回路",
        ("人口", "工资税基", "教育/医疗/养老成本", "基金余额", "转移支付"),
        ("tax_rate", "service_cost", "transfer_rule", "capacity_threshold"),
        "budget identity + service response + capacity penalty",
        ("财政收支", "基金余额", "人均公共支出", "服务使用率", "迁移流量"),
        ("预算守恒", "支出结构误差", "基金路径", "服务—迁移弹性"),
        ("预算口径变化", "隐性债务未观测", "中央与地方边界不一致"),
    ),
)


def mechanism_catalog() -> dict[str, dict[str, object]]:
    """返回稳定的 JSON 友好机制目录。"""
    return {card.name: card.as_dict() for card in MECHANISM_CARDS}

