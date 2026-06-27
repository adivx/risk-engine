# risk-engine — project brief

## Goal
A dependency-light Value-at-Risk (VaR) and drawdown analytics lab that a
quant analyst can run on a single price series and read the answer off a
terminal — no Excel, no heavyweight data stack.

## Scope
- 1-day VaR and CVaR (expected shortfall) under three estimation engines:
  historical, parametric (normal), Monte Carlo.
- Drawdown analytics: max drawdown (with peak/trough locations), current
  drawdown, longest underwater stretch.
- Pure stdlib math; `rich` only at the CLI surface.
- Input: any price CSV (OHLCV or bare close) or a seeded synthetic curve.

## Out of scope
Multi-asset / portfolio risk, stress testing, scenario analysis, position
sizing.

## API sketch
    riskengine.risk.var_estimate(returns, alpha) -> dict per engine
    riskengine.risk.drawdown_series(prices)      -> per-point drawdown
    riskengine.data.load_prices_csv(path)        -> PriceSeries
    risk-engine [--csv PATH] [--alpha A] [command]
