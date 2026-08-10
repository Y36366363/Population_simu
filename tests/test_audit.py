import unittest

from population_simu.family_world import FamilyWorld
from tests.test_family_world import family_scenario


class AuditTests(unittest.TestCase):
    def test_family_world_audit_passes_for_valid_run(self):
        world = FamilyWorld(family_scenario())
        world.run(2002)
        report = world.audit()
        self.assertTrue(report["ok"], report["issues"])

    def test_audit_detects_partition_error(self):
        world = FamilyWorld(family_scenario())
        snapshot = world.snapshot()
        snapshot["countries"]["TST"]["regions"][0]["population"] += 1
        from population_simu.audit import audit_snapshot

        self.assertTrue(audit_snapshot(snapshot))


if __name__ == "__main__":
    unittest.main()

