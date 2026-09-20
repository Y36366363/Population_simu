# Frozen route decision · 2026-09-20

## Decision

The project will be developed as a narrow computational-demography study of
whether a household-level mechanistic simulator can reproduce held-out U.S.
state fertility dynamics better, or more interpretably, than simpler models.
The simulator is not treated as a causal estimator.

## What is frozen now

- **Primary outcome:** state-year `ASFR_15_44`, constructed as live births to
  women aged 15–44 divided by the same-age female exposure denominator.
- **Primary exposure:** `housing_cost_burden`.
- **Calibration:** 2010–2017.
- **Untouched test:** 2018, 2019 and 2021. 2020 remains a sensitivity year
  because its housing series has a different ACS5 measurement status.
- **Predictive baselines:** naive trend, cohort-component proxy and
  reduced-form statistical model.
- **Mechanism models:** household full, no-housing and no-household variants.
- **Interpretation:** replication of observed patterns and mechanism
  diagnostics, not a policy effect or causal counterfactual.

## Conditional second exposure

Childcare is the planned second exposure, but it is **not yet part of the
primary specification**. It may enter only after a single documented series
has the same definition, geography, denominator and year coverage across the
calibration and test windows. Until then, childcare results must be labelled
an auxiliary sensitivity analysis; no mixed proxy series or synthetic fill is
allowed.

This is preferable to declaring two exposures frozen when only one is
currently observed in the comparable panel.

## Required comparison and evidence

Each model must use the same state-year keys and rolling-origin splits. The
report must include RMSE, MAPE, CRPS and interval coverage, with state and
Census-region strata. Full versus ablated household variants use paired
state-year bootstrap intervals. A better household fit is evidence about
replication or interpretability only; it is not evidence that housing or
childcare caused fertility changes.

## Current stopping rule

Do not add new social mechanisms, countries, policies or UI complexity before
the following are complete: (1) the frozen panel audit, (2) all four model
comparisons, (3) mechanism ablation, (4) untouched-year evaluation, and (5)
an explicit accounting of the missing age–marital-status–parity hazard data.
