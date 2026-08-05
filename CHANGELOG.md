# Changelog

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
