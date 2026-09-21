# Housing-primary rolling-origin results · 2026-09-21

This is a predictive replication report, not a causal estimate. The primary outcome is state-year `ASFR_15_44`; calibration uses 2010–2017 and the untouched test years are 2018, 2019 and 2021. 2020 is excluded from the primary specification.

## Overall rolling-origin diagnostics

Each expanding-window origin uses 20 common-random Monte Carlo repetitions and 1,000 bootstrap draws over fold scores. CRPS is in ASFR-per-1,000 units. Coverage is the nominal 10–90% interval coverage.

| origin window | model | MAPE | RMSE | CRPS | coverage | interval width |
|---:|---|---:|---:|---:|---:|---:|
| 6 years | `naive_trend` | 1.47% | 0.908 | 0.908 | 0.00% | 0.000 |
| 6 years | `cohort_proxy` | 1.58% | 0.975 | 0.975 | 0.00% | 0.000 |
| 6 years | `reduced_form` | 2.15% | 1.329 | 1.329 | 0.00% | 0.000 |
| 6 years | `household` | 2.03% | 1.251 | 1.232 | 2.00% | 0.167 |
| 6 years | `household_no_housing` | 2.03% | 1.251 | 1.251 | 0.00% | 0.000 |
| 6 years | `household_no_household` | 1.47% | 0.908 | 0.908 | 0.00% | 0.000 |
| 7 years | `naive_trend` | 1.49% | 0.908 | 0.908 | 0.00% | 0.000 |
| 7 years | `cohort_proxy` | 1.74% | 1.062 | 1.062 | 0.00% | 0.000 |
| 7 years | `reduced_form` | 2.26% | 1.390 | 1.390 | 0.00% | 0.000 |
| 7 years | `household` | 2.24% | 1.367 | 1.345 | 4.00% | 0.302 |
| 7 years | `household_no_housing` | 2.24% | 1.367 | 1.367 | 0.00% | 0.000 |
| 7 years | `household_no_household` | 1.49% | 0.908 | 0.908 | 0.00% | 0.000 |
| 8 years | `naive_trend` | 1.38% | 0.830 | 0.830 | 0.00% | 0.000 |
| 8 years | `cohort_proxy` | 1.38% | 0.821 | 0.821 | 0.00% | 0.000 |
| 8 years | `reduced_form` | 2.32% | 1.398 | 1.398 | 0.00% | 0.000 |
| 8 years | `household` | 1.98% | 1.184 | 1.172 | 4.00% | 0.429 |
| 8 years | `household_no_housing` | 1.98% | 1.184 | 1.184 | 0.00% | 0.000 |
| 8 years | `household_no_household` | 1.38% | 0.830 | 0.830 | 0.00% | 0.000 |

## Regional MAPE (initial window = 6 years)

| model | Northeast | Midwest | South | West |
|---|---:|---:|---:|---:|
| `naive_trend` | 1.42% | 1.34% | 1.16% | 2.03% |
| `cohort_proxy` | 1.34% | 1.62% | 1.15% | 2.24% |
| `reduced_form` | 1.77% | 2.33% | 1.93% | 2.51% |
| `household` | 1.53% | 1.89% | 1.47% | 3.20% |
| `household_no_housing` | 1.53% | 1.89% | 1.47% | 3.20% |
| `household_no_household` | 1.42% | 1.34% | 1.16% | 2.03% |

## Interpretation of the household ablation

1. `household_no_household` currently bypasses household formation, marriage, fertility and migration events and uses the recent two-year trend. It is therefore mathematically equivalent to the `naive_trend` control under this forecast contract. Its lower error is evidence that the full stochastic adapter adds predictive noise in this implementation, not evidence that household mechanisms are false or causally harmful.
2. `household` is worse than the trend control in the rolling-origin table. The plausible, testable explanations are the seeded World process, the proxy female exposure, and the calibration-to-ASFR scaling; these are model limitations to audit, not substantive demographic conclusions.
3. `household_no_housing` is identical to `household` in these rolling folds. This means the current one-year aggregate adapter does not transmit enough variation from the exogenous housing series to change the forecast path. Housing sensitivity should therefore be described as unresolved rather than as a measured fertility effect.
4. Deterministic baselines have zero-width intervals, so their 10–90% coverage is mechanically zero. A calibrated predictive interval for those baselines requires a pre-specified residual or bootstrap construction; the current coverage values must not be read as probabilistic model failure.

## Scope gates

- Childcare remains outside the primary specification until one documented state-year series has a stable definition, denominator, source and full calibration/test coverage.
- Age–marital-status–parity hazards remain prior-only until state-year births and matching exposure denominators pass the strict five-dimensional key audit.
- No causal counterfactual is reported from this artifact.

Source artifact: `docs/artifacts/housing_primary_rolling_origin_2026-09-21.json`.
