# D eligibility-gate test plan

Status: fixed tests-only contract merged in PR #2 as confirmed by the user; the
implementation is being checked against that unchanged contract. Do not change
expected outcomes without a newly reviewed tests-only revision.

## Trace and scope

- Requirements: FR-D, NFR-D.
- Invariant/decision: INV-D, ADR-002.
- Owner: D. Safety acceptance reviewer: a team member other than D.
- Offline suite: `test/offline/test_eligibility.py`; no model API, market API,
  account input, or live credential is used.
- PR #2 supplied the fixed tests-only contract. The application implementation
  now exists locally and is verified against that contract in this work session.

## Candidate public evaluator contract

`tradingagents.enhancements.eligibility.evaluate_eligibility(...)` accepts
`decision_mode="team"`, a candidate rating, a market-analyst execution state
(`completed`, `not_run`, or `failed`), market-evidence state (`valid`, `not_run`,
or `unavailable`), optional snapshot date, and analysis date. It returns an immutable decision with
`final_rating`, `eligible`, ordered `reason_codes`, and a deterministic
`user_message`. Unknown/missing states and malformed dates fail closed. This
interface is implemented locally with passing offline regression. Remote CI and
independent safety and integration review remain pending.

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
| D-UNIT-10 | The D-UNIT-03–06 matrix explicitly pairs candidate `Buy` with one analyst, evidence or date failure at a time | Each of the 16 variants returns `REVIEW` and exactly its own reason code |
| D-INT-01 | Team mode runs graph with valid evidence from the preceding trading day and a model rating of `Overweight` | Graph returns authoritative `Overweight`, completed/valid market statuses, the actual snapshot date, and an empty reason list |
| D-INT-02 | Team mode has unavailable market evidence while the model returns `Buy` | Final graph output is `REVIEW`; no actionable candidate text is exposed as final decision |
| D-INT-03 | Team mode runs with market analyst unselected | Final graph output is `REVIEW` with `market_analyst_not_run`; no pending settlement entry is created |
| D-INT-04 | Standard mode | Existing upstream result path is preserved |
| D-STREAM-01 | Real team-mode graph stream with unavailable evidence and a scripted PM `Buy` | No yielded decision or message exposes the rejected candidate, and at least one state publishes `REVIEW` with the reason |
| D-STREAM-02 | Inject an intermediate candidate `Buy` chunk into the CLI stream before the gated `REVIEW` chunk | No live decision panel contains `Buy`, and the last panel and completion notice show `REVIEW` |
| D-OUT-01 | Ineligible graph state is written as Markdown and HTML | Both show `REVIEW` and user-visible trigger reasons; neither shows candidate rating as final |
| D-OUT-02 | CLI exposes `--decision-mode standard|team`, defaulting to `standard` | Mode reaches analysis config; invalid mode is rejected |
| D-OUT-03 | CLI analysis completes with an ineligible final state, without opting to print the full report | Completion notice shows `REVIEW` and the same user-visible trigger reasons |
| D-OUT-04 | CLI's final report display receives ineligible final state | CLI display shows `REVIEW` and the same user-visible trigger reasons |
| D-OUT-05 | Invoke the CLI command with `--decision-mode team` and run analysis setup | `TradingAgentsGraph` construction receives `decision_mode="team"` |
| D-LOG-01 | State log receives ineligible final state | Stored authoritative rating/reasons are `REVIEW`/gate reasons |
| D-MEM-01 | A `REVIEW` result is recorded | No pending settlement/reflection entry is created |

## NFR-D measurement

Use the independent negative evaluator cases (D-UNIT-03–08 and D-UNIT-10,
counting the D-UNIT-03–06 matrix once), graph cases (D-INT-02–03), and stream
cases (D-STREAM-01–02) as the bypass denominator.
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
- At the original test-only baseline, the new tests failed against the absent
  feature. Current implementation results are recorded in
  `docs/verification/d-eligibility.md`.
- Actual focused baseline on the initial PR #2 tests-only head (`0448de2`):
  `python -m pytest test/offline/test_eligibility.py -q` collected 34 cases, with
  32 failures and 2 passes (report fixture and vocabulary). One original
  presentation check also depended on terminal wrapping; the correction fixes
  its console width without removing its content assertions. The two team-mode graph integration cases
  failed because `TradingAgentsGraph` does not yet accept `decision_mode`.
- Regression command excluding the new, deliberately red gate contract and its
  two expected-red graph cases:
  `python -m pytest test/offline -q --ignore=test/offline/test_eligibility.py -k
  'not test_team_mode_gate_rejects_model_buy_when_verified_market_data_is_unavailable
  and not test_team_mode_with_no_market_analyst_fails_closed_as_review'` reported
  1427 passed, 1 skipped, 2 deselected, 100 subtests passed. This verifies prior
  offline tests remain green in the tests-only revision.
- PR #2 was squash-merged to `main` according to the user's session update. This
  work uses its merged tests as the fixed acceptance contract. Historical review
  details remain in the prior review artifacts and are not re-evaluated here.

## PR #2 review correction

Review of `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db` concluded
`CHANGES REQUIRED` (`docs/review-memo.md`). The correction covers findings 2–5
with D-INT-01, D-OUT-05, D-STREAM-01–02 and the explicit 16-variant Buy matrix;
finding 6 is addressed in `docs/verification/d-eligibility.md` using fresh
read-only GitHub metadata. Finding 1 remains pending: return the PR to draft and
obtain the required independent human Comment review of the revised tests-only
commit. The local memo is not a GitHub test-plan approval.

The final revised full run (`.venv/bin/python -m pytest -q --tb=no --disable-warnings`)
reported **36 failed, 1430 passed, 1 skipped, 1 deselected, 100 subtests passed**.
Every failure is in D's tests-first cases; the prior offline suite passed in the
same run. No expected-failure markers, skips, CI exclusions or application stubs
were introduced to make these unimplemented acceptance cases pass. Keep this
tests-only stage as a draft; after approval and implementation, all acceptance
and regression tests must pass. Static/schema/dependency checks passed; see the
verification log for exact commands and their scope.

## Implementation continuation

The review-correction section above is the historical pre-merge record. The user
subsequently confirmed PR #2 was merged and approved the implementation blueprint.
`test_eligibility.py` and the four D graph cases are unchanged in this work.
Supplementary `test_eligibility_adapter.py` tests exercise actual row-date
selection, typed stale exceptions without releasing prices, analyst execution
failure, and rejection of report prose when execution metadata is absent. Two
upstream CLI exact-flags fixtures retain their old assertions and add only the
new literal default mode. Current commands/results and remaining reviews are in
`docs/verification/d-eligibility.md`; no historical red result is presented as
current passing evidence.
