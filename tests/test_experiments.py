"""Scientific contracts for reusable, paired FamilyWorld experiments."""

from copy import deepcopy
from dataclasses import asdict, replace
import json
import statistics
import unittest

from population_simu.experiments import (
    ExperimentArm,
    apply_intervention,
    run_experiment,
)
from population_simu.family_config import FamilyScenario
from population_simu.family_world import FamilyWorld


def small_scenario():
    """Two small countries and explicit regions allow scope and flow checks."""
    country = {
        "id": "A", "name": "Alpha", "initial_clans": 3,
        "initial_development": 0.4, "annual_development_gain": 0.003,
        "initial_urbanization": 0.5, "annual_urbanization_gain": 0.002,
        "education_access": 0.6, "cost_of_children": 0.7,
        "baseline_family_resources": 100.0, "initial_children_per_family": 1,
        "regions": [
            {"id": "urban", "name": "City", "urban": True, "initial_share": 0.5},
            {"id": "rural", "name": "Country", "urban": False, "initial_share": 0.5},
        ],
    }
    second = deepcopy(country)
    second.update(id="B", name="Beta")
    return FamilyScenario.from_dict({
        "name": "generic-experiment-test",
        "simulation": {
            "start_year": 2000, "end_year": 2006, "random_seed": 91,
            "international_migration_rate": 0.04,
        },
        "countries": [country, second],
    })


def observable_world_state(world):
    """Cover mutable model inputs, population state and the random stream."""
    return deepcopy({
        "scenario": asdict(world.scenario),
        "countries": {key: asdict(value) for key, value in world.countries.items()},
        "regions": {key: [asdict(value) for value in values]
                    for key, values in world.regions.items()},
        "snapshot": world.snapshot(),
        "rng": world.rng.getstate(),
        "people": {key: asdict(value) for key, value in world.people.items()},
        "households": {key: asdict(value) for key, value in world.households.items()},
    })


class ExperimentContractsTests(unittest.TestCase):
    def test_noop_arm_matches_baseline_and_has_zero_paired_differences(self):
        report = run_experiment(small_scenario(), [ExperimentArm("noop")],
                                years=2, seeds=[17, 23],
                                metrics=("population", "median_household_resources"))
        self.assertEqual(len(report["runs"]), 2)
        for run in report["runs"]:
            self.assertTrue(run["checkpoint_fingerprint"])
            self.assertEqual(run["baseline"]["history"], run["arms"]["noop"]["history"])
            self.assertEqual(run["baseline"]["audits"], run["arms"]["noop"]["audits"])
        # 2 seeds x 2 countries x 2 post-intervention years x 2 metrics.
        self.assertEqual(len(report["paired_differences"]), 16)
        self.assertTrue(all(row["difference"] == 0 for row in report["paired_differences"]))
        self.assertTrue(all(row["mean_difference"] == 0 for row in report["summary"]))

    def test_intervention_changes_only_named_country_and_region_fields(self):
        scenario = small_scenario()
        original = asdict(scenario)
        world = FamilyWorld(scenario)
        before = observable_world_state(world)
        record = apply_intervention(world, ExperimentArm(
            "education-and-housing",
            country_parameters={"A": {"public_education_quality": 0.91}},
            region_parameters={"A": {"urban": {"housing_cost": 0.25}}},
        ))
        self.assertIsInstance(record, dict)
        self.assertTrue(record)
        self.assertEqual(world.countries["A"].public_education_quality, 0.91)
        self.assertEqual(world.regions["A"][0].housing_cost, 0.25)
        self.assertEqual(asdict(world.countries["B"]), before["countries"]["B"])
        self.assertEqual([asdict(region) for region in world.regions["B"]], before["regions"]["B"])
        self.assertEqual(asdict(world.regions["A"][1]), before["regions"]["A"][1])
        self.assertEqual(world.rng.getstate(), before["rng"])
        self.assertEqual({key: asdict(value) for key, value in world.people.items()}, before["people"])
        self.assertEqual({key: asdict(value) for key, value in world.households.items()}, before["households"])
        self.assertEqual(asdict(scenario), original)

    def test_invalid_country_changes_are_rejected_atomically(self):
        invalid_changes = [
            {"A": {"unknown_knob": 0.3}},
            {"missing": {"housing_pressure": 0.3}},
            {"A": {"housing_pressure": float("nan")}},
            {"A": {"housing_pressure": float("inf")}},
            {"A": {"housing_pressure": True}},
            {"A": {"housing_pressure": 1.1}},
            {"A": {"housing_pressure": -0.1}},
            {"A": {"housing_pressure": "0.3"}},
            {"A": {"initial_clans": 4}},
            {"A": {"initial_children_per_family": 2}},
            {"A": {"initial_development": 0.7}},
            {"A": {"annual_development_gain": 0.007}},
            {"A": {"annual_urbanization_gain": 0.007}},
            {"A": {"baseline_family_resources": 200}},
            {"A": {"id": "changed"}},
            {"A": {"name": "changed"}},
            {"A": {"random_seed": 7}},
            {"A": {"regions": ()}},
        ]
        for changes in invalid_changes:
            with self.subTest(changes=changes):
                world = FamilyWorld(small_scenario())
                before = observable_world_state(world)
                with self.assertRaises((TypeError, ValueError)):
                    apply_intervention(world, ExperimentArm("invalid", country_parameters=changes))
                self.assertEqual(observable_world_state(world), before)

    def test_country_housing_change_does_not_silently_rebuild_fallback_regions(self):
        scenario = small_scenario()
        scenario = replace(scenario, countries=tuple(replace(country, regions=())
                                                     for country in scenario.countries))
        world = FamilyWorld(scenario)
        before = {key: tuple(asdict(region) for region in regions)
                  for key, regions in world.regions.items()}
        apply_intervention(world, ExperimentArm(
            "national-housing", country_parameters={"A": {"housing_pressure": 0.9}}))
        self.assertEqual(world.countries["A"].housing_pressure, 0.9)
        self.assertEqual({key: tuple(asdict(region) for region in regions)
                          for key, regions in world.regions.items()}, before)

    def test_fallback_region_override_is_synchronized_with_effective_configuration(self):
        scenario = small_scenario()
        scenario = replace(scenario, countries=tuple(replace(country, regions=())
                                                     for country in scenario.countries))
        world = FamilyWorld(scenario)
        before = [asdict(region) for region in world.regions["A"]]
        region_id = world.regions["A"][0].id
        apply_intervention(world, ExperimentArm(
            "local-housing", region_parameters={"A": {region_id: {"housing_cost": 0.2}}}))
        expected = deepcopy(before)
        expected[0]["housing_cost"] = 0.2
        self.assertEqual([asdict(region) for region in world.regions["A"]], expected)
        self.assertEqual([asdict(region) for region in world.countries["A"].regions], expected)
        effective_country = next(country for country in world.scenario.countries if country.id == "A")
        self.assertEqual([asdict(region) for region in effective_country.regions], expected)
        self.assertEqual(scenario.countries[0].regions, ())

    def test_valid_country_change_is_not_applied_when_a_region_change_is_invalid(self):
        invalid_regions = [
            {"A": {"missing": {"housing_cost": 0.5}}},
            {"missing": {"urban": {"housing_cost": 0.5}}},
            {"A": {"urban": {"unknown_knob": 0.5}}},
            {"A": {"urban": {"housing_cost": float("nan")}}},
            {"A": {"urban": {"housing_cost": float("inf")}}},
            {"A": {"urban": {"housing_cost": True}}},
            {"A": {"urban": {"initial_share": 0.9}}},
            {"A": {"urban": {"id": "renamed"}}},
            {"A": {"urban": {"urban": False}}},
        ]
        for changes in invalid_regions:
            with self.subTest(changes=changes):
                world = FamilyWorld(small_scenario())
                before = observable_world_state(world)
                with self.assertRaises((TypeError, ValueError)):
                    apply_intervention(world, ExperimentArm(
                        "mixed-invalid", country_parameters={"A": {"housing_pressure": 0.25}},
                        region_parameters=changes,
                    ))
                self.assertEqual(observable_world_state(world), before)

    def test_unknown_disabled_process_is_rejected_before_any_parameter_changes(self):
        world = FamilyWorld(small_scenario())
        before = observable_world_state(world)
        with self.assertRaises((TypeError, ValueError)):
            apply_intervention(world, ExperimentArm(
                "invalid-process", country_parameters={"A": {"housing_pressure": 0.25}},
                disabled_processes=("not_a_process",),
            ))
        self.assertEqual(observable_world_state(world), before)

    def test_process_ablation_reaches_the_engine_and_population_accounts(self):
        report = run_experiment(small_scenario(), [ExperimentArm(
            "events-off", disabled_processes=(
                "births", "deaths", "internal_migration", "international_migration",
                "partnership", "divorce", "climate_events",
            ))], years=2, seeds=[11], metrics=("population", "births", "deaths"))
        result = report["runs"][0]["arms"]["events-off"]
        fields = ("births", "deaths", "internal_migrants", "migrants", "remarriages",
                  "divorces", "climate_events")
        for row in result["history"]:
            for field in fields:
                self.assertEqual(row[field], 0, (row["year"], row["country"], field))
        for audit in result["audits"][1:]:
            ledger = audit["regional_population_balance"]
            self.assertTrue(ledger["all_regions_balanced"])
            for region in ledger["regions"]:
                for field in (
                    "births", "deaths", "internal_migration_in", "internal_migration_out",
                    "international_migration_in", "international_migration_out",
                    "partnership_relocation_in", "partnership_relocation_out",
                    "divorce_relocation_in", "divorce_relocation_out",
                ):
                    self.assertEqual(region[field], 0, (audit["year"], region, field))
        totals = {}
        for row in result["history"]:
            totals[row["year"]] = totals.get(row["year"], 0) + row["population"]
        self.assertEqual(len(set(totals.values())), 1)

    def test_arm_order_cannot_change_another_arms_trajectory(self):
        scenario = small_scenario()
        before = asdict(scenario)
        arms = [ExperimentArm("housing", country_parameters={"A": {"housing_pressure": 0.1}}),
                ExperimentArm("education", country_parameters={"B": {"public_education_quality": 0.9}})]
        first = run_experiment(scenario, arms, years=2, seeds=[19, 29], metrics=("population",))
        second = run_experiment(scenario, list(reversed(arms)), years=2, seeds=[19, 29],
                                 metrics=("population",))
        for left, right in zip(first["runs"], second["runs"]):
            self.assertEqual(left["seed"], right["seed"])
            self.assertEqual(left["checkpoint_fingerprint"], right["checkpoint_fingerprint"])
            self.assertEqual(left["baseline"], right["baseline"])
            self.assertEqual(left["arms"], right["arms"])
        self.assertEqual(asdict(scenario), before)

    def test_frozen_exogenous_path_is_saved_and_replayed_across_ablation(self):
        report = run_experiment(
            small_scenario(),
            [ExperimentArm("no-births", disabled_processes=("births",))],
            years=2,
            seeds=[19],
            metrics=("population",),
            freeze_exogenous_path=True,
        )
        self.assertTrue(report["metadata"]["event_aligned_common_random_numbers"])
        self.assertEqual(report["metadata"]["event_alignment_scope"],
                         "economic and climate exogenous events only")
        run = report["runs"][0]
        frozen = run["frozen_exogenous_path"]
        self.assertEqual(frozen["kind"], "frozen_exogenous_path")
        # Two annual steps: two countries plus four regions per step.
        self.assertEqual(len(frozen["values"]), 12)
        baseline = {(row["country"], row["year"]): row for row in run["baseline"]["history"]}
        treatment = {(row["country"], row["year"]): row
                     for row in run["arms"]["no-births"]["history"]}
        for key in baseline:
            self.assertEqual(baseline[key]["economic_cycle_index"],
                             treatment[key]["economic_cycle_index"])
            self.assertEqual(baseline[key]["climate_events"], treatment[key]["climate_events"])
        json.dumps(report, allow_nan=False)

    def test_frozen_path_rejects_conflicting_shock_intervention(self):
        arms = [
            ExperimentArm(
                "different-shock",
                country_parameters={"A": {"shock_probability": 0.9}},
            ),
            ExperimentArm(
                "different-exposure",
                region_parameters={"A": {"urban": {"population_exposure": 0.9}}},
            ),
        ]
        for arm in arms:
            with self.subTest(arm=arm.name), self.assertRaisesRegex(
                    ValueError, "frozen exogenous paths"):
                run_experiment(small_scenario(), [arm], years=1, seeds=[19],
                               metrics=("population",), freeze_exogenous_path=True)

    def test_warmup_forks_at_the_requested_year_without_reseeding(self):
        report = run_experiment(small_scenario(), [ExperimentArm("noop")],
                                years=2, seeds=[43], warmup_years=1,
                                metrics=("population",))
        run = report["runs"][0]
        self.assertEqual(run["start_year"], 2001)
        self.assertEqual({row["year"] for row in run["baseline"]["history"]}, {2001, 2002, 2003})
        self.assertEqual(run["baseline"]["history"], run["arms"]["noop"]["history"])
        self.assertEqual({row["year"] for row in report["paired_differences"]}, {2002, 2003})
        # Running uninterrupted from the same seed must yield the same endpoint.
        uninterrupted = run_experiment(small_scenario(), [ExperimentArm("noop")],
                                       years=3, seeds=[43], metrics=("population",))
        expected = [row for row in uninterrupted["runs"][0]["baseline"]["history"]
                    if row["year"] >= 2001]
        self.assertEqual(run["baseline"]["history"], expected)

    def test_paired_scores_and_seed_summary_are_derived_from_the_saved_histories(self):
        metrics = ("population", "median_household_resources", "tax_revenue")
        report = run_experiment(small_scenario(), [ExperimentArm(
            "tax", country_parameters={"A": {"tax_rate": 0.6}})],
            years=2, seeds=[31, 47], metrics=metrics)
        run_by_seed = {run["seed"]: run for run in report["runs"]}
        grouped = {}
        self.assertEqual(len(report["paired_differences"]), 24)
        for row in report["paired_differences"]:
            run = run_by_seed[row["seed"]]
            key = (row["country"], row["year"])
            baseline = next(item for item in run["baseline"]["history"]
                            if (item["country"], item["year"]) == key)[row["metric"]]
            value = next(item for item in run["arms"][row["arm"]]["history"]
                         if (item["country"], item["year"]) == key)[row["metric"]]
            self.assertEqual(row["baseline"], baseline)
            self.assertEqual(row["value"], value)
            self.assertAlmostEqual(row["difference"], value - baseline)
            grouped.setdefault((row["arm"], *key, row["metric"]), []).append(value - baseline)
        self.assertEqual(len(report["summary"]), len(grouped))
        for row in report["summary"]:
            values = grouped[(row["arm"], row["country"], row["year"], row["metric"])]
            self.assertEqual(row["n_seeds"], 2)
            self.assertAlmostEqual(row["mean_difference"], statistics.fmean(values))
            self.assertEqual(row["seed_min"], min(values))
            self.assertEqual(row["seed_max"], max(values))
            self.assertAlmostEqual(row["sample_sd"], statistics.stdev(values))

    def test_each_arm_has_closed_population_accounts_and_explicit_evidence_limits(self):
        report = run_experiment(small_scenario(), [ExperimentArm(
            "welfare", country_parameters={"A": {"welfare_floor": 0.5}})],
            years=2, seeds=[13], metrics=("population",))
        metadata = report["metadata"]
        self.assertEqual(metadata["engine"], "FamilyWorld")
        self.assertEqual(metadata["time_step"], "year")
        self.assertTrue(metadata["same_checkpoint_per_seed"])
        self.assertFalse(metadata["event_aligned_common_random_numbers"])
        self.assertFalse(metadata["causal_estimate"])
        self.assertEqual(metadata["checkpoint_storage"], "in_memory_same_code")
        for run in report["runs"]:
            for result in [run["baseline"], *run["arms"].values()]:
                self.assertEqual(len(result["audits"]), 3)
                self.assertIsNone(result["audits"][0]["population_balance"])
                for audit in result["audits"]:
                    self.assertTrue(audit["ok"], audit["issues"])
                    if audit["population_balance"] is not None:
                        balance = audit["population_balance"]
                        self.assertTrue(balance["balanced"])
                        self.assertEqual(balance["population"], balance["expected_population"])
                        self.assertEqual(balance["population"],
                                         balance["previous_population"] + balance["births"] - balance["deaths"])
                        regional = audit["regional_population_balance"]
                        self.assertTrue(regional["all_regions_balanced"])
                        self.assertEqual(
                            sum(row["closing_population"] for row in regional["regions"]),
                            balance["population"],
                        )
                        self.assertTrue(all(
                            row["closing_population"] == row["expected_population"]
                            for row in regional["regions"]
                        ))
        self.assertTrue(all(row["sample_sd"] is None for row in report["summary"]))
        # Reports must be portable JSON; NaN/Infinity must never leak into artifacts.
        json.dumps(report, allow_nan=False)

    def test_invalid_arm_names_and_duplicate_names_are_rejected(self):
        for names in (("baseline",), ("",), ("   ",), ("same", "same")):
            with self.subTest(names=names), self.assertRaises((TypeError, ValueError)):
                run_experiment(small_scenario(), [ExperimentArm(name) for name in names],
                               years=1, seeds=[11], metrics=("population",))

    def test_unknown_or_non_numeric_metrics_are_rejected(self):
        for metrics in (("not_a_metric",), ("policy",), ("country",), ("population", "population")):
            with self.subTest(metrics=metrics), self.assertRaises((TypeError, ValueError)):
                run_experiment(small_scenario(), [ExperimentArm("noop")],
                               years=1, seeds=[11], metrics=metrics)

    def test_invalid_run_design_cannot_create_misleading_replicates(self):
        invalid = [
            {"seeds": []}, {"seeds": [11, 11]}, {"seeds": [True]}, {"seeds": [-1]},
            {"seeds": [1.5]}, {"years": 0}, {"years": -1}, {"years": True},
            {"years": 1.5}, {"warmup_years": -1}, {"warmup_years": True},
            {"warmup_years": 0.5}, {"freeze_exogenous_path": 1},
        ]
        for changes in invalid:
            settings = {"years": 1, "seeds": [11], "warmup_years": 0, **changes}
            with self.subTest(changes=changes), self.assertRaises((TypeError, ValueError)):
                run_experiment(small_scenario(), [ExperimentArm("noop")], **settings,
                               metrics=("population",))


if __name__ == "__main__":
    unittest.main()
