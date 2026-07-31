import math
import unittest

from riskengine.risk import (
    current_drawdown,
    drawdown_series,
    historical_cvar,
    historical_var,
    longest_drawdown_stretch,
    max_drawdown,
    monte_carlo_cvar,
    monte_carlo_var,
    parametric_cvar,
    parametric_var,
    var_estimate,
)


class TestHistoricalVar(unittest.TestCase):
    def test_var_is_loss_positive(self):
        returns = [0.01, -0.02, 0.005, -0.03, 0.02, -0.015]
        self.assertGreater(historical_var(returns, 0.05), 0.0)

    def test_small_alpha_takes_worst_loss(self):
        returns = [-0.01, -0.05, -0.10]
        # ceil(0.5 * 3) - 1 = 1 -> second-worst loss = 5%.
        self.assertAlmostEqual(historical_var(returns, 0.5), 0.05)

    def test_high_alpha_is_mild_loss(self):
        returns = [-0.01, -0.02, -0.03]
        # alpha -> 1 means "the worst 9-in-10 outcome": the mildest loss.
        self.assertAlmostEqual(historical_var(returns, 0.9), 0.01)

    def test_tiny_alpha_is_worst_loss(self):
        returns = [-0.01, -0.02, -0.05]
        # ceil(0.01 * 3) - 1 = 0 -> the single worst loss = 5%.
        self.assertAlmostEqual(historical_var(returns, 0.01), 0.05)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            historical_var([], 0.05)

    def test_bad_alpha(self):
        with self.assertRaises(ValueError):
            historical_var([1.0], 0.0)


class TestHistoricalCvar(unittest.TestCase):
    def test_cvar_is_mean_of_tail(self):
        returns = [-0.01, -0.02, -0.03, -0.04, -0.05, 0.05, 0.06, 0.07]
        cvar = historical_cvar(returns, 0.25)
        # Worst quarter = the two worst losses -> mean 4.5%.
        self.assertAlmostEqual(cvar, 0.045)

    def test_cvar_at_least_var(self):
        returns = [0.01, -0.02, -0.04, -0.06, 0.03]
        var = historical_var(returns, 0.05)
        cvar = historical_cvar(returns, 0.05)
        self.assertGreaterEqual(cvar, var)


class TestParametric(unittest.TestCase):
    def test_parametric_var_matches_normal(self):
        # mu=0, sigma=1, alpha=0.05 -> z=-1.645 -> VaR=1.645.
        self.assertAlmostEqual(parametric_var(0.0, 1.0, 0.05), 1.64485, places=4)

    def test_parametric_cvar_exceeds_var(self):
        var = parametric_var(0.0005, 0.01, 0.05)
        cvar = parametric_cvar(0.0005, 0.01, 0.05)
        self.assertGreater(cvar, var)

    def test_parametric_cvar_formula(self):
        # ES = sigma * phi(z)/alpha - mu; with sigma=1, mu=0, alpha=0.05.
        expected = 2.0627  # phi(-1.645)/0.05
        self.assertAlmostEqual(parametric_cvar(0.0, 1.0, 0.05), expected, places=3)


class TestMonteCarlo(unittest.TestCase):
    def test_seeded_reproducible(self):
        a = monte_carlo_var(0.0005, 0.01, 0.05, n_paths=5000, seed=7)
        b = monte_carlo_var(0.0005, 0.01, 0.05, n_paths=5000, seed=7)
        self.assertEqual(a, b)

    def test_mc_converges_to_parametric(self):
        var_mc = monte_carlo_var(0.0, 0.01, 0.05, n_paths=50_000, seed=1)
        var_par = parametric_var(0.0, 0.01, 0.05)
        self.assertAlmostEqual(var_mc, var_par, delta=0.0005)

    def test_mc_cvar_close_to_parametric_cvar(self):
        cvar_mc = monte_carlo_cvar(0.0, 0.01, 0.05, n_paths=50_000, seed=1)
        cvar_par = parametric_cvar(0.0, 0.01, 0.05)
        self.assertAlmostEqual(cvar_mc, cvar_par, delta=0.001)


class TestVarEstimate(unittest.TestCase):
    def test_shape(self):
        est = var_estimate([0.01, -0.01, 0.02, -0.02, 0.005, -0.005], alpha=0.05)
        self.assertEqual(set(est), {"historical", "parametric", "monte_carlo"})
        for engine in est.values():
            self.assertIn("var", engine)
            self.assertIn("cvar", engine)


class TestDrawdowns(unittest.TestCase):
    def test_drawdown_series_tracks_running_peak(self):
        prices = [100.0, 120.0, 90.0, 110.0]
        dd = drawdown_series(prices)
        self.assertEqual(dd[0], 0.0)
        self.assertEqual(dd[1], 0.0)
        self.assertAlmostEqual(dd[2], 90.0 / 120.0 - 1.0)
        self.assertAlmostEqual(dd[3], 110.0 / 120.0 - 1.0)

    def test_max_drawdown_known_case(self):
        prices = [100.0, 120.0, 80.0, 130.0]
        dd, peak_i, trough_i = max_drawdown(prices)
        self.assertAlmostEqual(dd, -(40.0 / 120.0))
        self.assertEqual((peak_i, trough_i), (1, 2))

    def test_monotonic_up_is_zero(self):
        dd, peak_i, trough_i = max_drawdown([100.0, 101.0, 102.0])
        self.assertEqual(dd, 0.0)
        self.assertEqual(peak_i, trough_i)

    def test_half_loss(self):
        dd, _, _ = max_drawdown([100.0, 50.0, 100.0])
        self.assertAlmostEqual(dd, -0.5)

    def test_current_drawdown(self):
        prices = [100.0, 150.0, 120.0]
        self.assertAlmostEqual(current_drawdown(prices), 120.0 / 150.0 - 1.0)

    def test_longest_stretch(self):
        # Underwater from index 2..5 = 4 obs.
        prices = [100.0, 110.0, 90.0, 95.0, 85.0, 99.0, 120.0, 115.0, 80.0]
        length, start, end = longest_drawdown_stretch(prices)
        self.assertEqual(length, 4)
        self.assertEqual((start, end), (2, 5))

    def test_no_underwater(self):
        length, _, _ = longest_drawdown_stretch([100.0, 101.0, 102.0])
        self.assertEqual(length, 0)

    def test_entirely_underwater(self):
        # Never above the running peak after the first obs -> underwater
        # from index 1 through the end = 3 obs.
        prices = [100.0, 90.0, 80.0, 70.0]
        length, start, end = longest_drawdown_stretch(prices)
        self.assertEqual((length, start, end), (3, 1, 3))


if __name__ == "__main__":
    unittest.main()
