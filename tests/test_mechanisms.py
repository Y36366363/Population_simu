import unittest

from population_simu.mechanisms import MECHANISM_CARDS, mechanism_catalog


class MechanismCardTests(unittest.TestCase):
    def test_every_card_has_required_audit_fields(self):
        required = ("purpose", "inputs", "parameters", "probability_rule",
                    "observables", "validation_metrics", "failure_scope")
        catalog = mechanism_catalog()
        self.assertGreaterEqual(len(catalog), 8)
        for card in MECHANISM_CARDS:
            data = catalog[card.name]
            self.assertTrue(all(data[field] for field in required))


if __name__ == "__main__":
    unittest.main()
