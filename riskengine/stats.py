"""Return statistics and the normal distribution, pure stdlib.

The parametric VaR and CVaR engines need the normal CDF/inverse far
into the tail, so both are implemented here instead of tabulated: the
CDF via ``math.erf``, the inverse via Acklam's rational approximation
(~1e-9 accuracy). Sample moments are computed from a single return
series and annualized on demand.
"""

import math
from typing import List, Sequence

PERIODS_PER_YEAR = 252


def mean(xs) -> float:
    """Arithmetic mean of any iterable (generators included)."""
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def sample_variance(xs: Sequence[float]) -> float:
    """Unbiased sample variance (n-1 denominator)."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else 0.0


def sample_std(xs: Sequence[float]) -> float:
    """Sample standard deviation of a return series."""
    return math.sqrt(sample_variance(xs))


def annualize_daily_mean(mu_daily: float, periods: int = PERIODS_PER_YEAR) -> float:
    """Arithmetic annualization of a daily mean return."""
    return mu_daily * periods


def annualize_daily_std(sigma_daily: float, periods: int = PERIODS_PER_YEAR) -> float:
    """sqrt(N) scaling of daily volatility."""
    return sigma_daily * math.sqrt(periods)


def normal_pdf(x: float) -> float:
    """Standard-normal probability density."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def normal_cdf(x: float) -> float:
    """Standard-normal CDF via the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_inv(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation).

    Accurate to roughly 1e-9 for 0 < p < 1. Raises ValueError at the
    endpoints, which are never finite.

    Acklam's rational approximation is used rather than a Newton solve
    because it is closed-form and stays accurate down to p ~ 1e-16 --
    exactly where the VaR tail lives. Example: normal_inv(0.05) ~ -1.6449.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")

    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.3577518672690, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996,
         3.754408661907416]
    p_low = 0.02425

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p <= 1.0 - p_low:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    )
