"""Tail-risk analytics: VaR, CVaR and drawdowns.

Value at Risk is reported as a *loss* (positive number): a 1-day 95%
VaR of 2.1% means a 2.1% loss is the worst 1-in-20 daily outcome under
the model. CVaR (expected shortfall) is the mean loss *beyond* the VaR
cut, which captures how bad the tail actually is.

Three estimation engines are offered:

  historical  — quantile of the actual observed return series; no model
  parametric  — normal model fitted to the sample mean and volatility
  Monte Carlo — quantile of returns simulated from the fitted normal
                model (smoother tail than the raw parametric quantile)

All VaR/CVaR are in the period units of the input series (daily unless
the caller rescales). Drawdown analytics operate on price/wealth series
directly. Everything here is pure stdlib.
"""

import math
import random
from typing import List, Sequence, Tuple

from .stats import normal_inv, normal_pdf, sample_std


# ------------------------------------------------------------------ VaR / CVaR

def _validate_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")


def historical_var(returns: Sequence[float], alpha: float = 0.05) -> float:
    """VaR from the empirical return distribution (a loss, so > 0).

    The alpha-quantile of losses, computed as the k-th worst return
    where k = ceil(alpha * n). No distributional assumption.
    """
    _validate_alpha(alpha)
    s = sorted(returns)
    if not s:
        raise ValueError("returns series is empty")
    idx = max(0, int(math.ceil(alpha * len(s))) - 1)
    return -s[idx]


def historical_cvar(returns: Sequence[float], alpha: float = 0.05) -> float:
    """Expected shortfall: mean loss beyond the historical VaR cut."""
    _validate_alpha(alpha)
    s = sorted(returns)
    if not s:
        raise ValueError("returns series is empty")
    k = max(1, int(math.ceil(alpha * len(s))))
    return -sum(s[:k]) / k


def parametric_var(mu_daily: float, vol_daily: float, alpha: float = 0.05) -> float:
    """VaR under normality: −(μ + z_α σ), a loss so > 0 for small alpha."""
    _validate_alpha(alpha)
    z = normal_inv(alpha)
    return -(mu_daily + z * vol_daily)


def parametric_cvar(mu_daily: float, vol_daily: float, alpha: float = 0.05) -> float:
    """Expected shortfall under normality: σ·φ(z_α)/α − μ.

    Closed form for the normal model (the hazard-weighted tail). φ is
    the standard-normal density, z_α the alpha-quantile.
    """
    _validate_alpha(alpha)
    z = normal_inv(alpha)
    return vol_daily * normal_pdf(z) / alpha - mu_daily


def _simulate_returns(mu_daily: float, vol_daily: float,
                      n_paths: int, seed: int) -> List[float]:
    """n draws from N(mu_daily, vol_daily^2), deterministic for a seed."""
    rng = random.Random(seed)
    return [rng.gauss(mu_daily, vol_daily) for _ in range(n_paths)]


def monte_carlo_var(mu_daily: float, vol_daily: float, alpha: float = 0.05,
                    n_paths: int = 10_000, seed: int = 42) -> float:
    """VaR by simulating from the fitted normal model, then taking the
    empirical quantile. More stable than the parametric quantile for
    small samples and trivially extensible to fat-tailed draws."""
    sims = _simulate_returns(mu_daily, vol_daily, n_paths, seed)
    return historical_var(sims, alpha)


def monte_carlo_cvar(mu_daily: float, vol_daily: float, alpha: float = 0.05,
                     n_paths: int = 10_000, seed: int = 42) -> float:
    """Expected shortfall of the simulated normal series."""
    sims = _simulate_returns(mu_daily, vol_daily, n_paths, seed)
    return historical_cvar(sims, alpha)


def var_estimate(returns: Sequence[float], alpha: float = 0.05,
                 n_paths: int = 10_000, seed: int = 42) -> dict:
    """One-call risk report for a return series.

    Returns a dict keyed by engine name ("historical", "parametric",
    "monte_carlo"), each with "var" and "cvar" (losses, > 0).
    """
    mu = sum(returns) / len(returns)
    vol = sample_std(returns)
    return {
        "historical": {
            "var": historical_var(returns, alpha),
            "cvar": historical_cvar(returns, alpha),
        },
        "parametric": {
            "var": parametric_var(mu, vol, alpha),
            "cvar": parametric_cvar(mu, vol, alpha),
        },
        "monte_carlo": {
            "var": monte_carlo_var(mu, vol, alpha, n_paths, seed),
            "cvar": monte_carlo_cvar(mu, vol, alpha, n_paths, seed),
        },
    }


# ------------------------------------------------------------------ drawdowns

def drawdown_series(prices: Sequence[float]) -> List[float]:
    """Per-point drawdown vs the running peak (<= 0 for every point)."""
    peak = prices[0]
    out = []
    for p in prices:
        peak = max(peak, p)
        out.append(p / peak - 1.0)
    return out


def max_drawdown(prices: Sequence[float]) -> Tuple[float, int, int]:
    """Largest peak-to-trough decline, returned as (dd, peak_idx, trough_idx).

    dd <= 0; for a monotone-up series it is exactly 0.0.
    """
    dd = 0.0
    peak = prices[0]
    peak_idx = trough_idx = 0
    running_peak_idx = 0
    for i, p in enumerate(prices):
        if p >= peak:
            peak = p
            running_peak_idx = i
        elif p / peak - 1.0 < dd:
            dd = p / peak - 1.0
            peak_idx = running_peak_idx
            trough_idx = i
    return dd, peak_idx, trough_idx


def current_drawdown(prices: Sequence[float]) -> float:
    """Drawdown at the final observation vs its own running peak."""
    dd = drawdown_series(prices)
    return dd[-1]


def longest_drawdown_stretch(prices: Sequence[float]) -> Tuple[int, int, int]:
    """Longest continuous underwater period: (length, start_idx, end_idx).

    An "underwater" day is one whose drawdown is below 0. Length is in
    index spans, so a single underwater point has length 1.
    """
    best = (0, 0, 0)
    start = None
    for i, dd in enumerate(drawdown_series(prices)):
        if dd < 0:
            if start is None:
                start = i
            length = i - start + 1
            if length > best[0]:
                best = (length, start, i)
        else:
            start = None
    return best
