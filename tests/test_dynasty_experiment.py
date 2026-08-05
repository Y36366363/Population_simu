import unittest

from population_simu.dynasty_experiment import DynastyParameters, run_cell


class DynastyExperimentTests(unittest.TestCase):
    def test_reproducible(self):
        params = DynastyParameters()
        args = dict(
            initial_resources=100,
            initial_children=2,
            trials=300,
            generations=3,
            seed=8,
            parameters=params,
        )
        self.assertEqual(run_cell(**args), run_cell(**args))

    def test_resource_dilution_can_reduce_lineage_survival(self):
        params = DynastyParameters(material_deadline=58)
        concentrated = run_cell(
            initial_resources=100,
            initial_children=1,
            trials=1200,
            generations=4,
            seed=20,
            parameters=params,
        )
        dispersed = run_cell(
            initial_resources=100,
            initial_children=3,
            trials=1200,
            generations=4,
            seed=23,
            parameters=params,
        )
        self.assertGreater(
            concentrated["survival_to_final_generation"],
            dispersed["survival_to_final_generation"],
        )


if __name__ == "__main__":
    unittest.main()
