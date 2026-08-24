import unittest

from population_simu.benchmarks import (
    compare_models,
    compare_models_rolling,
    fixed_trend_runner,
    wpp_style_runner,
    paired_model_comparison,
    rank_models,
    reduced_form_runner,
    household_simulator_runner,
)

from population_simu.calibration import (
    grid_search,
    random_search,
    temporal_split,
    evaluate_parameters,
    rolling_origin_splits,
    leave_one_group_out,
    interval_metrics,
    empirical_crps,
    crps_metrics,
    stratified_interval_metrics,
    replay_errors,
    replay_errors_by_group,
)
from population_simu.household_calibration import calibrate_household_parameters, calibrate_fertility_observations
from population_simu.national_calibration import FertilityObservation


class CalibrationTests(unittest.TestCase):
    def test_household_calibration_marks_unidentified_hazards_as_priors(self):
        rows = [{"entity": "A", "year": year, "asfr_15_44": 60 + year - 2010,
                 "housing_cost_burden": 0.3 + 0.01 * (year - 2010)}
                for year in range(2010, 2014)]
        calibrated = calibrate_household_parameters(rows)
        self.assertIn("housing_elasticity", calibrated.identified)
        self.assertIn("partnership_exposure", calibrated.prior_only)

    def test_weighted_fertility_observations_identify_age_marriage_and_parity(self):
        rows = []
        for age, rate in ((18, .02), (22, .05), (26, .08), (30, .07), (34, .04)):
            rows.append(FertilityObservation("US", 2015, "married", "all", age,
                                             rate * 1000, 1000))
            rows.append(FertilityObservation("US", 2015, "unmarried", "all", age,
                                             0, 1000))
        for parity, rate in (("first", .08), ("second", .04), ("third_plus", .02)):
            rows.append(FertilityObservation("US", 2015, "married", parity, 30,
                                             rate * 1000, 1000))
        calibrated = calibrate_fertility_observations(rows)
        self.assertIn("age_profile", calibrated.identified)
        self.assertIn("partnership_exposure", calibrated.identified)
        self.assertIn("parity_progression", calibrated.identified)
        self.assertAlmostEqual(calibrated.partnership_exposure, .5)
        self.assertAlmostEqual(calibrated.parity_progression[1], .5)

    def test_sparse_observations_do_not_claim_identification(self):
        calibrated = calibrate_fertility_observations([
            {"age": 30, "marital": "married", "parity": "first",
             "births": 3, "exposure": 100}
        ])
        self.assertIn("age_profile", calibrated.prior_only)
        self.assertIn("partnership_exposure", calibrated.prior_only)
        self.assertAlmostEqual(calibrated.female_exposure_scale, 1.0)

    def test_reduced_form_and_household_runners_cover_comparable_contract(self):
        rows = []
        for entity in ("A", "B"):
            for year in range(2010, 2015):
                rows.append({"entity": entity, "year": year,
                             "asfr_15_44": 60 + (year - 2010),
                             "housing_cost_burden": 0.35,
                             "births_15_44": 60000,
                             "female_15_44": 1000000})
        models = {"reduced": reduced_form_runner(), "household": household_simulator_runner()}
        for runner in models.values():
            forecast = runner(rows[:-2], [2013, 2014], 7)
            self.assertEqual({(r["entity"], r["year"]) for r in forecast},
                             {(entity, year) for entity in ("A", "B") for year in (2013, 2014)})

    def test_replay_errors_aligns_by_year(self):
        observed = [{"year": 2000, "population": 10}, {"year": 2001, "population": 12}]
        simulated = [{"year": 2000, "population": 9}, {"year": 2001, "population": 13}]
        result = replay_errors(observed, simulated, metrics=("population",))
        self.assertEqual(result["population"]["n"], 2)
        self.assertAlmostEqual(result["population"]["bias"], 0.0)

    def test_grid_search_returns_best_parameter(self):
        observed = [{"year": year, "population": 10 + year - 2000}
                    for year in range(2000, 2003)]

        def simulate(parameters):
            offset = parameters["offset"]
            return [{"year": year, "population": 10 + year - 2000 + offset}
                    for year in range(2000, 2003)]

        results = grid_search(observed, {"offset": [-1, 0, 1]}, simulate,
                              metrics=("population",))
        self.assertEqual(results[0]["parameters"], {"offset": 0.0})
        self.assertEqual(results[0]["objective"], 0.0)

    def test_random_search_is_reproducible(self):
        observed = [{"year": 2000, "population": 1.5}]

        def simulate(parameters):
            return [{"year": 2000, "population": parameters["x"]}]

        first = random_search(observed, {"x": (0, 2)}, simulate,
                              trials=5, seed=7, metrics=("population",))
        second = random_search(observed, {"x": (0, 2)}, simulate,
                               trials=5, seed=7, metrics=("population",))
        self.assertEqual(first, second)

    def test_grouped_replay_keeps_entities_separate(self):
        observed = [
            {"entity": "A", "year": 2000, "population": 10},
            {"entity": "B", "year": 2000, "population": 20},
        ]
        simulated = [
            {"entity": "A", "year": 2000, "population": 11},
            {"entity": "B", "year": 2000, "population": 18},
        ]
        result = replay_errors_by_group(observed, simulated, metrics=("population",))
        self.assertEqual(set(result), {"A", "B"})
        self.assertEqual(result["A"]["population"]["mae"], 1)

    def test_temporal_split_keeps_future_years_out_of_training(self):
        rows = [{"entity": entity, "year": year, "population": year}
                for entity in ("A", "B") for year in range(2000, 2010)]
        train, validation = temporal_split(rows, validation_fraction=0.2,
                                           group="entity")
        self.assertLess(max(row["year"] for row in train),
                        min(row["year"] for row in validation))
        self.assertEqual(len(train), 16)
        self.assertEqual(len(validation), 4)

    def test_csv_loader_rejects_missing_year(self):
        import tempfile
        from pathlib import Path
        from population_simu.calibration import load_observed_csv

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("entity,population\nA,1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_observed_csv(path)

    def test_evaluate_parameters_returns_validation_objective(self):
        observed = [{"year": 2000, "population": 10}]
        result = evaluate_parameters(
            observed, {"offset": 1},
            lambda parameters: [{"year": 2000, "population": 11}],
            metrics=("population",),
        )
        self.assertEqual(result["objective"], 1)

    def test_rolling_origin_uses_only_past_years(self):
        rows = [{"year": year, "population": year} for year in range(2000, 2008)]
        folds = rolling_origin_splits(rows, initial_train_years=3, horizon=2)
        self.assertEqual(len(folds), 3)
        self.assertLess(max(r["year"] for r in folds[0][0]), min(r["year"] for r in folds[0][1]))
        self.assertEqual([r["year"] for r in folds[-1][1]], [2005, 2006])

    def test_leave_one_group_out_reports_each_entity(self):
        rows = [{"entity": entity, "year": 2000, "population": value}
                for entity, value in (("A", 10), ("B", 20))]
        results = leave_one_group_out(
            rows, lambda train: {"offset": 0},
            lambda params: rows, metrics=("population",), group="entity")
        self.assertEqual([row["held_out"] for row in results], ["A", "B"])

    def test_interval_metrics_reports_coverage_and_width(self):
        observed = [{"year": 2000, "population": 10}]
        replicas = [[{"year": 2000, "population": value}] for value in (8, 9, 10, 11, 12)]
        result = interval_metrics(observed, replicas, metrics=("population",))
        self.assertEqual(result["population"]["coverage"], 1.0)
        self.assertGreater(result["population"]["mean_interval_width"], 0)

    def test_empirical_crps_is_zero_for_perfect_point_samples(self):
        self.assertEqual(empirical_crps(10, [10, 10, 10]), 0.0)

    def test_crps_and_stratified_intervals(self):
        observed = [{"entity": "A", "year": 2000, "population": 10}]
        replicas = [[{"entity": "A", "year": 2000, "population": value}]
                    for value in (9, 10, 11)]
        self.assertAlmostEqual(crps_metrics(observed, replicas,
                                            metrics=("population",), group="entity")
                               ["population"]["mean_crps"], 2 / 9)
        result = stratified_interval_metrics(observed, replicas, strata=("entity",),
                                             metrics=("population",))
        self.assertIn("A", result)

    def test_baseline_models_can_be_compared(self):
        observed = [{"entity": "A", "year": year, "population": 100 + 2 * (year - 2000)}
                    for year in range(2000, 2006)]
        result = compare_models(
            observed,
            {"fixed_trend": fixed_trend_runner(), "wpp_style": wpp_style_runner()},
            train_years=4, horizon=2, metric="population", replicates=2,
        )
        self.assertEqual(set(result), {"fixed_trend", "wpp_style"})
        self.assertIn("mean_crps", result["fixed_trend"]["crps"]["population"])

    def test_rolling_comparison_reports_bootstrap_and_baseline_delta(self):
        observed = [
            {"entity": entity, "year": year, "population": 100 + 2 * (year - 2000) + offset}
            for entity, offset in (("A", 0), ("B", 20))
            for year in range(2000, 2010)
        ]
        result = compare_models_rolling(
            observed,
            {"fixed": fixed_trend_runner(), "damped": wpp_style_runner()},
            initial_train_years=4, horizon=2, step=2, replicates=3,
            bootstrap_draws=100, baseline="fixed",
        )
        self.assertIn("lower_95", result["fixed"]["summary"]["mape"])
        self.assertIn("win_rate", result["damped"]["vs_baseline"])
        self.assertIn("relative_improvement", result["damped"]["vs_baseline"])
        self.assertGreaterEqual(result["damped"]["vs_baseline"]["win_rate"], 0)

    def test_paired_comparison_and_ranking_are_explicit(self):
        observed = [{"entity": "A", "year": year, "population": 100 + 2 * (year - 2000)}
                    for year in range(2000, 2010)]
        result = compare_models_rolling(
            observed,
            {"fixed": fixed_trend_runner(), "damped": wpp_style_runner()},
            initial_train_years=4, horizon=2, step=2, replicates=2,
            bootstrap_draws=100,
        )
        paired = paired_model_comparison(result, "fixed", "damped", bootstrap_draws=100)
        self.assertEqual(paired["delta_definition"], "candidate - reference")
        ranking = rank_models(result)
        self.assertEqual(ranking[0]["rank"], 1)
        self.assertIn("interpretation", ranking[0])

    def test_model_comparison_rejects_incomplete_forecast(self):
        observed = [{"entity": "A", "year": year, "population": 100 + year}
                    for year in range(2000, 2005)]

        def incomplete(train, years, seed):
            return [{"entity": "A", "year": years[0], "population": 1}]

        with self.assertRaises(ValueError):
            compare_models(observed, {"bad": incomplete}, train_years=2,
                           horizon=2, replicates=2)

    def test_rolling_comparison_rejects_unknown_baseline(self):
        with self.assertRaises(ValueError):
            compare_models_rolling(
                [{"entity": "A", "year": y, "population": y} for y in range(5)],
                {"fixed": fixed_trend_runner()}, initial_train_years=2,
                baseline="missing", bootstrap_draws=100,
            )


if __name__ == "__main__":
    unittest.main()
