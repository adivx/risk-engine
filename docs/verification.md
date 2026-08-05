# Verification

The numbers are checked four ways, so a wrong answer fails loudly instead of
printing a plausible-looking table.

1. **Known values.** `parametric_var` is checked against the textbook z-scores
   (1.6449 at α = 5%) and `parametric_cvar` against the closed form φ(z_α)/α —
   no numeric integration, no hand-waving.

2. **Cross-engine agreement.** On a long sample drawn from a known normal,
   all three engines must converge to the same VaR/CVaR within a small delta
   (the historical and Monte Carlo rows only within sampling noise).

3. **Edge cases.** Empty return series, α outside (0, 1), single-point and flat
   price series, same-day drawdown recovery, rows with a missing close.

4. **Reproducibility.** The synthetic curve and Monte Carlo engines are
   seeded; every run and every number in the README reproduces byte-for-byte.
   The 5-year sample report, the chart, and the embedded-API examples are all
   pinned to fixed seeds.

Run everything with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
