# Changelog

## 0.2.0 — 2026-08-10

- Cornish-Fisher VaR engine: normal quantile adjusted for the sample's
  skewness and excess kurtosis (Zangari) — a VaR-only row in the report
  and `--json` output.
- Kupiec POF backtest: counts realized breaches and reports the
  likelihood-ratio statistic and p-value, so a VaR model can be validated
  rather than just computed.
- Hardening: `var_estimate` and the drawdown helpers raise `ValueError`
  on empty input; CLI analytics errors exit 2 with a message instead of a
  raw traceback (`--alpha 1.5`, `--years 0`, missing CSV).
- Version bump also fixes a drift where `__version__` still read 0.1.0.

## 0.1.1 — 2026-08-05

- Run via `python -m riskengine`; package marked typed (`py.typed`).
- Friendly error message when a CSV path is missing.
- Hardening tests: cross-engine consistency, `normal_inv` symmetry, drawdown
  and CSV-loader edge cases.

## 0.1.0 — 2026-08-05

- Three 1-day VaR/CVaR engines: historical, parametric (normal), Monte Carlo.
- Drawdown analytics: max drawdown (peak/trough locations), current drawdown,
  longest underwater stretch.
- Rich CLI (`report` / `chart`) plus a pure-stdlib SVG drawdown chart.
- OHLCV-aware CSV loader and a seeded synthetic equity curve.
