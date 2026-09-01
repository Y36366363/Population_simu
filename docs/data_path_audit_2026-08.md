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

## Batch collection workflow

`data/observed/us_2021/wonder_batches_2010_2017.json` contains 48 one-year/state-
chunk requests. Save each successful browser export as `<id>.tsv` in a local
directory (raw files may remain outside Git), then run:

```bash
PYTHONPATH=src python3 scripts/collect_wonder_batches.py \
  data/observed/us_2021/wonder_batches_2010_2017.json \
  --input-dir /path/to/wonder_tsv \
  --output /path/to/wonder_births_2010_2017.csv
```

The command marks every batch `success` or `failed`, records row counts/errors,
and merges only successful files. It exits nonzero when no batch succeeded.

After all required batches are successful, align them with the ACS panels:

```bash
PYTHONPATH=src python3 scripts/build_wonder_acs_panel.py \
  /path/to/wonder_births_2010_2017.csv \
  data/observed/us_2021/acs_exposure_age_marital_2010_2017.csv \
  data/observed/us_2021/acs_exposure_age_marital_2018_2021.csv \
  --births-test /path/to/wonder_births_2018_2021.csv \
  --output-dir data/observed/us_2021
```

The alignment script aggregates live-birth-order counts to `parity=all`, then
strictly checks that all eight calibration years and all four test years are
present before writing outputs.

The 48-file manifest covers only 2010–2017. To produce the untouched 2018–2021
test panel, a separate WONDER export (or equivalent NCHS public-use birth file)
must be supplied with `--births-test`; the script now refuses to infer test births
from calibration data.

### Do we need all 48 WONDER files?

- **Formal statewide study:** yes. The manifest covers every 2010–2017 year and
  all 52 state/territory codes used by the ACS panel (8 × 6 state chunks). A
  missing batch means the statewide calibration estimand is incomplete.
- **Pipeline smoke test:** no. One successful batch plus a small synthetic or
  archived comparison can test parsing and key alignment, but must not be used
  for the headline calibration or model comparison.
- **Practical sequence:** download one batch first, run the collector, then
  continue in six-batch year groups. Keep raw TSVs outside Git if redistribution
  is restricted; commit only the manifest status, checksum, and derived panel.

Run `scripts/check_wonder_completeness.py` before calibration. It verifies both
that all 48 files exist and that each file contains every state FIPS listed in
its manifest entry. A nonzero exit means the files are suitable only for smoke
tests, not for the formal statewide estimand.

The Census API key must be requested by the project owner from the Census API
portal and supplied at runtime as `CENSUS_API_KEY`; it is never committed,
printed, or embedded in the repository.

For the 2018–2021 untouched numerator, CDC/NCHS also lists annual public-use
birth archives (for example, `Nat2018us.zip` through `Nat2021us.zip`). These are
large fixed-width files, so they are an alternative ingestion path rather than
something to download automatically during tests. The repository records their
official URLs and a pending status in
`nchs_birth_public_use_2018_2021.json`; field-level state-of-residence and
marital/birth-order availability must be verified against each year’s user guide
before substitution.
