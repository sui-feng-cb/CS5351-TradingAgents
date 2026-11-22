# D eligibility-gate test plan

Status: tests-only plan prepared; independent non-D test approval is pending.

## Trace and scope

- Requirements: FR-D, NFR-D.
- Invariant/decision: INV-D, ADR-002.
- Owner: D. Safety acceptance reviewer: a team member other than D.
- Offline suite: `test/offline/test_eligibility.py`; no model API, market API,
  account input, or live credential is used.
- The application implementation is explicitly outside this tests-only stage.

## Candidate public evaluator contract

`tradingagents.enhancements.eligibility.evaluate_eligibility(...)` accepts
`decision_mode="team"`, a candidate rating, a market-analyst execution state
(`completed`, `not_run`, or `failed`), market-evidence state (`valid`, `not_run`,
or `unavailable`), optional snapshot date, and analysis date. It returns an immutable decision with
`final_rating`, `eligible`, ordered `reason_codes`, and a deterministic
`user_message`. Unknown/missing states and malformed dates fail closed. This is a
proposal for test review, not an implemented interface.

The exact valid rating values are `Buy`, `Overweight`, `Hold`, `Underweight`,
`Sell`. Valid evidence requires a valid ISO calendar date no later than the
analysis date and no more than 10 calendar days earlier. The 10-day limit reuses
the current upstream `MAX_OHLCV_STALE_DAYS`; tests cover its inclusive boundary.

Proposed reason precedence (all applicable reasons, fixed order):

1. `market_analyst_not_run`, `market_analyst_failed`, or
   `market_analyst_invalid_status`.
2. `market_evidence_missing`, `market_evidence_not_run`,
   `market_evidence_unavailable`, or `market_evidence_invalid_status`.
3. `market_snapshot_date_missing`, `market_snapshot_date_invalid`,
   `market_snapshot_after_analysis`, or `market_snapshot_stale` (date checks
   apply when evidence status is `valid`).
4. `analysis_date_invalid`.
5. `invalid_rating`.

The evaluator returns the candidate rating unchanged only when it is in the
allowlist and all evidence preconditions pass. Otherwise it returns exactly
`REVIEW`; human-visible message must state that review is required and name the
triggering conditions. Tests assert reason codes and final ratings directly,
without calling production helpers to construct expected values.

## Fixed cases

| ID | Case | Expected result |
|---|---|---|
| D-UNIT-01 | Each of the five allowed ratings with completed market analyst, valid snapshot on analysis date | Same rating; eligible; no reason codes |
| D-UNIT-02 | Snapshot is 10 calendar days before analysis date | Same rating; eligible |
| D-UNIT-03 | Analyst did not run or failed | `REVIEW`; matching analyst reason |
| D-UNIT-04 | Evidence object missing, not run, unavailable or unknown status | `REVIEW`; matching evidence reason |
| D-UNIT-05 | Valid evidence has missing, malformed, future or 11-day-old snapshot date | `REVIEW`; matching date reason |
| D-UNIT-06 | Analysis date malformed or impossible | `REVIEW`; `analysis_date_invalid` |
| D-UNIT-07 | Rating absent, `REVIEW`, case-mismatched, extra prose or outside the exact allowlist | `REVIEW`; `invalid_rating` |
| D-UNIT-08 | Analyst not run, evidence unavailable and candidate `Buy` simultaneously | `REVIEW`; all applicable reasons in fixed order |
| D-UNIT-09 | The analyst report/narrative says `Buy` while evidence status is unavailable | Candidate narrative does not change `REVIEW` decision |
| D-INT-01 | Team mode runs graph with valid evidence and allowed rating | Gate runs after PM and before final state; eligible rating is authoritative |
| D-INT-02 | Team mode has unavailable market evidence while the model returns `Buy` | Final graph output is `REVIEW`; no actionable candidate text is exposed as final decision |
| D-INT-03 | Team mode runs with market analyst unselected | Final graph output is `REVIEW` with `market_analyst_not_run`; no pending settlement entry is created |
| D-INT-04 | Standard mode | Existing upstream result path is preserved |
| D-OUT-01 | Ineligible graph state is written as Markdown and HTML | Both show `REVIEW` and user-visible trigger reasons; neither shows candidate rating as final |
| D-OUT-02 | CLI exposes `--decision-mode standard|team`, defaulting to `standard` | Mode reaches analysis config; invalid mode is rejected |
| D-OUT-03 | CLI analysis completes with an ineligible final state, without opting to print the full report | Completion notice shows `REVIEW` and the same user-visible trigger reasons |
| D-OUT-04 | CLI's final report display receives ineligible final state | CLI display shows `REVIEW` and the same user-visible trigger reasons |
| D-LOG-01 | State log receives ineligible final state | Stored authoritative rating/reasons are `REVIEW`/gate reasons |
| D-MEM-01 | A `REVIEW` result is recorded | No pending settlement/reflection entry is created |

## NFR-D measurement

The fixed negative cases D-UNIT-03–09 and D-INT-02 are the bypass denominator.
Count a bypass if a blocked case produces any allowed final rating in graph,
CLI, Markdown, HTML or state log, or creates a pending settlement/reflection
entry. Acceptance requires **0 bypasses**. The tests are deterministic and CI
must run them on every applicable change.

## Baseline and approval record

- Baseline before adding D tests, Python 3.13.18, local `.venv`:
  `python -m pytest`: 1427 passed, 1 skipped, 1 deselected.
- Baseline governance, Ruff, mypy (`scripts/check_governance.py`) and pip checks
  passed. Full command output belongs in the active session/export, not fabricated
  into this plan.
- New tests are expected to fail against the unimplemented feature baseline.
- Actual focused baseline on the tests-only draft:
  `python -m pytest test/offline/test_eligibility.py -q` collected 34 cases, with
  32 failing against absent gate/CLI/report/settlement behavior and 2 passing
  independent structural checks. The two team-mode graph integration cases
  failed because `TradingAgentsGraph` does not yet accept `decision_mode`.
- Regression command excluding the new, deliberately red gate contract and its
  two expected-red graph cases:
  `python -m pytest test/offline -q --ignore=test/offline/test_eligibility.py -k
  'not test_team_mode_gate_rejects_model_buy_when_verified_market_data_is_unavailable
  and not test_team_mode_with_no_market_analyst_fails_closed_as_review'` reported
  1427 passed, 1 skipped, 2 deselected, 100 subtests passed. This verifies prior
  offline tests remain green in the tests-only revision.
- `Test-Plan-Approved: <full SHA>` and reviewer rationale: pending. No D
  application code may be written until a non-D reviewer approves the tests-only
  revision through the documented same-PR GitHub review process.
