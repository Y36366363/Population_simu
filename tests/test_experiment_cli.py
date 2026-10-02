from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from population_simu.experiments import ExperimentArm, apply_intervention, run_experiment, run_spec
from population_simu.family_config import FamilyScenario
from population_simu.family_world import FamilyWorld

ROOT = Path(__file__).resolve().parents[1]


def scenario():
    full = FamilyScenario.from_json(ROOT / "scenarios/family_major_countries.json")
    return replace(full, countries=(replace(full.countries[0], initial_clans=2),))


class ExperimentCliTests(unittest.TestCase):
    def test_relative_spec_runs_from_another_directory_and_reproduces_json(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "scenario.json").write_text(json.dumps(asdict(scenario())))
            specification = {
                "schema_version": 1, "scenario": "scenario.json", "years": 1,
                "warmup_years": 1, "seeds": [19], "metrics": ["population"],
                "arms": [{"name": "noop"}, {"name": "no_births", "disabled_processes": ["births"]}],
            }
            (directory / "spec.json").write_text(json.dumps(specification))
            command = [sys.executable, str(ROOT / "scripts/run_controlled_experiment.py"),
                       "spec.json", "--output", "result.json"]
            first = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = json.loads((directory / "result.json").read_text())
            second = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(saved, json.loads((directory / "result.json").read_text()))
            self.assertEqual(saved["runs"][0]["start_year"], 1971)
            self.assertTrue(all(row["difference"] == 0 for row in saved["paired_differences"]
                                if row["arm"] == "noop"))
            self.assertEqual(len(saved["spec"]["sha256"]), 64)

    def test_spec_rejects_unknown_fields_and_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "spec.json"
            for invalid in ({"schema_version": 2}, {"schema_version": True},
                            {"schema_version": 1, "ignored_control": 1}):
                path.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    run_spec(path)

    def test_process_sets_are_recorded_as_json_safe_sorted_names(self):
        report = run_experiment(scenario(), [ExperimentArm(
            "process_set", disabled_processes={"deaths", "births"})],
            years=1, seeds=[5], metrics=("population",))
        encoded = json.dumps(report, allow_nan=False)
        names = json.loads(encoded)["configuration"]["arms"][0]["disabled_processes"]
        self.assertEqual(names, ["births", "deaths"])

    def test_retrospective_technology_growth_override_is_rejected(self):
        world = FamilyWorld(scenario())
        world.step()
        before = world.checkpoint().fingerprint
        with self.assertRaises(ValueError):
            apply_intervention(world, ExperimentArm(
                "retroactive", country_parameters={"CHN": {"technology_growth": 0.1}}))
        self.assertEqual(before, world.checkpoint().fingerprint)

    def test_numerical_overflow_fails_the_experiment_audit(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            run_experiment(scenario(), [ExperimentArm(
                "overflow", country_parameters={"CHN": {"health_budget_per_person": 1e308}})],
                years=1, seeds=[11], metrics=("public_spending",))


if __name__ == "__main__":
    unittest.main()
