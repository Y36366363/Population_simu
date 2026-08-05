from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import random
import statistics


def run_cell(*, resources: float, children: int, trials: int, seed: int) -> dict[str, float | int]:
    """固定总资源与子女数，重复生成家庭，观察集中与分散投资的取舍。"""
    rng = random.Random(seed)
    per_child_investment = resources / (children**0.92)
    parent_status = min(0.8, 0.05 + 0.15 * math.log10(1 + resources))
    successful_children = 0
    any_success = 0
    best_scores: list[float] = []
    all_scores: list[float] = []
    for _ in range(trials):
        family_scores = []
        for _ in range(children):
            potential = rng.betavariate(2, 2)
            investment_signal = min(1.0, math.log1p(per_child_investment) / 4.5)
            luck = rng.gauss(0, 0.11)
            rare_breakthrough = 0.32 if potential > 0.91 and rng.random() < 0.18 else 0.0
            score = min(
                1.0,
                max(
                    0.0,
                    0.08
                    + 0.34 * potential
                    + 0.30 * investment_signal
                    + 0.09
                    + 0.12 * parent_status
                    + luck
                    + rare_breakthrough,
                ),
            )
            family_scores.append(score)
            all_scores.append(score)
        successes = sum(score >= 0.70 for score in family_scores)
        successful_children += successes
        any_success += successes > 0
        best_scores.append(max(family_scores))
    return {
        "family_resources": resources,
        "children": children,
        "investment_per_child": round(per_child_investment, 4),
        "mean_child_score": round(statistics.fmean(all_scores), 5),
        "per_child_success_rate": round(successful_children / (trials * children), 5),
        "family_any_success_rate": round(any_success / trials, 5),
        "mean_best_child_score": round(statistics.fmean(best_scores), 5),
        "expected_successful_children": round(successful_children / trials, 5),
        "trials": trials,
    }


def run_experiment(resources: list[float], child_counts: list[int], trials: int, seed: int) -> list[dict]:
    rows = []
    for resource_index, resource in enumerate(resources):
        for children in child_counts:
            rows.append(
                run_cell(
                    resources=resource,
                    children=children,
                    trials=trials,
                    seed=seed + resource_index * 10_000 + children,
                )
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="固定家庭资源的一孩/二孩/三孩 Monte Carlo 实验")
    parser.add_argument("--resources", nargs="+", type=float, default=[5, 100, 300])
    parser.add_argument("--children", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--trials", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--output", type=Path, default=Path("outputs/resource_micro_experiment.csv"))
    args = parser.parse_args()
    if any(value <= 0 for value in args.resources):
        raise SystemExit("resources 必须大于 0")
    if any(value < 1 for value in args.children):
        raise SystemExit("children 必须至少为 1")

    rows = run_experiment(args.resources, args.children, args.trials, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"资源 {row['family_resources']:g} / {row['children']}孩："
            f"单个成功 {row['per_child_success_rate']:.1%}，"
            f"至少一个成功 {row['family_any_success_rate']:.1%}，"
            f"每孩投入 {row['investment_per_child']:.1f}"
        )
    print(f"结果：{args.output.resolve()}")


if __name__ == "__main__":
    main()

