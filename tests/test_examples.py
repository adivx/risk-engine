"""Contract tests for the public API surface the README/examples document."""

import os
import tempfile
import unittest

from riskengine.data import load_prices_csv
from riskengine.risk import (
    historical_cvar,
    historical_var,
    var_estimate,
)

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                      "sample_data", "sample_ohlcv.csv")


class TestPublicApiContract(unittest.TestCase):
    def test_var_estimate_returns_all_engines(self):
        ps = load_prices_csv(SAMPLE)
        est = var_estimate(ps.returns())
        self.assertEqual(set(est), {"historical", "parametric", "monte_carlo"})

    def test_losses_are_positive(self):
        ps = load_prices_csv(SAMPLE)
        for engine in var_estimate(ps.returns()).values():
            self.assertGreater(engine["var"], 0.0)
            self.assertGreater(engine["cvar"], 0.0)

    def test_historical_cvar_at_least_var(self):
        ps = load_prices_csv(SAMPLE)
        returns = ps.returns()
        self.assertGreaterEqual(historical_cvar(returns, 0.05),
                                historical_var(returns, 0.05))

    def test_drawdown_svg_roundtrip(self):
        from riskengine.cli import drawdown_svg
        with tempfile.TemporaryDirectory() as tmp:
            out = drawdown_svg([100.0, 80.0, 90.0], out=os.path.join(tmp, "dd.svg"))
            with open(out) as f:
                self.assertIn("<svg", f.read())


if __name__ == "__main__":
    unittest.main()
