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

The project will reject these inputs in strict mode if they are incomplete or
duplicate keys are present.
