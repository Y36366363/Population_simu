from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Occupation:
    id: str
    name: str
    status: float
    income: float
    human_gate: float
    social_gate: float
    political_gate: float
    health_risk: float
    education_years: int = 0
    job_loss_risk: float = 0.03
    sector: str = "market"
    licensed_required: bool = False


OCCUPATIONS: dict[str, Occupation] = {
    "political": Occupation("political", "政治与公共权力职业", 0.92, 13.0, 0.62, 0.72, 0.72, 0.03, 16, 0.008, "state"),
    "civil_service": Occupation("civil_service", "公务员", 0.68, 8.4, 0.58, 0.42, 0.20, 0.03, 16, 0.010, "state"),
    "soe_manager": Occupation("soe_manager", "国企管理人员", 0.74, 10.2, 0.60, 0.52, 0.22, 0.05, 15, 0.018, "soe"),
    "soe_worker": Occupation("soe_worker", "国企职工", 0.48, 6.4, 0.34, 0.20, 0.04, 0.11, 12, 0.020, "soe"),
    "medical_trainee": Occupation("medical_trainee", "医学教育与住院培训", 0.55, 3.6, 0.72, 0.34, 0.05, 0.10, 15, 0.015, "licensed"),
    "medical": Occupation("medical", "执业医生", 0.84, 12.0, 0.82, 0.42, 0.10, 0.08, 18, 0.012, "licensed", True),
    "professional": Occupation("professional", "工程/科研/专业人员", 0.76, 10.5, 0.72, 0.34, 0.05, 0.04, 16, 0.028, "market"),
    "business": Occupation("business", "企业经营者", 0.80, 14.0, 0.48, 0.68, 0.24, 0.08, 13, 0.070, "market"),
    "public_service": Occupation("public_service", "教育及其他公共服务", 0.62, 7.8, 0.58, 0.44, 0.14, 0.04, 16, 0.016, "state"),
    "skilled": Occupation("skilled", "技术工人与一般职员", 0.48, 6.2, 0.42, 0.22, 0.02, 0.10, 12, 0.040, "market"),
    "routine": Occupation("routine", "常规服务与生产劳动", 0.32, 4.2, 0.20, 0.12, 0.0, 0.18, 10, 0.060, "market"),
    "precarious": Occupation("precarious", "高风险不稳定劳动", 0.16, 2.6, 0.05, 0.05, 0.0, 0.32, 8, 0.110, "informal"),
    "unemployed": Occupation("unemployed", "失业", 0.06, 0.5, 0.0, 0.0, 0.0, 0.08, 0, 0.0, "none"),
    "dependent": Occupation("dependent", "未就业/依赖家庭", 0.08, 0.8, 0.0, 0.0, 0.0, 0.10, 0, 0.0, "none"),
}


# 同职业优势表示知识、执照准备、关系网络与职业认知传递，并非遗传决定。
INHERITANCE_CHANNEL = {
    "political": ("political", "civil_service", "soe_manager", "business"),
    "civil_service": ("civil_service", "political", "public_service", "soe_manager"),
    "soe_manager": ("soe_manager", "civil_service", "business", "soe_worker"),
    "soe_worker": ("soe_worker", "skilled", "routine", "soe_manager"),
    "medical_trainee": ("medical_trainee", "medical", "professional"),
    "medical": ("medical", "medical_trainee", "professional"),
    "professional": ("professional", "medical", "public_service"),
    "business": ("business", "political", "professional"),
    "public_service": ("public_service", "civil_service", "professional"),
    "skilled": ("skilled", "professional", "routine"),
    "routine": ("routine", "skilled", "precarious"),
    "precarious": ("precarious", "routine", "skilled"),
    "unemployed": ("unemployed", "precarious", "routine"),
    "dependent": ("dependent", "precarious", "routine"),
}


BASE_OCCUPATION_WEIGHT = {
    "political": 0.05,
    "civil_service": 0.13,
    "soe_manager": 0.07,
    "soe_worker": 0.16,
    "medical_trainee": 0.06,
    "medical": 0.08,
    "professional": 0.16,
    "business": 0.12,
    "public_service": 0.16,
    "skilled": 0.27,
    "routine": 0.28,
    "precarious": 0.18,
    "unemployed": 0.04,
    "dependent": 0.07,
}
