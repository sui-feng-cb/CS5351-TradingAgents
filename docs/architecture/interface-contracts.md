# Interface contracts

Status: A–C contracts remain proposals. The D evaluator and graph interface are
implemented and locally tested against the merged PR #2 test contract. Remote
CI, independent safety review and integration review remain pending.

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
  Storage is one `run_manifest.json` per run directory plus a read-only local
  scan (not a shared index). Contract below is a tests-first proposal awaiting
  non-C approval (`docs/testing/c-manifest-test-plan.md`).

  ### C manifest v1 proposal

  - One manifest per execution attempt; `run_id` is a fresh UUID per attempt.
  - Frozen field whitelist: schema_version, run_id, ticker, asset_type,
    trade_date, as_of, started_at, finished_at, code_version, analysts, models,
    configured_data_vendors, status, reports, error, unknown_fields. Extra
    top-level keys are rejected.
  - `status` is `running | succeeded | failed`; analysis outcome and report-save
    outcome are expressed separately, not as one overloaded field.
  - UTC-aware ISO-8601 timestamps; `trade_date`/`as_of` remain `YYYY-MM-DD`.
  - `models` validates per-tier provider/model; `configured_data_vendors` is the
    source configuration, not per-request provenance.
  - Errors store a fixed code plus safe text; no traceback blob, no secret.
  - `reports` paths are relative to the results root and are the paths
    `save_reports` actually returned; a skipped save is `null`; a reused custom
    save path updates the existing record by explicit run association (team
    confirmation pending).
  - Query is read-only; bad JSON, unknown schema_version, missing declared
    reports and out-of-root paths each warn and the scan continues; no report is
    modified or deleted. A missing-manifest warning is only for recognizable run
    directories.
  - Same-day reruns and checkpoint resumes keep prior records and do not change
    existing checkpoint behavior.
  - Team-confirmation items not yet locked: A/Python run-association interface,
    backtest coverage, and the reused-custom-path policy.
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

### D qualification boundary

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

The local D implementation uses a frozen `EligibilityDecision` with
`final_rating`, `eligible`, a tuple of `reason_codes`, and `user_message`.
`evaluate_eligibility` is a team-only evaluator; non-team modes raise `ValueError`
and standard graph runs do not invoke it. Team graph state records
`eligibility_status` (`eligible`/`ineligible`), `eligibility_checked`, the reason
list and `eligibility_message`. Initial statuses are `not_run`, with a null
snapshot date. Actual analyst execution, rather than report claims, updates the
execution status. The trusted snapshot adapter uses the requested ticker/date;
stale-data exceptions expose the actual row date as typed metadata. A valid
evidence status means rows were acquired; the gate separately checks freshness.
Candidate fields are internal, cleared at qualification, and omitted from
`stream_run`. No new manifest schema or A–C feature is introduced here.

PR #3 corrections further require a finite latest Close before the adapter emits
valid evidence. Invalid price content maps to existing unavailable-evidence
handling. Free-text PM candidates in team mode use only complete own-rating
fields with exact five-tier values; missing/invalid/conflicting fields cannot be
rescued by a quoted consensus rating. Standard parsing is unchanged. Public
`stream_run` states withhold the Trader proposal until eligibility has completed
successfully; rejected completion clears it. These rules apply to values and
nested task states and are covered by the expanded graph and team-rating tests.
Pre-fix team checkpoints start a fresh run under the versioned team signature;
standard checkpoint IDs remain unchanged.

For team free text, a CommonMark line break can delimit a rating field. A
newline inside a code span cannot delimit a field. Other lines in the same
paragraph remain subject to exact-rating validation.

Use UTC-aware stored timestamps; analysis dates remain explicit trading dates.
Freeze schema, null semantics, identifiers and errors before parallel coding.
Reserve `test/offline/test_comparison.py`, `test_events.py`, `test_manifest.py`,
`test_eligibility.py` for owners A, B, C, D respectively. Shared CLI/graph/report
files require coordinated integration PRs; no direct private cross-module imports.
