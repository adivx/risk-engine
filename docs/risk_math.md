# Risk math

All metrics are in the period units of the input series (daily by default).

## VaR

The α-VaR is the worst 1-in-(1/α) loss under the model. It is reported as a
*positive* loss: a 2.1% VaR means "a 2.1% loss is the worst 1-in-20 daily
outcome."

- **Historical** — the empirical α-quantile of observed returns: the k-th
  worst loss with k = ceil(α·n). No distributional assumption.
- **Parametric** — VaR = −(μ + z_α·σ) under a fitted normal N(μ, σ²).
- **Monte Carlo** — the α-quantile of returns simulated from the fitted
  normal model.

## CVaR (expected shortfall)

The mean loss *beyond* the VaR cut — how bad the tail actually is.

- **Historical** — mean of the worst k returns, k = ceil(α·n).
- **Parametric** — closed form σ·φ(z_α)/α − μ, where φ is the standard-normal
  density and z_α the α-quantile.
- **Monte Carlo** — mean of the simulated tail.

## Drawdowns

Drawdown at t is price_t / peak − 1, where peak is the running maximum so far.
Max drawdown is the largest peak-to-trough decline; the longest underwater
stretch is the longest run of observations with drawdown below zero.

## Caveat

The parametric and Monte Carlo engines assume daily returns are Gaussian. Real
returns have fatter tails, so in stress periods those rows run *lower* than the
historical one — read them together. A wide gap between historical and
parametric VaR is the classic signature of fat tails.
