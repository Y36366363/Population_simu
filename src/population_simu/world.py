from __future__ import annotations

from collections import defaultdict
import math
import random

from .config import RegionConfig, Scenario
from .models import Household, Person, YearStats


class World:
    """离散年度、家庭级的随机人口模拟世界。

    第一版有意保持透明：所有概率函数都在本文件中，方便后续替换成
    真实生命表、生育率曲线、迁移矩阵或统计估计模型。
    """

    def __init__(self, scenario: Scenario):
        scenario.validate()
        self.scenario = scenario
        self.rng = random.Random(scenario.simulation.random_seed)
        self.regions = {region.id: region for region in scenario.regions}
        self.people: dict[int, Person] = {}
        self.households: dict[int, Household] = {}
        self.next_person_id = 1
        self.next_household_id = 1
        self.year = scenario.simulation.start_year
        self.history: list[YearStats] = []
        self._seed_population(scenario.simulation.initial_people)
        self.history.append(self._summarize(births=0, deaths=0, migrations=0))

    def _weighted_region(self) -> RegionConfig:
        regions = list(self.regions.values())
        return self.rng.choices(regions, weights=[r.initial_share for r in regions], k=1)[0]

    def _new_household(self, region_id: str) -> Household:
        household = Household(id=self.next_household_id, region_id=region_id)
        self.households[household.id] = household
        self.next_household_id += 1
        return household

    def _new_person(self, *, age: int, sex: str, household: Household, **kwargs) -> Person:
        person = Person(
            id=self.next_person_id,
            age=age,
            sex=sex,
            household_id=household.id,
            region_id=household.region_id,
            **kwargs,
        )
        self.people[person.id] = person
        household.member_ids.append(person.id)
        self.next_person_id += 1
        return person

    def _seed_population(self, target: int) -> None:
        """生成结构合理但非真实国家校准数据的初始家庭。"""
        while len(self.people) < target:
            region = self._weighted_region()
            household = self._new_household(region.id)
            remaining = target - len(self.people)
            if remaining == 1:
                age = self.rng.randint(20, 80)
                self._new_person(
                    age=age,
                    sex=self.rng.choice(("F", "M")),
                    household=household,
                    education=self._education_for_age(age, region),
                    income_tier=self.rng.choices((0, 1, 2), (0.25, 0.55, 0.20))[0],
                )
                continue

            # 混合年轻/中年家庭与老年家庭，避免初始世界几乎没有老人。
            adult_age = (
                self.rng.randint(65, 84)
                if self.rng.random() < 0.14
                else min(68, max(20, round(self.rng.triangular(22, 68, 38))))
            )
            has_pair = remaining >= 2 and self.rng.random() < 0.72
            first = self._new_person(
                age=adult_age,
                sex="F" if has_pair else self.rng.choice(("F", "M")),
                household=household,
                education=self._education_for_age(adult_age, region),
                income_tier=self.rng.choices((0, 1, 2), (0.28, 0.55, 0.17))[0],
                partnered=has_pair,
            )
            second = None
            if has_pair:
                second_age = max(18, min(75, adult_age + self.rng.randint(-3, 5)))
                second = self._new_person(
                    age=second_age,
                    sex="M",
                    household=household,
                    education=self._education_for_age(second_age, region),
                    income_tier=self.rng.choices((0, 1, 2), (0.25, 0.55, 0.20))[0],
                    partnered=True,
                )
            max_children = min(3, target - len(self.people)) if adult_age <= 58 else 0
            child_count = self.rng.choices(range(max_children + 1), weights=[4, 4, 2, 1][: max_children + 1])[0]
            for _ in range(child_count):
                age = self.rng.randint(0, min(20, max(0, adult_age - 18)))
                self._new_person(
                    age=age,
                    sex=self.rng.choice(("F", "M")),
                    household=household,
                    education=self._education_for_age(age, region),
                    income_tier=0,
                    mother_id=first.id if first.sex == "F" else None,
                    father_id=second.id if second else None,
                )
                household.children_ever_born += 1

    def _education_for_age(self, age: int, region: RegionConfig) -> int:
        if age < 6:
            return 0
        if age < 15:
            return 1
        if age < 20:
            return 2
        tertiary_chance = 0.12 + 0.55 * region.education_access
        return 3 if self.rng.random() < tertiary_chance else 2

    @staticmethod
    def _mortality_probability(age: int, sex: str) -> float:
        infant = 0.004 if age == 0 else 0.0
        accident = 0.00035 + (0.00055 if sex == "M" and 15 <= age <= 35 else 0)
        ageing = 0.00002 * math.exp(max(0, age - 30) / 10.5)
        return min(0.55, infant + accident + ageing)

    def _education_transitions(self) -> None:
        policy = self.scenario.policy
        for person in self.living_people:
            region = self.regions[person.region_id]
            access = min(0.98, region.education_access * (0.7 + 0.6 * policy.education_investment))
            if person.age == 6:
                person.education = max(person.education, 1)
            elif person.age == 15 and self.rng.random() < access:
                person.education = max(person.education, 2)
            elif person.age == 19 and self.rng.random() < access * 0.72:
                person.education = 3

    def _income_transitions(self) -> None:
        policy = self.scenario.policy
        for person in self.living_people:
            if not 20 <= person.age <= 64:
                continue
            region = self.regions[person.region_id]
            upward = 0.012 + 0.018 * person.education + 0.03 * region.opportunity * policy.upward_mobility
            downward = 0.018 + 0.012 * (1 - region.opportunity)
            draw = self.rng.random()
            if draw < upward and person.income_tier < 2:
                person.income_tier += 1
            elif draw > 1 - downward and person.income_tier > 0:
                person.income_tier -= 1

    def _form_households(self) -> None:
        rate = self.scenario.simulation.pair_formation_rate
        by_region: dict[str, dict[str, list[Person]]] = defaultdict(lambda: {"F": [], "M": []})
        for person in self.living_people:
            if 22 <= person.age <= 40 and not person.partnered:
                by_region[person.region_id][person.sex].append(person)
        for pools in by_region.values():
            self.rng.shuffle(pools["F"])
            self.rng.shuffle(pools["M"])
            pair_count = min(len(pools["F"]), len(pools["M"]))
            for woman, man in zip(pools["F"][:pair_count], pools["M"][:pair_count]):
                if abs(woman.age - man.age) > 10 or self.rng.random() >= rate:
                    continue
                new_home = self._new_household(woman.region_id)
                self._move_person(woman, new_home)
                self._move_person(man, new_home)
                woman.partnered = man.partnered = True

    def _move_person(self, person: Person, destination: Household) -> None:
        origin = self.households[person.household_id]
        if person.id in origin.member_ids:
            origin.member_ids.remove(person.id)
        destination.member_ids.append(person.id)
        person.household_id = destination.id
        person.region_id = destination.region_id

    def _births(self) -> int:
        births = 0
        tfr = self.scenario.simulation.baseline_tfr
        policy = self.scenario.policy
        for household in list(self.households.values()):
            members = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            women = [p for p in members if p.sex == "F" and p.partnered and 18 <= p.age <= 44]
            partnered_men = [p for p in members if p.sex == "M" and p.partnered and 18 <= p.age <= 60]
            if not women or not partnered_men:
                continue
            mother = min(women, key=lambda p: abs(p.age - 29))
            age_factor = max(0.08, 1 - ((mother.age - 29) / 16) ** 2)
            parity_factor = 1 / (1 + 0.55 * household.children_ever_born)
            support_factor = 1 + 0.25 * policy.childcare_support
            annual_probability = min(
                0.45,
                # baseline_tfr 是一生总和口径；18 是对“有伴侣家庭”的首版
                # 暴露年数近似。真实校准时应替换为年龄别/孩次别生育率。
                (tfr / 18.0) * policy.fertility_multiplier * age_factor * parity_factor * support_factor,
            )
            if self.rng.random() < annual_probability:
                father = partnered_men[0]
                self._new_person(
                    age=0,
                    sex=self.rng.choice(("F", "M")),
                    household=household,
                    education=0,
                    income_tier=0,
                    mother_id=mother.id,
                    father_id=father.id,
                )
                household.children_ever_born += 1
                births += 1
        return births

    def _migrate_households(self) -> int:
        migrations = 0
        base_rate = self.scenario.simulation.household_migration_rate
        openness = self.scenario.policy.migration_openness
        region_list = list(self.regions.values())
        for household in list(self.households.values()):
            living = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            if not living or self.rng.random() >= base_rate * openness:
                continue
            origin = self.regions[household.region_id]
            candidates = [r for r in region_list if r.id != origin.id]
            if not candidates:
                continue
            scores = [max(0.01, r.wage_index + r.opportunity - 0.8 * r.housing_cost) for r in candidates]
            destination = self.rng.choices(candidates, weights=scores, k=1)[0]
            origin_score = origin.wage_index + origin.opportunity - 0.8 * origin.housing_cost
            destination_score = destination.wage_index + destination.opportunity - 0.8 * destination.housing_cost
            educated = sum(p.education >= 3 for p in living) / len(living)
            acceptance = 0.35 + 0.25 * educated + 0.20 * max(-0.5, destination_score - origin_score)
            if self.rng.random() >= acceptance:
                continue
            household.region_id = destination.id
            household.moves += 1
            for person in living:
                person.region_id = destination.id
            migrations += len(living)
        return migrations

    def _deaths(self) -> int:
        deaths = 0
        for person in self.living_people:
            if self.rng.random() < self._mortality_probability(person.age, person.sex):
                person.alive = False
                person.partnered = False
                deaths += 1
        # 单人死亡不应让空家庭永久留在统计里；丧偶者恢复为未配对状态。
        for household_id, household in list(self.households.items()):
            living = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            if not living:
                del self.households[household_id]
            elif len([p for p in living if p.partnered]) < 2:
                for person in living:
                    person.partnered = False
        return deaths

    @property
    def living_people(self) -> list[Person]:
        return [person for person in self.people.values() if person.alive]

    def step(self) -> YearStats:
        for person in self.living_people:
            person.age += 1
        self.year += 1
        self._education_transitions()
        self._income_transitions()
        self._form_households()
        births = self._births()
        migrations = self._migrate_households()
        deaths = self._deaths()
        stats = self._summarize(births=births, deaths=deaths, migrations=migrations)
        self.history.append(stats)
        return stats

    def run(self, years: int | None = None) -> list[YearStats]:
        for _ in range(years if years is not None else self.scenario.simulation.years):
            self.step()
        return self.history

    def _summarize(self, *, births: int, deaths: int, migrations: int) -> YearStats:
        people = self.living_people
        population = len(people)
        divisor = max(1, population)
        by_region = {region_id: 0 for region_id in self.regions}
        for person in people:
            by_region[person.region_id] += 1
        return YearStats(
            year=self.year,
            population=population,
            households=len(self.households),
            births=births,
            deaths=deaths,
            migrations=migrations,
            mean_age=sum(p.age for p in people) / divisor,
            child_share=sum(p.age < 15 for p in people) / divisor,
            working_age_share=sum(15 <= p.age < 65 for p in people) / divisor,
            senior_share=sum(p.age >= 65 for p in people) / divisor,
            tertiary_share=sum(p.education >= 3 for p in people if p.age >= 25)
            / max(1, sum(p.age >= 25 for p in people)),
            top_income_share=sum(p.income_tier == 2 for p in people if 20 <= p.age < 65)
            / max(1, sum(20 <= p.age < 65 for p in people)),
            population_by_region=by_region,
        )
