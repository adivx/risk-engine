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

When to use which engine: historical for the raw empirical answer,
parametric for a smooth, sample-size-independent estimate, and Monte
Carlo when the draw distribution will later be swapped for something
fatter-tailed than the normal. A wide gap between historical and
parametric VaR is the classic signal of fat tails in the sample.

All VaR/CVaR are in the period units of the input series (daily unless
the caller rescales). Drawdown analytics operate on price/wealth series
directly. Everything here is pure stdlib.
"""

import math
import random
from typing import List, Sequence, Tuple

from .stats import (
    normal_inv,
    normal_pdf,
    sample_excess_kurtosis,
    sample_skew,
    sample_std,
)


# ------------------------------------------------------------------ VaR / CVaR

def _validate_alpha(alpha: float) -> None:
    """Raise ValueError unless ``alpha`` is strictly between 0 and 1."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")


def historical_var(returns: Sequence[float], alpha: float = 0.05) -> float:
    """VaR from the empirical return distribution (a loss, so > 0).

    The alpha-quantile of losses, computed as the k-th worst return
    where k = ceil(alpha * n). No distributional assumption.

    Args:
        returns: Sequence of period returns (can be negative/positive).
        alpha: Tail quantile (e.g., 0.05 for 95% VaR), strictly in (0, 1).

    Returns:
        Positive number = loss at the alpha quantile.

    Raises:
        ValueError: If returns is empty or alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    s = sorted(returns)
    if not s:
        raise ValueError("returns series is empty")
    idx = max(0, int(math.ceil(alpha * len(s))) - 1)
    return -s[idx]


def historical_cvar(returns: Sequence[float], alpha: float = 0.05) -> float:
    """Expected shortfall (CVaR): mean loss beyond the historical VaR cut.

    Args:
        returns: Sequence of period returns.
        alpha: Tail quantile (e.g., 0.05), strictly in (0, 1).

    Returns:
        Positive number = average loss in the worst alpha-fraction of outcomes.

    Raises:
        ValueError: If returns is empty or alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    s = sorted(returns)
    if not s:
        raise ValueError("returns series is empty")
    k = max(1, int(math.ceil(alpha * len(s))))
    return -sum(s[:k]) / k


def parametric_var(mu_daily: float, vol_daily: float, alpha: float = 0.05) -> float:
    """VaR under normality: −(μ + z_α σ), a loss so > 0 for small alpha.

    Args:
        mu_daily: Mean daily return.
        vol_daily: Standard deviation of daily returns.
        alpha: Tail quantile in (0, 1).

    Returns:
        Positive number = loss at the alpha quantile under normal model.

    Raises:
        ValueError: If alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    z = normal_inv(alpha)
    return -(mu_daily + z * vol_daily)


def parametric_cvar(mu_daily: float, vol_daily: float, alpha: float = 0.05) -> float:
    """Expected shortfall under normality: σ·φ(z_α)/α − μ.

    Closed form for the normal model (the hazard-weighted tail). φ is
    the standard-normal density, z_α the alpha-quantile.

    Args:
        mu_daily: Mean daily return.
        vol_daily: Standard deviation of daily returns.
        alpha: Tail quantile in (0, 1).

    Returns:
        Positive number = expected loss beyond the VaR cut under normal model.

    Raises:
        ValueError: If alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    z = normal_inv(alpha)
    return vol_daily * normal_pdf(z) / alpha - mu_daily


def _simulate_returns(mu_daily: float, vol_daily: float,
                      n_paths: int, seed: int) -> List[float]:
    """Generate n draws from N(mu_daily, vol_daily^2), deterministic for a seed.

    Args:
        mu_daily: Mean daily return.
        vol_daily: Standard deviation of daily returns.
        n_paths: Number of draws.
        seed: RNG seed for reproducibility.

    Returns:
        List of simulated returns.
    """
    rng = random.Random(seed)
    return [rng.gauss(mu_daily, vol_daily) for _ in range(n_paths)]


def monte_carlo_var(mu_daily: float, vol_daily: float, alpha: float = 0.05,
                    n_paths: int = 10_000, seed: int = 42) -> float:
    """VaR by simulating from the fitted normal model, then taking the
    empirical quantile. More stable than the parametric quantile for
    small samples and trivially extensible to fat-tailed draws.

    Args:
        mu_daily: Mean daily return.
        vol_daily: Standard deviation of daily returns.
        alpha: Tail quantile in (0, 1).
        n_paths: Number of simulation paths (default 10,000).
        seed: RNG seed (default 42).

    Returns:
        Positive number = loss at the alpha quantile of simulated returns.
    """
    sims = _simulate_returns(mu_daily, vol_daily, n_paths, seed)
    return historical_var(sims, alpha)


def monte_carlo_cvar(mu_daily: float, vol_daily: float, alpha: float = 0.05,
                     n_paths: int = 10_000, seed: int = 42) -> float:
    """Expected shortfall of the simulated normal series.

    Args:
        mu_daily: Mean daily return.
        vol_daily: Standard deviation of daily returns.
        alpha: Tail quantile in (0, 1).
        n_paths: Number of simulation paths (default 10,000).
        seed: RNG seed (default 42).

    Returns:
        Positive number = expected loss beyond the VaR cut in simulation.
    """
    sims = _simulate_returns(mu_daily, vol_daily, n_paths, seed)
    return historical_cvar(sims, alpha)


def cornish_fisher_var(returns: Sequence[float], alpha: float = 0.05) -> float:
    """VaR under the Cornish-Fisher expansion (Zangari): the normal
    quantile corrected for the sample's own skewness and excess kurtosis.

    The correction is exact for the normal (skew ~ 0, kurtosis ~ 0), so
    the gap to the parametric engine is precisely the fat-tail signal the
    historical/parametric spread flags — here made explicit rather than
    inferred.

    Args:
        returns: Sequence of period returns.
        alpha: Tail quantile in (0, 1).

    Returns:
        Positive number = loss at the corrected quantile.

    Raises:
        ValueError: If returns is empty or alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    if not returns:
        raise ValueError("returns series is empty")
    mu = sum(returns) / len(returns)
    vol = sample_std(returns)
    z = normal_inv(alpha)
    s = sample_skew(returns)
    k = sample_excess_kurtosis(returns)
    z_cf = (z
            + (z * z - 1.0) * s / 6.0
            + (z ** 3 - 3.0 * z) * k / 24.0
            - (2.0 * z ** 3 - 5.0 * z) * s * s / 36.0)
    return -(mu + z_cf * vol)


def _ln(p: float) -> float:
    """Safe log: returns 0.0 at p == 0 (handles the log-0 edge in Kupiec)."""
    return 0.0 if p == 0.0 else math.log(p)


def kupiec_pof(returns: Sequence[float], var: float, alpha: float = 0.05) -> dict:
    """Kupiec proportion-of-failures (POF) backtest of a VaR model.

    Counts realized breaches (-r > var) and tests whether the observed
    exceedance rate matches the model's alpha via the likelihood-ratio
    statistic, which is asymptotically chi-squared(1). A well-calibrated
    model yields a high p_value; a model that breaches too often (or
    never) is flagged.

    Args:
        returns: Sequence of period returns.
        var: VaR threshold (positive loss number) to test.
        alpha: Tail quantile in (0, 1).

    Returns:
        Dict with keys: "breaches" (int), "expected" (float),
        "exceedance_rate" (float), "lr" (float), "p_value" (float).

    Raises:
        ValueError: If returns is empty or alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    if not returns:
        raise ValueError("returns series is empty")
    n = len(returns)
    x = sum(1.0 for r in returns if -r > var)
    p = x / n
    lr = -2.0 * ((n - x) * _ln(1.0 - alpha) + x * _ln(alpha)
                 - (n - x) * _ln(1.0 - p) - x * _ln(p))
    p_value = 1.0 - math.erf(math.sqrt(lr / 2.0))  # chi-square(1) survival
    return {
        "breaches": int(x),
        "expected": alpha * n,
        "exceedance_rate": p,
        "lr": lr,
        "p_value": p_value,
    }


def var_estimate(returns: Sequence[float], alpha: float = 0.05,
                 n_paths: int = 10_000, seed: int = 42) -> dict:
    """One-call risk report for a return series across all engines.

    Args:
        returns: Sequence of period returns.
        alpha: Tail quantile in (0, 1) (default 0.05 = 95% VaR).
        n_paths: Simulation paths for Monte Carlo (default 10,000).
        seed: RNG seed for Monte Carlo (default 42).

    Returns:
        Dict keyed by engine ("historical", "parametric", "monte_carlo",
        "cornish_fisher"), each with "var" and "cvar" (losses > 0).
        Cornish-Fisher has no closed-form CVaR, so it exposes "var" only.

    Raises:
        ValueError: If returns is empty or alpha not in (0, 1).
    """
    _validate_alpha(alpha)
    if not returns:
        raise ValueError("returns series is empty")
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
        "cornish_fisher": {
            "var": cornish_fisher_var(returns, alpha),
        },
    }


# ------------------------------------------------------------------ drawdowns

def drawdown_series(prices: Sequence[float]) -> List[float]:
    """Per-point drawdown vs the running peak (<= 0 for every point).

    Args:
        prices: Sequence of price/wealth levels.

    Returns:
        List of drawdowns (negative fractions, 0.0 at peaks).

    Raises:
        ValueError: If prices is empty.
    """
    if not prices:
        raise ValueError("prices series is empty")
    peak = prices[0]
    out = []
    for p in prices:
        peak = max(peak, p)
        out.append(p / peak - 1.0)
    return out


def max_drawdown(prices: Sequence[float]) -> Tuple[float, int, int]:
    """Largest peak-to-trough decline, returned as (dd, peak_idx, trough_idx).

    dd <= 0; for a monotone-up series it is exactly 0.0.

    Args:
        prices: Sequence of price/wealth levels.

    Returns:
        Tuple of (drawdown_fraction, peak_index, trough_index).
        drawdown_fraction is negative (e.g., -0.25 for -25%).

    Raises:
        ValueError: If prices is empty.
    """
    if not prices:
        raise ValueError("prices series is empty")
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
    """Drawdown at the final observation vs its own running peak.

    Args:
        prices: Sequence of price/wealth levels.

    Returns:
        Current drawdown fraction (<= 0).

    Raises:
        ValueError: If prices is empty.
    """
    dd = drawdown_series(prices)
    return dd[-1]


def longest_drawdown_stretch(prices: Sequence[float]) -> Tuple[int, int, int]:
    """Longest continuous underwater period: (length, start_idx, end_idx).

    An "underwater" day is one whose drawdown is below 0. Length is in
    index spans, so a single underwater point has length 1.

    Args:
        prices: Sequence of price/wealth levels.

    Returns:
        Tuple of (length, start_index, end_index). Length is 0 if never underwater.
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
