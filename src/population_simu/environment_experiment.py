"""环境冲击单因素敏感性分析 CLI。"""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path

from .family_config import FamilyScenario
from .family_world import FamilyWorld
from .monte_carlo import common_random_seeds, summarize


def run_sensitivity(
    scenario_path: str,
    years: int,
    replicates: int,
    seed: int,
    probabilities: tuple[float, ...],
) -> list[dict]:
    base = FamilyScenario.from_json(scenario_path)
    seeds = common_random_seeds(seed, replicates)
    rows: list[dict] = []
    for probability in probabilities:
        metrics = {"population": [], "environmental_stress": [], "fiscal_balance": [], "climate_events": []}
        for random_seed in seeds:
            countries = tuple(
                replace(country, climate_shock_probability=probability)
                for country in base.countries
            )
            scenario = replace(
                base,
                countries=countries,
                simulation=replace(base.simulation, random_seed=random_seed),
            )
            target = min(scenario.simulation.end_year, scenario.simulation.start_year + years)
            final = FamilyWorld(scenario).run(target)
            for country_id in {country.id for country in countries}:
                row = next(item for item in reversed(final) if item.country_id == country_id)
                for metric in metrics:
                    metrics[metric].append(float(getattr(row, metric)))
        for metric, values in metrics.items():
            summary = summarize(values).as_dict()
            rows.append({"shock_probability": probability, "metric": metric, **summary})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="环境冲击概率的共同随机数敏感性分析")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--years", type=int, default=30)
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260810)
    parser.add_argument("--probabilities", type=float, nargs="+", default=(0.0, 0.01, 0.03, 0.06))
    parser.add_argument("--output", type=Path, default=Path("outputs/environment_sensitivity.csv"))
    args = parser.parse_args()
    if args.years < 0 or args.replicates < 1 or any(value < 0 or value > 1 for value in args.probabilities):
        raise SystemExit("years/replicates 或 probabilities 参数无效")
    rows = run_sensitivity(str(args.scenario), args.years, args.replicates, args.seed, tuple(args.probabilities))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()

