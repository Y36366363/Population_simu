"""Summarize persistent birth candidates without retaining person-level records."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def summarize(result):
    for record in result["records"]:
        first, final = record["years"][0], record["years"][-1]
        a = {r["household_id"]: r for r in first["candidates"]}
        b = {r["household_id"]: r for r in final["candidates"]}
        common = a.keys() & b.keys()
        age = parity = 0.0
        # No cap is active in this frozen study; require that before attribution.
        for hid in common:
            x, y = a[hid], b[hid]
            constant = x["probability"] / (x["age_factor"] * x["parity_factor"])
            constant2 = y["probability"] / (y["age_factor"] * y["parity_factor"])
            assert abs(constant - constant2) < 1e-12 and x["probability"] < 0.45 and y["probability"] < 0.45
            age += constant * (y["age_factor"] - x["age_factor"]) * (y["parity_factor"] + x["parity_factor"]) / 2
            parity += constant * (y["parity_factor"] - x["parity_factor"]) * (y["age_factor"] + x["age_factor"]) / 2
        row = {"persistent_count": len(common), "exited_count": len(a.keys()-b.keys()),
               "entered_count": len(b.keys()-a.keys()),
               "persistent_probability_change": sum(b[i]["probability"]-a[i]["probability"] for i in common),
               "persistent_age_contribution": age, "persistent_parity_contribution": parity,
               "exit_expected_birth_loss": -sum(a[i]["probability"] for i in a.keys()-b.keys()),
               "entry_expected_birth_gain": sum(b[i]["probability"] for i in b.keys()-a.keys()),
               "same_selected_mother_count": sum(a[i]["mother_id"] == b[i]["mother_id"] for i in common)}
        assert abs(age + parity - row["persistent_probability_change"]) < 1e-10
        assert abs(row["persistent_probability_change"] + row["exit_expected_birth_loss"] +
                   row["entry_expected_birth_gain"] - record["decomposition"]["expected_birth_change"]) < 1e-10
        record["cohort_accounting"] = row
        for year in record["years"]:
            year.pop("candidates", None)
    for adjusted in (False, True):
        selected = [r["cohort_accounting"] for r in result["records"] if r["adjusted"] == adjusted]
        result["summary"][str(adjusted)]["cohort_means"] = {
            key: statistics.mean(r[key] for r in selected) for key in selected[0]}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.source.read_text()))
    result["raw_source_sha256"] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    result["source_sha256"]["scripts/summarize_birth_cohorts.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(result["summary"], indent=2))
