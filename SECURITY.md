# Security policy

risk-engine is an analytics lab, not a trading or custody system. It reads
price CSVs and prints statistics; it holds no credentials and makes no
network calls.

## Reporting a vulnerability

If you find a bug with security implications (for example, a crash on
malformed CSV input), open a private issue or email the maintainer directly.
We'll respond within a few days.

## Scope

- Malformed CSV input should raise a clean `ValueError`, never execute code.
- No analytics module may make a network call.
