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
import json
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
    """Format a decimal as a percentage string, e.g. ``0.052 -> "5.2%"``."""
    return f"{x * 100:.{nd}f}%"


def _signed_pct(x: float, nd: int = 2) -> str:
    """Format a decimal as a signed percentage, e.g. ``-0.02 -> "-2.00%"``."""
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


def _report(bundle: Tuple[PriceSeries, float], alpha: float = 0.05) -> dict:
    series, rf_annual = bundle
    returns = series.returns()
    if not returns:
        raise ValueError("returns series is empty")
    mu_d = sum(returns) / len(returns)
    vol_d = sample_std(returns)
    return {
        "mu_d": mu_d,
        "vol_d": vol_d,
        "mu_a": annualize_daily_mean(mu_d),
        "vol_a": annualize_daily_std(vol_d),
        "sharpe": _sharpe(mu_d, vol_d, rf_annual, series.periods_per_year),
        "annual_return": _annualized_return(series),
        "var": var_estimate(returns, alpha=alpha, seed=0),
    }


def _collect(bundle: Tuple[PriceSeries, float], args) -> dict:
    """Everything the report shows, as a JSON-serializable dict.

    The machine-readable payload behind both the rich tables and the
    ``--json`` path, so they can never drift apart.
    """
    series, rf_annual = bundle
    r = _report(bundle, alpha=args.alpha)
    dd, peak_i, trough_i = max_drawdown(series.prices)
    days, start_i, end_i = longest_drawdown_stretch(series.prices)
    return {
        "version": __version__,
        "alpha": args.alpha,
        "rf": rf_annual,
        "series": _describe_series(series),
        "annual_return": r["annual_return"],
        "annual_vol": r["vol_a"],
        "sharpe": r["sharpe"],
        "var": r["var"],
        "drawdown": {
            "max": dd,
            "max_peak_idx": peak_i,
            "max_trough_idx": trough_i,
            "current": current_drawdown(series.prices),
            "longest_stretch_obs": days,
            "longest_start_idx": start_i,
            "longest_end_idx": end_i,
        },
    }


def _sharpe(mu_d: float, vol_d: float, rf_annual: float, periods: int = 252) -> float:
    """Annualized Sharpe from daily moments and an annual risk-free rate."""
    excess = annualize_daily_mean(mu_d, periods) - rf_annual
    return excess / annualize_daily_std(vol_d, periods) if vol_d else 0.0


# ---------------------------------------------------------------- commands

def _cmd_report(bundle, args):
    series, rf_annual = bundle
    data = _collect(bundle, args)

    # Machine-readable path — the full report as JSON, no rich output.
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    summary = Panel(
        f"[cyan]risk-engine {__version__}[/cyan] — VaR & drawdown analytics\n"
        f"{_describe_series(series)}\n"
        f"annual return [bold]{_signed_pct(data['annual_return'])}[/bold] · "
        f"vol [bold]{_pct(data['annual_vol'])}[/bold] · "
        f"Sharpe (rf {rf_annual:.2%}) [bold]{data['sharpe']:.2f}[/bold]",
        border_style="cyan",
    )
    console.print(summary)

    risk = data["var"]
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
    t.add_row("Cornish-Fisher", _loss(risk["cornish_fisher"]["var"]), "—")
    console.print(t)

    dd = data["drawdown"]
    dd_t = Table(title="Drawdown analytics", header_style="bold magenta")
    dd_t.add_column("Metric", style="bold")
    dd_t.add_column("Value")
    dd_t.add_row("Max drawdown",
                 f"[red]{_pct(dd['max'], 2)}[/red]  "
                 f"(obs {dd['max_peak_idx']:,} → obs {dd['max_trough_idx']:,})")
    dd_t.add_row("Current drawdown", _pct(dd["current"], 2))
    dd_t.add_row("Longest underwater stretch",
                 f"{dd['longest_stretch_obs']:,} obs  "
                 f"(obs {dd['longest_start_idx']:,} → obs {dd['longest_end_idx']:,})")
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
    p.add_argument("--json", action="store_true",
                   help="print the report as JSON instead of rich tables "
                        "(machine-readable)")
    p.add_argument("--version", action="version", version=f"risk-engine {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        series = (load_prices_csv(args.csv)
                  if args.csv
                  else synthetic_equity_curve(seed=args.seed, years=args.years,
                                              annual_mu=args.annual_mu,
                                              annual_sigma=args.annual_sigma))
        bundle = (series, args.rf)
        _DISPATCH[args.command](bundle, args)
    except (OSError, ValueError) as exc:
        print(f"risk-engine: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
