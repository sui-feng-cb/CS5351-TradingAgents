---
name: pr2-test-corrections
description: Use when continuing D eligibility tests-first work after the PR #2 CHANGES REQUIRED review, including stream publication and CLI mode propagation coverage.
---

# PR #2 test correction checkpoint

Requirements: FR-D, NFR-D, INV-D, GOV-01; ADR-002. The user's request was to
correct the tests using `docs/review-memo.md` and provide commit/push commands.
No source implementation, staging, commit, push or remote review was performed.

## Reusable test design

- A pure evaluator that always returns REVIEW can pass negative cases. Include
  the real graph's positive team-mode path and assert an allowed final rating,
  completed analyst/valid evidence, actual snapshot date and no reason codes.
  The sample snapshot ends one trading day before the analysis date, so simply
  copying the requested date cannot satisfy the test.
- Check CLI mode propagation by invoking the real CLI command, retaining its
  selection/configuration code, and intercepting graph construction before
  model/data clients are initialized. Checking callback flags alone is weak.
- Inspect each graph stream emission. For the CLI, inject a candidate Buy chunk
  followed by gated REVIEW; capture every live decision panel with a fresh real
  MessageBuffer. Checking only the final saved report misses earlier exposure.
- Pair literal Buy with each independent failed precondition using named pytest
  parameters. Preserve all original variants; do not add duplicates merely to
  increase test counts.
- Terminal text wraps. Fix the plain console width for literal sentence checks
  to avoid treating line wraps as missing semantic content.

## Actual verification and pending work

Full local Python 3.13.18 pytest run: 36 failed, 1430 passed, 1 skipped,
1 deselected, 100 subtests passed. All failures are D tests-first cases (absent
evaluator/mode, observed CLI candidate leak, REVIEW settlement). Prior offline
regressions passed. Ruff, governance/schema, mypy for check_governance, pip check
and diff check passed. See `docs/verification/d-eligibility.md` for commands.

Historical read-only GitHub checks recorded PR #2 at
`0448de2b0e7ff1aa06f1ed2a61f91dca292a81db` as ready, with failed New York test
jobs and passing governance, same-PR, install and Ruff checks. Those checks
describe the policy at that time. ADR-003 later made same-PR test review advisory;
no retrospective GitHub approval is required. Human plan/test approval and
independent final/safety review remain separate requirements.

The original `docs/review-memo.md`, existing AI-use review entry and untracked
`.opencode/skills/pr2-review/` were user-provided work and were preserved. This
skill is a summary, not an original session transcript. TUI `/export` and genuine
human annotations remain pending; do not fabricate a transcript or approval.
