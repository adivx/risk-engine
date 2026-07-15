"""How to embed risk-engine in your own analytics app."""

from riskengine.data import PriceSeries
from riskengine.risk import var_estimate


def score_a_strategy(prices: list) -> dict:
    """Return the 1-day 95% tail risk of a strategy's equity curve."""
    series = PriceSeries(name="strategy", dates=[], prices=prices)
    return var_estimate(series.returns(), alpha=0.05)


if __name__ == "__main__":
    import random

    rng = random.Random(1)
    equity = [100.0]
    for _ in range(252):
        equity.append(equity[-1] * (1.0 + rng.gauss(0.0005, 0.015)))
    print(score_a_strategy(equity))
