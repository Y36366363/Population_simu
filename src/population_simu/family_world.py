from __future__ import annotations

from collections import defaultdict
import math
import random
import statistics

from .capitals import CapitalBundle, sigmoid
from .family_config import Country, FamilyScenario
from .family_models import Clan, FamilyBranch, FamilyPerson, FamilyYearStats
from .occupations import BASE_OCCUPATION_WEIGHT, INHERITANCE_CHANNEL, OCCUPATIONS


class FamilyWorld:
    """以姓氏家族及其家庭分支为核心的离散年度模拟器。"""

    def __init__(self, scenario: FamilyScenario):
        scenario.validate()
        self.scenario = scenario
        self.countries = {country.id: country for country in scenario.countries}
        self.rng = random.Random(scenario.simulation.random_seed)
        self.year = scenario.simulation.start_year
        self.clans: dict[int, Clan] = {}
        self.households: dict[int, FamilyBranch] = {}
        self.people: dict[int, FamilyPerson] = {}
        self.history: list[FamilyYearStats] = []
        self.next_clan_id = 1
        self.next_household_id = 1
        self.next_person_id = 1
        self._recent_upward: dict[str, tuple[int, int]] = {}
        self._recent_occupation: dict[str, tuple[int, int, int, int]] = {}
        self._occupation_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        self._seed_countries()
        self.history.extend(self._summaries({}, {}, {}, {}))

    @property
    def living_people(self) -> list[FamilyPerson]:
        return [person for person in self.people.values() if person.alive]

    def _surname(self, country: Country, index: int) -> str:
        if country.id == "CHN":
            common = (
                "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻"
                "柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳唐罗薛雷贺倪汤滕殷毕郝邬"
                "安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏"
                "成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐"
                "邱骆高夏蔡田樊胡凌霍虞万支柯管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石"
                "崔吉龚程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗"
                "山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟"
            )
            if index < len(common):
                return common[index]
            return f"华族{index + 1:03d}"
        return f"{country.id}-族{index + 1:03d}"

    def _seed_countries(self) -> None:
        for country in self.countries.values():
            for index in range(country.initial_clans):
                base = country.baseline_family_resources
                # 对数分布同时产生大量普通家庭、少量极贫与极富家庭。
                resources = max(1.0, base * math.exp(self.rng.gauss(-0.15, 0.85)))
                household = self._new_household(
                    clan_id=self.next_clan_id,
                    surname=self._surname(country, index),
                    country_id=country.id,
                    generation=0,
                    resources=resources,
                    parent_ids=(),
                    capitals=self._initial_capitals(country, resources),
                )
                clan = Clan(
                    id=self.next_clan_id,
                    surname=household.surname,
                    origin_country_id=country.id,
                    founder_household_id=household.id,
                    founder_resources=resources,
                    branch_ids=[household.id],
                )
                self.clans[clan.id] = clan
                self.next_clan_id += 1
                mother_age = self.rng.randint(24, 38)
                father_age = min(48, max(22, mother_age + self.rng.randint(-2, 6)))
                mother = self._new_person(household, mother_age, "F", partnered=True)
                father = self._new_person(household, father_age, "M", partnered=True)
                initial_children = min(5, self._poisson(country.initial_children_per_family * 0.55))
                initial_policy = country.policy_at(self.year)
                if initial_policy.max_children is not None and initial_policy.enforcement >= 0.999:
                    initial_children = min(initial_children, initial_policy.max_children)
                for _ in range(initial_children):
                    age = self.rng.randint(0, min(16, mother_age - 18))
                    self._new_person(
                        household,
                        age,
                        self.rng.choice(("F", "M")),
                        mother_id=mother.id,
                        father_id=father.id,
                    )
                    household.children_ever_born += 1
                    clan.total_births += 1

    def _poisson(self, mean: float) -> int:
        limit = math.exp(-mean)
        product = 1.0
        count = 0
        while product > limit:
            count += 1
            product *= self.rng.random()
        return count - 1

    def _new_household(
        self,
        *,
        clan_id: int,
        surname: str,
        country_id: str,
        generation: int,
        resources: float,
        parent_ids: tuple[int, ...],
        capitals: CapitalBundle,
    ) -> FamilyBranch:
        household = FamilyBranch(
            id=self.next_household_id,
            clan_id=clan_id,
            surname=surname,
            country_id=country_id,
            generation=generation,
            resources=resources,
            permanent_income=max(1.0, resources * 0.12),
            capitals=capitals,
            parent_household_ids=parent_ids,
        )
        country = self.countries[country_id]
        owner = capitals.housing >= (0.28 + 0.22 * country.housing_pressure)
        household.property_count = 1.0 if owner else 0.0
        household.property_value = resources * (0.65 + 1.4 * capitals.housing) if owner else 0.0
        neighborhood_advantage = capitals.normalized_financial(country.baseline_family_resources)
        household.school_quality = min(
            1.0,
            max(
                0.05,
                country.public_education_quality
                * (1 - country.education_inequality * (0.55 - neighborhood_advantage)),
            ),
        )
        self.households[household.id] = household
        self.next_household_id += 1
        return household

    def _initial_capitals(self, country: Country, resources: float) -> CapitalBundle:
        relative = resources / max(1.0, country.baseline_family_resources)
        wealth = min(1.0, max(0.02, math.log1p(relative * 2.5) / math.log(3.5)))
        return CapitalBundle(
            financial=resources,
            human=min(1.0, 0.18 + 0.42 * country.education_access + self.rng.gauss(0, 0.10)),
            social=min(1.0, max(0.02, 0.10 + 0.46 * wealth + self.rng.gauss(0, 0.12))),
            political=min(1.0, max(0.0, 0.02 + 0.22 * wealth + self.rng.gauss(0, 0.07))),
            cultural=min(1.0, max(0.02, 0.14 + 0.38 * country.education_access + self.rng.gauss(0, 0.10))),
            housing=min(1.0, max(0.02, 0.18 + 0.56 * wealth - 0.22 * country.housing_pressure)),
            health=min(1.0, max(0.20, 0.55 + 0.25 * country.initial_development + self.rng.gauss(0, 0.08))),
            care_time=min(1.0, max(0.10, 0.72 - 0.15 * country.initial_urbanization + self.rng.gauss(0, 0.08))),
            debt=max(0.0, min(1.0, 0.24 + 0.18 * country.housing_pressure - 0.20 * wealth + self.rng.gauss(0, 0.08))),
        )

    def _new_person(
        self,
        household: FamilyBranch,
        age: int,
        sex: str,
        *,
        partnered: bool = False,
        mother_id: int | None = None,
        father_id: int | None = None,
    ) -> FamilyPerson:
        # beta(2, 2) 让大多数人的先天潜力居中，但保留少量极端值。
        potential = self.rng.betavariate(2, 2)
        country = self.countries[household.country_id]
        development = country.development_at(self.year, self.scenario.simulation.start_year)
        adult_status = min(1.0, max(0.0, 0.20 + 0.35 * potential + 0.35 * development + self.rng.gauss(0, 0.10)))
        occupation = self._seed_occupation(household) if age >= 22 else "dependent"
        occupation_status = OCCUPATIONS[occupation].status
        parent_occupations = [
            self.people[parent_id].occupation
            for parent_id in (mother_id, father_id)
            if parent_id is not None and parent_id in self.people
        ]
        parent_occupation = (
            max(parent_occupations, key=lambda item: OCCUPATIONS[item].status)
            if parent_occupations
            else None
        )
        person = FamilyPerson(
            id=self.next_person_id,
            clan_id=household.clan_id,
            surname=household.surname,
            country_id=household.country_id,
            household_id=household.id,
            age=age,
            sex=sex,
            innate_potential=potential,
            human_capital=adult_status if age >= 22 else 0.0,
            economic_status=(0.55 * adult_status + 0.45 * occupation_status) if age >= 22 else 0.0,
            occupation=occupation,
            social_capital=household.capitals.social if age >= 22 else 0.0,
            political_capital=household.capitals.political if age >= 22 else 0.0,
            cultural_capital=household.capitals.cultural if age >= 22 else 0.0,
            housing_security=household.capitals.housing if age >= 22 else 0.0,
            health_capital=household.capitals.health,
            debt_burden=household.capitals.debt if age >= 22 else 0.0,
            adult_viability=household.capitals.viability(country.baseline_family_resources) if age >= 22 else 0.0,
            education_years=(OCCUPATIONS[occupation].education_years if age >= 22 else max(0, min(age - 5, 12))),
            training_years=(country.medical_training_years if occupation == "medical" else 0),
            licensed=occupation == "medical",
            career_tenure=max(0, age - 22) if age >= 22 else 0,
            political_rank=1 if occupation == "political" else 0,
            faction_id=(self.rng.randrange(country.faction_count) if occupation == "political" else None),
            patron_power=(household.capitals.political if occupation in ("political", "civil_service") else 0.0),
            parent_occupation=parent_occupation,
            partnered=partnered,
            mother_id=mother_id,
            father_id=father_id,
        )
        self.people[person.id] = person
        household.member_ids.append(person.id)
        self.next_person_id += 1
        return person

    def _seed_occupation(self, household: FamilyBranch) -> str:
        viability = household.capitals.viability(
            self.countries[household.country_id].baseline_family_resources
        )
        if viability > 0.72:
            pool = ("political", "medical", "professional", "business", "public_service", "skilled")
            weights = (0.08, 0.13, 0.22, 0.20, 0.17, 0.20)
        elif viability > 0.48:
            pool = ("medical", "professional", "business", "public_service", "skilled", "routine")
            weights = (0.06, 0.16, 0.12, 0.17, 0.30, 0.19)
        else:
            pool = ("public_service", "skilled", "routine", "precarious", "dependent")
            weights = (0.05, 0.24, 0.36, 0.28, 0.07)
        return self.rng.choices(pool, weights=weights, k=1)[0]

    def _mortality_probability(self, person: FamilyPerson) -> float:
        country = self.countries[person.country_id]
        development = country.development_at(self.year, self.scenario.simulation.start_year)
        infant = (0.025 * (1 - 0.85 * development)) if person.age == 0 else 0.0
        ageing = 0.000025 * math.exp(max(0, person.age - 30) / 10.2)
        accident = 0.0005 + (0.0005 if person.sex == "M" and 15 <= person.age <= 35 else 0)
        occupation_risk = OCCUPATIONS[person.occupation].health_risk if person.age >= 22 else 0.0
        health_multiplier = 1.35 - 0.55 * person.health_capital
        return min(
            0.65,
            (infant + ageing + accident + 0.0015 * occupation_risk)
            * (1.15 - 0.45 * development)
            * health_multiplier,
        )

    def _allocate_resources(self) -> dict[str, list[float]]:
        investments: dict[str, list[float]] = defaultdict(list)
        share = self.scenario.simulation.resource_investment_share
        for household in self.households.values():
            children = [
                self.people[pid]
                for pid in household.member_ids
                if self.people[pid].alive and self.people[pid].age <= 21
            ]
            if not children:
                continue
            # 同样预算在多个孩子之间摊薄；指数略低于 1，表示共享住房等规模经济。
            total_budget = max(0.0, household.resources) * share
            per_child = total_budget / (len(children) ** 0.92)
            country = self.countries[household.country_id]
            public_quality = household.school_quality
            access = (
                0.45 * country.education_access
                + 0.35 * public_quality
                + 0.20 * country.development_at(self.year, self.scenario.simulation.start_year)
            )
            for child in children:
                effective = per_child * min(1.0, access)
                child.cumulative_investment += effective
                if 6 <= child.age <= 24:
                    private_supplement = 0.12 * math.log1p(effective)
                    yearly_progress = min(
                        1.0,
                        0.35 + 0.48 * public_quality + private_supplement + 0.08 * child.innate_potential,
                    )
                    child.education_years += yearly_progress
                child.human_capital = min(
                    1.0,
                    child.human_capital + 0.008 * math.log1p(effective) + 0.003 * child.innate_potential,
                )
                # 关系、文化与政治资本也代际传递，但不是简单用现金购买。
                child.social_capital = min(
                    1.0,
                    child.social_capital + 0.018 * household.capitals.social / (len(children) ** 0.35),
                )
                child.political_capital = min(
                    1.0,
                    child.political_capital + 0.014 * household.capitals.political / (len(children) ** 0.20),
                )
                child.cultural_capital = min(
                    1.0,
                    child.cultural_capital + 0.020 * household.capitals.cultural / (len(children) ** 0.30),
                )
                child.health_capital = min(
                    1.0,
                    child.health_capital + 0.004 * household.capitals.health - 0.002 * household.capitals.debt,
                )
                investments[household.country_id].append(effective)
            household.resources = max(0.1, household.resources - total_budget * 0.08)
            household.capitals.financial = household.resources
            household.capitals.care_time = max(
                0.02, household.capitals.care_time - 0.006 * max(0, len(children) - 1)
            )
        return investments

    def _mature_young_adults(self) -> None:
        upward: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        occupation_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for person in self.living_people:
            if person.age != 22:
                continue
            country = self.countries[person.country_id]
            development = country.development_at(self.year, self.scenario.simulation.start_year)
            parent_statuses = [
                self.people[parent_id].economic_status
                for parent_id in (person.mother_id, person.father_id)
                if parent_id is not None and parent_id in self.people
            ]
            parent_status = statistics.fmean(parent_statuses) if parent_statuses else 0.35
            investment_signal = math.log1p(person.cumulative_investment) / 8.0
            # “爆发孩子”来自先天潜力、教育投资和小概率运气的共同作用。
            luck = self.rng.gauss(0, 0.11)
            rare_breakthrough = 0.32 if person.innate_potential > 0.91 and self.rng.random() < 0.18 else 0.0
            base_status = (
                0.08
                + 0.34 * person.innate_potential
                + 0.30 * min(1.0, investment_signal)
                + 0.18 * development
                + 0.12 * parent_status
                + luck
                + rare_breakthrough
            )
            person.human_capital = min(1.0, max(person.human_capital, base_status - 0.08))
            household = self.households[person.household_id]
            person.social_capital = min(1.0, person.social_capital + 0.58 * household.capitals.social)
            person.political_capital = min(1.0, person.political_capital + 0.72 * household.capitals.political)
            person.cultural_capital = min(1.0, person.cultural_capital + 0.62 * household.capitals.cultural)
            person.housing_security = household.capitals.housing
            person.debt_burden = household.capitals.debt
            parent_occupations = [
                self.people[parent_id].occupation
                for parent_id in (person.mother_id, person.father_id)
                if parent_id is not None and parent_id in self.people
            ]
            person.occupation = self._choose_occupation(person, country, parent_occupations)
            person.parent_occupation = (
                max(parent_occupations, key=lambda item: OCCUPATIONS[item].status)
                if parent_occupations
                else None
            )
            if person.occupation == "civil_service":
                political_parents = [
                    self.people[parent_id]
                    for parent_id in (person.mother_id, person.father_id)
                    if parent_id is not None
                    and parent_id in self.people
                    and self.people[parent_id].faction_id is not None
                ]
                person.faction_id = (
                    political_parents[0].faction_id
                    if political_parents and self.rng.random() > country.anti_nepotism_strength
                    else self.rng.randrange(country.faction_count)
                )
                person.patron_power = max(
                    [parent.patron_power for parent in political_parents] + [person.political_capital * 0.5]
                )
            occupation_status = OCCUPATIONS[person.occupation].status
            person.economic_status = min(1.0, max(0.0, 0.55 * base_status + 0.45 * occupation_status))
            person.adult_viability = self._person_viability(person, country)
            upward[person.country_id][1] += 1
            if person.economic_status >= parent_status + 0.15:
                upward[person.country_id][0] += 1
            occupation_stats[person.country_id][1] += 1
            if person.occupation in parent_occupations:
                occupation_stats[person.country_id][0] += 1
            if "precarious" in parent_occupations:
                occupation_stats[person.country_id][3] += 1
                if person.occupation == "precarious":
                    occupation_stats[person.country_id][2] += 1
        self._recent_upward = {country_id: tuple(values) for country_id, values in upward.items()}
        self._recent_occupation = {
            country_id: tuple(values) for country_id, values in occupation_stats.items()
        }
        for country_id, values in occupation_stats.items():
            totals = self._occupation_totals[country_id]
            for index, value in enumerate(values):
                totals[index] += value

    def _choose_occupation(
        self, person: FamilyPerson, country: Country, parent_occupations: list[str]
    ) -> str:
        weights = []
        occupation_ids = [
            occupation_id
            for occupation_id in OCCUPATIONS
            if occupation_id not in ("political", "medical", "unemployed")
        ]
        openness = country.institutional_openness
        persistence = country.occupational_inheritance
        for occupation_id in occupation_ids:
            occupation = OCCUPATIONS[occupation_id]
            human_access = sigmoid(9 * (person.human_capital - occupation.human_gate))
            social_access = sigmoid(8 * (person.social_capital - occupation.social_gate))
            political_access = sigmoid(9 * (person.political_capital - occupation.political_gate))
            gate = 0.52 * human_access + 0.28 * social_access + 0.20 * political_access
            if occupation_id in ("routine", "precarious", "dependent"):
                gate += 0.32 * (1 - person.human_capital)
            inherited = 0.0
            for parent_occupation in parent_occupations:
                related = INHERITANCE_CHANNEL[parent_occupation]
                if occupation_id == parent_occupation:
                    inherited = max(inherited, 2.8)
                elif occupation_id in related:
                    inherited = max(inherited, 1.25)
            network_multiplier = 1 + persistence * inherited * (1.35 - openness)
            # 开放制度降低关系门槛，让能力权重更大；封闭制度反之。
            merit_multiplier = 0.55 + openness * (0.45 + 0.80 * person.innate_potential)
            sector_multiplier = 1.0
            if occupation_id == "medical_trainee":
                education_gate = sigmoid(1.4 * (person.education_years - 13.5))
                sector_multiplier *= education_gate
            elif occupation_id == "civil_service":
                exam_gate = sigmoid(
                    7
                    * (
                        0.55 * person.human_capital
                        + 0.25 * person.cultural_capital
                        + 0.20 * person.innate_potential
                        - country.civil_service_selectivity
                    )
                )
                sector_multiplier *= exam_gate * (0.55 + country.state_sector_share)
            elif occupation_id in ("soe_manager", "soe_worker"):
                sector_multiplier *= 0.35 + 2.2 * country.state_sector_share
            weights.append(
                max(
                    0.0005,
                    gate
                    * network_multiplier
                    * merit_multiplier
                    * BASE_OCCUPATION_WEIGHT[occupation_id]
                    * sector_multiplier,
                )
            )
        return self.rng.choices(occupation_ids, weights=weights, k=1)[0]

    def _person_viability(self, person: FamilyPerson, country: Country) -> float:
        capital = CapitalBundle(
            financial=max(0.0, self.households[person.household_id].resources * 0.35),
            human=person.human_capital,
            social=person.social_capital,
            political=person.political_capital,
            cultural=person.cultural_capital,
            housing=person.housing_security,
            health=person.health_capital,
            care_time=self.households[person.household_id].capitals.care_time,
            debt=person.debt_burden,
        )
        return capital.viability(country.baseline_family_resources)

    def _deadline(self, country: Country) -> float:
        development = country.development_at(self.year, self.scenario.simulation.start_year)
        policy = country.policy_at(self.year)
        return min(
            0.78,
            max(
                0.22,
                0.18
                + 0.10 * development
                + 0.10 * country.housing_pressure
                + 0.06 * country.cost_of_children
                - 0.12 * country.welfare_floor
                - 0.08 * policy.child_support,
            ),
        )

    def _earn_resources(self) -> None:
        for household in self.households.values():
            adults = [
                self.people[pid]
                for pid in household.member_ids
                if self.people[pid].alive and 22 <= self.people[pid].age <= 67
            ]
            country = self.countries[household.country_id]
            development = country.development_at(self.year, self.scenario.simulation.start_year)
            if adults:
                income = sum(
                    OCCUPATIONS[p.occupation].income
                    * (0.42 + development)
                    * (0.70 + 0.55 * p.human_capital)
                    for p in adults
                )
                household.permanent_income = 0.85 * household.permanent_income + 0.15 * income
                living_count = len([pid for pid in household.member_ids if self.people[pid].alive])
                consumption = (1.8 + 1.1 * country.cost_of_children * development) * living_count
                debt_service = household.capitals.debt * 2.2 * country.housing_pressure
                household.resources = max(0.1, household.resources + income - consumption - debt_service)
                household.capitals.human = statistics.fmean(p.human_capital for p in adults)
                household.capitals.social = min(
                    1.0,
                    0.985 * household.capitals.social
                    + 0.003 * sum(OCCUPATIONS[p.occupation].status for p in adults),
                )
                household.capitals.political = min(
                    1.0,
                    0.99 * household.capitals.political
                    + 0.012 * sum(p.occupation == "political" for p in adults)
                    + 0.004 * sum(p.occupation == "public_service" for p in adults),
                )
                household.capitals.cultural = min(
                    1.0, 0.99 * household.capitals.cultural + 0.004 * household.capitals.human
                )
                household.capitals.housing = min(
                    1.0,
                    household.capitals.housing
                    + 0.003 * (household.resources / max(1.0, country.baseline_family_resources) - 0.5),
                )
                household.capitals.debt = min(
                    1.0,
                    max(
                        0.0,
                        household.capitals.debt
                        + 0.005 * max(0.0, consumption - income)
                        - 0.003 * max(0.0, income - consumption),
                    ),
                )
            else:
                household.resources = max(0.1, household.resources * 0.97)
                household.capitals.debt = min(1.0, household.capitals.debt + 0.006)
            household.capitals.financial = household.resources
            if household.property_count > 0:
                appreciation = (
                    0.004
                    + 0.022
                    * development
                    * country.housing_pressure
                    * (1 - country.housing_supply_elasticity)
                )
                household.property_value *= 1 + appreciation
                household.capitals.housing = min(
                    1.0,
                    0.65 * household.capitals.housing
                    + 0.35
                    * min(
                        1.0,
                        household.property_value / max(1.0, country.baseline_family_resources * 2),
                    ),
                )
            elif household.resources > country.baseline_family_resources * (
                1.2 + country.housing_pressure
            ):
                purchase_probability = 0.025 * country.housing_supply_elasticity
                if self.rng.random() < purchase_probability:
                    down_payment = household.resources * 0.30
                    household.resources -= down_payment
                    household.property_count = 1.0
                    household.property_value = down_payment * 3.0
                    household.capitals.housing = 0.42
                    household.capitals.debt = min(1.0, household.capitals.debt + 0.35)
            neighborhood_advantage = household.capitals.normalized_financial(
                country.baseline_family_resources
            )
            household.school_quality = min(
                1.0,
                max(
                    0.05,
                    country.public_education_quality
                    * (1 - country.education_inequality * (0.55 - neighborhood_advantage)),
                ),
            )
            for person in adults:
                person.adult_viability = self._person_viability(person, country)

    def _career_transitions(self) -> None:
        for person in self.living_people:
            if not 22 <= person.age <= 67:
                continue
            country = self.countries[person.country_id]
            occupation = OCCUPATIONS[person.occupation]
            person.career_tenure += 1

            if person.occupation == "unemployed":
                person.unemployment_years += 1
                person.economic_status = max(0.0, person.economic_status - 0.025)
                person.health_capital = max(0.05, person.health_capital - 0.008)
                search_probability = min(
                    0.88,
                    0.28
                    + 0.35 * person.human_capital
                    + 0.22 * person.social_capital
                    + 0.15 * country.welfare_floor
                    - 0.035 * min(6, person.unemployment_years),
                )
                if self.rng.random() < search_probability:
                    if person.previous_occupation and self.rng.random() < 0.46:
                        next_occupation = person.previous_occupation
                    else:
                        next_occupation = self._choose_occupation(
                            person,
                            country,
                            [person.parent_occupation] if person.parent_occupation else [],
                        )
                    person.occupation = next_occupation
                    person.unemployment_years = 0
                    person.career_tenure = 0
                continue

            if person.occupation == "medical_trainee":
                person.training_years += 1
                person.human_capital = min(1.0, person.human_capital + 0.025)
                if person.training_years >= country.medical_training_years:
                    family_bonus = 0.08 if person.parent_occupation == "medical" else 0.0
                    pass_probability = min(
                        0.96,
                        country.medical_license_pass_rate
                        * (0.55 + 0.55 * person.human_capital)
                        + family_bonus,
                    )
                    if self.rng.random() < pass_probability:
                        person.occupation = "medical"
                        person.licensed = True
                        person.career_tenure = 0
                    elif person.training_years > country.medical_training_years + 3:
                        person.occupation = self.rng.choice(("professional", "public_service"))
                        person.licensed = False

            elif person.occupation == "civil_service":
                dynasty_bonus = (
                    0.06 * (1 - country.anti_nepotism_strength)
                    if person.parent_occupation in ("political", "civil_service")
                    else 0.0
                )
                promotion_probability = max(
                    0.002,
                    0.008
                    + 0.022 * person.human_capital
                    + 0.035 * person.political_capital
                    + 0.040 * person.patron_power
                    + dynasty_bonus
                    - 0.025 * country.civil_service_selectivity,
                )
                if self.rng.random() < promotion_probability:
                    person.occupation = "political"
                    person.political_rank = 1
                    person.career_tenure = 0

            elif person.occupation == "political":
                person.patron_power = min(
                    1.0,
                    person.patron_power + 0.008 * person.political_rank + 0.004 * person.career_tenure,
                )
                person.political_capital = min(1.0, person.political_capital + 0.006 * person.political_rank)
                if person.career_tenure % country.political_term_years == 0:
                    network_score = 0.45 * person.patron_power + 0.30 * person.political_capital
                    merit_score = 0.25 * person.human_capital
                    promotion_probability = min(0.55, 0.05 + network_score + merit_score)
                    exit_probability = 0.035 + 0.06 * country.anti_nepotism_strength * person.patron_power
                    draw = self.rng.random()
                    if draw < exit_probability:
                        person.occupation = "civil_service"
                        person.political_rank = 0
                        person.patron_power *= 0.55
                    elif draw < exit_probability + promotion_probability and person.political_rank < 4:
                        person.political_rank += 1

            occupation = OCCUPATIONS[person.occupation]
            job_loss = occupation.job_loss_risk * (0.35 + country.base_unemployment_rate * 3)
            if (
                country.soe_reform_year is not None
                and country.soe_reform_year <= self.year <= country.soe_reform_year + 3
                and occupation.sector == "soe"
            ):
                job_loss += country.soe_reform_shock
            if occupation.sector not in ("none", "licensed") and self.rng.random() < job_loss:
                person.previous_occupation = person.occupation
                person.occupation = "unemployed"
                person.unemployment_years = 1
                person.career_tenure = 0
                continue

            injury_probability = 0.001 + 0.018 * occupation.health_risk
            if self.rng.random() < injury_probability:
                severity = min(1.0, self.rng.betavariate(1.6, 4.5))
                person.injury_level = max(person.injury_level, severity)
                person.health_capital = max(0.05, person.health_capital - 0.35 * severity)
                person.economic_status = max(0.0, person.economic_status - 0.22 * severity)
                household = self.households[person.household_id]
                uninsured_cost = severity * 18.0 * (1 - country.worker_compensation)
                household.resources = max(0.1, household.resources - uninsured_cost)
                household.capitals.debt = min(1.0, household.capitals.debt + uninsured_cost / 100)

    def _form_family_branches(self) -> None:
        pools: dict[str, dict[str, list[FamilyPerson]]] = defaultdict(lambda: {"F": [], "M": []})
        for person in self.living_people:
            if 22 <= person.age <= 39 and not person.partnered:
                pools[person.country_id][person.sex].append(person)
        rate = self.scenario.simulation.adult_pairing_rate
        for country_id, sexes in pools.items():
            self.rng.shuffle(sexes["F"])
            self.rng.shuffle(sexes["M"])
            men = sexes["M"]
            country = self.countries[country_id]
            deadline = self._deadline(country)
            for woman in sexes["F"]:
                compatible = [man for man in men if abs(man.age - woman.age) <= 9]
                if not compatible:
                    continue
                # 同类婚配：教育、职业地位和资本接近者更容易进入同一配对池。
                match_weights = []
                for man in compatible:
                    status_distance = abs(man.economic_status - woman.economic_status)
                    education_distance = abs(man.education_years - woman.education_years) / 12
                    housing_distance = abs(man.housing_security - woman.housing_security)
                    distance = (
                        0.52 * status_distance
                        + 0.30 * education_distance
                        + 0.18 * housing_distance
                    )
                    weight = 0.08 + math.exp(
                        -5.2 * country.assortative_mating_strength * distance
                    )
                    if (
                        man.faction_id is not None
                        and woman.faction_id is not None
                        and man.faction_id == woman.faction_id
                    ):
                        weight *= 1.25
                    elite_mismatch = (man.economic_status >= 0.72) != (
                        woman.economic_status >= 0.72
                    )
                    if elite_mismatch:
                        weight *= 1 - country.elite_marriage_closure
                    match_weights.append(max(0.002, weight))
                man = self.rng.choices(compatible, weights=match_weights, k=1)[0]
                viability = min(woman.adult_viability, man.adult_viability)
                formation_gate = country.welfare_floor + (1 - country.welfare_floor) * sigmoid(
                    11 * (viability - deadline)
                )
                if self.rng.random() >= rate * formation_gate:
                    continue
                men.remove(man)
                primary = man if self.scenario.simulation.surname_rule == "paternal" else self.rng.choice((woman, man))
                origins = (self.households[woman.household_id], self.households[man.household_id])
                inheritance = 0.0
                for origin in origins:
                    transfer = origin.resources * self.scenario.simulation.inheritance_share
                    origin.resources -= transfer
                    inheritance += transfer
                    if origin.property_value > 0:
                        housing_gift = (
                            origin.property_value
                            * self.scenario.simulation.inheritance_share
                            * 0.22
                            * (1 - country.property_inheritance_tax)
                        )
                        origin.property_value = max(0.0, origin.property_value - housing_gift)
                        inheritance += housing_gift
                    origin.capitals.financial = origin.resources
                generation = max(origin.generation for origin in origins) + 1
                development = country.development_at(self.year, self.scenario.simulation.start_year)
                new_capitals = CapitalBundle(
                    financial=max(1.0, inheritance),
                    human=statistics.fmean((woman.human_capital, man.human_capital)),
                    social=min(1.0, 0.72 * max(woman.social_capital, man.social_capital)),
                    political=min(1.0, 0.82 * max(woman.political_capital, man.political_capital)),
                    cultural=min(1.0, 0.76 * statistics.fmean((woman.cultural_capital, man.cultural_capital))),
                    housing=min(1.0, 0.52 * max(woman.housing_security, man.housing_security)),
                    health=statistics.fmean((woman.health_capital, man.health_capital)),
                    care_time=max(0.12, 0.78 - 0.16 * development),
                    debt=min(1.0, 0.55 * statistics.fmean((woman.debt_burden, man.debt_burden)) + 0.18 * country.housing_pressure),
                )
                new_home = self._new_household(
                    clan_id=primary.clan_id,
                    surname=primary.surname,
                    country_id=country_id,
                    generation=generation,
                    resources=max(1.0, inheritance),
                    parent_ids=tuple(origin.id for origin in origins),
                    capitals=new_capitals,
                )
                self.clans[primary.clan_id].branch_ids.append(new_home.id)
                self._move_person(woman, new_home)
                self._move_person(man, new_home)
                woman.partnered = man.partnered = True
                woman.housing_security = man.housing_security = new_capitals.housing
                woman.debt_burden = man.debt_burden = new_capitals.debt
                woman.adult_viability = self._person_viability(woman, country)
                man.adult_viability = self._person_viability(man, country)

    def _move_person(self, person: FamilyPerson, destination: FamilyBranch) -> None:
        origin = self.households[person.household_id]
        if person.id in origin.member_ids:
            origin.member_ids.remove(person.id)
        destination.member_ids.append(person.id)
        person.household_id = destination.id
        person.country_id = destination.country_id

    def _desired_children(self, household: FamilyBranch, country: Country) -> float:
        development = country.development_at(self.year, self.scenario.simulation.start_year)
        urbanization = country.urbanization_at(self.year, self.scenario.simulation.start_year)
        ratio = household.resources / max(1.0, country.baseline_family_resources)
        poverty_bonus = 1.25 * max(0.0, 1.0 - ratio)
        rich_bonus = country.rich_fertility_rebound * max(0.0, math.log2(max(1.0, ratio)) - 1.0)
        development_penalty = 0.60 * development + 0.22 * urbanization
        cost_penalty = 0.35 * country.cost_of_children * development
        return max(
            0.35,
            country.initial_children_per_family * (1.0 - development_penalty) + poverty_bonus + rich_bonus - cost_penalty,
        )

    def _births(self) -> dict[str, int]:
        births: dict[str, int] = defaultdict(int)
        for household in list(self.households.values()):
            members = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            women = [p for p in members if p.sex == "F" and p.partnered and 18 <= p.age <= 44]
            men = [p for p in members if p.sex == "M" and p.partnered and 18 <= p.age <= 60]
            if not women or not men:
                continue
            mother = min(women, key=lambda person: abs(person.age - 29))
            father = men[0]
            country = self.countries[household.country_id]
            policy = country.policy_at(self.year)
            desired = self._desired_children(household, country)
            gap = max(0.0, desired - household.children_ever_born)
            age_factor = max(0.08, 1.0 - ((mother.age - 29) / 16) ** 2)
            probability = min(0.48, gap / 7.5) * age_factor * policy.fertility_multiplier
            if policy.max_children is not None and household.children_ever_born >= policy.max_children:
                probability *= 1.0 - policy.enforcement
            probability *= 1.0 + 0.20 * policy.child_support
            capacity = household.capitals.viability(country.baseline_family_resources)
            deadline = self._deadline(country)
            realization_gate = country.welfare_floor + (1 - country.welfare_floor) * sigmoid(
                13 * (capacity - deadline)
            )
            # “想生”与“能稳定成家并生育”分开：死线以下愿望可能仍高，但实现率下降。
            probability *= realization_gate
            if self.rng.random() >= probability:
                continue
            child = self._new_person(
                household,
                0,
                self.rng.choice(("F", "M")),
                mother_id=mother.id,
                father_id=father.id,
            )
            # 子女按当前家庭主姓归入该家族；跨国迁移不改变姓氏家族。
            child.clan_id = household.clan_id
            child.surname = household.surname
            household.children_ever_born += 1
            clan = self.clans[household.clan_id]
            clan.total_births += 1
            births[household.country_id] += 1
        return births

    def _international_migration(self) -> dict[str, int]:
        migrants: dict[str, int] = defaultdict(int)
        rate = self.scenario.simulation.international_migration_rate
        countries = list(self.countries.values())
        if len(countries) < 2:
            return migrants
        for household in list(self.households.values()):
            living = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            if not living or self.rng.random() >= rate:
                continue
            origin_id = household.country_id
            candidates = [country for country in countries if country.id != origin_id]
            weights = [
                0.1 + country.development_at(self.year, self.scenario.simulation.start_year)
                for country in candidates
            ]
            destination = self.rng.choices(candidates, weights=weights, k=1)[0]
            household.country_id = destination.id
            household.migration_count += 1
            for person in living:
                person.country_id = destination.id
            migrants[origin_id] += len(living)
            migrants[destination.id] += len(living)
        return migrants

    def _deaths(self) -> dict[str, int]:
        deaths: dict[str, int] = defaultdict(int)
        for person in self.living_people:
            if self.rng.random() < self._mortality_probability(person):
                self._transfer_estate_if_last_adult(person)
                person.alive = False
                person.partnered = False
                deaths[person.country_id] += 1
        for household_id, household in list(self.households.items()):
            living = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            if not living:
                del self.households[household_id]
            elif len([person for person in living if person.partnered]) < 2:
                for person in living:
                    person.partnered = False
        return deaths

    def _transfer_estate_if_last_adult(self, person: FamilyPerson) -> None:
        household = self.households.get(person.household_id)
        if household is None or household.property_value <= 0:
            return
        other_adults = [
            self.people[pid]
            for pid in household.member_ids
            if pid != person.id and self.people[pid].alive and self.people[pid].age >= 30
        ]
        if other_adults:
            return
        heirs = [
            child
            for child in self.living_people
            if (child.mother_id == person.id or child.father_id == person.id)
            and child.household_id != household.id
        ]
        if not heirs:
            return
        country = self.countries[person.country_id]
        estate = household.property_value * (1 - country.property_inheritance_tax)
        share = estate / len(heirs)
        for heir in heirs:
            destination = self.households.get(heir.household_id)
            if destination is None:
                continue
            destination.property_value += share
            destination.property_count += 1 / len(heirs)
            destination.capitals.housing = min(
                1.0, destination.capitals.housing + 0.24 / (len(heirs) ** 0.45)
            )
        household.property_value = 0.0
        household.property_count = 0.0

    def _update_clan_peaks(self) -> None:
        counts: dict[int, int] = defaultdict(int)
        for person in self.living_people:
            counts[person.clan_id] += 1
        for clan_id, count in counts.items():
            self.clans[clan_id].peak_living_members = max(self.clans[clan_id].peak_living_members, count)

    def step(self) -> list[FamilyYearStats]:
        self.year += 1
        for person in self.living_people:
            person.age += 1
        investments = self._allocate_resources()
        self._mature_young_adults()
        self._career_transitions()
        self._earn_resources()
        self._form_family_branches()
        births = self._births()
        migrants = self._international_migration()
        deaths = self._deaths()
        self._update_clan_peaks()
        stats = self._summaries(births, deaths, migrants, investments)
        self.history.extend(stats)
        return stats

    def run(self, end_year: int | None = None) -> list[FamilyYearStats]:
        target = end_year if end_year is not None else self.scenario.simulation.end_year
        if target < self.year:
            raise ValueError("目标年份不能早于当前年份")
        while self.year < target:
            self.step()
        return self.history

    def _summaries(
        self,
        births: dict[str, int],
        deaths: dict[str, int],
        migrants: dict[str, int],
        investments: dict[str, list[float]],
    ) -> list[FamilyYearStats]:
        summaries = []
        people_by_country: dict[str, list[FamilyPerson]] = defaultdict(list)
        homes_by_country: dict[str, list[FamilyBranch]] = defaultdict(list)
        clan_counts: dict[int, int] = defaultdict(int)
        for person in self.living_people:
            people_by_country[person.country_id].append(person)
            clan_counts[person.clan_id] += 1
        for household in self.households.values():
            homes_by_country[household.country_id].append(household)
        for country_id, country in self.countries.items():
            people = people_by_country[country_id]
            homes = homes_by_country[country_id]
            completed = []
            for home in homes:
                women = [self.people[pid] for pid in home.member_ids if self.people[pid].sex == "F"]
                if any(woman.age >= 45 for woman in women):
                    completed.append(home.children_ever_born)
            origin_clans = [clan for clan in self.clans.values() if clan.origin_country_id == country_id]
            bottom_cutoff = statistics.median(clan.founder_resources for clan in origin_clans)
            bottom_clans = [clan for clan in origin_clans if clan.founder_resources <= bottom_cutoff]
            extinct_bottom = sum(clan_counts[clan.id] == 0 for clan in bottom_clans)
            upward_count, matured_count = self._recent_upward.get(country_id, (0, 0))
            persistent, occupation_matured, precarious_persistent, precarious_parented = (
                self._occupation_totals[country_id]
            )
            resources = [home.resources for home in homes]
            young_adults = [person for person in people if 22 <= person.age <= 40]
            working_adults = [person for person in people if 22 <= person.age <= 67]
            political_adults = [person for person in working_adults if person.occupation == "political"]
            faction_counts: dict[int, int] = defaultdict(int)
            for person in political_adults:
                if person.faction_id is not None:
                    faction_counts[person.faction_id] += 1
            faction_total = sum(faction_counts.values())
            paired_homes = []
            elite_paired_homes = 0
            for home in homes:
                paired = [
                    self.people[pid]
                    for pid in home.member_ids
                    if self.people[pid].alive
                    and self.people[pid].partnered
                    and self.people[pid].age >= 22
                ]
                if len(paired) >= 2:
                    paired_homes.append(home)
                    elite_paired_homes += sum(person.economic_status >= 0.72 for person in paired) >= 2
            deadline = self._deadline(country)
            fertility_gaps = [
                max(0.0, self._desired_children(home, country) - home.children_ever_born)
                for home in homes
                if any(
                    self.people[pid].alive and self.people[pid].partnered
                    for pid in home.member_ids
                )
            ]
            summaries.append(
                FamilyYearStats(
                    year=self.year,
                    country_id=country_id,
                    policy=country.policy_at(self.year).name,
                    population=len(people),
                    households=len(homes),
                    living_clans=sum(clan_counts[clan.id] > 0 for clan in origin_clans),
                    births=births.get(country_id, 0),
                    deaths=deaths.get(country_id, 0),
                    migrants=migrants.get(country_id, 0),
                    mean_children_per_completed_family=(statistics.fmean(completed) if completed else 0.0),
                    mean_child_investment=(statistics.fmean(investments.get(country_id, [])) if investments.get(country_id) else 0.0),
                    upward_mobility_rate=upward_count / max(1, matured_count),
                    high_status_share=sum(person.economic_status >= 0.75 for person in people if person.age >= 22)
                    / max(1, sum(person.age >= 22 for person in people)),
                    median_household_resources=statistics.median(resources) if resources else 0.0,
                    bottom_clan_extinction_share=extinct_bottom / max(1, len(bottom_clans)),
                    below_deadline_share=sum(person.adult_viability < deadline for person in young_adults)
                    / max(1, len(young_adults)),
                    occupational_persistence_rate=persistent / max(1, occupation_matured),
                    precarious_inheritance_rate=precarious_persistent / max(1, precarious_parented),
                    fertility_realization_gap=(statistics.fmean(fertility_gaps) if fertility_gaps else 0.0),
                    political_occupation_share=sum(
                        person.occupation == "political" for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    medical_occupation_share=sum(
                        person.occupation == "medical" for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    precarious_occupation_share=sum(
                        person.occupation == "precarious" for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    unemployment_rate=sum(
                        person.occupation == "unemployed" for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    injury_rate=sum(person.injury_level > 0 for person in working_adults)
                    / max(1, len(working_adults)),
                    homeownership_rate=sum(home.property_count > 0 for home in homes)
                    / max(1, len(homes)),
                    licensed_physician_share=sum(
                        person.occupation == "medical" and person.licensed
                        for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    state_sector_share=sum(
                        OCCUPATIONS[person.occupation].sector in ("state", "soe")
                        for person in working_adults
                    )
                    / max(1, len(working_adults)),
                    political_dynasty_share=sum(
                        person.parent_occupation in ("political", "civil_service")
                        for person in political_adults
                    )
                    / max(1, len(political_adults)),
                    faction_concentration=sum(
                        (count / max(1, faction_total)) ** 2 for count in faction_counts.values()
                    ),
                    elite_marriage_share=elite_paired_homes / max(1, len(paired_homes)),
                )
            )
        return summaries
