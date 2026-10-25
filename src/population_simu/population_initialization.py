"""Narrow training-only exposure-share diagnostic, preserving whole households.

This does not reconstruct a full joint age-sex-household distribution. Integer
household age translations fit one margin without altering links or RNG state.
"""
from __future__ import annotations

import math


def age_sex_counts(world):
    return {f"{sex}_{band}": sum(
        p.sex == sex and lower <= p.age <= upper for p in world.living_people
    ) for sex in ("F", "M") for band, lower, upper in (
        ("0_14", 0, 14), ("15_44", 15, 44), ("45_plus", 45, 120))}


def match_female_exposure_share(world, target_share: float):
    if not math.isfinite(target_share) or not 0 < target_share < 1:
        raise ValueError("target share must lie strictly between zero and one")
    before = age_sex_counts(world)
    target = round(len(world.living_people) * target_share)
    remaining = target - before["F_15_44"]
    candidates = []
    for household in world.households.values():
        members = [world.people[pid] for pid in household.member_ids]
        old = sum(p.sex == "F" and 15 <= p.age <= 44 for p in members)
        if not any(p.sex == "F" for p in members):
            continue
        lower = max(-30, -min(p.age for p in members))
        adults = [p.age for p in members if p.age >= 18]
        if adults:
            lower = max(lower, 18 - min(adults))
        upper = min(30, 110 - max(p.age for p in members))
        women_ages = [p.age for p in members if p.sex == "F"]
        for shift in range(-30, 31):
            if shift == 0 or not lower <= shift <= upper:
                continue
            change = sum(15 <= age + shift <= 44 for age in women_ages) - old
            if change and change * remaining > 0:
                candidates.append((abs(shift) * len(members), abs(shift),
                                   household.id, shift, change))
    used = set()
    shifted_people = 0
    maximum_shift = 0
    for _, _, hid, shift, change in sorted(candidates):
        if hid in used or abs(remaining - change) >= abs(remaining):
            continue
        for pid in world.households[hid].member_ids:
            world.people[pid].age += shift
            shifted_people += 1
        used.add(hid)
        remaining -= change
        maximum_shift = max(maximum_shift, abs(shift))
        if remaining == 0:
            break
    if remaining:
        raise ValueError(f"household age translation cannot match margin: residual={remaining}")
    # The initial summary must describe the adjusted world, without new RNG draws.
    world.history[0] = world._summarize(births=0, deaths=0, migrations=0)
    return {"before": before, "after": age_sex_counts(world),
            "target_share": target_share, "target_count": target,
            "shifted_households": len(used), "shifted_people": shifted_people,
            "maximum_absolute_age_shift": maximum_shift,
            "scope": "one female-15-44 margin; not full age-sex calibration"}
