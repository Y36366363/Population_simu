"""Compare exact aggregate social-norm profiles with the ordered-index baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


SEGMENTS = ("early", "late")
STATE_FIELDS = ("end_population", "end_households", "end_transfer_records")


def compare_aggregate_profiles(
    baseline: dict[str, object], candidate: dict[str, object]
) -> dict[str, object]:
    if baseline.get("kind") != "family_world_phase_profile" or candidate.get("kind") != baseline.get("kind"):
        raise ValueError("both inputs must be FamilyWorld phase profiles")
    if baseline.get("configuration") != candidate.get("configuration"):
        raise ValueError("profile configurations must match exactly")
    old_runs = {int(run["seed"]): run for run in baseline["runs"]}
    new_runs = {int(run["seed"]): run for run in candidate["runs"]}
    if old_runs.keys() != new_runs.keys():
        raise ValueError("profile seed sets must match exactly")

    rows = []
    for seed in sorted(old_runs):
        for segment in SEGMENTS:
            old = old_runs[seed][segment]
            new = new_runs[seed][segment]
            old_diag = old["nested_diagnostics"]
            new_diag = new["nested_diagnostics"]
            old_rate = float(old["step_seconds_per_year"])
            new_rate = float(new["step_seconds_per_year"])
            rows.append({
                "seed": seed,
                "segment": segment,
                "state_endpoints_equal": all(
                    old[field] == new[field] for field in STATE_FIELDS
                ),
                "desired_children_calls_equal": (
                    old_diag["_desired_children"]["calls"]
                    == new_diag["_desired_children"]["calls"]
                ),
                "index_build_calls_equal": (
                    old_diag["_build_social_norm_index"]["calls"]
                    == new_diag["_build_social_norm_index"]["calls"]
                ),
                "birth_updates_match_modeled_births": (
                    new_diag["record_birth"]["calls"] == new["modeled_births"]
                ),
                "modeled_births": new["modeled_births"],
                "candidate_to_baseline_step_ratio": round(new_rate / old_rate, 6),
                "candidate_to_baseline_phase_ratio": {
                    phase: round(
                        float(new["phases"][phase]["seconds_per_year"])
                        / float(old["phases"][phase]["seconds_per_year"]),
                        6,
                    )
                    for phase in ("_summaries", "_births")
                },
            })

    checks = (
        "state_endpoints_equal",
        "desired_children_calls_equal",
        "index_build_calls_equal",
        "birth_updates_match_modeled_births",
    )
    aggregate = {
        f"all_{check}": all(row[check] for row in rows)
        for check in checks
    }
    aggregate["median_candidate_to_baseline_step_ratio"] = {
        segment: round(statistics.median(
            float(row["candidate_to_baseline_step_ratio"])
            for row in rows if row["segment"] == segment
        ), 6)
        for segment in SEGMENTS
    }
    report = {
        "schema_version": 1,
        "kind": "exact_social_norm_aggregate_profile_comparison",
        "scope": "strict structural checks and machine-specific timing diagnostics",
        "configuration": candidate["configuration"],
        "rows": rows,
        "aggregate": aggregate,
        "acceptance": {
            "passed": all(aggregate[f"all_{check}"] for check in checks),
            "timing_is_not_an_acceptance_gate": True,
        },
        "interpretation_boundary": [
            "yearly complete-state fingerprints are checked separately",
            "integer count/sum equivalence applies to current small integer child counts",
            "timings are machine-specific and do not establish empirical validity",
        ],
    }
    json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare_aggregate_profiles(
        json.loads(args.baseline.read_text(encoding="utf-8")),
        json.loads(args.candidate.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "acceptance": report["acceptance"],
        "median_step_ratios": report["aggregate"]["median_candidate_to_baseline_step_ratio"],
    }, ensure_ascii=False))
    return 0 if report["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
