from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from population_simu.family_checkpoint import FamilyCheckpoint, fingerprint_world
from population_simu.family_config import FamilyScenario
from population_simu.family_world import DISABLABLE_PROCESSES, FamilyWorld


def checkpoint_scenario(**overrides):
    countries = []
    for country_id in ("AAA", "BBB"):
        country = {
            "id": country_id,
            "name": country_id,
            "initial_clans": 8,
            "initial_development": 0.45,
            "annual_development_gain": 0.003,
            "initial_urbanization": 0.4,
            "annual_urbanization_gain": 0.002,
            "education_access": 0.6,
            "cost_of_children": 0.7,
            "baseline_family_resources": 100,
            "initial_children_per_family": 2,
            "climate_shock_probability": 1.0,
            "climate_shock_severity": 0.2,
        }
        country.update(overrides)
        countries.append(country)
    return FamilyScenario.from_dict({
        "name": "checkpoint-test",
        "simulation": {
            "start_year": 2000,
            "end_year": 2020,
            "random_seed": 31415,
            "international_migration_rate": 0.2,
        },
        "countries": countries,
    })


class FamilyCheckpointTests(unittest.TestCase):
    def test_archived_ledger_survives_checkpoint_and_continuation(self):
        world = FamilyWorld(checkpoint_scenario())
        world.run(2002)
        world.transfer_ledger.archive_before(2003)
        before_summary = world.transfer_ledger.summary()
        before_count = world.transfer_ledger.record_count
        restored = world.checkpoint().restore()
        self.assertEqual(restored.transfer_ledger.summary(), before_summary)
        self.assertEqual(restored.transfer_ledger.record_count, before_count)
        self.assertTrue(restored.transfer_ledger.audit()["ok"])
        world.step()
        restored.step()
        self.assertEqual(fingerprint_world(restored), fingerprint_world(world))

    def test_warmed_checkpoint_restores_complete_identical_continuation(self):
        world = FamilyWorld(checkpoint_scenario())
        world.run(2005)
        before = fingerprint_world(world)
        checkpoint = world.checkpoint()
        self.assertIsInstance(checkpoint, FamilyCheckpoint)
        self.assertEqual(checkpoint.year, 2005)
        self.assertEqual(checkpoint.fingerprint, before)
        first, second = checkpoint.restore(), checkpoint.restore()
        self.assertEqual(fingerprint_world(first), before)
        self.assertEqual(fingerprint_world(second), before)
        self.assertIs(first.countries["AAA"], first.scenario.countries[0])
        for _ in range(4):
            world.step()
            first.step()
            second.step()
            self.assertEqual(fingerprint_world(world), fingerprint_world(first))
            self.assertEqual(fingerprint_world(world), fingerprint_world(second))
        # Advancing the source and both forks cannot advance the checkpoint.
        self.assertEqual(fingerprint_world(checkpoint.restore()), before)

    def test_source_checkpoint_and_restores_share_no_mutable_state(self):
        world = FamilyWorld(checkpoint_scenario())
        world.run(2002)
        checkpoint = FamilyCheckpoint.capture(world)
        first, second = checkpoint.restore(), checkpoint.restore()
        original = checkpoint.fingerprint
        next(iter(first.people.values())).age += 10
        home = next(iter(first.households.values()))
        home.capitals.financial += 900
        home.member_ids.append(-1)
        next(iter(first.clans.values())).branch_ids.append(-1)
        first.scenario.countries[0].social_norm_sources["kin"] = 0.99
        first.scenario.countries[0].migration_matrix["extra"] = {"extra": 3.0}
        first.region_history[0]["regions"][0]["population"] = -1
        first._government_funds["AAA"] += 20
        first._environment.seed += 3
        first._environmental_stress[("AAA", "AAA-urban")] = 0.99
        first.rng.random()
        self.assertNotEqual(fingerprint_world(first), original)
        self.assertEqual(fingerprint_world(world), original)
        self.assertEqual(fingerprint_world(second), original)
        self.assertEqual(fingerprint_world(checkpoint.restore()), original)
        world.people.clear()
        self.assertEqual(fingerprint_world(checkpoint.restore()), original)

    def test_fingerprint_covers_state_configuration_history_and_randomness(self):
        world = FamilyWorld(checkpoint_scenario())
        original = fingerprint_world(world)

        def change_person(item):
            next(iter(item.people.values())).age += 1

        def change_config(item):
            item.scenario = replace(item.scenario, name="changed")

        def change_history(item):
            item.history[0] = replace(item.history[0], births=10)

        mutations = (
            change_person,
            change_config,
            change_history,
            lambda item: item.rng.random(),
            lambda item: setattr(item, "next_person_id", item.next_person_id + 1),
            lambda item: item._shock_residual.update(AAA=0.3),
            lambda item: item._government_funds.update(AAA=20.0),
            lambda item: item.configure_disabled_processes(["births"]),
            lambda item: setattr(item._environment, "seed", item._environment.seed + 1),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation.__name__):
                changed = deepcopy(world)
                mutation(changed)
                self.assertNotEqual(fingerprint_world(changed), original)
                self.assertEqual(fingerprint_world(world), original)

    def test_fingerprint_preserves_iteration_order_and_mutable_aliases(self):
        world = FamilyWorld(checkpoint_scenario())
        reordered = deepcopy(world)
        reordered.people = dict(reversed(tuple(reordered.people.items())))
        self.assertNotEqual(fingerprint_world(world), fingerprint_world(reordered))
        unlinked = deepcopy(world)
        unlinked.countries["AAA"] = deepcopy(unlinked.countries["AAA"])
        self.assertNotEqual(fingerprint_world(world), fingerprint_world(unlinked))
        self.assertEqual(fingerprint_world(world), fingerprint_world(deepcopy(world)))

    def test_snapshot_mutation_cannot_change_world_or_future_history(self):
        world = FamilyWorld(checkpoint_scenario())
        original = fingerprint_world(world)
        snapshot = world.snapshot()
        snapshot["region_history"][0]["regions"][0]["population"] = -100
        snapshot["region_history"].clear()
        snapshot["countries"]["AAA"]["regions"][0]["population"] = -100
        self.assertEqual(fingerprint_world(world), original)

    def test_unknown_or_malformed_disabled_processes_are_atomic_errors(self):
        world = FamilyWorld(checkpoint_scenario())
        world.configure_disabled_processes(["births"])
        original = fingerprint_world(world)
        for invalid in (["migration"], ["deaths", "typo"], "deaths", [1], None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    world.configure_disabled_processes(invalid)
                self.assertEqual(fingerprint_world(world), original)

    def test_disabled_event_processes_are_not_called_and_report_zero_events(self):
        world = FamilyWorld(checkpoint_scenario())
        world.configure_disabled_processes(DISABLABLE_PROCESSES)
        population = len(world.living_people)
        process_methods = (
            "_births", "_deaths", "_internal_migration", "_international_migration",
            "_form_family_branches", "_divorces",
        )
        with ExitStack() as stack:
            for method in process_methods:
                stack.enter_context(patch.object(
                    world, method, side_effect=AssertionError(f"Disabled {method} called")
                ))
            stack.enter_context(patch.object(
                world._environment, "events_for_year",
                side_effect=AssertionError("Disabled climate events called"),
            ))
            stats = world.step()
        self.assertEqual(len(world.living_people), population)
        for row in stats:
            for name in ("births", "deaths", "internal_migrants", "migrants", "divorces", "remarriages", "climate_events"):
                self.assertEqual(getattr(row, name), 0)
        restored = world.checkpoint().restore()
        self.assertEqual(restored.disabled_processes, DISABLABLE_PROCESSES)

    def test_disabled_processes_can_be_reenabled(self):
        world = FamilyWorld(checkpoint_scenario())
        world.configure_disabled_processes(["births"])
        world.configure_disabled_processes([])
        self.assertEqual(world.disabled_processes, frozenset())
        with patch.object(world, "_births", return_value={}) as births:
            world.step()
        births.assert_called_once_with()

    def test_stopping_new_climate_events_clears_events_and_keeps_recovery(self):
        world = FamilyWorld(checkpoint_scenario())
        world.step()
        self.assertTrue(world._climate_events)
        old_stress = dict(world._environmental_stress)
        world.configure_disabled_processes(["climate_events"])
        expected = {
            (country_id, region.id): world._environment.next_stress(
                old_stress[(country_id, region.id)], None,
                world._environment_config(world.countries[country_id]),
                region.recovery_cost,
            )
            for country_id, regions in world.regions.items()
            for region in regions
        }
        stats = world.step()
        self.assertEqual(world._climate_events, {})
        self.assertEqual(world._environmental_stress, expected)
        self.assertTrue(all(row.climate_events == 0 for row in stats))
        for key, stress in expected.items():
            self.assertLess(stress, old_stress[key])
            self.assertGreaterEqual(stress, world.countries[key[0]].environmental_pressure)
        self.assertTrue(all(
            row["climate_event"] == 0 for row in world.region_history[-1]["regions"]
        ))


if __name__ == "__main__":
    unittest.main()
