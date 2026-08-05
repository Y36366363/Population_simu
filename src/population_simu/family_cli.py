from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .family_config import FamilyScenario
from .family_world import FamilyWorld


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="姓氏家族—家庭分支人口模拟沙盘")
    parser.add_argument("scenario", type=Path, help="家庭模型 JSON 情景")
    parser.add_argument("--end-year", type=int, help="覆盖情景终止年份")
    parser.add_argument("--output", type=Path, default=Path("outputs/family_timeline.csv"))
    args = parser.parse_args()

    scenario = FamilyScenario.from_json(args.scenario)
    world = FamilyWorld(scenario)
    world.run(args.end_year)
    _write_csv(args.output, [row.flat_dict() for row in world.history])

    clan_output = args.output.with_name(f"{args.output.stem}_clans.csv")
    clan_rows = []
    living_counts = {clan_id: 0 for clan_id in world.clans}
    occupation_counts = {clan_id: {} for clan_id in world.clans}
    for person in world.living_people:
        living_counts[person.clan_id] += 1
        if person.age >= 22:
            counts = occupation_counts[person.clan_id]
            counts[person.occupation] = counts.get(person.occupation, 0) + 1
    for clan in world.clans.values():
        clan_occupations = occupation_counts[clan.id]
        adult_count = sum(clan_occupations.values())
        dominant_occupation = (
            max(clan_occupations, key=clan_occupations.get) if clan_occupations else "none"
        )
        clan_rows.append(
            {
                "clan_id": clan.id,
                "surname": clan.surname,
                "origin_country": clan.origin_country_id,
                "founder_resources": round(clan.founder_resources, 4),
                "branches_created": len(clan.branch_ids),
                "total_births": clan.total_births,
                "living_members": living_counts[clan.id],
                "peak_living_members": clan.peak_living_members,
                "extinct": int(living_counts[clan.id] == 0),
                "dominant_occupation": dominant_occupation,
                "political_share": round(clan_occupations.get("political", 0) / max(1, adult_count), 5),
                "medical_share": round(clan_occupations.get("medical", 0) / max(1, adult_count), 5),
                "precarious_share": round(clan_occupations.get("precarious", 0) / max(1, adult_count), 5),
            }
        )
    _write_csv(clan_output, clan_rows)

    print(f"情景：{scenario.name}，{scenario.simulation.start_year}—{world.year}")
    for country in scenario.countries:
        first = next(row for row in world.history if row.country_id == country.id)
        last = next(row for row in reversed(world.history) if row.country_id == country.id)
        print(
            f"{country.name}: 人口 {first.population:,} → {last.population:,}；"
            f"户均完成生育 {last.mean_children_per_completed_family:.2f}；"
            f"高阶层占比 {last.high_status_share:.1%}；"
            f"死线以下青年 {last.below_deadline_share:.1%}；"
            f"职业同类继承 {last.occupational_persistence_rate:.1%}；"
            f"底部家族消失 {last.bottom_clan_extinction_share:.1%}"
        )
    print(f"年度结果：{args.output.resolve()}")
    print(f"家族结果：{clan_output.resolve()}")


if __name__ == "__main__":
    main()
