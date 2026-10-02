"""Export declared defaults, loaded scenarios, and initialized family regions.

Run from the repository root without installing the package::

    python3 scripts/export_configuration_inventory.py

This is a configuration audit, not a calibration or realism assessment. It
initializes family worlds at their starting year and does not advance them.
"""

from __future__ import annotations

import argparse
from dataclasses import MISSING, asdict, fields, is_dataclass
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from population_simu import config, family_config
from population_simu.family_world import FamilyWorld


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module_inventory(module: ModuleType) -> dict[str, object]:
    """Inspect only dataclasses defined by the requested configuration module."""
    source = Path(module.__file__).resolve()
    classes = []
    for name, cls in vars(module).items():
        if not isinstance(cls, type) or not is_dataclass(cls) or cls.__module__ != module.__name__:
            continue
        declared_fields = []
        for item in fields(cls):
            entry = {"name": item.name, "type": str(item.type), "required": False}
            if item.default is not MISSING:
                entry.update(default_kind="value", default_value=item.default)
            elif item.default_factory is not MISSING:
                factory = item.default_factory
                entry.update(
                    default_kind="factory",
                    default_factory=f"{factory.__module__}.{factory.__qualname__}",
                    default_value=factory(),
                )
            else:
                entry.update(required=True, default_kind="missing")
            declared_fields.append(entry)
        classes.append({"name": name, "field_count": len(declared_fields), "fields": declared_fields})
    return {
        "module": module.__name__,
        "source_path": source.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(source),
        "dataclasses": classes,
    }


def family_initialization(scenario: family_config.FamilyScenario, explicit: dict) -> dict[str, object]:
    world = FamilyWorld(scenario)
    people = world.living_people
    explicit_countries = {country["id"]: country for country in explicit["countries"]}
    countries = []
    for country in scenario.countries:
        configured = explicit_countries[country.id]
        inputs = {}
        for name in ("fertility_age_profile", "mortality_age_profile", "migration_age_profile", "migration_matrix"):
            value = getattr(country, name)
            item = {
                "explicit_key_present": name in configured,
                "missing_or_empty": not bool(value),
                "status": "provided_unverified" if value else "absent_or_empty",
            }
            if name == "migration_matrix":
                item.update(
                    origin_count=len(value),
                    configured_od_entries=sum(len(destinations) for destinations in value.values()),
                )
            else:
                item["age_rate_points"] = len(value)
            inputs[name] = item
        regions = [
            {"definition": asdict(region), "derived_service_index": region.service_index}
            for region in world.regions[country.id]
        ]
        countries.append({
            "country_id": country.id,
            "initial_population": sum(person.country_id == country.id for person in people),
            "initial_households": sum(home.country_id == country.id for home in world.households.values()),
            "initial_clans": sum(clan.origin_country_id == country.id for clan in world.clans.values()),
            "region_source": "configured_regions" if country.regions else "engine_urban_rural_fallback",
            "actual_region_count": len(regions),
            "actual_regions": regions,
            "age_profiles_and_od": inputs,
        })
    audit = world.audit()
    if not audit["ok"]:
        raise ValueError(f"Initial family-world audit failed for {scenario.name}: {audit['issues']}")
    return {
        "year": world.year,
        "steps_run": 0,
        "initial_population": len(people),
        "initial_households": len(world.households),
        "initial_clans": len(world.clans),
        "initial_structure_audit": audit,
        "countries": countries,
    }


def build_inventory() -> dict[str, object]:
    modules = [module_inventory(config), module_inventory(family_config)]
    scenarios = []
    for path in sorted((ROOT / "scenarios").glob("*.json")):
        explicit = json.loads(path.read_text(encoding="utf-8"))
        family = "countries" in explicit
        scenario_cls = family_config.FamilyScenario if family else config.Scenario
        scenario = scenario_cls.from_dict(explicit)
        scenario.validate()
        record = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "scenario_type": f"{scenario_cls.__module__}.{scenario_cls.__name__}",
            "validation": {"passed": True, "method": "from_dict_then_validate"},
            "explicit_configuration": explicit,
            "effective_configuration": asdict(scenario),
        }
        if family:
            record["initialization"] = family_initialization(scenario, explicit)
        scenarios.append(record)
    source_paths = sorted((ROOT / "src" / "population_simu").glob("*.py"))
    source_paths.append(Path(__file__).resolve())
    classes = [cls for module in modules for cls in module["dataclasses"]]
    all_fields = [item for cls in classes for item in cls["fields"]]
    family_records = [item for item in scenarios if "initialization" in item]
    family_countries = [country for item in family_records for country in item["initialization"]["countries"]]
    summary = {
        "configuration_modules": len(modules),
        "dataclasses": len(classes),
        "declared_fields": len(all_fields),
        "required_fields": sum(item["required"] for item in all_fields),
        "fields_with_defaults": sum(not item["required"] for item in all_fields),
        "scenarios": len(scenarios),
        "family_scenarios": len(family_records),
        "simple_scenarios": len(scenarios) - len(family_records),
        "family_country_instances": len(family_countries),
        "family_countries_using_fallback_regions": sum(
            item["region_source"] == "engine_urban_rural_fallback" for item in family_countries
        ),
        "family_actual_region_definitions": sum(item["actual_region_count"] for item in family_countries),
        "family_country_instances_missing_all_profiles_and_od": sum(
            all(value["missing_or_empty"] for value in item["age_profiles_and_od"].values())
            for item in family_countries
        ),
    }
    return {
        "schema_version": 1,
        "kind": "configuration_inventory",
        "evidence_status": "configuration_audit_only",
        "interpretation": [
            "Declared defaults and explicit scenario values are model settings; this audit does not establish that they were empirically estimated.",
            "Validation confirms the existing configuration validators accept the inputs; it does not establish empirical realism or completeness of validation.",
            "Effective configuration is the complete dataclass state returned by from_dict; actual family regions separately include engine-generated urban/rural fallbacks.",
            "Initial populations are synthetic seeded agents at the configured start year, not observed country population counts; no simulation step is run.",
            "A supplied age profile or OD table would still require independent source and calibration verification; absent tables use engine fallback mechanisms.",
            "Country and region counts aggregate scenario instances, including fictional experiment arms, rather than unique real geographic entities.",
        ],
        "source_sha256": {path.relative_to(ROOT).as_posix(): sha256(path) for path in source_paths},
        "summary": summary,
        "configuration_modules": modules,
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "docs" / "artifacts" / "configuration_inventory_2026-10-02.json",
    )
    args = parser.parse_args()
    payload = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": payload["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
