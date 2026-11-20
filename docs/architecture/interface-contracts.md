# Proposed interface contracts

Status: draft. No executable feature interfaces are claimed.

- A: exactly two distinct tickers, shared canonical date/config; sequentially call
  upstream propagate/save_reports, isolating each run. Return per-ticker status,
  rating, summary and report path, plus a comparison report.
- B: 2–3 tickers, window ≤7 days, ≤5 records per ticker. Each record contains a
  run-scoped evidence ID, ticker, published_at, source and title/snippet. Output
  groups reference input IDs; deterministic validation requires ≥2 tickers and
  correct provenance. At most one grouping call; no silent SDK retries in that cap.
- C: versioned manifest records run ID, ticker, date/as-of, start/end, available
  code version, configured providers/models/analysts, status and relative paths.
  Unknowns are explicit. Query is read-only and tolerates individual bad files.
- D: market execution status and snapshot date are machine metadata, not inferred
  from model text. Missing/unavailable/not-run/future evidence or invalid rating
  yields authoritative REVIEW plus reason codes before publication/settlement.

Use UTC-aware stored timestamps; analysis dates remain explicit trading dates.
Freeze schema, null semantics, identifiers and errors before parallel coding.
Reserve `test/offline/test_comparison.py`, `test_events.py`, `test_manifest.py`,
`test_eligibility.py` for owners A, B, C, D respectively. Shared CLI/graph/report
files require coordinated integration PRs; no direct private cross-module imports.
