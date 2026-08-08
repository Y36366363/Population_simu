"""家庭世界的共同随机数情景比较 CLI。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .family_config import FamilyScenario
from .family_world import FamilyWorld
from .monte_carlo import common_random_seeds, summarize


def run_replicates(scenario_paths: list[str], years: int, replicates: int, seed: int) -> list[dict]:
    seeds = common_random_seeds(seed, replicates)
    collected: dict[tuple[str, str, str], list[float]] = {}
    for path in scenario_paths:
        for random_seed in seeds:
            scenario = FamilyScenario.from_json(path)
            scenario = FamilyScenario(
                name=scenario.name,
                simulation=scenario.simulation.__class__(**{
                    **scenario.simulation.__dict__, "random_seed": random_seed
                }),
                countries=scenario.countries,
            )
            target = min(scenario.simulation.end_year, scenario.simulation.start_year + years)
            rows = FamilyWorld(scenario).run(target)
            final_by_country = {row.country_id: row for row in rows if row.year == target}
            for country, row in final_by_country.items():
                for metric in ("population", "households", "median_household_resources", "high_status_share"):
                    collected.setdefault((Path(path).name, country, metric), []).append(float(getattr(row, metric)))
    output = []
    for (scenario, country, metric), values in sorted(collected.items()):
        row = {"scenario": scenario, "country": country, "metric": metric}
        row.update(summarize(values).as_dict())
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="用共同随机数比较家庭人口情景并输出置信区间")
    parser.add_argument("scenarios", nargs="+", help="家庭情景 JSON 文件")
    parser.add_argument("--years", type=int, default=30)
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260808)
    parser.add_argument("--output", type=Path, default=Path("outputs/family_monte_carlo.csv"))
    args = parser.parse_args()
    if args.years < 0 or args.replicates < 1:
        raise SystemExit("years 不能为负，replicates 必须至少为 1")
    rows = run_replicates(args.scenarios, args.years, args.replicates, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()
