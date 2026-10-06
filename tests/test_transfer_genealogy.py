import json
import unittest

from population_simu.family_models import FamilyPerson
from population_simu.genealogy import BilateralGenealogy
from population_simu.transfer_ledger import TransferLedger, TransferRecord


def person(person_id, *, mother=None, father=None, sex=None):
    return FamilyPerson(
        id=person_id,
        clan_id=1,
        surname="Test",
        country_id="A",
        household_id=1,
        age=30,
        sex=sex or ("F" if person_id % 2 else "M"),
        innate_potential=0.5,
        region_id="urban",
        mother_id=mother,
        father_id=father,
    )


class TransferLedgerTests(unittest.TestCase):
    def test_records_both_counterparties_and_separate_channels(self):
        ledger = TransferLedger()
        ledger.record(
            year=2001,
            kind="household_formation_transfer",
            sender="household:1",
            receiver="household:2",
            cash_amount=12.5,
            resource_kind="property_value",
            resource_amount=8.0,
        )
        ledger.record(
            year=2001,
            kind="grandparent_care",
            sender="person:7",
            receiver="household:2",
            resource_kind="care_time",
            resource_amount=0.4,
        )
        self.assertEqual(len(ledger.query(entity="household:2")), 2)
        self.assertEqual(len(ledger.query(resource_kind="care_time")), 1)
        self.assertTrue(ledger.audit()["ok"])
        self.assertEqual(ledger.summary(), [
            {"year": 2001, "kind": "grandparent_care", "resource_kind": "care_time",
             "records": 1, "cash_amount": 0.0, "resource_amount": 0.4},
            {"year": 2001, "kind": "household_formation_transfer",
             "resource_kind": "property_value", "records": 1,
             "cash_amount": 12.5, "resource_amount": 8.0},
        ])
        json.dumps(ledger.as_dict(), allow_nan=False)

    def test_rejects_ambiguous_or_invalid_transfers(self):
        with self.assertRaises(ValueError):
            TransferRecord(2001, "gift", "household:1", "household:1", cash_amount=1)
        with self.assertRaises(ValueError):
            TransferRecord(2001, "gift", "household:1", "household:2")
        with self.assertRaises(ValueError):
            TransferRecord(2001, "gift", "household:1", "household:2",
                           resource_amount=1)

    def test_audit_checks_counterparties_and_years(self):
        ledger = TransferLedger()
        ledger.record(year=2002, kind="gift", sender="household:1",
                      receiver="person:2", cash_amount=1)
        audit = ledger.audit(valid_entities={"household:1"}, year_range=(2000, 2001))
        self.assertFalse(audit["ok"])
        self.assertEqual(len(audit["issues"]), 2)

    def test_strict_registry_preserves_historical_counterparties(self):
        ledger = TransferLedger(strict_entities=True)
        ledger.register_entity("household:1")
        ledger.register_entity("household:2")
        ledger.record(year=2001, kind="gift", sender="household:1",
                      receiver="household:2", cash_amount=1)
        self.assertTrue(ledger.audit(year_range=(2001, 2002))["ok"])
        with self.assertRaisesRegex(ValueError, "unregistered"):
            ledger.record(year=2002, kind="gift", sender="household:1",
                          receiver="household:3", cash_amount=1)

    def test_system_floor_is_an_explicit_counterparty_not_a_hidden_transfer(self):
        ledger = TransferLedger(strict_entities=True)
        for entity in ("system:minimum_resource_floor", "household:2"):
            ledger.register_entity(entity)
        ledger.record(
            year=2001,
            kind="minimum_resource_floor",
            sender="system:minimum_resource_floor",
            receiver="household:2",
            cash_amount=0.08,
        )
        row = ledger.query(kind="minimum_resource_floor")[0]
        self.assertEqual(row.sender, "system:minimum_resource_floor")
        self.assertEqual(row.cash_amount, 0.08)
        self.assertTrue(ledger.audit()["ok"])


class BilateralGenealogyTests(unittest.TestCase):
    def test_separates_maternal_and_paternal_ancestry_and_finds_descendants(self):
        people = {
            1: person(1, mother=2, father=3),
            2: person(2, mother=4, father=5),
            3: person(3, mother=6, father=7),
            4: person(4),
            5: person(5),
            6: person(6),
            7: person(7),
            8: person(8, mother=1, father=None),
            9: person(9, mother=8, father=None),
        }
        result = BilateralGenealogy(people).query(1)
        self.assertEqual({row["person_id"] for row in result["maternal_ancestors"]},
                         {2, 4, 5})
        self.assertEqual({row["person_id"] for row in result["paternal_ancestors"]},
                         {3, 6, 7})
        self.assertEqual(result["descendants"], [
            {"person_id": 8, "distance": 1},
            {"person_id": 9, "distance": 2},
        ])

    def test_pedigree_collapse_marks_both_sides_and_generation_limit(self):
        people = {
            1: person(1, mother=2, father=3),
            2: person(2, mother=4),
            3: person(3, father=4),
            4: person(4),
        }
        full = BilateralGenealogy(people).query(1)
        shared = next(row for row in full["ancestors"] if row["person_id"] == 4)
        self.assertEqual(shared["sides"], ["maternal", "paternal"])
        limited = BilateralGenealogy(people).query(1, max_generations=1)
        self.assertEqual({row["person_id"] for row in limited["ancestors"]}, {2, 3})
        with self.assertRaises(ValueError):
            BilateralGenealogy(people).query(1, max_generations=0)

    def test_genealogy_audit_detects_role_errors_and_cycles(self):
        valid = {
            1: person(1, mother=2, father=3),
            2: person(2, sex="F"),
            3: person(3, sex="M"),
        }
        self.assertTrue(BilateralGenealogy(valid).audit()["ok"])
        invalid = {
            1: person(1, mother=2, father=3),
            2: person(2, mother=1, sex="M"),
            3: person(3, sex="F"),
        }
        audit = BilateralGenealogy(invalid).audit()
        self.assertFalse(audit["ok"])
        self.assertTrue(any("cycle" in issue for issue in audit["issues"]))
        self.assertTrue(any("expected F" in issue or "expected M" in issue
                            for issue in audit["issues"]))


if __name__ == "__main__":
    unittest.main()
