---
name: pr5-manifest-review
description: Reusable evidence and findings from the PR #5 C manifest/query tests-first review.
---

# PR #5 C manifest/query review

## PR #9 fix re-review — `2a24550` (2026-11-24)

PR `sui-feng-cb/CS5351-TradingAgents#9`, base
`6ad32855d84cb9e77f03ee9e1cf3661a916572db`, reviewed head
`2a245507a77839823f9e380335f45214d0d7544d`, previous head `ac2c5ca`.
The user limited this round to the prior save-failure finding and explicitly
approved unchanged v1 structure: status denotes analysis outcome, while an
otherwise successful analysis may carry error `report_save_failed` /
`Report save failed.`. A skipped save has null error. Query warns and retains
the match. References: FR-C, SEC-01/INV-SECRET, ADR-001/003, C v1 contract.

Decision: **APPROVE**. Internal save_failed bookkeeping is excluded from the
public reports mapping. Fixed error serialization, skipped-save control,
query match retention/warning and display-after-failure pass; interface and
schema descriptions reflect the confirmed semantics. Reuse these checks when
reviewing lifecycle bookkeeping: analysis outcome and post-analysis I/O outcome
must remain independently observable without leaking exception text.

Actual Python 3.13.18 verification:

- C suite: 50 passed; targeted save/query cases: 5 passed, 45 deselected.
- Full default offline suite: 1678 passed, 1 skipped, 2 deselected,
  24 warnings, 100 subtests passed.
- Governance with current PR base, full Ruff, governance-script mypy, pip check,
  PR whitespace check excluding raw transcripts and fix-commit diff check pass.
- Latest PR/push CI runs 45218398337 / 45218380901 succeed on reviewed head;
  all displayed checks pass, including safety review. PR is MERGEABLE.

Main was temporarily detached for verification and restored to `6ad3285`.
Only review memo, AI-use log (REVIEW-PR9-002) and this skill changed; no new
application/tests, remote comment/review, commit, push or merge. Full active
TUI /export remains a human action; no export is invented. Detailed commands
and results are in `docs/review-memo.md`.

## Re-review at `677e9f396e9ae3498d218a42d1a49f1e8270af48`

The corrections resolve the prior review findings: path traversal now uses a
verified external target with an open spy; CLI query monitors mutations and
snapshots results; schema negatives cover eight malformed variants; failed-run
serialization has safe-value assertions; real CLI tests cover ticker/date/
combined/no-match filters and malformed JSON warnings; successful report saving
checks the returned relative path.

Two failed Python 3.13 CI runs (`pull_request` and `push`) both ran the same head
and both report 29 C-only expected failures, 1532 passes, 1 skip, 1 deselection
and 100 subtests. The implementation module and CLI query command are absent, so
tests report the missing import/command and no manifest files. This is expected
for tests-first but remains a required-check merge blocker until implementation
makes the acceptance tests pass. Governance, safety review, Ruff and clean install
passed remotely.

Review decision: `APPROVE` for tests-and-docs scope only; not a green-CI or
merge approval. Team confirmation remains needed for the candidate CLI JSON
envelope, fixed failure error literals and proposed NFR-C timing threshold. The
test-plan header's suite count should be updated from 20 to 29.

## Scope

- Repository: `sui-feng-cb/CS5351-TradingAgents`
- PR: [#5](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/5)
- Initial review head: `64f7bec36e91b83f976708ff5310966530596010`
- Re-review head: `677e9f396e9ae3498d218a42d1a49f1e8270af48`
- Requirements: FR-C, NFR-C, SEC-01, GOV-01.
- Review results: initial tests-first review `CHANGES REQUIRED`; re-review
  `APPROVE` limited to tests-and-docs. No C application implementation was
  present or approved.
- GitHub review approval: [submitted for tests-and-docs scope only](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/5#pullrequestreview-6017260315).

## Reusable review checks

The C acceptance contract must independently prove:

1. schema rejection of unknown/missing fields, malformed UUID/date/timestamps
   and invalid report/error shapes, not only positive fixture validation;
2. failed-run fixed error code and safe bounded message without traceback or
   credential values;
3. no access to report paths outside the results root;
4. byte/content and filesystem-operation preservation for read-only CLI queries;
5. actual Typer wiring for ticker-only, date-only, combined and no-match filters;
6. saved-report integration recording the exact relative paths returned by the
   report-saving lifecycle.

The path-containment and CLI read-only gaps were P1; the remaining four gaps
were P2. Review-only probes showed that a no-op schema validator, a
`{"status":"failed"}` record, an implementation that reads an out-of-root file,
and a query that overwrites a report could pass the corresponding current
assertions. The temporary probe file was removed after verification.

## Actual verification

- Full local command: `TZ=America/New_York .venv/bin/python -m pytest -q
  --tb=line --disable-warnings`
  - Result: 1532 passed, 20 expected C acceptance failures, 1 skipped, 1
    deselected, 100 subtests passed.
- Passed: governance against base, full-repository Ruff, governance-script
  mypy, `pip check`, and `git diff --check main...HEAD`.
- Remote PR state: governance, safety review, Ruff and clean-install checks
  passed; Python 3.13 test jobs failed on the intentionally absent C module and
  CLI command.

## Session artifact boundary

The active-session TUI `/export` was unavailable through the tool interface.
The user must perform the real export and place it under `transcripts/raw/`; no
replacement transcript is fabricated.
