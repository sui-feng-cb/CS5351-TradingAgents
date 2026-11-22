# D eligibility-gate work log and verification evidence

Status: test-first work in progress; no D application implementation is claimed.

## Current session record — 2026-11-22

- User approved the detailed D execution blueprint, then directed development to
  begin. This authorizes work on the local `D` branch; it does not authorize a
  `main` commit, merge, remote synchronization, or a bypass of test approval.
  The user subsequently authorized a tests-only commit on local `D`, a non-force
  push only to `origin/D`, and creation of a draft PR for independent review.
- Initial `git status --short --branch`: clean local branch `D`. HEAD was
  `825d477 chore(governance): adopt same-PR GitHub Flow (#1)` and local `D`,
  `main`, and `origin/main` pointed at this commit. No remote fetch/pull was run.
- At the pre-PR read-only ref checks, `origin/D` pointed to
  `578d15edff2bb3b03b955022e02bd2ea67346a0b`, then was absent while
  `origin/main` remained at `825d477352a86213beec8dca20dc23d62d0a6f1a`. No remote
  ancestry synchronization was attempted. `gh` was unavailable locally.
- PR #2 is now present at `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`, based on
  `main`. Its local tracking branch is `D...origin/D` at the same head. See the
  dated PR findings in `docs/review-memo.md`. The review-driven test correction
  in this session is local and uncommitted.
- A fresh read-only `gh pr view 2` confirmed that the PR is still ready (not
  draft), the two `tests (py3.13, America/New_York)` checks failed, and governance,
  same-PR reviews, clean-install and Ruff checks succeeded. GitHub reviews are
  empty. `gh` is now available; its earlier unavailability is historical, not
  a current publication blocker. No PR state or review was changed in this work.
- Project environment: `.venv`, Python 3.13.18.

### Pre-change baseline

| Check | Actual result |
|---|---|
| `.venv/bin/python -m pytest` | 1427 passed, 1 skipped, 1 deselected. The skip needs optional `langchain_aws`; the deselected test is live. |
| `.venv/bin/python scripts/check_governance.py` | Passed registry/schema/layout/permission checks and the basic credential-pattern scan. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python -m mypy scripts/check_governance.py` | Passed. |
| `.venv/bin/python -m pip check` | Passed. |

These are the pre-change baseline only and do not verify any D behavior.

## D1–D9 artifact ledger

| Deliverable | Relevant artifacts | Current state / next evidence |
|---|---|---|
| D1 Requirements | `docs/req/requirements.yaml`, `docs/req/req-schema.json` | FR-D/NFR-D remain planned and pending review/freeze. Governance/schema validation passed in the correction session. |
| D2 Architecture | `docs/architecture/architecture-blueprint.md`, `interface-contracts.md`, `invariants.md`, `runtime-policy-catalog.md`, `trace-matrix.md`, `adr/002-deterministic-eligibility-gate.md` | Proposed team/standard boundary, evidence statuses, reason codes and stale-data reuse documented; ADR remains proposed pending safety review. |
| D3 Coding governance | `docs/code-governance/structural-constraints.md`, `verification-constraints.md`, `AGENTS.md`, `Prompt.md`, `.opencode/rules.md`, `.agent/rules.md` | Structural and verification references updated. Human-owned rules were not edited. Prompt and entrypoint continue to require plan/test review before application code. |
| D4 Verification governance | `docs/testing/d-eligibility-test-plan.md`, `docs/code-governance/verification-constraints.md`, this log | Test matrix revised for PR #2 findings: positive team graph, per-condition Buy conflicts, CLI-to-graph mode forwarding and pre-gate stream leakage. Independent test approval is still pending. |
| D5 Annotated sessions | `transcripts/README.md`, active OpenCode session | No export or annotation has been created in this work yet. At session end, export the actual session with TUI `/export`, annotate only real interventions, then link it here and from the AI-use log/PR. |
| D6 Process report | `Report.md` | Blueprint approval and real baseline recorded. Update with tests-only review, implementation, failures, rework, verification, integration and actual contributions as they occur. |
| D7 Repository/CI | `.github/workflows/ci.yml`, `docs/ai-use-log.yaml`, GitHub PR | PR #2 exists at the reviewed tests-only head; current test corrections are uncommitted. `gh` read-only checks confirmed its ready state and missing reviews. Return the PR to draft and request review of the revised head; no new push or PR review has occurred. |
| D8 Source/tests | `test/offline/test_eligibility.py`, `test/offline/test_graph_end_to_end.py`, reserved `src/tradingagents/enhancements/eligibility.py` | Acceptance tests drafted; application module intentionally not created pending independent test approval. |
| D9 Static prompt | `Prompt.md`, `AGENTS.md`, `.opencode/rules.md` | Existing stop-before-application-code and staged-review requirements followed. No D prompt change currently needed. |

## Test-first gate and pending approval

The approved blueprint and current user request are recorded, but the D
tests-only contract has not yet received the required independent non-D review.
The PR #2 review required test corrections, which are now prepared locally. Do
not write application code until a reviewer has approved the exact revised
tests-only commit through the documented
same-PR review process, including its full SHA and rationale. The approval
permalink must later be cross-linked from the PR and AI-use log.

The new focused tests show the expected red baseline against absent feature code;
recorded details follow. This red baseline is not a feature pass.

### Initial PR #2 tests-only change checks (`0448de2`)

After drafting the tests and documents:

| Check | Actual result |
|---|---|
| `.venv/bin/python -m pytest test/offline/test_eligibility.py -q` | 32 failed, 2 passed. The passing checks cover the report fixture and existing five-rating vocabulary; failures include the absent evaluator, CLI mode, settlement behavior and the terminal-wrap test issue corrected below. |
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py::test_a_full_run_reaches_a_logged_decision -q` | 2 passed (free-text and structured paths), confirming the existing standard-mode graph helper remains compatible. |
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py::test_team_mode_gate_rejects_model_buy_when_verified_market_data_is_unavailable -q` | Expected red baseline: `TradingAgentsGraph` does not yet accept `decision_mode`; this establishes that the new team-mode integration contract is not implemented. |
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py::test_team_mode_gate_rejects_model_buy_when_verified_market_data_is_unavailable test/offline/test_graph_end_to_end.py::test_team_mode_with_no_market_analyst_fails_closed_as_review -q` | 2 expected failures because `decision_mode` is not implemented. |
| Full prior offline regression excluding the new tests-only contract and its two new graph cases | 1427 passed, 1 skipped, 2 deselected, 100 subtests passed. |
| `.venv/bin/python -m ruff check .` | Passed after correcting the test import order. |
| `.venv/bin/python scripts/check_governance.py` | Passed after document/requirements edits. |
| `git diff --check` | Passed. |

The whole new tests-only suite has been run and documents its red baseline. The
previous offline regression was rerun with only the newly introduced acceptance
cases deselected; all prior cases passed. An initial Ruff run flagged import
order; it was corrected, and the subsequent full-repository Ruff run passed. No
test approval or application-code authorization is inferred from these results.

## PR #2 correction: actual local validation

Requirements: FR-D, NFR-D, INV-D; ADR-002. No `src/` implementation was changed.

- Consolidated all 16 individual analyst/evidence/date failure variants into an
  explicit candidate-`Buy` matrix with literal reason expectations. All original
  failure variants remain covered, including missing and impossible dates.
- Added a positive graph case using a snapshot from the preceding trading day;
  this rejects a stub gate that always returns `REVIEW` or invents the snapshot
  date from the analysis date. Added a real graph-stream rejection case.
- Added a CLI-command-to-graph-constructor test that retains real selection and
  configuration setup, intercepting construction before any network/model setup.
  Its standard-mode control reaches the intercepted constructor successfully;
  only the team-mode invocation fails on the missing option.
- The CLI stream test now injects `Buy` then gated `REVIEW`, uses the real
  `MessageBuffer`, and captures every live decision panel. It currently fails on
  the actual intermediate `Buy` exposure, not on test plumbing.
- Fixed a presentation-test defect: the original literal sentence assertion was
  broken by terminal line wrapping. A fixed-width, plain Rich console now makes
  this check independent of the runner's terminal width, preserving its expected
  content. This display check passes on the upstream baseline.

| Command | Actual result |
|---|---|
| `.venv/bin/python -m pytest -q --tb=line --disable-warnings` | 36 failed, 1430 passed, 1 skipped, 1 deselected, 100 subtests passed. All failures are D tests-first cases: 28 absent-evaluator cases, 2 missing CLI-mode cases, 1 CLI stream leak, 1 REVIEW settlement case, and 4 graph cases awaiting `decision_mode`. All previous offline tests passed in the same full run. |
| `.venv/bin/python -m pytest -q --tb=no --disable-warnings` (final test revision, including standard-mode control) | Same result: 36 failed, 1430 passed, 1 skipped, 1 deselected, 100 subtests passed. No unrelated failure. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python scripts/check_governance.py --base main` | Passed schema/layout/permissions/basic credential scan and checks against the current committed refs; it does not certify an uncommitted PR diff or approve the tests. |
| `.venv/bin/python -m mypy scripts/check_governance.py` | Passed. |
| `.venv/bin/python -m pip check` | Passed. |
| `git diff --check` | Passed. |

These are deliberately red acceptance results before implementation, not a zero-
bypass claim. CI for this local revision has not run, and the review verdict has
not changed. Original user-provided review findings/AI-use entries remain intact.
The working tree has not been staged, committed or pushed in this correction
session, as requested. Full TUI `/export` is unavailable through these tools; the
user must export the actual session and add real human annotations for D5.

## Outstanding reviews and delivery evidence

- Return PR #2 to draft while acceptance tests are deliberately red. After the
  user commits and pushes, request a non-D GitHub Comment review on that new SHA.
- Obtain a current non-D review of the revised test-only head, including the
  required approval marker and rationale; link it in the PR and AI-use record.
- Build review, verification review, non-D safety review and integration review
  are all outstanding.
- No results, model outputs, reviewer approvals, GitHub checks or transcript
  exports beyond the facts above have been fabricated.
