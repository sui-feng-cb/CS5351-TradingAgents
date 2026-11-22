---
name: pr3-eligibility-fixes
description: Continue or verify the concrete PR #3 corrections for finite Close evidence, exact team free-text own ratings and qualified public Trader streaming.
---

# PR #3 correction handoff

Read the current requirements, ADR-002, interface contracts, INV-D and
`docs/review-memo.md` before changing the boundary. This skill records real
observations; it is not human approval of another change.

- Reviewed head: `a8d60b660251b83c886bbf00b30ddd75f83bf528` on PR #3.
- User authorized reading the recorded review, repairing code, testing, staging
  and returning commit/push commands and PR text. No publication was executed.
- Preserve the pre-existing review memo, REVIEW-PR3-001 and review skill; append
  a separate implementation response without changing the reviewer's verdict.

## Enforcement and independent tests

1. The upstream loader's dropna retains infinities. Team snapshot metadata must
   verify a finite latest Close before publishing valid evidence. Keep the real
   loader active in graph regression tests; inject only synthetic Ticker.history.
   Assert REVIEW, unavailable evidence and zero pending decisions for both signs
   of infinity. A finite control must preserve Buy and normal pending behavior.
2. Standard free-text heuristics may choose consensus Buy after Strong Buy or a
   missing own rating. Team PM fallback uses `parse_team_rating`, which accepts
   only complete own fields with exact five-tier values after Markdown wrappers.
   Missing, invalid and conflicting fields fail closed. Paired graph mode tests
   keep the standard heuristic behavior explicit. Prompts/models are unchanged.
3. Public graph values and nested tasks share `_public_stream_state`. Remove PM
   candidate keys and withhold Trader proposals until checked and eligible.
   Rejected completion clears the proposal. Inspect every stream frame and
   require a positive eligible release so an always-hide repair cannot pass.
4. Version team checkpoint signatures when accepted evidence or candidate
   semantics change; a real pre-fix SQLite checkpoint bypassed new checks on
   resume. Preserve standard signatures.

The original `test_eligibility.py` is unchanged. The existing negative graph
stream assertion was strengthened; graph/adapter regressions and 28 literal
parser cases were added, for 42 additional tests overall. No assertion was
weakened to obtain green results.

## Actual verification

- Before production edits, graph/parser tests: 34 failed, 20 passed, including
  28 missing-parser failures and real graph bypass/early-publication failures.
- Initial repaired D-focused suite: 93 passed.
- Final full suite and America/New_York console pytest: each 1512 passed,
  1 skipped, 1 deselected, 100 subtests passed, 24 existing warnings.
- Ruff, governance schema/permissions/credential scan, governance-script mypy,
  pip check and correction diff check passed.
- Source of complete commands/results: `docs/verification/d-eligibility.md`.

## Remaining handoff

Keep `CHANGES REQUIRED` until independent corrected-head review. Do not fabricate
missing pre-implementation approval evidence or relax the same-PR validator.
Remote CI has not run for the local correction. Active full-session TUI `/export`
is unavailable through tools; real annotations are in
`transcripts/annotations/pr3-eligibility-fixes-2026-11-22.md`, and a user export
with exact cross-links remains pending. Earlier raw files must not be silently
relabeled as the current correction session.
