# Interface contracts

Status: FR-C/NFR-C (the run manifest and `manifest query`) are implemented locally
on the C branch and the D evaluator and graph interface are implemented and
locally tested against the merged PR #2 test contract; A and B remain proposals.
The C implementation PR's independent review, remote CI, and the D safety and
integration reviews remain pending.

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
  scan (not a shared index). **Implemented locally** in
  `tradingagents.enhancements.manifest` (47 C acceptance cases; the
  implementation PR still needs an independent non-C review); the
  machine-readable schema is
  `docs/architecture/run-manifest-v1.schema.json` (Draft 2020-12). A few
  interface items still await team confirmation, including the
  reused-custom-report-directory policy (see below).

  ### C manifest v1

  - One manifest per execution attempt; `run_id` is a fresh UUID per attempt, at
    `<results_root>/<ticker>/<YYYY-MM-DD>/runs/<uuid>/run_manifest.json`.
  - Frozen field whitelist (16 top-level fields): schema_version, run_id, ticker,
    asset_type, trade_date, as_of, started_at, finished_at, code_version,
    analysts, models, configured_data_vendors, status, reports, error,
    unknown_fields. Extra top-level keys are rejected.
  - Nullable: `finished_at` (running), `code_version` (unknown), `models`
    (unknown), `error` (success). `trade_date`/`as_of` are `YYYY-MM-DD`;
    `started_at`/`finished_at` are UTC-aware ISO-8601.
  - `status` is `running | succeeded | failed`; analysis outcome and report-save
    outcome are expressed separately, not as one overloaded field.
  - `models` validates per-tier `provider`/`model` only (no endpoints/keys);
    `configured_data_vendors` is the filtered source configuration, not
    per-request provenance.
  - Errors store a fixed code plus safe text; no traceback blob, no secret.
  - `reports` is a required top-level object whose two keys
    (`complete_report_md`, `complete_report_html`) are **optional** and may be
    `null`; each present value is a path **relative to the results root** that
    `save_reports` actually returned. Unknown report keys are rejected. When a
    report directory is reused, a later save updates the existing record by
    explicit run association; that reuse policy is still to be confirmed by the
    team.
  - **Path containment is checked at runtime, not by the schema.** On query, each
    manifest and each declared report path is resolved (symlinks included) and
    must stay within the results root; an out-of-root path warns and the record
    or report is skipped. On write, the CLI resolves the target manifest path and
    refuses to write outside the results root before creating any directory. The
    JSON Schema can express types and relative-string shape but not filesystem
    containment, so that invariant lives in code.
  - Query is read-only; bad JSON, unknown schema_version, missing declared
    reports and out-of-root paths each warn and the scan continues; no report is
    modified or deleted. A missing-manifest warning is only for recognizable run
    directories.
  - Same-day reruns and checkpoint resumes keep prior records and do not change
    existing checkpoint behavior.
  - Team-confirmation items not yet locked: A/Python run-association interface,
    backtest coverage, the reused-custom-path policy, the `analysis_failed` /
    `Analysis failed.` fixed values and the CLI `matches`/`warnings` outer shape.
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
