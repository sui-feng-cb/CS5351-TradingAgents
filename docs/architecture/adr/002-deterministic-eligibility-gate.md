# ADR-002: deterministic team-mode decision eligibility gate

- Status: implemented and locally tested against the merged tests-only contract;
  independent non-D safety review, remote CI and integration review remain required.
- Requirements: FR-D, NFR-D.
- Invariant: INV-D.

## Context

The upstream Portfolio Manager supplies the candidate rating and narrative. The
existing verified-market-snapshot tool returns human-readable text for an agent;
that text is not a trustworthy machine interface for deciding whether a final
rating may be published. A model can also return an allowed rating when critical
market data was not executed, unavailable, missing, future-dated or stale. The
qualification boundary therefore needs deterministic evidence metadata and must
run before a final graph state can reach the CLI, reports or decision log.

## Decision and implementation

1. Add an explicit `standard` / `team` decision mode. `standard` is the default
   and preserves the upstream path. Python graph callers can select
   `decision_mode="team"`; the CLI will expose `--decision-mode standard|team`.
2. In team mode, track market-analyst selection and execution separately from
   market-evidence acquisition. A deterministic market-data adapter provides a
   status (`valid`, `unavailable`, `not_run`) and a canonical snapshot date; no
   status or date is inferred from model prose. Missing or malformed metadata
   fails closed.
3. Reuse the upstream OHLCV stale-data policy (`MAX_OHLCV_STALE_DAYS`, currently
   10 calendar days). Reject a snapshot after the analysis date or older than
   this bound. This avoids creating a second freshness policy.
4. Run a deterministic eligibility node after the Portfolio Manager and before
   graph completion. It accepts only the exact five allowed rating values. Any
   unmet condition sets authoritative `final_rating="REVIEW"`, emits ordered
   reason codes, and replaces public final-decision text with a review notice.
   The candidate's free-form Buy/Sell narrative is not exposed as the final
   decision when the gate rejects it.
5. Keep `REVIEW` decisions out of pending settlement/reflection. Reports, CLI
   output and state logs use the gate's final rating and reasons. Non-critical
   analyst omissions continue following the existing runtime policy.

The implementation keeps the evaluator pure and places trusted market evidence
acquisition in the graph using the existing cached OHLCV path. Snapshot date is
read from actual rows, with the analysis-date cutoff applied before metadata is
returned. The existing stale-data exception carries an optional typed
`snapshot_date`, letting the gate distinguish a stale snapshot from unavailable
data while the OHLCV loader still rejects stale prices. No freshness bypass is
added to the loader. Team-mode Portfolio Manager output is held in
candidate-only state keys until the gate writes public final fields. The CLI
stream adapter withholds those candidate fields, and blocked reports omit the
Trader's action proposal so it cannot appear as a secondary final call.

### PR #3 review corrections

Review of `a8d60b660251b83c886bbf00b30ddd75f83bf528` found three concrete INV-D
bypasses despite the then-passing offline suite. The user requested corrections
under the existing FR-D/NFR-D scope:

- Before publishing valid team evidence, the snapshot adapter requires a finite
  latest Close. `+inf`, `-inf`, NaN, missing and nonnumeric close values fail closed
  as unavailable evidence, using the existing `market_evidence_unavailable`
  reason. The production loader's standard-mode behavior and stale guard remain
  unchanged. A dated row alone is insufficient evidence of a usable price.
- Structured Portfolio Manager ratings retain their typed value. For free text,
  team mode reads complete, model-owned rating fields and requires an exact
  case-sensitive five-tier value after removing Markdown wrappers. Missing,
  invalid or conflicting own fields return REVIEW, resulting in `invalid_rating`;
  consensus quotations cannot supply the candidate. Standard mode retains the
  upstream heuristic parser. Prompts and model selection are unchanged.
- `stream_run` withholds `trader_investment_plan` in both top-level values and
  nested task results until `eligibility_checked=True` and the result is eligible.
  Completed rejected output clears the proposal; eligible output releases it.
  PM candidate fields continue to be withheld. The raw compiled LangGraph and
  private checkpoints remain internal execution surfaces, not the public stream
  projection.
- Version the team checkpoint signature so a pre-fix run cannot resume with
  already-accepted evidence or a candidate produced by the old parser. Standard
  checkpoint IDs remain unchanged.

The additions strengthen the existing acceptance boundary without changing the
rating vocabulary, 10-day freshness limit or reason ordering. Regression tests
first reproduced the review failures; current results and the independent-review
boundary are recorded in `docs/verification/d-eligibility.md`.

## Alternatives considered

| Option | Assessment |
|---|---|
| Trust the market analyst's prose or ask another model to validate it | Rejected: model text cannot establish provider execution status or snapshot date. |
| Parse status/date back out of model-visible tool output | Rejected: couples enforcement to rendered text and makes evidence authority ambiguous. |
| Validate typed metadata with a deterministic graph node | Implemented locally: separates data provenance from narrative and places enforcement before publication. |
| Gate every upstream run by default | Rejected: silently changes existing callers and conflicts with the explicit team-mode boundary. |

## Consequences and boundaries

- Team-mode graph, CLI, state and report adapters are coordinated integration
  changes and require review beyond the D-owned pure qualification module.
- The evidence adapter may use the existing cached OHLCV path; its test must
  prove that it does not accept rows beyond `trade_date` and that stale data
  follows the existing 10-day policy.
- A team-mode market-analyst subgraph wrapper records `failed` on an execution
  exception and allows the remaining graph to reach `REVIEW`. A successful but
  empty report also records `failed`. Missing execution metadata is not inferred
  from report prose. Unexpected failures elsewhere propagate without publishing
  a completed rating or creating a pending decision.
- A `REVIEW` reason is machine-readable and user-visible. It must remain stable
  across CLI, Markdown, HTML and structured run-state output.
- Offline tests mock data and model clients; no live provider call is part of
  D's acceptance test suite.

## Reconsider if

- Team requirements define another decision-mode interface or rating vocabulary.
- The upstream OHLCV stale policy changes or is unsuitable for the project.
- A structured upstream market-evidence API becomes available and removes the
  need for a team adapter.
- Review finds the proposed failure propagation or safe-report representation
  inadequate.
