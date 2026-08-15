import unittest

from population_simu.fertility import FertilitySchedule
from population_simu.hazards import AgeRateProfile
from population_simu.national_calibration import (
    AgeSpecificMigrationMatrix,
    FertilityScheduleRecord,
    LifeTableSchedule,
    MigrationRecord,
    NationalCalibrationBundle,
)


class NationalCalibrationTests(unittest.TestCase):
    def _bundle(self):
        profile = AgeRateProfile((0, 50, 100), (0.01, 0.02, 0.2))
        return NationalCalibrationBundle(
            life_tables=(LifeTableSchedule("A", 2000, {"F": profile, "M": profile}),),
            migration_matrices=(AgeSpecificMigrationMatrix(
                2000,
                (MigrationRecord("A", "B", "F", 20, 0.1),
                 MigrationRecord("A", "B", "M", 20, 0.1)),
                ("A", "B", "outside"),
            ),),
            fertility_records=(FertilityScheduleRecord(
                "A", 2000, "married", "first", profile),),
            metadata={"source": "test"},
        )

    def test_bundle_validates_and_compiles_fertility(self):
        bundle = self._bundle()
        self.assertTrue(bundle.validate(strict=False).ok)
        self.assertIsInstance(bundle.fertility_schedule("A", 2000), FertilitySchedule)
        self.assertIn("B", bundle.migration_matrix(2000).to_hazards()["A"])
        inputs = bundle.compile_cohort_inputs("A", 2000, local_nodes=("A", "B"))
        self.assertIn("outside", inputs["external_nodes"])
        self.assertIn("A", inputs["mortality_rates"])

    def test_strict_mode_rejects_incomplete_life_table(self):
        bundle = self._bundle()
        report = bundle.validate(strict=True)
        self.assertFalse(report.ok)
        self.assertTrue(any("完整生命表" in error for error in report.errors))

    def test_duplicate_fertility_record_is_rejected(self):
        bundle = self._bundle()
        duplicate = FertilityScheduleRecord("A", 2000, "married", "first",
                                            AgeRateProfile((0,), (0.1,)))
        invalid = NationalCalibrationBundle(
            life_tables=bundle.life_tables,
            migration_matrices=bundle.migration_matrices,
            fertility_records=bundle.fertility_records + (duplicate,),
            metadata={"source": "test"},
        )
        self.assertFalse(invalid.validate(strict=False).ok)


if __name__ == "__main__":
    unittest.main()
