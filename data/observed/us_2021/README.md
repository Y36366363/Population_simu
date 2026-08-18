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

`us_housing_panel_2021.csv` is the first verified state-year slice, generated from the
official 2021 table-based Summary File B25070 via `fetch_us_housing_ftp.py`. It is not
yet the 2007–2021 panel; earlier years must be downloaded and version-pinned before any
calibration claim is made.
