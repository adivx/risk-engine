# API reference

The analytics modules are pure stdlib; `rich` is confined to the CLI. All
VaR/CVaR values are reported as *losses* (> 0) in the period units of the
input series (daily by default).

## `riskengine.risk`

| Function | Returns |
|---|---|
| `historical_var(returns, alpha=0.05)` | float — empirical α-quantile of losses |
| `historical_cvar(returns, alpha=0.05)` | float — mean loss beyond the historical VaR cut |
| `parametric_var(mu_daily, vol_daily, alpha=0.05)` | float — `-(μ + z_α·σ)` under normality |
| `parametric_cvar(mu_daily, vol_daily, alpha=0.05)` | float — closed form `σ·φ(z_α)/α − μ` |
| `monte_carlo_var(mu_daily, vol_daily, alpha=0.05, n_paths=10_000, seed=42)` | float — simulated quantile |
| `monte_carlo_cvar(mu_daily, vol_daily, alpha=0.05, n_paths=10_000, seed=42)` | float — simulated tail mean |
| `var_estimate(returns, alpha=0.05, n_paths=10_000, seed=42)` | dict — all three engines, each `{"var", "cvar"}` |
| `drawdown_series(prices)` | list[float] — drawdown vs running peak, ≤ 0 |
| `max_drawdown(prices)` | `(dd, peak_idx, trough_idx)` |
| `current_drawdown(prices)` | float — drawdown at the final observation |
| `longest_drawdown_stretch(prices)` | `(length, start_idx, end_idx)` |

`alpha` must be strictly between 0 and 1; empty return/pricing inputs raise
`ValueError`.

## `riskengine.data`

| Function | Returns |
|---|---|
| `PriceSeries(name, dates, prices, periods_per_year=252)` | dataclass with `n_obs`, `returns()`, `from_date()`, `to_date()` |
| `load_prices_csv(path, name="CSV")` | PriceSeries — OHLCV-aware, skips rows with no close |
| `synthetic_equity_curve(seed=42, years=5, annual_mu=0.09, annual_sigma=0.16, start=100.0, name="Synthetic")` | PriceSeries — seeded GBM, deterministic per seed |

## `riskengine.stats`

| Function | Notes |
|---|---|
| `mean(xs)` / `sample_variance(xs)` / `sample_std(xs)` | sample (n−1) variance |
| `annualize_daily_mean(mu_daily, periods=252)` | arithmetic scaling |
| `annualize_daily_std(sigma_daily, periods=252)` | √periods scaling |
| `normal_pdf(x)` / `normal_cdf(x)` | standard normal density / CDF |
| `normal_inv(p)` | quantile function (Acklam rational approx); rejects 0 and 1 |
