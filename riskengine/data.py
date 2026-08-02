"""Market data: CSV loading + a seeded synthetic equity curve.

``load_prices_csv`` reads a single-asset price series from a CSV. It
recognizes OHLCV files (``sample_data/sample_ohlcv.csv``, by using the
``close`` column), a bare single numeric column, or an optional leading
date column that is carried along but not used in analytics. Real data
drops in without any schema — ``--csv`` on the CLI.

``synthetic_equity_curve`` is the default path: a geometric Brownian
motion with realistic drift/vol, seeded so every run reproduces offline.
"""

import csv
import datetime as dt
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

PERIODS_PER_YEAR = 252

_CLOSE_COLUMNS = ("adj close", "close", "close price")


@dataclass
class PriceSeries:
    """A single-asset price series with its observation dates.

    dates:   ISO date strings (may be empty for bare numeric CSVs)
    prices:  one close per observation
    periods_per_year: trading days in a year (252)
    """

    name: str
    dates: List[str]
    prices: List[float]
    periods_per_year: int = field(default=PERIODS_PER_YEAR)

    @property
    def n_obs(self) -> int:
        return len(self.prices)

    def returns(self) -> List[float]:
        """Period-over-period returns (n_obs - 1 values)."""
        return [
            self.prices[t] / self.prices[t - 1] - 1.0
            for t in range(1, len(self.prices))
        ]

    def from_date(self) -> Optional[str]:
        return self.dates[0] if self.dates else None

    def to_date(self) -> Optional[str]:
        return self.dates[-1] if self.dates else None


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def load_prices_csv(path: str, name: str = "CSV") -> PriceSeries:
    """Load a price series from a CSV.

    Picks the ``close`` column for OHLCV files; otherwise the first
    numeric column. A leading non-numeric column is treated as dates.

    Accepted schemas:
      date,open,high,low,close,volume   -> uses the close column
      date,close                         -> same
      close                              -> bare single numeric column
      price                              -> bare numeric, any header name
    Raises ValueError for empty files or files with no numeric columns.
    """
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{path} is empty")

    header = [c.strip().lower() for c in rows[0]]
    data = rows[1:]

    # Prefer an explicit close column (OHLCV files); else the first
    # numeric column, with any leading non-numeric column as dates.
    close_idx = next((i for i, c in enumerate(header) if c in _CLOSE_COLUMNS), None)
    numeric_idx = [
        i for i in range(len(header))
        if i < len(data[0]) and _is_float(data[0][i])
    ]
    if close_idx is None:
        if not numeric_idx:
            raise ValueError(f"{path} contains no numeric price columns")
        close_idx = numeric_idx[0]

    date_idx = next((i for i in range(len(header)) if i not in numeric_idx), None)
    dates: List[str] = []
    prices: List[float] = []
    for row in data:
        if not row or len(row) <= close_idx or not _is_float(row[close_idx]):
            continue
        if date_idx is not None and date_idx < len(row) and row[date_idx].strip():
            dates.append(row[date_idx].strip())
        prices.append(float(row[close_idx]))

    if len(prices) < 2:
        raise ValueError(f"{path} has fewer than 2 usable price rows")
    if dates and len(dates) != len(prices):
        dates = dates[: len(prices)]
    return PriceSeries(name=name, dates=dates, prices=prices)


def synthetic_equity_curve(
    seed: int = 42,
    years: int = 5,
    annual_mu: float = 0.09,
    annual_sigma: float = 0.16,
    start: float = 100.0,
    name: str = "Synthetic",
) -> PriceSeries:
    """A seeded geometric Brownian motion equity curve.

    Daily log-returns ~ N(mu/252, sigma^2/252); prices compound on top of
    a $100 start. Deterministic for a given seed. Dates are real
    weekdays spanning the requested number of years.
    """
    rng = random.Random(seed)
    mu_d = annual_mu / PERIODS_PER_YEAR
    sig_d = annual_sigma / math.sqrt(PERIODS_PER_YEAR)

    prices = [start]
    d = dt.date.today() - dt.timedelta(days=years * 365)
    dates = []
    while len(prices) - 1 < years * PERIODS_PER_YEAR:
        if d.weekday() < 5:  # skip weekends for realistic trading days
            prices.append(prices[-1] * (1.0 + rng.gauss(mu_d, sig_d)))
            dates.append(d.isoformat())
        d += dt.timedelta(days=1)

    return PriceSeries(name=name, dates=dates, prices=prices)
