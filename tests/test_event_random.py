import json
import unittest

from population_simu.environment import EnvironmentalConfig, EnvironmentalProcess
from population_simu.event_random import EventKey, EventRandom, ExogenousPath
from population_simu.family_world import FamilyWorld

from tests.test_experiments import small_scenario


class EventRandomTests(unittest.TestCase):
    def test_keyed_stream_is_independent_of_lookup_order(self):
        keys = [
            EventKey("economic_shock", 2001, "A"),
            EventKey("climate_event", 2001, "A", "urban"),
            EventKey("climate_event", 2001, "A", "rural"),
        ]
        generator = EventRandom(73)
        forward = {key: generator.stream(key).random() for key in keys}
        reverse = {key: generator.stream(key).random() for key in reversed(keys)}
        self.assertEqual(forward, reverse)
        self.assertEqual(generator.stream(keys[0]).random(), forward[keys[0]])
        self.assertNotEqual(
            generator.stream(keys[0]).random(),
            generator.stream(EventKey("economic_shock", 2001, "A", draw="severity")).random(),
        )

    def test_record_freeze_json_round_trip_and_strict_missing_key(self):
        first = EventKey("climate_event", 2001, "A", "urban")
        missing = EventKey("climate_event", 2001, "A", "rural")
        recording = ExogenousPath(record_missing=True)
        self.assertEqual(recording.resolve(first, lambda: {"occurred": False}),
                         {"occurred": False})
        frozen = ExogenousPath.from_dict(json.loads(json.dumps(recording.freeze().as_dict())))
        self.assertEqual(frozen.resolve(first, lambda: {"occurred": True}),
                         {"occurred": False})
        with self.assertRaises(KeyError):
            frozen.resolve(missing, lambda: {"occurred": False})
        with self.assertRaises(ValueError):
            ExogenousPath({first.token: float("nan")})

    def test_climate_draws_are_stable_when_region_order_changes(self):
        config = EnvironmentalConfig(event_probability=1.0, event_severity=0.4)
        process = EnvironmentalProcess(123)
        forward = process.events_for_year(2000, "TST", ("urban", "rural"), config)
        reverse = process.events_for_year(2000, "TST", ("rural", "urban"), config)
        self.assertEqual(forward, reverse)

    def test_world_external_states_ignore_main_rng_consumption(self):
        left = FamilyWorld(small_scenario())
        right = FamilyWorld(small_scenario())
        for _ in range(100):
            right.rng.random()
        left.year = right.year = 2001
        left._update_economic_cycle()
        right._update_economic_cycle()
        left._update_environment()
        right._update_environment()
        self.assertEqual(left._economic_cycle, right._economic_cycle)
        self.assertEqual(left._shock_residual, right._shock_residual)
        self.assertEqual(left._climate_events, right._climate_events)

    def test_recorded_world_path_replays_with_a_different_root_seed(self):
        first = FamilyWorld(small_scenario())
        first.begin_exogenous_path_recording()
        first.year = 2001
        first._update_economic_cycle()
        first._update_environment()
        frozen = first.freeze_exogenous_path()
        expected_cycle = dict(first._economic_cycle)
        expected_events = dict(first._climate_events)

        alternate = small_scenario()
        alternate = type(alternate)(
            name=alternate.name,
            simulation=type(alternate.simulation)(
                **{**alternate.simulation.__dict__, "random_seed": 999}
            ),
            countries=alternate.countries,
        )
        replay = FamilyWorld(alternate)
        replay.configure_exogenous_path(frozen)
        replay.year = 2001
        replay._update_economic_cycle()
        replay._update_environment()
        self.assertEqual(replay._economic_cycle, expected_cycle)
        self.assertEqual(replay._climate_events, expected_events)
        self.assertEqual(len(frozen), len(first.countries) + sum(map(len, first.regions.values())))


if __name__ == "__main__":
    unittest.main()
