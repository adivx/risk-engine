# Architecture

One module, one concern:

    riskengine/stats.py   sample moments, annualization, normal CDF/inverse
    riskengine/data.py    PriceSeries, CSV loading, seeded synthetic curve
    riskengine/risk.py    VaR/CVaR engines + drawdown analytics
    riskengine/cli.py     rich report, SVG chart, argument dispatch

## Data flow

A CSV (or the seeded generator) becomes a `PriceSeries`. Its `returns()`
feed the three VaR engines; its `prices` feed the drawdown analytics. The
CLI layers a report and an SVG chart on top — nothing more.

    prices ──► PriceSeries ──┬── returns() ──► historical / parametric / MC VaR+CVaR
                             └── prices    ──► drawdowns (max, current, underwater)

Analytics modules stay pure stdlib so they can be embedded and tested in
isolation; `rich` is confined to `cli.py`.
