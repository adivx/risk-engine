"""Compare the three VaR engines and flag fat tails.

The headline diagnostic of the risk lab: when the *historical* VaR is
meaningfully larger than the *parametric* (normal) VaR, the empirical tail
is fatter than a Gaussian fit — the gap is a quick stand-in for tail risk.

Exits non-zero when the gap exceeds `--threshold`, so it can gate in CI or
a scheduled risk check.

    python tools/compare_engines.py                          # synthetic
    python tools/compare_engines.py --csv sample_data/sample_ohlcv.csv
    python tools/compare_engines.py --csv returns.csv --alpha 0.01 --threshold 0.003
"""

import argparse
import sys

from riskengine.data import load_prices_csv, synthetic_equity_curve
from riskengine.risk import var_estimate


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", metavar="PATH",
                   help="price CSV instead of seeded synthetic data")
    p.add_argument("--alpha", type=float, default=0.05,
                   help="tail quantile (default 0.05)")
    p.add_argument("--threshold", type=float, default=0.002,
                   help="historical-vs-parametric gap (as a decimal loss) "
                        "that triggers a non-zero exit (default 0.002)")
    p.add_argument("--seed", type=int, default=42,
                   help="seed for synthetic data (default 42)")
    args = p.parse_args()

    series = (load_prices_csv(args.csv)
              if args.csv
              else synthetic_equity_curve(seed=args.seed, years=5))
    report = var_estimate(series.returns(), alpha=args.alpha)

    hist, para = report["historical"]["var"], report["parametric"]["var"]
    gap = hist - para
    print(f"{series.name}: α = {args.alpha:.0%}")
    for engine in ("historical", "parametric", "monte_carlo"):
        v = report[engine]
        print(f"  {engine:<12} VaR {v['var'] * 100:6.2f}%  "
              f"CVaR {v['cvar'] * 100:6.2f}%")
    print(f"\ngap (historical − parametric) = {gap * 100:+.2f}pp "
          f"({'fat tails' if gap > 0 else 'within a normal model'})")

    if gap > args.threshold:
        print(f"\nthreshold {args.threshold * 100:.1f}pp exceeded — tail risk "
              f"flagged.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
