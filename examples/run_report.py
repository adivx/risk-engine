"""Run the full risk report from the library API (no CLI).

Equivalent to:  risk-engine --csv sample_data/sample_ohlcv.csv
"""

from riskengine.data import load_prices_csv
from riskengine.risk import (
    current_drawdown,
    longest_drawdown_stretch,
    max_drawdown,
    var_estimate,
)

SAMPLE = "sample_data/sample_ohlcv.csv"


def main() -> None:
    series = load_prices_csv(SAMPLE, name="SPX")
    risk = var_estimate(series.returns(), alpha=0.05)
    dd, peak_i, trough_i = max_drawdown(series.prices)
    days, start_i, end_i = longest_drawdown_stretch(series.prices)
    cur = current_drawdown(series.prices)

    print(f"{series.name} · {series.n_obs:,} obs")
    for engine in ("historical", "parametric", "monte_carlo"):
        v = risk[engine]
        print(f"  {engine:>11}  VaR {v['var'] * 100:5.2f}%  "
              f"CVaR {v['cvar'] * 100:5.2f}%")
    print(f"  max drawdown {dd * 100:.1f}% (obs {peak_i} → obs {trough_i})")
    print(f"  current drawdown {cur * 100:.1f}%")
    print(f"  longest underwater {days} obs (obs {start_i} → obs {end_i})")


if __name__ == "__main__":
    main()
