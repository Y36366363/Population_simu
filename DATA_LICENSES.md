# Data licenses, provenance, and citation

The repository's MIT License applies to the original software, tests, scripts,
documentation, static web interface, scenario definitions, and synthetic test
fixtures. It does **not** relicense files under `data/observed/`.

Observed data remain subject to the terms of their respective providers. The
tables below record the best provenance currently available in the repository.
Where an exact retrieval date was not saved, this document says so and records
the first Git commit date as an audit trail rather than presenting it as a
download date.

## Our World in Data, UN WPP, and HMD

| Repository path | Provider and exact source | Retrieval record | Project transformation | Redistribution and use | Recommended citation |
| --- | --- | --- | --- | --- | --- |
| `data/observed/owid_demography_sample.csv` | [OWID Population](https://ourworldindata.org/grapher/population), [Crude birth rate](https://ourworldindata.org/grapher/crude-birth-rate), [Crude death rate](https://ourworldindata.org/grapher/crude-death-rate), and [Total fertility rate](https://ourworldindata.org/grapher/children-born-per-woman); underlying sources are identified in each chart's metadata and are primarily UN World Population Prospects 2024 for this snapshot | Downloaded 2026-08-12 | Four-country, 1950–2023 subset; `births_estimated` and `deaths_estimated` are project-derived as population × crude rate / 1,000 | Not MIT. OWID-produced work is generally CC BY; third-party data keep the provider's terms. Preserve both OWID and underlying-provider attribution and indicate the project-derived columns | “UN DESA Population Division (2024), *World Population Prospects 2024*, processed by Our World in Data; retrieved 2026-08-12; subset and derived columns by Population Simu.” |
| `data/observed/owid_age_sex_death_rates_sample.csv` | [OWID annual death rates by age and sex](https://ourworldindata.org/grapher/annual-death-rates-in-different-age-groups-by-sex), combining Human Mortality Database and UN WPP series as identified by OWID | Exact download date not recorded; first committed 2026-08-15 | Four-country, 1990–2023 subset at selected ages and sexes | Not MIT. Scientific use and attribution requirements from the [HMD user agreement](https://former.mortality.org/Public/UserAgreement.php) and the applicable UN/OWID terms remain in force. Do not treat this file as commercially unrestricted | “Human Mortality Database and UN DESA Population Division, processed by Our World in Data; selected age-sex-country subset by Population Simu; accessed no later than 2026-08-15.” |

OWID explains that third-party data distributed through its charts remain
subject to the original provider's terms. UN Population Division API material
is published under CC BY 3.0 IGO. Users should re-check the live chart metadata
before republishing an updated snapshot.

## World Bank

| Repository path | Provider and exact source | Retrieval record | Project transformation | Redistribution and use | Recommended citation |
| --- | --- | --- | --- | --- | --- |
| `data/observed/wb_age_sex_groups_sample.csv` | [World Bank Indicators API](https://api.worldbank.org/), indicators `SP.POP.0014.*.IN`, `SP.POP.1564.*.IN`, and `SP.POP.65UP.*.IN` | Exact download date not recorded; first committed 2026-08-15 | Four-country, 1990–2023 long-format subset | World Bank-produced open data are generally CC BY 4.0 with the World Bank's additional terms. Redistribution is permitted with attribution and an indication of modifications; this file is not MIT | “World Bank, World Development Indicators, population by age group and sex; accessed no later than 2026-08-15; reformatted by Population Simu.” |

## U.S. Census Bureau

| Repository path or group | Provider and exact source | Retrieval record | Project transformation | Redistribution and use | Recommended citation |
| --- | --- | --- | --- | --- | --- |
| `data/observed/us_2021/census_single_age_sex_2025.csv`; `us_population_single_age_sex_2021.csv` | [Census 2020–2025 national age-sex estimates](https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/national/asrh/nc-est2025-agesex-res.csv) | Exact download date not recorded; first committed 2026-08-16 | `scripts/build_us_pilot.py` selects the 2021 estimate and converts it to the project's country-year-sex-age contract | Public Census statistical product; not MIT. Preserve source attribution, do not imply Census endorsement, and comply with Census confidentiality and API terms | “U.S. Census Bureau, Vintage 2025 National Population Estimates, NC-EST2025-AGESEX-RES; 2021 values reformatted by Population Simu.” |
| `acs_exposure_age_marital_2010_2017.csv` and metadata | [ACS 1-year B12002 metadata/API](https://api.census.gov/data/2010/acs/acs1/groups/B12002.json) | Retrieved 2026-08-28 | State-year age-band × marital-status estimates; bands allocated uniformly to single ages and explicitly labeled `uniform_within_band` | Public Census API output; not MIT. Redistribution is allowed subject to the Census API terms and disclaimer below | “U.S. Census Bureau, American Community Survey 1-year table B12002, 2010–2017; age-band allocation by Population Simu; retrieved 2026-08-28.” |
| `acs_exposure_age_marital_2018_2021.csv` and metadata | [ACS B12002 metadata/API](https://api.census.gov/data/2018/acs/acs1/groups/B12002.json); 2020 uses ACS 5-year rather than the unavailable standard 1-year product | Retrieved 2026-08-29 | Same age-band allocation; 2020 source difference is recorded in metadata | Public Census API output; not MIT. Redistribution is allowed subject to the Census API terms and disclaimer below | “U.S. Census Bureau, ACS table B12002, 2018–2021 (2020 ACS 5-year); age-band allocation by Population Simu; retrieved 2026-08-29.” |
| `us_housing_panel_2021.csv`, `us_housing_panel_2007_2021.csv`, `us_housing_panel_2010_2021_comparable.csv`, and `us_housing_2020_acs5_sensitivity.csv` | Census ACS B25070 API, table-based, and sequence-file URLs recorded in the scripts and each CSV's `source_url` column | Exact retrieval dates were not saved for every panel; first commits: 2026-08-18, 2026-08-21, 2026-08-22, and 2026-09-14 respectively | State-level rent-burden shares; 2020 ACS 5-year value kept as a separately labeled sensitivity observation | Public Census statistical products; not MIT. Preserve per-row source URLs and estimate types | “U.S. Census Bureau, ACS table B25070; state-year extraction and documented transformations by Population Simu.” |
| `us_female_15_44_2007_2021.csv` | Exact Census PEP source files are listed in `us_fertility_manifest.json` | Retrieved 2026-08-20 | Sums single-age female civilian resident estimates for ages 15–44 | Public Census statistical product; not MIT. Preserve the manifest and attribution | “U.S. Census Bureau, Population Estimates Program, state female population ages 15–44, 2007–2021; aggregation by Population Simu; retrieved 2026-08-20.” |
| `census_age_sex.csv` | Exact source URL and intended role are not currently recorded | Exact download date not recorded; first committed 2026-08-16 | No current code, test, or documentation references this file | Provenance remediation required. Do not redistribute or cite it as a project result until the exact Census product, URL, vintage, and purpose are documented | No recommended citation until provenance is repaired |

Required Census API notice:

> This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.

Users must not use Census data, alone or in combination, to identify an
individual person, household, business, or other entity.

## CDC/NCHS published tables and vital-statistics reports

| Repository path or group | Provider and exact source | Retrieval record | Project transformation | Redistribution and use | Recommended citation |
| --- | --- | --- | --- | --- | --- |
| `cdc_us_life_table_male.xlsx`; `cdc_us_life_table_female.xlsx`; `us_life_table_male_2021.csv`; `us_life_table_female_2021.csv` | CDC/NCHS, *United States Life Tables, 2021*, [report](https://www.cdc.gov/nchs/data/nvsr/nvsr72/nvsr72-12.pdf), [Table 2 workbook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/72-12/Table02.xlsx), and [Table 3 workbook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/72-12/Table03.xlsx) | Exact download date not recorded; first committed 2026-08-16 | `scripts/build_us_pilot.py` extracts the published period `q_x` probability into single-age male and female CSVs | U.S. federal statistical publication; not MIT. Redistribution should retain CDC/NCHS attribution and must not imply CDC endorsement | “Arias E, Xu J, Kochanek K. United States Life Tables, 2021. National Vital Statistics Reports; vol. 72 no. 12. Hyattsville, MD: NCHS. 2023. Tables 2–3; converted by Population Simu.” |
| `us_state_births_2007_2021.csv`; the birth component of `us_fertility_panel.csv` and merged research panels | CDC/NCHS National Vital Statistics Reports listed exactly in `us_fertility_manifest.json` | Retrieved 2026-08-20 | State-year total live births transcribed from final natality report tables and combined with Census female denominators | Not MIT. Published aggregate statistics may be redistributed with source attribution; preserve the manifest, report URLs, definition, and checksums | “CDC/NCHS, National Vital Statistics Reports, final live births by mother's state of residence, 2007–2021; compiled by Population Simu; retrieved 2026-08-20.” |
| `wonder_batches_2010_2017.json`, `wonder_2010_00_validation.json`, and related progress metadata | [CDC WONDER Natality](https://wonder.cdc.gov/) | Query dates/statuses are recorded in the manifests where available | Query plans, validation status, and checksums; raw exports are intentionally kept outside Git | Project metadata may be redistributed, but any underlying WONDER data retain CDC/NCHS terms. These files do not grant access to restricted microdata | Cite the CDC WONDER Natality database, query date and grouping, plus Population Simu's manifest version |
| `nchs_birth_public_use_2018_2021.json` | CDC/NCHS Vital Statistics Online; exact pending archive URLs are stored in the JSON | Manifest created 2026-09-09; archives remain pending and are not committed | Download plan only | Project-authored manifest is reusable under MIT; future downloaded microdata will remain subject to NCHS terms and must not be added to the MIT scope | Cite CDC/NCHS Vital Statistics Online and the specific annual file used |

## NCHS National Survey of Family Growth

| Repository path | Provider and exact source | Retrieval record | Project transformation | Redistribution and use | Recommended citation |
| --- | --- | --- | --- | --- | --- |
| `nsfg_birth_rows_2010_2017.csv`, `nsfg_birth_rows_2018.csv`, `nsfg_exposure_snapshot_2018.csv`, and `nsfg_2018_calibration.json` | [CDC/NCHS 2017–2019 NSFG public-use files and documentation](https://www.cdc.gov/nchs/nsfg/nsfg_2017_2019_puf.htm) | Exact download date not recorded; derived files first committed 2026-08-24 | Weighted, aggregated birth histories and female respondent exposure snapshot; national validation only, not state-year calibration | Not MIT. Use only for statistical analysis/reporting; do not attempt identification, disclosure, or prohibited linkage. Redistribution of these derived extracts does not remove the NCHS Data User Agreement | “National Center for Health Statistics, National Survey of Family Growth, 2017–2019 public-use female respondent and pregnancy files; weighted aggregation by Population Simu; accessed no later than 2026-08-24.” |

The controlling conditions are in the
[NCHS Data User Agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html).

## Project-derived panels and validation artifacts

The following are generated by this project but depend on one or more observed
sources listed above:

- `data/observed/us_2021/us_fertility_panel.csv`
- `data/observed/us_2021/us_research_panel_*.csv`
- `data/observed/us_2021/*validation*.json`
- `data/observed/us_2021/*smoke*.json`
- `data/observed/us_2021/frozen_cross_validation*.json`
- `data/observed/us_2021/household_adapter_audit*.json`
- `data/observed/us_2021/comparable_four_model*.json`
- `data/observed/us_2021/fertility_baseline_smoke.json`
- `data/observed/us_2021/project_readiness*.json`
- `data/observed/us_2021/model_artifacts_manifest*.json`

These files may be redistributed for reproducibility with attribution to
Population Simu, but redistribution does not replace or relax the terms of the
underlying Census, CDC/NCHS, OWID, UN, HMD, or World Bank data. Cite the project,
the specific artifact version, and every upstream dataset used to create it.

## Synthetic data

Files under `data/fixtures/` are project-authored synthetic test fixtures and
are covered by the repository's MIT License. They are not observed population
records and must not be described as empirical evidence.

## Provider terms referenced

- [Our World in Data reuse FAQ](https://ourworldindata.org/faqs)
- [UN Population Division Data Portal API — CC BY 3.0 IGO](https://population.un.org/dataportalapi/index.html)
- [Human Mortality Database user agreement](https://former.mortality.org/Public/UserAgreement.php)
- [World Bank data access and licensing](https://datacatalog.worldbank.org/public-licenses)
- [Census Bureau API terms of service](https://www.census.gov/data/developers/about/terms-of-service.html)
- [Census Bureau citation guidance](https://www.census.gov/about/policies/citation.html)
- [NCHS Data User Agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)

This inventory is a reproducibility and attribution record, not legal advice.
When replacing or refreshing a dataset, update this file, the relevant manifest,
the retrieval date, exact URL, transformation description, and checksum in the
same commit.
