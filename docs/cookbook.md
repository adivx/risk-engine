# Cookbook

Short, copy-pasteable recipes on top of the CLI and the library. For the math
behind each metric see [risk_math.md](risk_math.md); for the full module API
see [api.md](api.md).

## Get a machine-readable report

Every number the CLI prints is available as JSON — handy for dashboards,
scheduled jobs, or comparisons across runs:

```bash
risk-engine --csv sample_data/sample_ohlcv.csv --json
risk-engine --json --alpha 0.01 > var_1pct.json
```

The JSON is the exact payload the rich tables are rendered from, so the two
output modes can never disagree.

## 1-day → N-day tail risk

VaR/CVaR are daily losses. For an N-day horizon, scale the **parametric**
engine by √N (normal returns): a 5-day 95% VaR ≈ 1-day VaR × √5. The
historical engine has no closed-form scaling — resample the series to N-day
returns instead:

```bash
# Parametric approximation: 5-day 95% VaR ≈ 1-day VaR × √5.
risk-engine --json | jq -r '.var.parametric.var' \
  | awk '{printf "5-day 95%% VaR ≈ %.2f%%\n", $1 * sqrt(5) * 100}'
```

Or build N-day returns from the daily series and feed them straight in — the
engines are unit-agnostic:

## Compare engines and flag fat tails

When the historical and parametric VaR disagree, that's usually the story —
fat tails make the empirical loss exceed the normal-model prediction. Gap
size is a quick stand-in for tail risk:

```bash
risk-engine --json | jq -r '
  ((.var.historical.var - .var.parametric.var)
   | if . > 0.002 then "fat tails — historical VaR exceeds normal by " + (. * 100 | round) + "bp"
     else "engines agree within 20bp" end)'
```

## Run the same report on many files

```bash
for f in portfolios/*.csv; do
  risk-engine --csv "$f" --json | jq -c '{series, alpha, var: .var.historical.var, drawdown: .drawdown.max}'
done
```

## Seed a reproducible demo

The synthetic series is seeded and reproducible — good for a slide deck or a
README example that needs to look identical every run:

```bash
risk-engine --seed 42 --years 3 --annual-mu 0.12 --annual-sigma 0.20
risk-engine --seed 42 --years 3 chart --out drawdown.svg
```

## Call the analytics from Python

```python
from riskengine.risk import var_estimate, max_drawdown
from riskengine.data import load_prices_csv

series = load_prices_csv("sample_data/sample_ohlcv.csv")
report = var_estimate(series.returns(), alpha=0.05)
print(report["historical"])          # {'var': ..., 'cvar': ...}
print(max_drawdown(series.prices))   # (dd, peak_idx, trough_idx)
```

## Compare against the sample series

`sample_data/sample_ohlcv.csv` is a fixed 252-day OHLCV series with known
output. If your numbers drift from a fresh clone's, suspect the input data
rather than the engine:

```bash
risk-engine --csv sample_data/sample_ohlcv.csv --json
```
