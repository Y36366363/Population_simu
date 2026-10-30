"""Frozen birth-stage accounting on the 2026-10-25 study paths."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from population_simu.birth_diagnostics import ObservedBirthWorld, state_fingerprint, decompose
from population_simu.world import World
from population_simu.config import Scenario, SimulationConfig, PolicyConfig, RegionConfig
from population_simu.household_calibration import calibrate_household_parameters
from population_simu.population_initialization import match_female_exposure_share
from evaluate_dynamic_exposure_holdout import load_panel
from evaluate_training_initialization import load_targets


def run(panel, acs):
    train = [r for r in load_panel(panel) if r["year"] <= 2017]
    calibration = calibrate_household_parameters(train)
    targets = load_targets(acs, train)
    records = []
    matches = 0
    for adjusted in (False, True):
        print(f"running adjusted={adjusted}", flush=True)
        for entity in sorted(targets):
            last = next(r for r in train if r["entity"] == entity and r["year"] == 2017)
            housing = last["housing_cost_burden"]
            for seed in range(20261020, 20261040):
                scenario = Scenario(
                    name=f"household_adapter_{entity}",
                    simulation=SimulationConfig(start_year=2017, years=4, initial_people=1200,
                        random_seed=seed, baseline_tfr=max(0.2, min(4.0,
                            last["asfr_15_44"] * calibration.tfr_conversion_years /
                            (1000 * max(0.1, calibration.partnership_exposure))))),
                    policy=PolicyConfig(childcare_support=max(0, min(1, 1-housing)),
                                        fertility_multiplier=calibration.housing_multiplier(housing)),
                    regions=(RegionConfig("state", entity, 1.0),))
                observed, baseline = ObservedBirthWorld(scenario), World(scenario)
                if adjusted:
                    for world in (observed, baseline):
                        match_female_exposure_share(world, targets[entity]["share"])
                for year in range(2018, 2022):
                    obs_stat, base_stat = observed.step(), baseline.step()
                    assert state_fingerprint(observed) == state_fingerprint(baseline)
                    matches += 1
                    row = observed.birth_observations[-1]
                    assert row["actual_births"] == obs_stat.births == base_stat.births
                first, final = observed.birth_observations[0], observed.birth_observations[-1]
                accounting = decompose(first, final)
                assert abs(accounting["candidate_count_contribution"] +
                           accounting["mean_probability_contribution"] -
                           accounting["expected_birth_change"]) < 1e-10
                for row in observed.birth_observations:
                    row["mean_probability"] = (row["expected_births"] / row["candidate_households"]
                                                if row["candidate_households"] else 0)
                    row["mean_age_factor"] = statistics.mean(c["age_factor"] for c in row["candidates"])
                    row["mean_parity_factor"] = statistics.mean(c["parity_factor"] for c in row["candidates"])
                    # Keep household probabilities for cohort follow-up in 2018/2021 only.
                    if row["year"] not in (2018, 2021):
                        row.pop("candidates")
                records.append({"entity": entity, "seed": seed, "adjusted": adjusted,
                                "years": observed.birth_observations, "decomposition": accounting})
        print(f"completed adjusted={adjusted}", flush=True)
    summary = {}
    for adjusted in (False, True):
        chosen = [r for r in records if r["adjusted"] == adjusted]
        annual = {}
        for year in range(2018, 2022):
            rows = [next(r for r in p["years"] if r["year"] == year) for p in chosen]
            annual[str(year)] = {metric: statistics.mean(r[metric] for r in rows) for metric in (
                "candidate_households", "expected_births", "actual_births", "mean_probability",
                "mean_age_factor", "mean_parity_factor", "women_18_44", "partnered_women_18_44")}
        summary[str(adjusted)] = {"annual_means": annual,
            "decomposition_mean": {metric: statistics.mean(p["decomposition"][metric] for p in chosen)
                                   for metric in chosen[0]["decomposition"]}}
    return {"design": {"training_years": list(range(2010, 2018)),
                        "forecast_years": [2018,2019,2020,2021], "states": 50,
                        "seeds": list(range(20261020,20261040)), "initial_people": 1200,
                        "decomposition": "2018 to 2021 expected births = candidate households * mean probability",
                        "same_seed_does_not_imply_event_alignment_between_initializations": True},
            "full_year_state_and_rng_matches": matches, "summary": summary, "records": records,
            "limits": ["internal accounting, not causal decomposition",
                       "mean probability change includes candidate composition and individual aging/parity",
                       "2018 is first forecast year, not observed 2017 baseline",
                       "no new historical prediction or calibration performed"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panel = ROOT / "data/observed/us_2021/us_research_panel_2010_2021_comparable.csv"
    acs = ROOT / "data/observed/us_2021/acs_b01001_2017_initialization.json"
    result = run(panel, acs)
    result["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (panel, acs, Path(__file__).resolve(), ROOT / "src/population_simu/world.py",
                  ROOT / "src/population_simu/birth_diagnostics.py",
                  ROOT / "src/population_simu/population_initialization.py")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"matches": result["full_year_state_and_rng_matches"],
                      "summary": result["summary"]}, indent=2))
