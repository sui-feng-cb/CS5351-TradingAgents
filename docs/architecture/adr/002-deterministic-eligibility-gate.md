# ADR-002: deterministic team-mode decision eligibility gate

- Status: proposed; requires non-D safety review and approved D acceptance tests.
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

## Decision proposal

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

## Alternatives considered

| Option | Assessment |
|---|---|
| Trust the market analyst's prose or ask another model to validate it | Rejected: model text cannot establish provider execution status or snapshot date. |
| Parse status/date back out of model-visible tool output | Rejected: couples enforcement to rendered text and makes evidence authority ambiguous. |
| Validate typed metadata with a deterministic graph node | Proposed: separates data provenance from narrative and places enforcement before publication. |
| Gate every upstream run by default | Rejected: silently changes existing callers and conflicts with the explicit team-mode boundary. |

## Consequences and boundaries

- Team-mode graph, CLI, state and report adapters are coordinated integration
  changes and require review beyond the D-owned pure qualification module.
- The evidence adapter may use the existing cached OHLCV path; its test must
  prove that it does not accept rows beyond `trade_date` and that stale data
  follows the existing 10-day policy.
- A failed market-analyst subgraph must not leave an actionable result. The
  integration must either preserve other completed work with `REVIEW`, or fail
  closed without publishing a rating; the accepted test contract will determine
  the exact runtime failure representation.
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
