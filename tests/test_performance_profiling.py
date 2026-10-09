import unittest

from population_simu.performance_profiling import STEP_PHASES, profile_simulation_phases

from tests.test_experiments import small_scenario


class PerformanceProfilingTests(unittest.TestCase):
    def test_profiles_two_periods_without_changing_model_contract(self):
        report = profile_simulation_phases(
            small_scenario(), years=4, seeds=[7, 8], split_after_years=2,
        )
        self.assertEqual(len(report["runs"]), 2)
        self.assertEqual(len(report["phase_growth_ranking"]), len(STEP_PHASES))
        self.assertGreater(report["median_step_late_to_early_ratio"], 0)
        for run in report["runs"]:
            self.assertEqual(run["early"]["years"], 2)
            self.assertEqual(run["late"]["years"], 2)
            self.assertEqual(run["late"]["end_year"], 2004)
            self.assertEqual(run["late"]["phases"]["_births"]["calls"], 2)
            self.assertGreater(
                run["late"]["nested_diagnostics"]["_desired_children"]["calls"], 0
            )
            self.assertGreater(run["late"]["unattributed_step_seconds"], 0)

    def test_rejects_invalid_design(self):
        with self.assertRaises(ValueError):
            profile_simulation_phases(small_scenario(), years=4, seeds=[7, 7])
        with self.assertRaises(ValueError):
            profile_simulation_phases(
                small_scenario(), years=4, seeds=[7], split_after_years=4,
            )


if __name__ == "__main__":
    unittest.main()
