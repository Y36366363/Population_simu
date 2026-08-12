import unittest

from population_simu.calibration import (
    grid_search,
    random_search,
    temporal_split,
    evaluate_parameters,
    rolling_origin_splits,
    leave_one_group_out,
    interval_metrics,
    replay_errors,
    replay_errors_by_group,
)


class CalibrationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
