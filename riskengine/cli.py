"""Rich CLI for the risk-engine lab.

Subcommands map one-to-one onto the analytics modules; the default
``risk-engine`` (no argument) runs the full report. Data is seeded
synthetic by default and real data can be dropped in with ``--csv``.

Example:
  risk-engine                        # synthetic 5y report
  risk-engine --csv sample_data/sample_ohlcv.csv --alpha 0.01
  risk-engine chart --out drawdown.svg
"""

import argparse
import sys
from typing import Any, Callable, Dict, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .data import PriceSeries, load_prices_csv, synthetic_equity_curve
from .risk import (
    current_drawdown,
    drawdown_series,
    longest_drawdown_stretch,
    max_drawdown,
    var_estimate,
)
from .stats import (
    annualize_daily_mean,
    annualize_daily_std,
    sample_std,
)

console = Console()


def _pct(x: float, nd: int = 1) -> str:
    return f"{x * 100:.{nd}f}%"


def _signed_pct(x: float, nd: int = 2) -> str:
    return f"{x * 100:+.{nd}f}%"


def _loss(x: float, nd: int = 2) -> str:
    """VaR/CVaR are already losses (>0); render with a minus to make
    the direction unambiguous for a reader."""
    return f"-{x * 100:.{nd}f}%"


def _describe_series(series: PriceSeries) -> str:
    lo = series.from_date() or f"n={series.n_obs:,}"
    hi = series.to_date() or ""
    span = f"{lo} → {hi}" if hi else lo
    return f"{series.name} · {series.n_obs:,} obs · {span}"


# ---------------------------------------------------------------- analytics

def _annualized_return(series: PriceSeries) -> float:
    """Geometric (compounded) annualized return over the series span."""
    total = series.prices[-1] / series.prices[0] - 1.0
    years = (len(series.prices) - 1) / series.periods_per_year
    return (1.0 + total) ** (1.0 / years) - 1.0 if years > 0 else 0.0


def _report(bundle: Tuple[PriceSeries, float]) -> dict:
    series, rf_annual = bundle
    returns = series.returns()
    mu_d = sum(returns) / len(returns)
    vol_d = sample_std(returns)
    return {
        "mu_d": mu_d,
        "vol_d": vol_d,
        "mu_a": annualize_daily_mean(mu_d),
        "vol_a": annualize_daily_std(vol_d),
        "sharpe": _sharpe(mu_d, vol_d, rf_annual, series.periods_per_year),
        "annual_return": _annualized_return(series),
        "var": var_estimate(returns, alpha=0.05, seed=0),
    }


def _sharpe(mu_d: float, vol_d: float, rf_annual: float, periods: int = 252) -> float:
    """Annualized Sharpe from daily moments and an annual risk-free rate."""
    excess = annualize_daily_mean(mu_d, periods) - rf_annual
    return excess / annualize_daily_std(vol_d, periods) if vol_d else 0.0


# ---------------------------------------------------------------- commands

def _cmd_report(bundle, args):
    series, rf_annual = bundle
    r = _report(bundle)

    # Drawdown stats on the price series.
    dd, peak_i, trough_i = max_drawdown(series.prices)
    days, start_i, end_i = longest_drawdown_stretch(series.prices)
    cur = current_drawdown(series.prices)

    summary = Panel(
        f"[cyan]risk-engine {__version__}[/cyan] — VaR & drawdown analytics\n"
        f"{_describe_series(series)}\n"
        f"annual return [bold]{_signed_pct(r['annual_return'])}[/bold] · "
        f"vol [bold]{_pct(r['vol_a'])}[/bold] · "
        f"Sharpe (rf {rf_annual:.2%}) [bold]{r['sharpe']:.2f}[/bold]",
        border_style="cyan",
    )
    console.print(summary)

    risk = r["var"]
    t = Table(title=f"Tail risk — 1-day VaR / CVaR (α = {args.alpha:.0%})",
              header_style="bold red")
    t.add_column("Engine", style="bold")
    t.add_column("VaR")
    t.add_column("CVaR")
    t.add_row("Historical", _loss(risk["historical"]["var"]),
              _loss(risk["historical"]["cvar"]))
    t.add_row("Parametric (normal)", _loss(risk["parametric"]["var"]),
              _loss(risk["parametric"]["cvar"]))
    t.add_row("Monte Carlo", _loss(risk["monte_carlo"]["var"]),
              _loss(risk["monte_carlo"]["cvar"]))
    console.print(t)

    dd_t = Table(title="Drawdown analytics", header_style="bold magenta")
    dd_t.add_column("Metric", style="bold")
    dd_t.add_column("Value")
    dd_t.add_row("Max drawdown",
                 f"[red]{_pct(dd, 2)}[/red]  "
                 f"(obs {peak_i:,} → obs {trough_i:,})")
    dd_t.add_row("Current drawdown", _pct(cur, 2))
    dd_t.add_row("Longest underwater stretch",
                 f"{days:,} obs  (obs {start_i:,} → obs {end_i:,})")
    console.print(dd_t)

    console.print(
        "[dim]VaR/CVaR are daily losses (>0); the 1-day α-VaR is the worst 1-in-N "
        f"outcome, CVaR is the mean loss beyond it (tail severity).[/dim]"
    )


def _cmd_chart(bundle, args):
    series, _ = bundle
    out = drawdown_svg(series.prices, series.dates, out=args.out)
    console.print(f"Wrote [bold]{out}[/bold] — open it in a browser (or add it to a README).")


# ---------------------------------------------------------------- SVG chart

def drawdown_svg(prices, dates=None, out="drawdown.svg", width=900, height=320):
    """Render the drawdown series as an SVG area chart (pure stdlib).

    Returns the output path. A negative-axis grid is drawn from the
    series' own min so the worst stretch is always on-screen.
    """
    dds = drawdown_series(prices)
    min_dd = min(dds)

    pad_l, pad_r, pad_t, pad_b = 60, 20, 24, 34
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def x(i):
        return pad_l + i * plot_w / max(len(dds) - 1, 1)

    def y(v):
        return pad_t + (v - 0.0) / (min_dd - 0.0) * plot_h if min_dd < 0 else pad_t

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    parts.append(
        f'<rect width="{width}" height="{height}" fill="#0e1117" rx="8"/>'
    )

    # Gridlines at 0%, -10%, ... down to the series min.
    step = 0.10 if min_dd <= -0.10 else 0.05
    tick = 0.0
    while tick >= min_dd or tick > -0.0001:
        gy = y(tick)
        label = f"{tick * 100:.0f}%"
        parts.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" '
            f'stroke="#3a3f4b" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" fill="#9aa0ab" font-size="12" '
            f'text-anchor="end">{label}</text>'
        )
        tick -= step

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(dds))
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="#ff6b6b" stroke-width="1.8"/>'
    )
    parts.append(
        f'<polygon points="{pad_l},{pad_t} {pts} {x(len(dds) - 1)},{pad_t}" '
        f'fill="#ff6b6b" opacity="0.25"/>'
    )

    parts.append(
        f'<text x="{pad_l}" y="{height - 10}" fill="#9aa0ab" font-size="12">'
        f"drawdown vs running peak · min {min_dd * 100:.1f}%</text>"
    )
    parts.append("</svg>")

    with open(out, "w") as f:
        f.write("\n".join(parts))
    return out


# ---------------------------------------------------------------- dispatch

_DISPATCH: Dict[str, Callable] = {
    "report": _cmd_report,
    "chart": _cmd_chart,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="risk-engine",
        description="Value-at-Risk & drawdown analytics lab — historical, "
                    "parametric, and Monte Carlo VaR/CVaR (pure stdlib Python).",
    )
    p.add_argument("command", nargs="?", default="report",
                   choices=["report", "chart"],
                   help="analytics to run (default: report)")
    p.add_argument("--csv", metavar="PATH",
                   help="load a real price series from a CSV instead of synthetic")
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    p.add_argument("--years", type=int, default=5,
                   help="years of synthetic daily history (default 5)")
    p.add_argument("--annual-mu", type=float, default=0.09,
                   help="annualized synthetic drift (default 0.09)")
    p.add_argument("--annual-sigma", type=float, default=0.16,
                   help="annualized synthetic volatility (default 0.16)")
    p.add_argument("--rf", type=float, default=0.03,
                   help="annual risk-free rate for Sharpe (default 0.03)")
    p.add_argument("--alpha", type=float, default=0.05,
                   help="tail quantile for VaR/CVaR (default 0.05)")
    p.add_argument("--out", metavar="PATH", default="drawdown.svg",
                   help="SVG output path for the chart (default drawdown.svg)")
    p.add_argument("--version", action="version", version=f"risk-engine {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    series = (load_prices_csv(args.csv)
              if args.csv
              else synthetic_equity_curve(seed=args.seed, years=args.years,
                                          annual_mu=args.annual_mu,
                                          annual_sigma=args.annual_sigma))
    bundle = (series, args.rf)
    _DISPATCH[args.command](bundle, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
