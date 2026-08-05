# Examples

Two ways to consume the library without the CLI:

- **`run_report.py`** — the full risk report through the library API: loads a
  series, estimates VaR/CVaR with all three engines, computes drawdowns, and
  prints a plain (non-`rich`) summary. This is what `risk-engine --csv …`
  does under the hood.
- **`embed_api.py`** — a taste of embedding `var_estimate` into your own
  strategy-scoring loop: seed the synthetic curve, score a rolling window,
  and print the last window's tail risk.

Run either from the repo root:

```bash
.venv/bin/python examples/run_report.py
.venv/bin/python examples/embed_api.py
```

Both are deterministic (seeded), so output reproduces run-to-run.
