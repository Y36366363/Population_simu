# Empirical data-path audit (2026-08-27)

This note records which sources are suitable for the frozen US state-year study.
It is an audit, not a claim that every source has already been downloaded.

| Component | Preferred source | Coverage / key fields | Decision |
|---|---|---|---|
| Birth numerator | CDC WONDER Natality | 2007–2024; residence state, year, mother's age group, marital status, live-birth order | Use for state-year age×marital births; retry in smaller queries if the five-way export times out |
| Female exposure | ACS PUMS 1-year (large states) / 5-year (small states) | 2010 onward; `AGEP`, `SEX`, `MAR`, `PWGTP`, state | Build weighted female age×marital exposure; 5-year estimates must not be mixed with 1-year estimates without a documented sensitivity run |
| Population denominator | Census Population Estimates / intercensal files | 2010–2020 single-year age×sex by state; later vintages revise history | Use for cohort-component reconciliation, not as a substitute for marital exposure |
| Microdata cross-check | CDC NSFG public-use files | National weighted birth histories and partnership variables; no public state identifier | External national validation only; never a state-year replacement |
| Birth public-use alternative | NCHS Vital Statistics Online | Annual birth public-use files, including 2007–2021 | Use when WONDER query export is unavailable; document file vintage and recodes |

## Identifiability rules

1. `state × year × age × marital × parity` births require the same five-dimensional
   risk-set exposure for a formal parity hazard.
2. If exposure is only `state × year × age × marital`, run
   `scripts/import_wonder_stratified.py --aggregate-parity`; interpret the output as
   total age-marital fertility, not first/second/third-birth hazards.
3. Preserve raw downloads outside Git when CDC suppression or terms prohibit
   redistribution; commit query metadata, checksums, and transformation code.
4. Calibration remains 2010–2017 and the untouched historical test remains 2018–2021.

## Reproducibility checklist

- Record WONDER query date, database vintage, grouping order, year selections, and
  export format.
- Record ACS release (1-year or 5-year), variable list, state geography, weighting
  variable, and age-band construction.
- Run duplicate-key, positive-exposure, year-coverage, and suppression checks before
  merging. Never silently impute a missing state-year cell.
- Keep national NSFG calibration separate from the primary state panel.
