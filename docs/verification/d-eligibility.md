# D eligibility-gate work log and verification evidence

Status: D application code is implemented locally; full offline regression has
passed. PR #3 review found three bypasses in the initial implementation; the
corrections below pass local regression but await corrected-head CI and independent
re-review. Earlier sections preserve the original implementation/tests-first evidence.

## PR #3 re-review repairs

The user directed repairs for the findings recorded at `a99b017` (FR-D, NFR-D,
INV-D, BASE-01; ADR-002). Regression tests first reproduced the two Markdown
code-block cases with valid evidence and a free-text PM. The pre-fix targeted
run using `-k 'markdown_code or markdown_examples or pre_fix'` reported 12
failed, 3 passed and 55 deselected; failures also exposed incorrect fence-length
handling and reuse of a v2 SQLite candidate. Two more parser cases cover a
multiline code span and an HTML comment. Team parsing now uses CommonMark block
structure, and the team checkpoint policy is v3. Standard behavior is unchanged.

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest test/offline/test_team_rating.py test/offline/test_graph_end_to_end.py -q --tb=short --disable-warnings` | 72 passed. |
| `.venv/bin/python -m pytest -q --tb=short --disable-warnings` | 1528 passed, 1 skipped, 1 deselected, 100 subtests passed (24 warnings). |
| `TZ=America/New_York .venv/bin/pytest -q --tb=short --disable-warnings` | Same counts using the CI entry point. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python -m mypy scripts/check_governance.py` and `.venv/bin/python -m pip check` | Passed. |
| `.venv/bin/python scripts/check_governance.py --base main` | Passed local registry, layout, permission, basic credential scan, and committed-ref checks. |

The remote PR #3 description was edited only to replace the mistyped PR #2 URL.
The GitHub response confirmed the corrected link is present and the old link is
absent. The correction has not been committed or pushed by the agent. The new
head still requires CI and re-review. Full active-session export is unavailable
through the tool interface; use TUI `/export` and link the real export to
`D-ELIG-PR3-FIX-002` after saving it.

## Historical PR #3 correction session — 2026-11-22

User direction: read the PR #3 findings already in `docs/review-memo.md`, repair
code, test, stage and return manual commit/push commands and template PR text.
Scope is FR-D/NFR-D/INV-D and standard-mode compatibility under ADR-002/BASE-01.
No new independent approval, commit, push or remote PR mutation was requested.
The initial worktree was `D...origin/D` at `a8d60b6`, with existing unstaged review
memo/AI-use log updates and an untracked `pr3-eligibility-review` skill. Those real
review artifacts were preserved and are included in the correction handoff.

### Repair plan and results

1. Write independent red regressions before production edits: use the real OHLCV
   loader with a synthetic `Ticker.history`, inject nonfinite latest Close values
   plus an older valid row, exercise free-text own rating versus consensus in
   team/standard graph paths, and inspect every public stream frame.
2. Reject unusable latest Close in the team metadata adapter before `valid`
   evidence is emitted. Reuse `market_evidence_unavailable`; do not modify the
   existing standard loader or relax its freshness/date behavior.
3. Add team-only exact own-field parsing to the PM free-text fallback. Values
   must be exact five-tier strings after Markdown wrappers; missing, conflicting
   or invalid own fields yield REVIEW/invalid_rating. Preserve standard heuristic
   parsing, typed structured output, model configuration and prompts.
4. Apply a common public-state projection to values and nested task emissions.
   Withhold Trader proposals until successful qualification, clear them on
   rejection and continue stripping PM candidate keys. Test eligible release to
   avoid accepting an always-withhold repair.
5. Version the team checkpoint signature to prevent reuse of evidence and
   candidates accepted under the pre-fix policy. Standard signatures stay stable.
6. Run the focused suite, all offline regression, the alternate CI timezone and
   repository checks, then synchronize D1–D9 artifacts and stage intended files.

Before code edits, the graph/parser run reported **34 failed, 20 passed**:
the existing negative stream case and five additional graph variants exposed
real bypasses/early publication, while 28 cases failed because the proposed exact
parser was absent. After corrections, the D-focused run reported **93 passed**.
Finite-price positive control and five invalid-price adapter cases were then
added. A separate SQLite checkpoint regression reproduced `Buy` on resume before
the signature change; it passes as part of the final full runs below.

| Command | Actual result |
|---|---|
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py test/offline/test_team_rating.py -q --tb=short --disable-warnings` before production repairs | 34 failed, 20 passed; independently reproduced review findings. |
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py test/offline/test_team_rating.py test/offline/test_eligibility.py test/offline/test_eligibility_adapter.py -q --tb=short --disable-warnings` after initial repairs | 93 passed. |
| `.venv/bin/python -m pytest test/offline/test_graph_end_to_end.py::test_team_run_does_not_resume_a_pre_fix_portfolio_candidate -q --tb=short` before signature change | 1 failed; old checkpoint published Buy. |
| `.venv/bin/python -m pytest -q --tb=short --disable-warnings` on final code/tests | **1512 passed, 1 skipped, 1 deselected, 100 subtests passed**, 24 warnings; 12.55s. |
| `TZ=America/New_York .venv/bin/pytest -q --tb=short --disable-warnings` | Same counts; 12.56s. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python scripts/check_governance.py --base main` | Passed schema/layout/permission synchronization, basic credential scan and committed-ref checks; does not validate a new GitHub approval or staged feature diff. |
| `.venv/bin/python -m mypy scripts/check_governance.py` | Passed; scope is the governance script. |
| `.venv/bin/python -m pip check` | Passed. |
| `git diff --check` | Passed for the correction worktree; existing raw exports were not edited. |

The optional `langchain_aws` dependency is absent and one live test is deselected.
Tests use scripted models and synthetic vendor history; no live provider call or
runtime dependency was added. The original `test_eligibility.py` is unchanged.
`test_graph_end_to_end.py` now strengthens the original rejected-stream case and
adds full graph regressions. No existing assertion was weakened or removed.

### D1–D9 correction ledger

| Deliverable | Actual update / boundary |
|---|---|
| D1 | Requirements retain existing rating vocabulary, freshness bound and reason semantics; test references include exact-own-rating and invalid-price regressions. |
| D2 | ADR-002, interface, runtime policy and trace matrix state finite-close validation, exact team free-text parsing and stream qualification. |
| D3 | Existing constraints are followed; no permission, CI gate or human-owned rule was relaxed. |
| D4 | This red/green log, BUG-D-003 and strengthened graph/adapter tests plus new literal `test_team_rating.py`; original review verdict preserved with a separate implementation response. |
| D5 | `transcripts/annotations/pr3-eligibility-fixes-2026-11-22.md` records the actual user direction. Prior exports exist under `transcripts/raw/`; no specific export is attributed to this active correction without evidence. Complete current TUI `/export` remains a user follow-up. |
| D6 | `Report.md` explains how independent review found failures despite 1470 prior passing tests and how additional expectations corrected them. |
| D7 | AI-use record `D-ELIG-PR3-FIX-001`, preserved REVIEW-PR3-001 and reusable correction skill; PR text follows `.github/PULL_REQUEST_TEMPLATE.md` and uses correct repository links. |
| D8 | Four production files updated, graph and adapter regressions extended, exact-rating regression file added; no runtime dependency or prompt/model change. |
| D9 | Review-driven scope and tests-before-code red run recorded; independent corrected-head review and genuine approval evidence remain required. |

Current local results address the three concrete P1 reproductions. They do not
change the reviewer's verdict, certify all possible inputs, or repair the missing
pre-implementation independent-review evidence described by the original review.
The same-PR review validator is unchanged. The correction handoff stages 23
intended files on `D`, including the existing local review artifacts;
`git diff --cached --check` passed, with no unstaged changes. Commit/push
commands are provided for manual execution only.

## Historical implementation session — 2026-11-22

The user confirmed PR #2 was squash-merged, main/D were updated, and the latest
D commit contained the prior review/session/skill artifacts. Those facts were
accepted without remote re-review. The user approved the implementation blueprint
and directed completion of implementation, D1–D9 updates, local checks and staging,
with commit/push commands returned for manual execution. Initial local worktree
was clean on `D`, at `0bf424f`; Python is `.venv` 3.13.18.

### Implemented boundary (FR-D, NFR-D, ADR-002, INV-D)

- Frozen `EligibilityDecision` and a pure team-only evaluator validate execution
  status, evidence status, canonical dates, the inclusive 10-calendar-day bound
  and exact rating values; ordered reasons and a stable explanation accompany
  every `REVIEW` outcome.
- The evidence graph node calls the existing Yahoo snapshot row path using the
  current ticker/date. `NoMarketDataError` now optionally carries a typed
  `snapshot_date` for stale rejection. The normal loader still rejects stale
  prices. No exception text is parsed and no freshness bypass remains.
- Team-mode market execution records completed/failed status independently of
  evidence acquisition. Absent execution metadata cannot be replaced by a report
  claiming success. Initial states are not-run/null; standard remains the default.
- The team Portfolio Manager stages candidate fields, then the gate writes the
  authoritative rating and replaces rejected public decision prose. Candidate
  fields are cleared and not yielded by `stream_run`. Rejected Trader proposals
  are removed from the final state; reports and CLI also withhold those proposals.
- CLI mode selection reaches graph construction, live panels withhold unqualified
  decisions, and completion output shows `REVIEW`, reason codes and explanation
  even with `--no-show`. Markdown, HTML and state logs carry the gate result.
- Team `REVIEW` is written to the state log but not to the pending memory log;
  no new settlement/reflection entry is created. The team checkpoint signature
  differs from standard without altering standard checkpoint identity.

### Actual failures and rework

1. Initial focused run: **2 failed, 52 passed**. The completion notice omitted
   uppercase `REVIEW`; a blocked complete report still exposed the Trader's Buy
   proposal. Both implementation defects were fixed; the next focused run was
   **54 passed**. Approved D acceptance tests were not changed.
2. Initial full run: **25 failed, 1441 passed, 1 skipped, 1 deselected**. Bare
   upstream graph fixtures lacked the newly introduced mode attribute; normal
   snapshot calls unnecessarily supplied a new loader keyword; two existing CLI
   exact-flags expectations lacked the added default mode. Production compatibility
   was fixed and those two old CLI expectations were extended with the literal
   `decision_mode: standard`, preserving all previous assertions. A targeted
   regression run across the affected suites then reported **208 passed**.
3. Ruff initially reported an import ordering issue and a Typer B008 default;
   reordered imports and the existing Annotated option style resolved both.
4. Final safety inspection replaced a temporary freshness-bypass parameter with
   typed stale exception metadata. Four additional adapter regression tests cover
   future-row filtering, stale-date propagation without releasing stale prices,
   market execution exceptions and missing execution metadata versus report prose.

### Current verification results

| Command | Actual result |
|---|---|
| `.venv/bin/python -m pytest -q --tb=short` | **1470 passed, 1 skipped, 1 deselected, 100 subtests passed** in 10.58s; 24 provider-model warnings. Optional `langchain_aws` is absent; the live test is deselected. |
| `TZ=America/New_York .venv/bin/pytest -q --disable-warnings` | Same counts: **1470 passed, 1 skipped, 1 deselected, 100 subtests passed**, 24 warnings, in 10.66s. This uses the actual CI test entry point in the alternate CI timezone. |
| `.venv/bin/python -m ruff check .` | Passed after final implementation changes. |
| `.venv/bin/python scripts/check_governance.py --base main` | Passed after D1–D9 artifact updates: schema/layout/permission synchronization/basic credential scan and committed-ref checks. The `--base` gate reads committed refs, not an uncommitted/staged feature diff. |
| `.venv/bin/python -m mypy scripts/check_governance.py` | Passed; this checks the governance script only. |
| `.venv/bin/python -m pip check` | Passed. |
| `git diff --check` and `git diff --cached --check` | Passed, including the final staged tree. |

All original D acceptance assertions passed, including the fixed independent Buy
conflict matrix and output/settlement checks. Observed bypasses are **0 in those
fixed tested cases**; this is not a universal guarantee for untested inputs.
No live model/data analysis or remote repository mutation ran.

### Current D1–D9 ledger

| Deliverable | This session's actual artifact | Remaining boundary |
|---|---|---|
| D1 | `requirements.yaml` marks FR-D/NFR-D implemented and points to executable tests. | Not marked verified/accepted before independent review. |
| D2 | Architecture, ADR-002, interface, invariant, runtime, memory and trace documents reflect the implementation. | Non-D safety and integration review pending. |
| D3 | Structural/verification constraints document code ownership, failure paths and verification scope. | An AGENTS.md status refresh was denied by the tool's default edit rules; leave that human-edit follow-up recorded rather than bypass permissions. Human-owned rules remain intact. |
| D4 | This log records actual red/green results; bug diary records rework; fixed D tests remain unchanged. | Final human verification review and remote CI pending. |
| D5 | Separate real-intervention annotations are in `transcripts/annotations/d-implementation-2026-11-22.md`. | The active-session TUI `/export` tool is unavailable; user must export the full session under `transcripts/raw/` and link its actual path. No substitute transcript was generated. |
| D6 | `Report.md` adds the approved scope, implementation, failures and evidence. | Names, contributions and personal reflections still require real human input. |
| D7 | AI-use entry `D-ELIG-IMPL-001` and reusable implementation skill added; 35 intended files staged after checks. | No commit, push, new PR, remote CI or final review is claimed. The existing same-PR review validator is unchanged; the merged tests-only PR must be accounted for in the future implementation PR review. |
| D8 | Evaluator plus existing graph/dataflow/CLI/report integration; four adapter regressions and two legacy CLI expectation updates. | No runtime dependency added; no changes to approved D acceptance tests. |
| D9 | The user's explicit blueprint approval and instruction to finish checks/staging are recorded in this session and annotations. | No human review or approval has been fabricated; project rules were not relaxed. |

### Local handoff

The final staged diff contains only this session's 35 intended files. There are
no unstaged differences. `git diff --cached --check`, final full-repository Ruff
and the final governance scan passed after staging. The two merged D acceptance
files are byte-unchanged relative to HEAD. Commit/push were not executed. This is
a locally validated handoff for committing and PR review; D5 full-session export,
entrypoint wording refresh, remote CI and independent reviews remain distinct
follow-ups rather than fabricated completion evidence.

## Historical tests-first session record — 2026-11-22

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

## Historical tests-first D1–D9 artifact ledger

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

## Historical test-first gate and pending approval

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

## Historical outstanding reviews and delivery evidence (before PR #2 merge)

- Return PR #2 to draft while acceptance tests are deliberately red. After the
  user commits and pushes, request a non-D GitHub Comment review on that new SHA.
- Obtain a current non-D review of the revised test-only head, including the
  required approval marker and rationale; link it in the PR and AI-use record.
- Build review, verification review, non-D safety review and integration review
  are all outstanding.
- No results, model outputs, reviewer approvals, GitHub checks or transcript
  exports beyond the facts above have been fabricated.
