"""Conservative labels for historical model-comparison evidence."""

from __future__ import annotations


def assess_rolling_origin_evidence(folds: list[dict[str, object]]) -> dict[str, object]:
    if not folds:
        raise ValueError("at least one rolling-origin fold is required")
    target_years = sorted({
        int(year) for fold in folds for year in fold.get("test_years", [])
    })
    if not target_years:
        raise ValueError("rolling-origin folds require test years")
    training_sets = [set(map(int, fold.get("train_years", []))) for fold in folds]
    training_windows_overlap = any(
        training_sets[left] & training_sets[right]
        for left in range(len(training_sets))
        for right in range(left + 1, len(training_sets))
    )
    prior_tests_enter_later_training = any(
        test_year in training_sets[later]
        for index, fold in enumerate(folds)
        for test_year in map(int, fold.get("test_years", []))
        for later in range(index + 1, len(folds))
    )
    level = (
        "exploratory_repeated_historical_check"
        if len(target_years) < 5 or prior_tests_enter_later_training
        else "limited_out_of_sample_validation"
    )
    limitations = []
    if len(target_years) < 5:
        limitations.append(f"only {len(target_years)} independent target years")
    if prior_tests_enter_later_training:
        limitations.append("later training windows contain earlier evaluation years")
    if training_windows_overlap:
        limitations.append("rolling training windows overlap")
    limitations.append("fold bootstrap does not create independent historical periods")
    return {
        "level": level,
        "independent_target_years": len(target_years),
        "target_years": target_years,
        "folds": len(folds),
        "training_windows_overlap": training_windows_overlap,
        "prior_tests_enter_later_training": prior_tests_enter_later_training,
        "bootstrap_unit": "whole rolling-origin fold",
        "limitations": limitations,
        "claim_boundary": (
            "model comparison is reproducible but not confirmatory evidence or causal identification"
        ),
    }
