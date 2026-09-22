# Future activation protocol · 2026-09-22

This document defines what would be required before the three currently frozen
components can enter the primary study. It is a gate, not a promise that the
components are already identified.

## 1. Childcare as a primary exposure

### Required data contract

Use one state-year measure throughout calibration and test, with a documented
definition such as formal care coverage among children under five, or licensed
slots per 100 children under five. Do not mix price, capacity, participation
and subsidy measures in one column. Every row must carry:

- state FIPS and year;
- numerator and denominator, not only a ratio;
- source URL, release/version and transformation note;
- a stable definition and unit;
- missingness and suppression flags.

The minimum primary panel is 50 states × 2010–2019 and 2021. 2020 remains a
sensitivity year unless the childcare source has a comparable pandemic-year
definition. The calibration/test split stays 2010–2017 versus 2018, 2019 and
2021.

### Estimation and checks

1. Freeze the exposure before looking at test errors.
2. Fit reduced-form models with housing only and housing + childcare.
3. Add full/no-childcare paired ablations to the household adapter.
4. Report measurement missingness, within-state changes, and exposure
   correlation with housing and year.
5. Require a pre-specified lag choice; do not choose the lag by test MAPE.

Childcare enters the primary specification only when the data gate reports
complete keys, valid denominators, provenance metadata and a frozen definition.
Until then, childcare remains an auxiliary mechanism or sensitivity input.

## 2. Formal age–marital-status–parity hazards

### Required numerator and denominator

For every state-year-age-group-marital-status-parity key, retain live birth
counts, exposure and a source-specific weight/audit field. The numerator needs
all 48 2010–2017 WONDER batches plus a separately documented 2018–2021 test
source. The denominator must use the same geography, age grouping, marital
definition and reference population. An all-parity denominator cannot silently
be reused as a parity-specific exposure.

ACS PUMS can supply weighted female exposure by age and marital status, but it
does not by itself identify parity exposure. NSFG can be a national validation
source, not a state-level replacement, unless a valid state design/identifier
is available and documented.

### Estimation sequence

1. Reconcile codebooks and age bands; preserve suppressed cells rather than
   replacing them with zero.
2. Run strict key, range, duplicate and total-birth audits.
3. Estimate discrete-time first, second and third-plus birth hazards using
   calibration years only; include age baseline, marital exposure and state/
   year effects as pre-specified terms.
4. Propagate survey/registration weights and cluster uncertainty at the
   appropriate design level.
5. Validate aggregate births and ASFR against an independent total series.
6. Run the untouched test replay and retain prior-only status for any hazard
   component that fails its denominator gate.

Formal hazard status can change only after all numerator batches, the test
numerator, matching denominators and aggregate reconciliation pass.

## 3. Causal policy counterfactuals

The simulator must not be called causal merely because it contains a policy
switch. Before a policy counterfactual, specify:

- the intervention, eligible population, timing and dose;
- the causal estimand and time horizon;
- a DAG and a list of pre-treatment confounders;
- positivity/overlap and treatment adoption rules;
- a reduced-form identification design (for example a justified event-study,
  difference-in-differences or synthetic-control comparison);
- placebo, pre-trend and alternative-window checks;
- uncertainty from both the statistical estimate and simulator parameters.

The correct sequence is: estimate the observed reduced-form effect, calibrate
the simulator to reproduce untreated and treated historical patterns, validate
held-out outcomes, then run the intervention under an explicitly labelled
structural extrapolation. If the policy is not historically identified, the
output must be labelled a model-based scenario, not a causal effect.

## Current status and next unlock

As of 2026-09-22, childcare is missing from the comparable panel and the
age–marital–parity gate remains blocked at 1/48 WONDER batches with only
all-parity ACS exposure. The next unlock is data completion and audit, not new
mechanisms or UI. The causal gate is later still: it requires a separate
identification design even after the data gates pass.
