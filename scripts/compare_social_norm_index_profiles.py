"""Validate phase-local social-norm index profiles against an unindexed baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


SEGMENTS = ("early", "late")
STATE_FIELDS = ("end_population", "end_households", "end_transfer_records")
REMOVED_PAIRWISE_DIAGNOSTICS = ("same_region", "same_kin", "shares_occupation")


def compare_index_profiles(
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
            years = int(new["years"])
            state_equal = all(old[field] == new[field] for field in STATE_FIELDS)
            desired_calls_equal = (
                old_diag["_desired_children"]["calls"]
                == new_diag["_desired_children"]["calls"]
            )
            removed_pairwise_calls = all(
                int(new_diag[name]["calls"]) == 0
                for name in REMOVED_PAIRWISE_DIAGNOSTICS
            )
            index_builds_exact = int(new_diag["_build_social_norm_index"]["calls"]) == 2 * years
            old_rate = float(old["step_seconds_per_year"])
            new_rate = float(new["step_seconds_per_year"])
            rows.append({
                "seed": seed,
                "segment": segment,
                "state_endpoints_equal": state_equal,
                "desired_children_calls_equal": desired_calls_equal,
                "pairwise_network_calls_removed": removed_pairwise_calls,
                "index_builds_exactly_twice_per_year": index_builds_exact,
                "baseline_step_seconds_per_year": old_rate,
                "candidate_step_seconds_per_year": new_rate,
                "candidate_to_baseline_step_ratio": round(new_rate / old_rate, 6),
                "baseline_pairwise_calls": {
                    name: int(old_diag[name]["calls"])
                    for name in REMOVED_PAIRWISE_DIAGNOSTICS
                },
                "candidate_index_build_calls": int(
                    new_diag["_build_social_norm_index"]["calls"]
                ),
            })

    aggregate = {
        "all_state_endpoints_equal": all(row["state_endpoints_equal"] for row in rows),
        "all_desired_children_calls_equal": all(
            row["desired_children_calls_equal"] for row in rows
        ),
        "all_pairwise_network_calls_removed": all(
            row["pairwise_network_calls_removed"] for row in rows
        ),
        "all_index_build_counts_exact": all(
            row["index_builds_exactly_twice_per_year"] for row in rows
        ),
        "median_candidate_to_baseline_step_ratio": {
            segment: round(statistics.median(
                float(row["candidate_to_baseline_step_ratio"])
                for row in rows if row["segment"] == segment
            ), 6)
            for segment in SEGMENTS
        },
    }
    report = {
        "schema_version": 1,
        "kind": "phase_local_social_norm_index_profile_comparison",
        "scope": "implementation equivalence and machine-specific runtime diagnostics",
        "configuration": candidate["configuration"],
        "rows": rows,
        "aggregate": aggregate,
        "acceptance": {
            "passed": all((
                aggregate["all_state_endpoints_equal"],
                aggregate["all_desired_children_calls_equal"],
                aggregate["all_pairwise_network_calls_removed"],
                aggregate["all_index_build_counts_exact"],
            )),
            "timing_is_not_an_acceptance_gate": True,
        },
        "interpretation_boundary": [
            "yearly complete-state fingerprints are checked in a separate artifact",
            "profile timings are machine- and load-specific",
            "runtime improvement does not establish empirical or causal validity",
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
    report = compare_index_profiles(
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
