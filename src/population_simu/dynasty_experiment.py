from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import math
from pathlib import Path
import random
import statistics

from .capitals import CapitalBundle, sigmoid
from .occupations import BASE_OCCUPATION_WEIGHT, INHERITANCE_CHANNEL, OCCUPATIONS


@dataclass
class Endowment:
    capitals: CapitalBundle
    occupation: str
    potential: float


@dataclass(frozen=True)
class DynastyParameters:
    development: float = 0.65
    housing_pressure: float = 0.75
    welfare_floor: float = 0.08
    institutional_openness: float = 0.5
    occupational_inheritance: float = 0.55
    material_deadline: float = 58.0

    @property
    def capital_deadline(self) -> float:
        return min(
            0.8,
            0.25
            + 0.18 * self.development
            + 0.18 * self.housing_pressure
            - 0.14 * self.welfare_floor,
        )


def choose_occupation(
    rng: random.Random,
    endowment: CapitalBundle,
    potential: float,
    parent_occupation: str,
    parameters: DynastyParameters,
) -> str:
    occupation_ids = list(OCCUPATIONS)
    weights = []
    for occupation_id in occupation_ids:
        occupation = OCCUPATIONS[occupation_id]
        human_access = sigmoid(9 * (endowment.human - occupation.human_gate))
        social_access = sigmoid(8 * (endowment.social - occupation.social_gate))
        political_access = sigmoid(9 * (endowment.political - occupation.political_gate))
        gate = 0.54 * human_access + 0.28 * social_access + 0.18 * political_access
        if occupation_id in ("routine", "precarious", "dependent"):
            gate += 0.35 * (1 - endowment.human)
        inherited = 0.0
        if occupation_id == parent_occupation:
            inherited = 2.8
        elif occupation_id in INHERITANCE_CHANNEL[parent_occupation]:
            inherited = 1.2
        network = 1 + parameters.occupational_inheritance * inherited * (
            1.35 - parameters.institutional_openness
        )
        merit = 0.55 + parameters.institutional_openness * (0.45 + 0.8 * potential)
        weights.append(
            max(0.0005, gate * network * merit * BASE_OCCUPATION_WEIGHT[occupation_id])
        )
    return rng.choices(occupation_ids, weights=weights, k=1)[0]


def allocate_children(
    rng: random.Random,
    household: CapitalBundle,
    child_count: int,
    parent_occupation: str,
    parameters: DynastyParameters,
) -> list[Endowment]:
    if child_count <= 0:
        return []
    financial = household.financial / (child_count**0.96)
    children = []
    for _ in range(child_count):
        potential = rng.betavariate(2, 2)
        human = min(
            1.0,
            0.10
            + 0.48 * household.human
            + 0.30 * sigmoid((financial - 35) / 16)
            + 0.14 * potential,
        )
        capitals = CapitalBundle(
            financial=financial,
            human=human,
            social=min(1.0, household.social * 0.74 / (child_count**0.22) + 0.08 * potential),
            political=min(1.0, household.political * 0.82 / (child_count**0.16)),
            cultural=min(1.0, household.cultural * 0.78 / (child_count**0.24) + 0.06 * human),
            housing=min(1.0, household.housing * 0.62 / (child_count**0.70)),
            health=min(1.0, household.health * 0.88 + rng.gauss(0, 0.04)),
            care_time=min(1.0, household.care_time / (child_count**0.78)),
            debt=min(1.0, household.debt + 0.10 * max(0, child_count - 1)),
        )
        occupation = choose_occupation(rng, capitals, potential, parent_occupation, parameters)
        children.append(Endowment(capitals=capitals, occupation=occupation, potential=potential))
    return children


def reproduction_probability(adult: Endowment, parameters: DynastyParameters) -> float:
    viability = adult.capitals.viability(100.0)
    # 现金/住房有一个可随社会条件改变的软阈值；不是“低于即归零”的硬切线。
    material_gate = sigmoid((adult.capitals.financial - parameters.material_deadline) / 8.5)
    capital_gate = sigmoid(15 * (viability - parameters.capital_deadline))
    occupation_security = 0.65 + 0.35 * OCCUPATIONS[adult.occupation].status
    return min(
        0.98,
        parameters.welfare_floor
        + (1 - parameters.welfare_floor) * material_gate * capital_gate * occupation_security,
    )


def next_generation(
    rng: random.Random,
    adults: list[Endowment],
    parameters: DynastyParameters,
) -> tuple[list[Endowment], int, int]:
    children: list[Endowment] = []
    inherited_occupations = 0
    occupation_children = 0
    for adult in adults:
        if rng.random() >= reproduction_probability(adult, parameters):
            continue
        # 同类婚配让伴侣资本与本人相关，但保留显著随机性。
        partner_factor = math.exp(rng.gauss(-0.08, 0.30))
        combined_financial = adult.capitals.financial * (1 + partner_factor)
        combined = adult.capitals.copy()
        combined.financial = combined_financial
        combined.human = min(1.0, adult.capitals.human * (0.88 + 0.18 * partner_factor))
        combined.social = min(1.0, adult.capitals.social * (1.25 + 0.12 * partner_factor))
        combined.political = min(1.0, adult.capitals.political * (1.20 + 0.10 * partner_factor))
        combined.cultural = min(1.0, adult.capitals.cultural * 1.18)
        combined.housing = min(1.0, adult.capitals.housing * (1.28 + 0.12 * partner_factor))
        combined.health = min(1.0, adult.capitals.health * 0.98)
        combined.care_time = min(1.0, 0.72 - 0.12 * parameters.development)
        combined.debt = min(1.0, adult.capitals.debt + 0.08 * parameters.housing_pressure)
        capacity = combined.viability(100.0)
        desired = max(
            0.4,
            1.60
            + 2.1 * capacity
            - 0.48 * parameters.development
            - 0.24 * parameters.housing_pressure
            + 0.30 * max(0.0, math.log2(max(1.0, combined_financial / 100))),
        )
        child_count = min(4, poisson(rng, desired))
        offspring = allocate_children(rng, combined, child_count, adult.occupation, parameters)
        occupation_children += len(offspring)
        inherited_occupations += sum(child.occupation == adult.occupation for child in offspring)
        children.extend(offspring)
    return children, inherited_occupations, occupation_children


def poisson(rng: random.Random, mean: float) -> int:
    limit = math.exp(-mean)
    product = 1.0
    count = 0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def run_cell(
    *,
    initial_resources: float,
    initial_children: int,
    trials: int,
    generations: int,
    seed: int,
    parameters: DynastyParameters,
    founder_occupation: str = "professional",
) -> dict[str, float | int | str]:
    rng = random.Random(seed)
    survived = 0
    final_counts = []
    total_descendants = []
    exact_occupation = 0
    occupation_children = 0
    initial_household = CapitalBundle(
        financial=initial_resources,
        human=0.68,
        social=0.52,
        political=0.18,
        cultural=0.62,
        housing=0.68,
        health=0.82,
        care_time=0.78,
        debt=0.12,
    )
    for _ in range(trials):
        adults = allocate_children(
            rng, initial_household, initial_children, founder_occupation, parameters
        )
        descendant_count = len(adults)
        for _generation in range(2, generations + 1):
            adults, inherited, compared = next_generation(rng, adults, parameters)
            exact_occupation += inherited
            occupation_children += compared
            descendant_count += len(adults)
            if not adults:
                break
        survived += bool(adults)
        final_counts.append(len(adults))
        total_descendants.append(descendant_count)
    return {
        "initial_resources": initial_resources,
        "initial_children": initial_children,
        "generations": generations,
        "survival_to_final_generation": round(survived / trials, 5),
        "extinction_before_final_generation": round(1 - survived / trials, 5),
        "mean_final_generation_descendants": round(statistics.fmean(final_counts), 5),
        "median_final_generation_descendants": statistics.median(final_counts),
        "mean_total_descendants": round(statistics.fmean(total_descendants), 5),
        "occupational_persistence_rate": round(exact_occupation / max(1, occupation_children), 5),
        "material_deadline": parameters.material_deadline,
        "capital_deadline": round(parameters.capital_deadline, 5),
        "trials": trials,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="多维资本、动态死线与家族延续实验")
    parser.add_argument("--resources", nargs="+", type=float, default=[100])
    parser.add_argument("--children", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--generations", type=int, default=4)
    parser.add_argument("--trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--material-deadline", type=float, default=58.0)
    parser.add_argument("--development", type=float, default=0.65)
    parser.add_argument("--housing-pressure", type=float, default=0.75)
    parser.add_argument("--welfare-floor", type=float, default=0.08)
    parser.add_argument("--institutional-openness", type=float, default=0.5)
    parser.add_argument("--occupational-inheritance", type=float, default=0.55)
    parser.add_argument("--output", type=Path, default=Path("outputs/dynasty_deadline_experiment.csv"))
    args = parser.parse_args()
    parameters = DynastyParameters(
        development=args.development,
        housing_pressure=args.housing_pressure,
        welfare_floor=args.welfare_floor,
        institutional_openness=args.institutional_openness,
        occupational_inheritance=args.occupational_inheritance,
        material_deadline=args.material_deadline,
    )
    rows = []
    for resource_index, resources in enumerate(args.resources):
        for children in args.children:
            rows.append(
                run_cell(
                    initial_resources=resources,
                    initial_children=children,
                    trials=args.trials,
                    generations=args.generations,
                    seed=args.seed + 10_000 * resource_index + children,
                    parameters=parameters,
                )
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"资源 {row['initial_resources']:g} / 首代{row['initial_children']}孩："
            f"延续到第{row['generations']}代 {row['survival_to_final_generation']:.1%}，"
            f"末代平均后代 {row['mean_final_generation_descendants']:.3f}，"
            f"职业同类继承 {row['occupational_persistence_rate']:.1%}"
        )
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()
