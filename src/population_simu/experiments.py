"""General controlled experiments on independently restored FamilyWorld branches.

Pairing means the same complete starting state per seed. It does not mean
event-aligned random shocks after populations or control flow diverge.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields, replace
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics

from .family_config import FamilyScenario
from .family_models import FamilyYearStats
from .family_world import DISABLABLE_PROCESSES, FamilyWorld


COUNTRY_RATIOS = frozenset("""
education_access rich_fertility_rebound institutional_openness welfare_floor
housing_pressure occupational_inheritance public_education_quality education_inequality
medical_license_pass_rate civil_service_selectivity state_sector_share base_unemployment_rate
worker_compensation property_inheritance_tax housing_supply_elasticity anti_nepotism_strength
assortative_mating_strength elite_marriage_closure shock_probability base_divorce_rate
remarriage_rate female_labor_access gender_pay_gap maternal_career_penalty son_preference
social_norm_strength public_education_reform housing_reform_strength high_welfare_strength
healthcare_access medical_cost_burden chronic_disease_base_rate public_long_term_care
pension_replacement_rate childcare_capacity childcare_subsidy grandparent_care_availability
dynamic_investment_strength investment_need_weight tax_rate automation_rate
labor_shortage_wage_pressure environmental_pressure climate_shock_probability
climate_shock_severity resource_constraint
""".split())
COUNTRY_NONNEGATIVE = frozenset({"cost_of_children", "education_budget_per_child",
                               "health_budget_per_person", "pension_budget_per_retiree"})
COUNTRY_POSITIVE = frozenset({"migration_logit_temperature", "carrying_capacity_scale",
                            "climate_recovery_years"})
COUNTRY_BOUNDED = {"fertility_peak_age": (18, 40, True),
                   "fertility_age_spread": (5, 30, False), "retirement_age": (50, 80, True)}
COUNTRY_PARAMETERS = COUNTRY_RATIOS | COUNTRY_NONNEGATIVE | COUNTRY_POSITIVE | COUNTRY_BOUNDED.keys()
REGION_RATIOS = frozenset("""education_quality job_opportunity amenity_supply school_supply
childcare_supply medical_supply transport_access safety_level historical_hazard_rate
population_exposure recovery_cost""".split())
REGION_PARAMETERS = REGION_RATIOS | {"wage_multiplier", "housing_cost"}
SIMULATION_PARAMETERS = frozenset({"adult_pairing_rate", "international_migration_rate",
                                   "resource_investment_share", "inheritance_share"})
PROCESSES = DISABLABLE_PROCESSES
AVAILABLE_METRICS = frozenset(item.name for item in fields(FamilyYearStats)
                            if item.name not in {"year", "country_id", "policy"})
DEFAULT_METRICS = ("population", "births", "deaths", "median_household_resources",
                   "high_status_share", "internal_migrants", "mean_childcare_gap", "climate_events")


@dataclass(frozen=True)
class ExperimentArm:
    name: str
    country_parameters: dict[str, dict[str, float | int]] = field(default_factory=dict)
    region_parameters: dict[str, dict[str, dict[str, float | int]]] = field(default_factory=dict)
    disabled_processes: tuple[str, ...] = ()
    simulation_parameters: dict[str, float | int] = field(default_factory=dict)


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _number(value, label):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{label} must be a finite number, not bool")


def _validate_patch(patch, scope):
    allowed = {"country": COUNTRY_PARAMETERS, "region": REGION_PARAMETERS,
               "simulation": SIMULATION_PARAMETERS}[scope]
    for name, value in _mapping(patch, scope).items():
        if name not in allowed:
            raise ValueError(f"unsupported {scope} parameter: {name}")
        _number(value, name)
        ratio = (scope == "simulation" or (scope == "country" and name in COUNTRY_RATIOS)
                 or (scope == "region" and name in REGION_RATIOS))
        if ratio and not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0, 1]")
        if scope == "country" and name in COUNTRY_BOUNDED:
            low, high, integer = COUNTRY_BOUNDED[name]
            if not low <= value <= high or (integer and type(value) is not int):
                raise ValueError(f"{name} has invalid bounds or integer type")
        elif not ratio:
            strictly_positive = name in COUNTRY_POSITIVE or name == "housing_cost"
            if value < 0 or (strictly_positive and value == 0):
                raise ValueError(f"{name} must be {'positive' if strictly_positive else 'nonnegative'}")


def _validate_arm(arm):
    if not isinstance(arm, ExperimentArm):
        raise ValueError("arms must be ExperimentArm instances")
    if not isinstance(arm.name, str) or not arm.name.strip() or arm.name == "baseline":
        raise ValueError("arm name must be nonempty and cannot be baseline")
    if isinstance(arm.disabled_processes, str) or not isinstance(arm.disabled_processes, (tuple, list, set, frozenset)):
        raise ValueError("disabled_processes must be a collection of process names")
    if any(not isinstance(name, str) or name not in PROCESSES for name in arm.disabled_processes):
        raise ValueError("unknown disabled process")
    if len(set(arm.disabled_processes)) != len(arm.disabled_processes):
        raise ValueError("duplicate disabled process")
    _validate_patch(arm.simulation_parameters, "simulation")
    for patch in _mapping(arm.country_parameters, "country_parameters").values():
        _validate_patch(patch, "country")
    for regions in _mapping(arm.region_parameters, "region_parameters").values():
        for patch in _mapping(regions, "regions").values():
            _validate_patch(patch, "region")


def apply_intervention(world: FamilyWorld, arm: ExperimentArm) -> dict:
    """Validate the entire intervention before changing the supplied branch.

Existing regional values are held fixed unless explicitly patched, including
regions originally generated from country-level initialization parameters.
Listed process suppressions are added to any already disabled processes.
"""
    _validate_arm(arm)
    unknown = (set(arm.country_parameters) | set(arm.region_parameters)) - set(world.countries)
    if unknown:
        raise ValueError(f"unknown country: {sorted(unknown)}")
    for country_id, patches in arm.region_parameters.items():
        unknown_regions = set(patches) - {r.id for r in world.regions[country_id]}
        if unknown_regions:
            raise ValueError(f"unknown region: {sorted(unknown_regions)}")
    changes = []

    def replacements(obj, patch, prefix):
        updates = {name: value for name, value in patch.items() if value != getattr(obj, name)}
        changes.extend({"path": f"{prefix}.{name}", "before": getattr(obj, name), "after": value}
                       for name, value in sorted(updates.items()))
        return replace(obj, **updates) if updates else obj

    new_simulation = replacements(world.scenario.simulation, arm.simulation_parameters, "simulation")
    countries = []
    new_regions = dict(world.regions)
    for country in world.scenario.countries:
        revised = replacements(country, arm.country_parameters.get(country.id, {}), f"countries.{country.id}")
        if country.id in arm.region_parameters:
            region_patches = arm.region_parameters[country.id]
            regions = tuple(replacements(region, region_patches.get(region.id, {}),
                                          f"regions.{country.id}.{region.id}")
                            for region in world.regions[country.id])
            if regions != world.regions[country.id]:
                revised = replace(revised, regions=regions)
                new_regions[country.id] = regions
        countries.append(revised)
    new_scenario = replace(world.scenario, simulation=new_simulation, countries=tuple(countries))
    new_scenario.validate()
    before_disabled = world.disabled_processes
    after_disabled = before_disabled | frozenset(arm.disabled_processes)
    # No mutation, cache clearing or RNG consumption occurs until validation succeeds.
    if changes:
        world.scenario = new_scenario
        world.countries = {country.id: country for country in new_scenario.countries}
        world.regions = new_regions
        world._capacity_cache.clear()
    if after_disabled != before_disabled:
        world.configure_disabled_processes(after_disabled)
    return {"name": arm.name, "changes": changes,
            "disabled_processes": {"before": sorted(before_disabled), "after": sorted(after_disabled)},
            "parameter_timing": "applied_after_checkpoint_before_next_annual_step",
            "region_semantics": "existing regions remain fixed unless explicitly patched"}


def audit_experiment_world(world: FamilyWorld, *, previous_population=None, stats=None) -> dict:
    """Fail-fast structural checks and global/regional population reconciliation."""
    issues = list(world.audit()["issues"])
    for row in (stats if stats is not None else [r for r in world.history if r.year == world.year]):
        for name in AVAILABLE_METRICS:
            value = getattr(row, name)
            try:
                finite = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                issues.append(f"{row.country_id}/{name} has a non-finite numeric result")
    membership = Counter()
    for household in world.households.values():
        for person_id in household.member_ids:
            person = world.people.get(person_id)
            if person is None:
                issues.append(f"household {household.id} references missing person {person_id}")
            elif person.alive:
                membership[person_id] += 1
                if person.household_id != household.id:
                    issues.append(f"person {person_id} has inconsistent household membership")
    for person in world.living_people:
        home = world.households.get(person.household_id)
        if membership[person.id] != 1 or home is None:
            issues.append(f"person {person.id} must belong to exactly one living household")
        elif (home.country_id, home.region_id) != (person.country_id, person.region_id):
            issues.append(f"person {person.id} household geography mismatch")
        if person.country_id not in world.regions or person.region_id not in {
                r.id for r in world.regions.get(person.country_id, ())}:
            issues.append(f"person {person.id} has unknown geography")
        for parent in (person.mother_id, person.father_id):
            if parent is not None and parent not in world.people:
                issues.append(f"person {person.id} references missing parent {parent}")
        if person.spouse_id is not None:
            spouse = world.people.get(person.spouse_id)
            if spouse is None or not spouse.alive or spouse.spouse_id != person.id:
                issues.append(f"person {person.id} has asymmetric spouse reference")
    balance = None
    regional_balance = None
    if previous_population is not None:
        births = sum(row.births for row in stats)
        deaths = sum(row.deaths for row in stats)
        population = len(world.living_people)
        expected = previous_population + births - deaths
        balance = {"previous_population": previous_population, "births": births, "deaths": deaths,
                   "population": population, "expected_population": expected,
                   "balanced": population == expected}
        if population != expected:
            issues.append("global population does not equal previous + births - deaths")
        if not world.population_flow_history or world.population_flow_history[-1]["year"] != world.year:
            issues.append("regional population flow ledger missing for annual step")
        else:
            regional_balance = deepcopy(world.population_flow_history[-1])
            if not regional_balance["all_regions_balanced"]:
                issues.append("regional population flow ledger does not close")
    return {"year": world.year, "ok": not issues, "issues": issues,
            "population_balance": balance, "regional_population_balance": regional_balance}


def _history_row(row):
    record = asdict(row)
    record["country"] = record.pop("country_id")
    return record


def _run_branch(world, years):
    audit = audit_experiment_world(world)
    if not audit["ok"]:
        raise ValueError(f"invalid checkpoint state: {audit['issues'][:8]}")
    history = [_history_row(row) for row in world.history if row.year == world.year]
    audits = [audit]
    for _ in range(years):
        before = len(world.living_people)
        stats = world.step()
        audit = audit_experiment_world(world, previous_population=before, stats=stats)
        if not audit["ok"]:
            raise ValueError(f"experiment audit failed at {world.year}: {audit['issues'][:8]}")
        history.extend(_history_row(row) for row in stats)
        audits.append(audit)
    return {"history": history, "audits": audits}


def source_hashes():
    return {f"src/population_simu/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))}


def run_experiment(scenario: FamilyScenario, arms: list[ExperimentArm], *, years: int,
                   seeds: list[int], warmup_years: int = 0,
                   metrics: tuple[str, ...] = DEFAULT_METRICS) -> dict:
    """Run baseline and general interventions from identical full checkpoints."""
    code_hashes = source_hashes()
    if type(years) is not int or years < 1 or type(warmup_years) is not int or warmup_years < 0:
        raise ValueError("years must be positive and warmup_years nonnegative integers")
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be distinct nonnegative integers")
    if not metrics or isinstance(metrics, str) or any(metric not in AVAILABLE_METRICS for metric in metrics):
        raise ValueError("unknown or empty metrics")
    if len(set(metrics)) != len(metrics):
        raise ValueError("duplicate metrics")
    if not arms:
        raise ValueError("at least one treatment arm is required")
    for arm in arms:
        _validate_arm(arm)
    if len({arm.name for arm in arms}) != len(arms):
        raise ValueError("duplicate arm name")
    scenario.validate()
    if scenario.simulation.start_year + warmup_years + years > scenario.simulation.end_year:
        raise ValueError("experiment exceeds scenario end_year")
    arms = sorted((replace(arm, disabled_processes=tuple(sorted(arm.disabled_processes)))
                   for arm in deepcopy(arms)), key=lambda arm: arm.name)
    differences, runs = [], []
    for seed in seeds:
        seeded = deepcopy(replace(scenario, simulation=replace(scenario.simulation, random_seed=seed)))
        initial = FamilyWorld(seeded)
        warmup = _run_branch(initial, warmup_years)
        checkpoint = initial.checkpoint()
        branches = {}
        # Validate every arm before advancing any branch beyond the checkpoint.
        for arm in arms:
            branch = checkpoint.restore()
            branches[arm.name] = (branch, apply_intervention(branch, arm))
        baseline = _run_branch(checkpoint.restore(), years)
        controls = {(row["country"], row["year"]): row for row in baseline["history"]}
        treatments = {}
        for arm in arms:
            branch, intervention = branches[arm.name]
            treatment = _run_branch(branch, years)
            treatment["intervention"] = intervention
            treatment["starting_checkpoint_fingerprint"] = checkpoint.fingerprint
            treatments[arm.name] = treatment
            for row in treatment["history"]:
                if row["year"] <= checkpoint.year:
                    continue
                control = controls[(row["country"], row["year"])]
                for metric in metrics:
                    difference = row[metric] - control[metric]
                    _number(difference, f"paired difference {arm.name}/{metric}")
                    differences.append({"seed": seed, "country": row["country"], "year": row["year"],
                                        "arm": arm.name, "metric": metric, "baseline": control[metric],
                                        "value": row[metric], "difference": difference})
        runs.append({"seed": seed, "checkpoint_fingerprint": checkpoint.fingerprint,
                     "start_year": checkpoint.year, "warmup_audits": warmup["audits"],
                     "baseline": baseline, "arms": treatments})
    grouped = defaultdict(list)
    for row in differences:
        grouped[(row["arm"], row["country"], row["year"], row["metric"])].append(row["difference"])
    summary = [{"arm": arm, "country": country, "year": year, "metric": metric,
                "n_seeds": len(values), "mean_difference": statistics.fmean(values),
                "seed_min": min(values), "seed_max": max(values),
                "sample_sd": statistics.stdev(values) if len(values) > 1 else None}
               for (arm, country, year, metric), values in sorted(grouped.items())]
    for row in summary:
        for name in ("mean_difference", "seed_min", "seed_max", "sample_sd"):
            if row[name] is not None:
                _number(row[name], f"summary {row['arm']}/{row['metric']}/{name}")
    if source_hashes() != code_hashes:
        raise ValueError("model source files changed during the experiment; rerun with stable code")
    return {"schema_version": 1, "kind": "controlled_family_experiment",
            "metadata": {"engine": "FamilyWorld", "time_step": "year",
                         "python_version": platform.python_version(),
                         "same_checkpoint_per_seed": True,
                         "event_aligned_common_random_numbers": False, "causal_estimate": False,
                         "checkpoint_storage": "in_memory_same_code",
                         "uncertainty": "paired seed mean, range and sample SD; not confidence intervals",
                         "region_policy": "country parameter changes do not rebuild existing regions",
                         "climate_ablation": "no new climate events; existing stress continues to recover",
                         "migration_ablation": "migration processes only; partnership-related moves remain possible",
                         "regional_flow_ledger": "event-stage births, deaths and relocations; every region must close annually"},
            "configuration": {"scenario": asdict(scenario), "arms": [asdict(arm) for arm in arms],
                              "years": years, "warmup_years": warmup_years,
                              "seeds": list(seeds), "metrics": list(metrics)},
            "source_sha256": code_hashes, "runs": runs,
            "paired_differences": differences, "summary": summary}


def run_spec(path: Path) -> dict:
    """Read a strict, versioned JSON experiment spec; no dynamic code execution."""
    spec_bytes = path.read_bytes()
    spec = json.loads(spec_bytes)
    _mapping(spec, "spec")
    allowed = {"schema_version", "name", "scenario", "years", "warmup_years", "seeds", "metrics", "arms"}
    if set(spec) - allowed or type(spec.get("schema_version")) is not int or spec["schema_version"] != 1:
        raise ValueError("unsupported experiment spec fields or version")
    scenario_path = (path.parent / spec["scenario"]).resolve()
    scenario_bytes = scenario_path.read_bytes()
    arms = []
    for item in spec["arms"]:
        _mapping(item, "arm")
        if set(item) - {field.name for field in fields(ExperimentArm)}:
            raise ValueError("unknown arm field")
        arms.append(ExperimentArm(**item))
    report = run_experiment(FamilyScenario.from_dict(json.loads(scenario_bytes)), arms,
                            years=spec["years"], seeds=spec["seeds"],
                            warmup_years=spec.get("warmup_years", 0),
                            metrics=tuple(spec.get("metrics", DEFAULT_METRICS)))
    report["spec"] = {"name": spec.get("name", path.stem),
                      "sha256": hashlib.sha256(spec_bytes).hexdigest(),
                      "scenario_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
                      "scenario_reference": spec["scenario"]}
    return report
