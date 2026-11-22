# PR Reviews

For each actual PR, record the reviewer, repository, PR URL and number, base/head
commits, scope, requirement and architecture alignment, code/test quality,
operational metadata, safety, efficiency and verification evidence. Findings must
be ordered by severity and include file/line references where applicable. Finish
with exactly one of `APPROVE`, `CHANGES REQUIRED` or `REJECT`, together with the
rationale. Do not self-approve safety changes or backdate approval to satisfy CI.

## PR #2

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2
- **Reviewer:** OpenCode, read-only review requested by the user
- **Reviewed head:** `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`
- **Base:** `main`
- **Date:** 2026-11-22
- **Scope:** Tests-first D eligibility-gate contract covering FR-D, NFR-D,
  INV-D and GOV-01. No application implementation is included in the PR.

### Alignment

The PR is aligned with the proposed team-mode eligibility boundary and adds a
literal status/date/rating test matrix, graph safety cases, CLI/report/state
expectations and process documentation. The intended boundary is consistent with
ADR-002, the interface contract proposal and INV-D. The PR correctly leaves the
application module unimplemented pending independent test-plan approval.

### Findings

1. **P1: Required independent test-plan approval is absent.** The PR is marked
   ready rather than draft, has no GitHub reviews, and its own description says
   that non-D review is pending. The documented flow requires a review whose first
   line is `Test-Plan-Approved: <full SHA>` before implementation or final review.

2. **P1: No positive team-mode graph integration test exists.** The test plan
   specifies D-INT-01, but the PR only adds unavailable-evidence and missing-market-
   analyst cases. Both new team-mode graph tests fail at construction because
   `TradingAgentsGraph` does not yet accept `decision_mode`; there is no test that
   valid evidence and an allowed rating pass through the graph and become the
   authoritative final result.

3. **P1: CLI tests do not prove that `decision_mode` reaches the graph.** The
   assertion in `test/offline/test_eligibility.py` only checks the `flags` passed to
   `run_analysis`. It does not check `TradingAgentsGraph` construction or the run
   configuration, so the option could be discarded after the CLI callback.

4. **P1: The stream path is not tested for candidate-rating leakage.** The
   eligibility contract requires gating before publication, but the fake graph in
   `test/offline/test_eligibility.py` emits only one final state. It cannot detect
   a `Buy` candidate being displayed in an earlier stream chunk before the gate
   replaces it with `REVIEW`.

5. **P1: The Buy-conflict negative matrix is incomplete.** The verification rules
   require a model `Buy` paired independently with each blocked analyst, evidence
   and snapshot-date condition. The PR covers one combined pure case and one
   unavailable-evidence graph case, but not every blocked condition.

6. **P2: The verification record is stale.**
   `docs/verification/d-eligibility.md` still states that `gh` was unavailable and
   that no commit, push or PR existed, although PR #2 and its head commit now
   exist. The record needs a follow-up entry with the actual PR and CI state.

### Verification evidence

- `.venv/bin/python scripts/check_governance.py`: passed.
- `.venv/bin/python -m pytest test/offline/test_eligibility.py -q`: `32 failed,
  2 passed` against the intentionally absent implementation.
- New team-mode graph tests: both failed at the missing `decision_mode` constructor
  parameter.
- Prior offline regression excluding the deliberately red new cases: `1427
  passed, 1 skipped, 2 deselected, 100 subtests passed`.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check`: passed.
- Remote governance, same-PR reviews, clean-install and Ruff checks: passed.
- Remote `tests (py3.13, America/New_York)` checks: failed.

### Decision

**CHANGES REQUIRED.** The tests-first scope is directionally appropriate, but the
PR cannot proceed as a ready PR until independent test-plan approval is recorded,
the missing positive and boundary tests are added, stale verification metadata is
corrected, and the required checks are green or the deliberately red tests-only
stage is explicitly kept as a draft under the documented workflow.

## PR #2 Re-review

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2
- **Reviewer:** OpenCode, read-only re-review requested by the user
- **Reviewed head:** `f4be027ebbc43c3226c63209b743cf7482711556`
- **Previous reviewed head:** `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`
- **Base:** `main`
- **Date:** 2026-11-22
- **Scope:** Re-review of the tests-only corrections for FR-D, NFR-D, INV-D and
  GOV-01. No application implementation is included.

### Re-review result

The previous implementation/test findings are resolved within the approved
tests-first scope:

1. A positive team-mode graph case now verifies valid evidence, the actual
   preceding-trading-day snapshot, an allowed rating and an empty reason list in
   `test/offline/test_graph_end_to_end.py:158-176`.
2. CLI forwarding is covered from command invocation through
   `TradingAgentsGraph` construction in `test/offline/test_eligibility.py:162-215`,
   including the standard-mode control and the `team` value.
3. Candidate-rating leakage is covered both at the real graph stream boundary in
   `test/offline/test_graph_end_to_end.py:228-255` and at the CLI live-display
   boundary in `test/offline/test_eligibility.py:218-307`.
4. The negative matrix now pairs candidate `Buy` independently with all 16
   analyst, evidence, snapshot-date and analysis-date failure variants in
   `test/offline/test_eligibility.py:53-83`.
5. The verification record now distinguishes historical initial-PR facts from
   the latest PR metadata and records the revised local validation in
   `docs/verification/d-eligibility.md:90-127`.

No new code-quality or test-design blocker was found in the revised tests-only
change. The intentionally failing acceptance tests are appropriate for a
tests-first contract because `src/tradingagents/enhancements/eligibility.py` and
the coordinated graph/CLI integration have not yet been implemented.

### Verification evidence

- `.venv/bin/python -m pytest -q --tb=no --disable-warnings`: `36 failed, 1430
  passed, 1 skipped, 1 deselected, 100 subtests passed`; all failures are in the
  new D tests-first cases.
- `.venv/bin/python scripts/check_governance.py --base main`: passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check`: passed.
- Remote governance, same-PR reviews, clean-install and Ruff checks: passed.
- Remote `tests (py3.13, America/New_York)` checks: failed only on the expected
  unimplemented D acceptance cases.
- The PR remains tests-only; no application stub, skip, expected-failure marker or
  CI exclusion was added to hide the unimplemented behavior.

### Decision

**APPROVE.** The revised tests-only contract satisfies the findings from the
previous review and is ready for the next tests-first workflow step. This approval
is limited to the revised test contract and its supporting evidence. It is not an
approval of application implementation, the proposed safety behavior, merge, or
settlement integration.

The repository still requires the documented independent non-D GitHub Comment
review with the exact first line `Test-Plan-Approved: f4be027ebbc43c3226c63209b743cf7482711556`.
The current GitHub PR has no submitted reviews, so this memo entry must not be
used as a substitute for that human approval or represented as a GitHub approval.

## Future review records

Every subsequent PR review must append a dated section using the same structure:

1. Repository, PR URL/number, reviewer, base commit and reviewed head SHA.
2. Scope plus requirement, ADR, invariant and architecture alignment.
3. Findings ordered by severity, with file/line references and concrete fixes.
4. Code/test quality, operational metadata, safety and efficiency observations.
5. Exact local and remote verification commands with real results.
6. A final `APPROVE`, `CHANGES REQUIRED` or `REJECT` decision and rationale.

Review conclusions must be recorded here after each actual PR review. GitHub review
submission, approval and merge remain separate actions and must not be implied by
this memo.
