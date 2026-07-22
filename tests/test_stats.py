import math
import unittest

from riskengine.stats import (
    annualize_daily_mean,
    annualize_daily_std,
    mean,
    normal_cdf,
    normal_inv,
    normal_pdf,
    sample_std,
    sample_variance,
)


class TestMeanAndVariance(unittest.TestCase):
    def test_mean_basic(self):
        self.assertAlmostEqual(mean([1, 2, 3]), 2.0)
        self.assertEqual(mean([]), 0.0)

    def test_sample_variance(self):
        # Sample (n-1) variance of 0..4 is 2.5.
        self.assertAlmostEqual(sample_variance([0, 1, 2, 3, 4]), 2.5)
        self.assertEqual(sample_variance([1.0]), 0.0)

    def test_sample_std(self):
        self.assertAlmostEqual(sample_std([0, 1, 2, 3, 4]), math.sqrt(2.5))


class TestAnnualization(unittest.TestCase):
    def test_mean_scales_arithmetically(self):
        self.assertAlmostEqual(annualize_daily_mean(0.0005), 0.126)

    def test_std_scales_by_sqrt(self):
        self.assertAlmostEqual(annualize_daily_std(0.01), 0.01 * math.sqrt(252))


class TestNormalDist(unittest.TestCase):
    def test_cdf_known_values(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5)
        self.assertAlmostEqual(normal_cdf(1.6448536269514722), 0.95, places=6)
        self.assertAlmostEqual(normal_cdf(-1.6448536269514722), 0.05, places=6)

    def test_inverse_roundtrips(self):
        for p in (0.001, 0.025, 0.05, 0.5, 0.95, 0.975, 0.999):
            self.assertAlmostEqual(normal_cdf(normal_inv(p)), p, places=6)

    def test_inverse_rejects_endpoints(self):
        with self.assertRaises(ValueError):
            normal_inv(0.0)
        with self.assertRaises(ValueError):
            normal_inv(1.0)

    def test_pdf_peak(self):
        self.assertAlmostEqual(normal_pdf(0.0), 1.0 / math.sqrt(2.0 * math.pi))
        self.assertLess(normal_pdf(3.0), normal_pdf(0.0))


if __name__ == "__main__":
    unittest.main()
