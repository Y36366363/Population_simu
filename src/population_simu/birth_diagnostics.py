"""Read-only observations immediately before World's existing birth draws."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json

from .world import World


def state_fingerprint(world):
    """Include every World instance field except the diagnostic observations."""
    state = {key: value for key, value in vars(world).items()
             if key not in {"birth_observations", "rng", "people", "households", "history",
                            "scenario", "regions"}}
    state.update(scenario=asdict(world.scenario),
                 regions={key: asdict(value) for key, value in world.regions.items()},
                 people=[asdict(p) for p in world.people.values()],
                 households=[asdict(h) for h in world.households.values()],
                 history=[asdict(s) for s in world.history], rng=world.rng.getstate())
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


class ObservedBirthWorld(World):
    def __init__(self, scenario):
        super().__init__(scenario)
        self.birth_observations = []

    def _births(self):
        candidates = []
        women_count = partnered_count = 0
        for household in list(self.households.values()):
            members = [self.people[pid] for pid in household.member_ids if self.people[pid].alive]
            women_count += sum(p.sex == "F" and 18 <= p.age <= 44 for p in members)
            women = [p for p in members if p.sex == "F" and p.partnered and 18 <= p.age <= 44]
            partnered_count += len(women)
            men = [p for p in members if p.sex == "M" and p.partnered and 18 <= p.age <= 60]
            if not women or not men:
                continue
            mother = min(women, key=lambda p: abs(p.age - 29))
            age_factor = max(0.08, 1 - ((mother.age - 29) / 16) ** 2)
            parity_factor = 1 / (1 + 0.55 * household.children_ever_born)
            constant = (self.scenario.simulation.baseline_tfr / 18.0
                        * self.scenario.policy.fertility_multiplier
                        * (1 + 0.25 * self.scenario.policy.childcare_support))
            probability = min(0.45, constant * age_factor * parity_factor)
            candidates.append({"household_id": household.id, "mother_id": mother.id,
                               "age": mother.age, "parity": household.children_ever_born,
                               "age_factor": age_factor, "parity_factor": parity_factor,
                               "probability": probability})
        # Delegate all events and all RNG operations to the unchanged engine.
        births = super()._births()
        self.birth_observations.append({
            "year": self.year, "women_18_44": women_count,
            "partnered_women_18_44": partnered_count,
            "candidate_households": len(candidates),
            "expected_births": sum(c["probability"] for c in candidates),
            "actual_births": births,
            "age_counts": dict(Counter(str(c["age"]) for c in candidates)),
            "parity_counts": dict(Counter(str(c["parity"]) for c in candidates)),
            "candidates": candidates,
        })
        return births


def decompose(first, last):
    """Symmetric exact accounting of E=N*p; this is not causal attribution."""
    n0, n1 = first["candidate_households"], last["candidate_households"]
    p0 = first["expected_births"] / n0 if n0 else 0.0
    p1 = last["expected_births"] / n1 if n1 else 0.0
    return {"candidate_count_contribution": (n1 - n0) * (p0 + p1) / 2,
            "mean_probability_contribution": (p1 - p0) * (n0 + n1) / 2,
            "expected_birth_change": last["expected_births"] - first["expected_births"]}
