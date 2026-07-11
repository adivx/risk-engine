# Design decisions

## Pure stdlib math

Acklam's rational approximation for the normal inverse CDF reaches ~1e-9
accuracy with no third-party dependency and no iteration. That keeps the
analytics importable anywhere — no numpy/scipy assumption — matching the "lab"
philosophy: a fresh venv, under a minute, deterministic output.

## `rich` only at the CLI boundary

The analytics modules are stdlib-only so they can be embedded and tested in
isolation. `rich` is a presentational convenience, confined to `cli.py`.

## Three engines for one number

Historical, parametric, and Monte Carlo answer the same question under
different assumptions. The *gap between them* is the signal: a wide gap
between historical and parametric VaR is the classic signature of fat tails
in the sample.

## Seeded synthetic data

The synthetic equity curve is a seeded geometric Brownian motion, so every
run and every README number reproduces exactly. Determinism matters for a
demo and for tests.
