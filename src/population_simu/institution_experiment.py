from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path

from .dynasty_experiment import DynastyParameters, run_cell


REGIMES = {
    "baseline": {},
    "public_education": {"public_education": 1.0},
    "housing_reform": {"housing_reform": 1.0},
    "anti_nepotism": {"anti_nepotism": 1.0, "institutional_openness": 0.78},
    "high_welfare": {"high_welfare": 1.0},
}


def run_institution_experiment(
    *,
    resources: float = 100,
    child_counts: tuple[int, ...] = (1, 2, 3),
    trials: int = 5_000,
    generations: int = 4,
    seed: int = 20260805,
) -> list[dict]:
    baseline = DynastyParameters(
        development=0.65,
        housing_pressure=0.75,
        welfare_floor=0.08,
        institutional_openness=0.50,
        occupational_inheritance=0.55,
        material_deadline=58.0,
    )
    rows = []
    for regime_name, overrides in REGIMES.items():
        parameters = replace(baseline, **overrides)
        for children in child_counts:
            row = run_cell(
                initial_resources=resources,
                initial_children=children,
                trials=trials,
                generations=generations,
                seed=seed + children,
                parameters=parameters,
            )
            row = {"regime": regime_name, **row}
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="公共教育、住房、反裙带和高福利制度开关实验")
    parser.add_argument("--resources", type=float, default=100)
    parser.add_argument("--children", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--trials", type=int, default=5_000)
    parser.add_argument("--generations", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/institution_switch_experiment.csv")
    )
    args = parser.parse_args()
    rows = run_institution_experiment(
        resources=args.resources,
        child_counts=tuple(args.children),
        trials=args.trials,
        generations=args.generations,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['regime']} / {row['initial_children']}孩："
            f"延续 {row['survival_to_final_generation']:.1%}，"
            f"末代后代 {row['mean_final_generation_descendants']:.3f}，"
            f"职业继承 {row['occupational_persistence_rate']:.1%}"
        )
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()
