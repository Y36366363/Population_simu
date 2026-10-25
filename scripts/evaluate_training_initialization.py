"""Frozen 2017 exposure-share initialization experiment; retain all outcomes.

Primary comparison: absolute 2021 mean GFR bias, adjusted versus original
dynamic-exposure World. This is a previously inspected historical diagnostic.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from population_simu.benchmarks import household_simulator_runner
from population_simu.population_initialization import match_female_exposure_share
from evaluate_dynamic_exposure_holdout import load_panel, _median_predictions, _error_summary
from random import Random


def load_targets(path, train):
    table = json.loads(path.read_text())
    header = table[0]
    records = [dict(zip(header, row)) for row in table[1:]]
    targets = {}
    state_map = {str(row["state"]).zfill(2): str(row["entity"]) for row in train}
    for row in records:
        if row["state"] not in state_map:
            continue
        # ACS B01001 female ages 15-17 through 40-44 (estimate columns 30-38).
        total = int(row["B01001_001E"])
        female = sum(int(row[f"B01001_{index:03d}E"]) for index in range(30, 39))
        if total <= 0 or not 0 < female < total:
            raise ValueError("invalid ACS margin")
        targets[state_map[row["state"]]] = {
            "year": 2017, "population": total, "female_15_44": female,
            "share": female / total,
            "female_total_share": int(row["B01001_026E"]) / total,
        }
    if set(targets) != set(state_map.values()) or len(targets) != 50:
        raise ValueError("ACS training margins must match all 50 states")
    return targets


def bootstrap_2021(observed, left, right, draws=2000):
    states = sorted(str(row["entity"]) for row in observed)
    actual = {str(row["entity"]): float(row["asfr_15_44"]) for row in observed}
    rng = Random(20261025)
    bias_deltas, mae_deltas = [], []
    for _ in range(draws):
        selected = [states[rng.randrange(len(states))] for _ in states]
        a = [left[(s, 2021)] - actual[s] for s in selected]
        b = [right[(s, 2021)] - actual[s] for s in selected]
        bias_deltas.append(abs(statistics.mean(b)) - abs(statistics.mean(a)))
        mae_deltas.append(statistics.mean(map(abs, b)) - statistics.mean(map(abs, a)))
    def summarize(values):
        values = sorted(values)
        return {"mean": statistics.mean(values), "lower_95": values[50],
                "upper_95": values[1949],
                "fraction_below_zero": sum(v < 0 for v in values) / draws}
    return {"resampling": "paired states; national shared shocks not accounted for",
            "draws": draws, "absolute_mean_bias_delta": summarize(bias_deltas),
            "mae_delta": summarize(mae_deltas),
            "definition": "adjusted - original; negative favors initialization adjustment"}


def evaluate(panel, acs, replicates=20, scale_paths=100):
    rows = load_panel(panel)
    train = [r for r in rows if r["year"] <= 2017]
    test = [r for r in rows if r["year"] in (2018, 2019, 2021)]
    targets = load_targets(acs, train)
    audits = defaultdict(list)
    def initialize(world, entity, year):
        if year != 2017 or targets[entity]["year"] != 2017:
            raise ValueError("only frozen 2017 training margins may initialize this study")
        audit = match_female_exposure_share(world, targets[entity]["share"])
        audits[entity].append(audit)

    models = {
        "original_dynamic": household_simulator_runner(
            exposure_denominator="dynamic_female_15_44", independent_scale_paths=scale_paths),
        "training_share_adjusted_dynamic": household_simulator_runner(
            exposure_denominator="dynamic_female_15_44", independent_scale_paths=scale_paths,
            initial_population_transform=initialize),
    }
    reports, points, raw_predictions = {}, {}, {}
    for name, runner in models.items():
        print(f"running {name}", flush=True)
        start = perf_counter()
        samples = [runner(train, [2018, 2019, 2021], 20261020 + i)
                   for i in range(replicates)]
        point = _median_predictions(samples)
        expected = {(r["entity"], r["year"]) for r in test}
        if set(point) != expected or any(len(sample) != len(expected) for sample in samples):
            raise ValueError("incomplete predictions")
        points[name] = point
        raw_predictions[name] = samples
        reports[name] = {"overall": _error_summary(test, point),
                         "by_year": {str(y): _error_summary(
                             [r for r in test if r["year"] == y], point)
                             for y in (2018, 2019, 2021)},
                         "elapsed_seconds": perf_counter() - start}
        print(json.dumps({name: reports[name]}), flush=True)

    state_results = []
    for row in test:
        if row["year"] != 2021:
            continue
        key = (row["entity"], 2021)
        actual = row["asfr_15_44"]
        a, b = points["original_dynamic"][key], points["training_share_adjusted_dynamic"][key]
        state_results.append({"entity": key[0], "actual": actual,
                              "original": a, "adjusted": b,
                              "absolute_error_delta": abs(b - actual) - abs(a - actual)})
    return {"kind": "training_only_2017_exposure_share_initialization_diagnostic",
            "design": {"calibration_years": list(range(2010, 2018)),
                       "evaluation_years": [2018, 2019, 2021],
                       "primary_endpoint": "absolute 2021 mean GFR bias",
                       "initial_people": 1200, "replicates": replicates,
                       "independent_scale_paths": scale_paths,
                       "target_seeds": [20261020 + i for i in range(replicates)],
                       "test_population_fields_passed_to_runner": False,
                       "scope": "one female-15-44 share, not full age-sex calibration",
                       "initialization": "minimum-cost whole-household age translations, max 30 years; no RNG draws",
                       "previously_inspected_test_years": True},
            "reports": reports, "training_targets": targets,
            "state_results_2021": state_results,
            "states_improved_2021": sum(r["absolute_error_delta"] < 0 for r in state_results),
            "paired_2021": bootstrap_2021([r for r in test if r["year"] == 2021],
                points["original_dynamic"], points["training_share_adjusted_dynamic"]),
            "initialization_audits": dict(audits), "predictions": raw_predictions,
            "limits": ["ACS resident survey vs PEP civilian denominators have different universes/vintages",
                       "only one observed margin is matched; sex ratio and age composition within 15-44 remain synthetic",
                       "household age translation preserves links and parent-child gaps, but education and parity remain synthetic",
                       "equal target seeds do not keep event-level RNG aligned after trajectories diverge",
                       "same independent seed bank reused within a model; not repeated scale-bank uncertainty",
                       "previously inspected years; no fresh independent historical validation"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--acs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.panel = args.panel.resolve()
    args.acs = args.acs.resolve()
    report = evaluate(args.panel, args.acs)
    files = [args.panel, args.acs, Path(__file__),
             ROOT / "scripts/evaluate_dynamic_exposure_holdout.py",
             ROOT / "src/population_simu/population_initialization.py",
             ROOT / "src/population_simu/benchmarks.py",
             ROOT / "src/population_simu/world.py",
             ROOT / "src/population_simu/household_calibration.py"]
    report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in files}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"reports": report["reports"], "paired": report["paired_2021"],
                      "states_improved": report["states_improved_2021"]}, indent=2))
