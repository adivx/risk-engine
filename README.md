# risk-engine

A dependency-light **Value-at-Risk & drawdown analytics lab** for Python 3.9+.
Point it at a price series -- synthetic or real -- and get back 1-day VaR and
CVaR (expected shortfall) under three estimation engines, plus full drawdown
analytics, in pure stdlib math. `rich` is the only third-party dependency
(for the CLI).

Fourth piece of a quant portfolio:

| Project | Shows |
|---|---|
| [ticker-terminal](https://github.com/adivx) | data engineering / live market data |
| [option-pricer](https://github.com/adivx/option-pricer) | derivatives math (Black--Scholes + Greeks) |
| [backtest-engine](https://github.com/adivx/backtest-engine) | strategy design, execution simulation, risk metrics |
| **risk-engine** | tail risk -- VaR / CVaR under historical, parametric & Monte Carlo models, drawdowns |

## What it does

**VaR** is reported as a *loss* (positive number): a 1-day 95% VaR of 2.1%
means a 2.1% loss is the worst 1-in-20 daily outcome under the model. **CVaR**
(expected shortfall) is the mean loss *beyond* the VaR cut -- it captures how
bad the tail actually is, not just where it starts. Three engines estimate it:

- **Historical** -- the empirical quantile of observed returns; no distributional assumption.
- **Parametric** -- a normal model fitted to the sample mean/vol; VaR = -(mu + z_alpha * sigma).
- **Monte Carlo** -- the quantile of returns simulated from the fitted normal model (smoother tail than the raw parametric quantile).

Drawdown analytics track peak-to-trough declines on the price series directly:
max drawdown (with the peak/trough locations), current drawdown, and the
longest continuous underwater stretch.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/risk-engine
```

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ risk-engine 0.1.0 -- VaR & drawdown analytics                               │
│ Synthetic - 1,261 obs - 2021-08-06 to 2026-06-04                            │
│ annual return -0.29% - vol 16.0% - Sharpe (rf 3.00%) -0.13                  │
╰──────────────────────────────────────────────────────────────────────────────╯
  Tail risk -- 1-day VaR / CVaR (alpha = 5%)
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Engine              ┃ VaR    ┃ CVaR   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ Historical          │ -1.63% │ -2.04% │
│ Parametric (normal) │ -1.65% │ -2.07% │
│ Monte Carlo         │ -1.64% │ -2.04% │
└─────────────────────┴────────┴────────┘
                      Drawdown analytics
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                     ┃ Value                          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Max drawdown               │ -43.25%  (obs 438 to obs 1,236)│
│ Current drawdown           │ -39.61%                        │
│ Longest underwater stretch │ 822 obs  (obs 439 to obs 1,260)│
└────────────────────────────┴────────────────────────────────┘
```

### Real data

The sample file is OHLCV; load it (or any price CSV) directly:

```bash
.venv/bin/risk-engine --csv sample_data/sample_ohlcv.csv
```

### Drawdown chart

```bash
.venv/bin/risk-engine chart --out drawdown.svg
```

Writes an SVG area chart of the drawdown series vs the running peak -- a nice
visual for a README or a risk deck.

## Structure

```
risk-engine/
├── riskengine/
│   ├── stats.py   # sample moments + normal CDF/inverse (Acklam), pure stdlib
│   ├── risk.py    # historical / parametric / Monte Carlo VaR+CVaR, drawdowns
│   ├── data.py    # CSV loading (OHLCV-aware) + seeded synthetic equity curve
│   └── cli.py     # rich CLI + pure-stdlib SVG drawdown chart
├── tests/         # unittest suite across every module
└── sample_data/   # sample OHLCV series
```

## CLI

```
usage: risk-engine [-h] [--csv PATH] [--seed SEED] [--years YEARS]
                   [--annual-mu ANNUAL_MU] [--annual-sigma ANNUAL_SIGMA]
                   [--rf RF] [--alpha ALPHA] [--out PATH] [--version]
                   [command]
```

`command` is one of `report` (default) or `chart`. Synthetic data is seeded and
reproducible; `--alpha` sets the tail quantile for VaR/CVaR (default 5%).
