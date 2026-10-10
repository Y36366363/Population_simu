"""Fail unless two world fingerprint captures match in every modeled state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if baseline["configuration"] != candidate["configuration"]:
        raise SystemExit("fingerprint configurations differ")
    baseline_runs = {int(run["seed"]): run for run in baseline["runs"]}
    candidate_runs = {int(run["seed"]): run for run in candidate["runs"]}
    if baseline_runs.keys() != candidate_runs.keys():
        raise SystemExit("fingerprint seed sets differ")
    comparisons = []
    for seed in baseline_runs:
        old, new = baseline_runs[seed], candidate_runs[seed]
        modeled_fields = (
            "yearly_fingerprints", "final_population", "final_households",
            "transfer_records", "rng_state_sha256",
        )
        fields = {field: old[field] == new[field] for field in modeled_fields}
        if not all(fields.values()):
            raise SystemExit(f"modeled state differs for seed {seed}: {fields}")
        old_seconds = float(old["step_seconds"])
        new_seconds = float(new["step_seconds"])
        comparisons.append({
            "seed": seed,
            "modeled_fields_equal": fields,
            "baseline_step_seconds": old_seconds,
            "candidate_step_seconds": new_seconds,
            "candidate_to_baseline_runtime_ratio": new_seconds / old_seconds,
            "runtime_reduction_share": 1.0 - new_seconds / old_seconds,
        })
    report = {
        "schema_version": 1,
        "kind": "strict_refactor_equivalence",
        "scope": "state equivalence and same-session timing; not empirical validation",
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "baseline_family_world_sha256": baseline["family_world_sha256"],
        "candidate_family_world_sha256": candidate["family_world_sha256"],
        "configuration": baseline["configuration"],
        "comparisons": comparisons,
        "all_modeled_states_equal": True,
        "source_changed": baseline["family_world_sha256"] != candidate["family_world_sha256"],
        "timing_note": "wall-clock results are machine-specific and were not used to relax equivalence",
    }
    if not report["source_changed"]:
        raise SystemExit("candidate family_world source did not change")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "all_modeled_states_equal": True,
        "runtime_reduction_shares": [row["runtime_reduction_share"] for row in comparisons],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
