# Interface contracts

Status: D contract proposal for test review; no D executable interface is claimed.

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
  from model text. The proposed public mode is `standard` (default; preserve
  upstream behavior) or `team` (apply the qualification gate). A team-mode run
  checks selected/actual market-analyst execution, independently verified
  market-evidence status, snapshot date and the exact five-tier final rating.
  Missing/unavailable/not-run/future/stale evidence or invalid rating yields
  authoritative `REVIEW` plus stable reason codes before any final state is
  streamed, reported or recorded for settlement. `REVIEW` is not queued for
  settlement/reflection. The existing OHLCV stale-data bound
  (`MAX_OHLCV_STALE_DAYS`, currently 10 calendar days) is the proposed freshness
  limit; D tests must pin the boundary and ADR-002 records this reuse.

### D qualification boundary proposal

- Python callers select `decision_mode="team"` on `TradingAgentsGraph`; the CLI
  exposes `--decision-mode standard|team`, defaulting to `standard` for upstream
  compatibility. The mode and selected analysts are run metadata.
- Evidence acquisition returns typed metadata (`valid`, `unavailable`, or
  `not_run`) and a canonical `snapshot_date` when valid. Market-analyst execution
  status is a separate field. It uses deterministic market-data code, not a
  model-generated report. An absent evidence object, unknown status,
  missing/malformed date, date after `trade_date`, or data older than the
  existing 10-calendar-day OHLCV freshness bound fails closed.
- A deterministic graph node runs after the Portfolio Manager and before graph
  completion/publication. It writes authoritative `final_rating`, eligibility
  status and ordered reason codes. Ineligible output replaces the public final
  decision text with a `REVIEW` notice; model candidate prose cannot remain the
  apparent final call. Standard mode passes through the existing flow.
- Team-mode final state exposes `market_analyst_status`,
  `market_evidence_status`, `snapshot_date` and `eligibility_reason_codes`.
  The reason list is empty on an eligible result. Public graph stream frames
  and CLI live decision panels only publish a final rating after qualification.
- Initial reason-code proposal (report all applicable causes in this order):
  `market_analyst_not_run`, `market_analyst_failed`,
  `market_analyst_invalid_status`,
  `market_evidence_missing`, `market_evidence_not_run`,
  `market_evidence_unavailable`, `market_evidence_invalid_status`,
  `market_snapshot_date_missing`, `market_snapshot_date_invalid`,
  `market_snapshot_after_analysis`, `market_snapshot_stale`,
  `analysis_date_invalid`, and `invalid_rating`. The D test plan fixes their expected mappings before
  implementation.

Use UTC-aware stored timestamps; analysis dates remain explicit trading dates.
Freeze schema, null semantics, identifiers and errors before parallel coding.
Reserve `test/offline/test_comparison.py`, `test_events.py`, `test_manifest.py`,
`test_eligibility.py` for owners A, B, C, D respectively. Shared CLI/graph/report
files require coordinated integration PRs; no direct private cross-module imports.
