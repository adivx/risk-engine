# Contributing

## Setup
    python3 -m venv .venv
    .venv/bin/pip install -e .

## Run the tests
    .venv/bin/python -m unittest discover -s tests -v

## Style
- Pure stdlib for the analytics modules; `rich` is allowed only in the CLI.
- One module, one concern: `stats` (math), `data` (I/O), `risk` (analytics),
  `cli` (surface).
- Every new analytics function needs a docstring and a unittest.

## Pull requests
- Small, single-purpose commits. Back every claim with a test.
- Keep the dependency footprint: no new third-party packages without
  discussion — the point of this project is that it runs anywhere.
