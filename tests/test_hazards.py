import unittest

from population_simu.hazards import (
    AgeRateProfile,
    duration_hazard,
    hazard_to_probability,
    logit_probability,
    softmax_weights,
)


class HazardTests(unittest.TestCase):
    def test_age_profile_interpolates_and_clamps(self):
        profile = AgeRateProfile((20, 30, 40), (0.1, 0.5, 0.2))
        self.assertEqual(profile.rate(10), 0.1)
        self.assertAlmostEqual(profile.rate(25), 0.3)
        self.assertEqual(profile.rate(50), 0.2)

    def test_logit_is_bounded_and_monotonic(self):
        self.assertGreater(logit_probability(2), logit_probability(-2))
        self.assertGreaterEqual(logit_probability(-100), 0)
        self.assertLessEqual(logit_probability(100), 1)

    def test_softmax_keeps_multiple_destinations_possible(self):
        weights = softmax_weights([1.0, 1.0, 0.0], temperature=0.4)
        self.assertEqual(len(weights), 3)
        self.assertTrue(all(weight > 0 for weight in weights))

    def test_hazard_conversion_is_bounded_and_monotonic(self):
        self.assertEqual(hazard_to_probability(0), 0.0)
        self.assertGreater(hazard_to_probability(1.0), hazard_to_probability(0.2))
        self.assertGreater(duration_hazard(0.1, 4, 0.1), duration_hazard(0.1, 0, 0.1))
