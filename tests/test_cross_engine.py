"""The three engines must agree on large normal samples.

Each engine estimates the same population number (the 1-day α-VaR), so on
a long sample drawn from a known normal they should converge to the same
value — the historical and Monte Carlo ones only within sampling noise.
"""

import random
import unittest

from riskengine.risk import (
    historical_var,
    monte_carlo_var,
    parametric_var,
    var_estimate,
)


class TestCrossEngineConsistency(unittest.TestCase):
    def test_historical_matches_parametric_on_large_sample(self):
        rng = random.Random(0)
        returns = [rng.gauss(0.0, 0.01) for _ in range(5000)]
        self.assertAlmostEqual(
            historical_var(returns, 0.05),
            parametric_var(0.0, 0.01, 0.05),
            delta=0.0005,
        )

    def test_monte_carlo_tracks_parametric(self):
        self.assertAlmostEqual(
            monte_carlo_var(0.0, 0.01, 0.05, n_paths=50_000, seed=1),
            parametric_var(0.0, 0.01, 0.05),
            delta=0.0005,
        )

    def test_var_estimate_runs_all_three(self):
        rng = random.Random(1)
        returns = [rng.gauss(0.0002, 0.012) for _ in range(2000)]
        est = var_estimate(returns, alpha=0.05)
        self.assertEqual(set(est), {"historical", "parametric", "monte_carlo"})
        for engine in est.values():
            self.assertGreater(engine["var"], 0.0)
            self.assertGreater(engine["cvar"], engine["var"])


if __name__ == "__main__":
    unittest.main()
