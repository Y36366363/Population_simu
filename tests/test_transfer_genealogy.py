import json
import unittest

from population_simu.family_models import FamilyPerson
from population_simu.genealogy import BilateralGenealogy
from population_simu.transfer_ledger import TransferLedger, TransferRecord


def person(person_id, *, mother=None, father=None):
    return FamilyPerson(
        id=person_id,
        clan_id=1,
        surname="Test",
        country_id="A",
        household_id=1,
        age=30,
        sex="F" if person_id % 2 else "M",
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


if __name__ == "__main__":
    unittest.main()
