import unittest

from population_simu.environment import EnvironmentalConfig, EnvironmentalProcess
from population_simu.environment_experiment import run_sensitivity


class EnvironmentTests(unittest.TestCase):
    def test_event_process_is_reproducible_and_isolated(self):
        config = EnvironmentalConfig(event_probability=1.0, event_severity=0.4)
        first = EnvironmentalProcess(123).events_for_year(2000, "TST", ("urban", "rural"), config)
        second = EnvironmentalProcess(123).events_for_year(2000, "TST", ("urban", "rural"), config)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {"urban", "rural"})

    def test_stress_recovers_without_new_event(self):
        config = EnvironmentalConfig(baseline_pressure=0.1, event_probability=1.0, recovery_years=4)
        event = EnvironmentalProcess(1).events_for_year(2000, "TST", ("urban",), config)["urban"]
        stressed = EnvironmentalProcess.next_stress(0.0, event, config)
        recovered = EnvironmentalProcess.next_stress(stressed, None, config)
        self.assertGreater(stressed, recovered)

    def test_sensitivity_uses_shared_replicates(self):
        rows = run_sensitivity(
            "scenarios/family_major_countries.json",
            years=1,
            replicates=2,
            seed=20260810,
            probabilities=(0.0, 1.0),
        )
        self.assertEqual({row["shock_probability"] for row in rows}, {0.0, 1.0})
        self.assertTrue(any(row["metric"] == "environmental_stress" for row in rows))


if __name__ == "__main__":
    unittest.main()
