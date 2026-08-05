"""Parametric VaR/CVaR across confidence levels + Monte Carlo convergence.

The parametric engine has closed forms — VaR = −z_α·σ and
CVaR = σ·φ(z_α)/α for μ = 0 — so it can be checked against the z-table
directly. Monte Carlo should converge onto those numbers as the number
of paths grows.
"""

import unittest

from riskengine.risk import (
    monte_carlo_cvar,
    monte_carlo_var,
    parametric_cvar,
    parametric_var,
)
from riskengine.stats import normal_inv, normal_pdf


class TestParametricAtAlphas(unittest.TestCase):
    def test_var_equals_minus_z(self):
        for alpha in (0.01, 0.05, 0.10):
            self.assertAlmostEqual(parametric_var(0.0, 1.0, alpha),
                                   -normal_inv(alpha), places=6)

    def test_cvar_closed_form(self):
        for alpha in (0.01, 0.05, 0.10):
            expected = normal_pdf(normal_inv(alpha)) / alpha
            self.assertAlmostEqual(parametric_cvar(0.0, 1.0, alpha),
                                   expected, places=6)


class TestMonteCarloConvergence(unittest.TestCase):
    def test_var_converges_at_100k_paths(self):
        self.assertAlmostEqual(
            monte_carlo_var(0.0, 0.01, 0.05, n_paths=100_000, seed=3),
            parametric_var(0.0, 0.01, 0.05),
            delta=0.0003,
        )

    def test_cvar_converges_at_100k_paths(self):
        self.assertAlmostEqual(
            monte_carlo_cvar(0.0, 0.01, 0.05, n_paths=100_000, seed=3),
            parametric_cvar(0.0, 0.01, 0.05),
            delta=0.0004,
        )


if __name__ == "__main__":
    unittest.main()
