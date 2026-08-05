from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .config import Scenario
from .world import World


def write_csv(world: World, output: Path) -> None:
    rows = [stats.flat_dict() for stats in world.history]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="家庭级人口、迁移与社会流动模拟")
    parser.add_argument("scenario", type=Path, help="JSON 情景文件")
    parser.add_argument("--years", type=int, help="覆盖情景中的模拟年数")
    parser.add_argument("--output", type=Path, default=Path("outputs/result.csv"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scenario = Scenario.from_json(args.scenario)
    world = World(scenario)
    world.run(args.years)
    write_csv(world, args.output)
    first, last = world.history[0], world.history[-1]
    print(f"情景：{scenario.name}")
    print(f"人口：{first.population:,} → {last.population:,}")
    print(f"65 岁以上占比：{first.senior_share:.1%} → {last.senior_share:.1%}")
    print(f"高等教育占比：{first.tertiary_share:.1%} → {last.tertiary_share:.1%}")
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()

