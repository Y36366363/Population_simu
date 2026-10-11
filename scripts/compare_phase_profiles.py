"""Compare two matched FamilyWorld phase profiles without treating timing as a gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


SEGMENTS = ("early", "late")
STATE_FIELDS = ("end_population", "end_households", "end_transfer_records")
PRESERVED_DIAGNOSTICS = ("_desired_children", "same_kin", "shares_occupation")


def _ratio(candidate: float, baseline: float) -> float | None:
    return round(candidate / baseline, 6) if baseline else None


def compare_profiles(baseline: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    """Return an auditable per-seed comparison for configuration-matched profiles."""
    if baseline.get("kind") != "family_world_phase_profile" or candidate.get("kind") != baseline.get("kind"):
        raise ValueError("both inputs must be FamilyWorld phase profiles")
    if baseline.get("configuration") != candidate.get("configuration"):
        raise ValueError("profile configurations must match exactly")

    baseline_runs = {int(run["seed"]): run for run in baseline["runs"]}
    candidate_runs = {int(run["seed"]): run for run in candidate["runs"]}
    if baseline_runs.keys() != candidate_runs.keys():
        raise ValueError("profile seed sets must match exactly")

    rows: list[dict[str, object]] = []
    for seed in sorted(baseline_runs):
        base_run = baseline_runs[seed]
        cand_run = candidate_runs[seed]
        for segment in SEGMENTS:
            base = base_run[segment]
            cand = cand_run[segment]
            state_equal = all(base[field] == cand[field] for field in STATE_FIELDS)
            base_diag = base["nested_diagnostics"]
            cand_diag = cand["nested_diagnostics"]
            preserved_calls_equal = all(
                base_diag[name]["calls"] == cand_diag[name]["calls"]
                for name in PRESERVED_DIAGNOSTICS
            )
            desired_calls = int(cand_diag["_desired_children"]["calls"])
            baseline_region_calls = int(base_diag["same_region"]["calls"])
            candidate_region_calls = int(cand_diag["same_region"]["calls"])
            # The legacy code evaluated same_region once for every peer and once
            # for every non-self colleague. The merged pass evaluates it once per
            # peer, hence candidate = (baseline + desired calls) / 2 exactly.
            merged_scan_relation_ok = (
                2 * candidate_region_calls == baseline_region_calls + desired_calls
            )
            phase_ratios = {
                name: _ratio(
                    float(cand["phases"][name]["seconds_per_year"]),
                    float(base["phases"][name]["seconds_per_year"]),
                )
                for name in ("_summaries", "_births")
            }
            rows.append({
                "seed": seed,
                "segment": segment,
                "state_endpoints_equal": state_equal,
                "preserved_diagnostic_calls_equal": preserved_calls_equal,
                "merged_scan_call_relation_ok": merged_scan_relation_ok,
                "baseline_step_seconds_per_year": base["step_seconds_per_year"],
                "candidate_step_seconds_per_year": cand["step_seconds_per_year"],
                "candidate_to_baseline_step_ratio": _ratio(
                    float(cand["step_seconds_per_year"]),
                    float(base["step_seconds_per_year"]),
                ),
                "same_region_calls": {
                    "baseline": baseline_region_calls,
                    "candidate": candidate_region_calls,
                    "reduction_fraction": round(
                        1 - candidate_region_calls / baseline_region_calls, 6
                    ),
                },
                "candidate_to_baseline_phase_ratio": phase_ratios,
            })

    def _median_ratio(segment: str, key: str) -> float:
        values = [float(row[key]) for row in rows if row["segment"] == segment]
        return round(statistics.median(values), 6)

    aggregate = {
        "all_state_endpoints_equal": all(row["state_endpoints_equal"] for row in rows),
        "all_preserved_diagnostic_calls_equal": all(
            row["preserved_diagnostic_calls_equal"] for row in rows
        ),
        "all_merged_scan_call_relations_hold": all(
            row["merged_scan_call_relation_ok"] for row in rows
        ),
        "median_candidate_to_baseline_step_ratio": {
            segment: _median_ratio(segment, "candidate_to_baseline_step_ratio")
            for segment in SEGMENTS
        },
        "total_same_region_calls": {
            segment: {
                "baseline": sum(
                    row["same_region_calls"]["baseline"]
                    for row in rows if row["segment"] == segment
                ),
                "candidate": sum(
                    row["same_region_calls"]["candidate"]
                    for row in rows if row["segment"] == segment
                ),
            }
            for segment in SEGMENTS
        },
    }
    for segment, counts in aggregate["total_same_region_calls"].items():
        counts["reduction_fraction"] = round(1 - counts["candidate"] / counts["baseline"], 6)

    baseline_sources = baseline.get("source_sha256", {})
    candidate_sources = candidate.get("source_sha256", {})
    changed_sources = sorted(
        path for path in set(baseline_sources) | set(candidate_sources)
        if baseline_sources.get(path) != candidate_sources.get(path)
    )
    report = {
        "schema_version": 1,
        "kind": "matched_family_world_phase_profile_comparison",
        "scope": "strict state/call equivalence plus machine-specific timing diagnostics",
        "configuration": candidate["configuration"],
        "changed_source_files": changed_sources,
        "rows": rows,
        "aggregate": aggregate,
        "acceptance": {
            "passed": all((
                aggregate["all_state_endpoints_equal"],
                aggregate["all_preserved_diagnostic_calls_equal"],
                aggregate["all_merged_scan_call_relations_hold"],
            )),
            "timing_is_not_an_acceptance_gate": True,
        },
        "interpretation_boundary": [
            "endpoint equality is weaker than the separate yearly full-fingerprint equivalence test",
            "cProfile timing is machine- and load-specific and is not a correctness gate",
            "this comparison validates an implementation refactor, not demographic realism",
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
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = compare_profiles(baseline, candidate)
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
