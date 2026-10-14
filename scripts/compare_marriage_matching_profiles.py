"""Compare exact marriage age-window profiles with the full-scan baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


SEGMENTS = ("early", "late")
STATE_FIELDS = ("end_population", "end_households", "end_transfer_records")


def compare_matching_profiles(
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
            years = int(new["years"])
            helper_calls = int(
                new["nested_diagnostics"]["_men_by_woman_age"]["calls"]
            )
            old_phase = old["phases"]["_form_family_branches"]
            new_phase = new["phases"]["_form_family_branches"]
            old_rate = float(old_phase["seconds_per_year"])
            new_rate = float(new_phase["seconds_per_year"])
            old_step = float(old["step_seconds_per_year"])
            new_step = float(new["step_seconds_per_year"])
            rows.append({
                "seed": seed,
                "segment": segment,
                "state_endpoints_equal": all(
                    old[field] == new[field] for field in STATE_FIELDS
                ),
                "pairing_phase_calls_equal": old_phase["calls"] == new_phase["calls"],
                "age_window_builds_cover_each_year": (
                    helper_calls > 0 and helper_calls % years == 0
                ),
                "age_window_build_calls": helper_calls,
                "country_pools_per_year": helper_calls // years,
                "candidate_to_baseline_pairing_ratio": round(new_rate / old_rate, 6),
                "candidate_to_baseline_step_ratio": round(new_step / old_step, 6),
            })

    country_pool_counts = {row["country_pools_per_year"] for row in rows}
    aggregate = {
        "all_state_endpoints_equal": all(row["state_endpoints_equal"] for row in rows),
        "all_pairing_phase_calls_equal": all(
            row["pairing_phase_calls_equal"] for row in rows
        ),
        "all_age_window_builds_cover_each_year": all(
            row["age_window_builds_cover_each_year"] for row in rows
        ),
        "country_pool_count_stable": len(country_pool_counts) == 1,
        "country_pools_per_year": next(iter(country_pool_counts)) if len(country_pool_counts) == 1 else None,
        "median_candidate_to_baseline_pairing_ratio": {
            segment: round(statistics.median(
                float(row["candidate_to_baseline_pairing_ratio"])
                for row in rows if row["segment"] == segment
            ), 6)
            for segment in SEGMENTS
        },
        "median_candidate_to_baseline_step_ratio": {
            segment: round(statistics.median(
                float(row["candidate_to_baseline_step_ratio"])
                for row in rows if row["segment"] == segment
            ), 6)
            for segment in SEGMENTS
        },
    }
    required = (
        "all_state_endpoints_equal",
        "all_pairing_phase_calls_equal",
        "all_age_window_builds_cover_each_year",
        "country_pool_count_stable",
    )
    report = {
        "schema_version": 1,
        "kind": "exact_marriage_age_window_profile_comparison",
        "scope": "matching-order structural checks and machine-specific timing",
        "configuration": candidate["configuration"],
        "rows": rows,
        "aggregate": aggregate,
        "acceptance": {
            "passed": all(aggregate[key] for key in required),
            "timing_is_not_an_acceptance_gate": True,
        },
        "interpretation_boundary": [
            "yearly full-state and RNG fingerprints are checked separately",
            "the index preserves shuffled order and performs no approximate matching",
            "runtime results do not validate marriage behavior against observations",
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
    report = compare_matching_profiles(
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
        "pairing_ratios": report["aggregate"]["median_candidate_to_baseline_pairing_ratio"],
    }, ensure_ascii=False))
    return 0 if report["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
