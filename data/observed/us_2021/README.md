# United States pilot (2021)

This directory contains a reproducible public-data ingestion pilot:

- `us_population_single_age_sex_2021.csv`: Census Bureau resident population
  estimate by single year of age and sex (July 1, 2021 field from the Vintage
  2025 file).
- `us_life_table_male_2021.csv` and `us_life_table_female_2021.csv`: CDC/NCHS
  United States Life Tables 2021, converted from the public Table 2 and Table 3
  workbooks. The `death_rate` field is the period `q_x` probability.

Run `python scripts/build_us_pilot.py` to reproduce the converted CSVs from the
downloaded workbooks. The pilot intentionally stops before claiming a complete
historical calibration: an age-sex origin-destination flow file and a joint
marital-status × parity female exposure file are still required. ACS's public
2020 migration-flow release publishes counts without crossed characteristics,
so assigning an age-sex distribution to it would be a derived proxy, not a real
OD observation.

Expected additional files:

```text
year,origin,destination,sex,age,hazard
country,year,marital,parity,age,births,exposure
```

`scripts/build_us_microdata_inputs.py` converts local, legally obtained extracts.
For ACS PUMS use `AGEP,SEX,ST,MIGSP,PWGTP`; `MIGSP` is the state of residence one
year earlier and `ST` is current residence. The script aggregates person weights,
retains `flow` and `exposure`, and calculates `hazard = flow / exposure`.

For NSFG or a natality extract, prepare weighted rows with `age,marital,parity,weight`
for births and female exposure. The output is accepted by
`fertility_schedule_from_observations`; it is not valid to use the NSFG respondent
count without its survey weight.

The project will reject these inputs in strict mode if they are incomplete or
duplicate keys are present.

Official acquisition references: [ACS PUMS](https://www.census.gov/programs-surveys/acs/microdata.html),
[ACS migration variables](https://www.census.gov/data/developers/data-sets/acs-migration-flows/2020.html),
and [NSFG public-use files](https://www.cdc.gov/nchs/nsfg/nsfg_2017_2019_puf.htm).

This update includes an actual, aggregated NSFG 2017–2019 public-use extract:
`nsfg_birth_rows_2010_2017.csv` contains weighted live births by outcome year,
mother age, formal marital status and birth order, parsed from the CDC fixed-width
file and its Stata dictionary. `nsfg_exposure_snapshot_2018.csv` contains the
weighted female respondent age/marital snapshot. The resulting
`nsfg_2018_calibration.json` is an external national validation, not a state-year
calibration: its exposure is a survey snapshot and its window overlaps the frozen
test period. It must not be fed into the primary 2010–2017 calibration.

For the primary denominator, `scripts/fetch_acs_marital_exposure.py` provides a
reproducible Census ACS B12002 downloader. It preserves age bands and labels its
uniform-within-band allocation; it cannot claim single-year observed exposure.
If the Census API is unavailable without a key, the script fails rather than using
synthetic values. State-level age/marital birth rows still require a CDC WONDER
export or public natality extract with the same year and geography definitions.

CDC WONDER's Natality 2007–2024 database is a viable replacement for the missing
public NSFG geography: it exposes mother's state of residence, age, marital status
and live-birth order (2003 onward). Use `scripts/import_wonder_stratified.py` with
a matching female-exposure export. Strict mode requires the denominator to carry
the same birth-order key; `--allow-all-parity-denominator` is sensitivity-only and
does not create a formal parity hazard.

`us_housing_panel_2021.csv` is the original verified state-year slice. The historical
ingestion path is `scripts/fetch_us_housing_historical.py`: it parses ACS sequence files
(2007–2017) using year-specific sequence metadata and table-based files (2018 onward),
and records the source URL and estimate type. `us_housing_panel_2007_2021.csv` is the
current auditable research slice; its manifest explicitly lists missing years rather
than imputing them. The present download contains 2018, 2019 and 2021 for the 50 states.
Older sequence files and the District of Columbia require a separate FTP-layout pass.
The 2020 standard ACS 1-year Summary File does not exist, so no 2020 value is fabricated;
the experimental/5-year alternatives must be handled as a separately flagged sensitivity.

`scripts/build_us_research_panel.py` merges the housing slice with the fixed fertility
outcome and writes `us_research_panel_2007_2021.csv` plus a manifest with row counts,
missing years and unmatched fertility rows. It is not model-ready until the manifest's
missing years are resolved under a pre-specified comparability rule.

The current primary alternative is `us_housing_panel_2010_2021_comparable.csv`: 50 states,
2010–2019 and 2021 (550 rows). Its manifest explicitly treats 2020 as a pandemic data gap
and moves the calibration start to 2010. The 2007–2009 ACS 3-year release is not copied into
individual years; it is reserved for a sensitivity analysis because a rolling three-year
estimate is not an annual observation.

`scripts/run_fertility_baseline_smoke.py` runs the two baselines on the fertility-only panel,
or all four runners when passed the merged comparable panel. The output is a forecast-pipeline
diagnostic, not a causal estimate.

The first frozen fertility outcome is now fixed in three files:

- `us_state_births_2007_2021.csv`: 765 state-year total live-birth counts extracted
  from NCHS final Natality report tables (mother's state of residence).
- `us_female_15_44_2007_2021.csv`: 765 Census PEP state-year female 15–44 denominators,
  summed from single-age civilian resident estimates.
- `us_fertility_panel.csv`: deterministic merge with `asfr_15_44 = births /
  female_15_44 * 1000`.

`us_fertility_manifest.json` records the exact source URLs, row counts and SHA-256
checksums. The outcome is a general fertility rate (all births), not yet a
marital-status × parity-specific rate. The housing panel remains incomplete, so the
full study readiness gate is intentionally still false.

To add the fertility outcome, export a state-by-year CDC WONDER Natality table as TSV
and prepare a Census female-age denominator CSV with `State,Year,Female15_44`. Then run
`PYTHONPATH=src python3 scripts/import_wonder_fertility.py births.tsv denominator.csv
--output us_fertility_panel.csv`. The importer computes `asfr_15_44` and rejects missing
or duplicate state-year denominators; no synthetic fertility rows are used.
