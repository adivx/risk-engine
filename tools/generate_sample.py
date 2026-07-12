"""Generate a seeded synthetic OHLCV CSV for local testing.

Writes `out_path` with columns date,open,high,low,close,volume from a
geometric Brownian motion, mirroring the schema of the bundled sample.
"""

import csv
import datetime as dt
import random
import sys

PERIODS_PER_YEAR = 252


def main(years: int = 1, start: float = 100.0, seed: int = 7,
         out_path: str = "synthetic_ohlcv.csv") -> None:
    """Write a synthetic daily OHLCV series to ``out_path``."""
    rng = random.Random(seed)
    mu_d = 0.08 / PERIODS_PER_YEAR
    sig_d = 0.18 / PERIODS_PER_YEAR
    d = dt.date(2020, 1, 1)
    price = start
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        while (d.year - 2020) < years:
            if d.weekday() < 5:  # trading days only
                op = price
                price = op * (1.0 + rng.gauss(mu_d, sig_d))
                hi = max(op, price) * (1.0 + abs(rng.gauss(0.0, 0.002)))
                lo = min(op, price) * (1.0 - abs(rng.gauss(0.0, 0.002)))
                w.writerow([d.isoformat(), f"{op:.4f}", f"{hi:.4f}",
                            f"{lo:.4f}", f"{price:.4f}",
                            rng.randint(100_000, 5_000_000)])
            d += dt.timedelta(days=1)


if __name__ == "__main__":
    years = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else "synthetic_ohlcv.csv"
    main(years=years, out_path=out)
    print(f"wrote {out}")
