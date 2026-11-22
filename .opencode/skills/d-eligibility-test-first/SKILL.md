---
name: d-eligibility-test-first
description: Use when planning or implementing the CS5351 D deterministic eligibility gate, its independent offline acceptance tests, or review-before-code workflow.
---

# D deterministic decision eligibility

## Required boundaries

- Trace work through FR-D, NFR-D, INV-D and ADR-002. The D pure evaluator is
  reserved for `src/tradingagents/enhancements/eligibility.py`; graph, CLI, state,
  reports and settlement changes require coordinated review.
- Preserve upstream behavior by default. The current contract proposal is
  `standard` mode by default and explicit `team` mode for the gate.
- Never derive evidence state or date from model-generated prose. The proposal
  uses deterministic evidence metadata and the upstream OHLCV 10-calendar-day
  stale bound; any change requires ADR review and test re-approval.
- The gate must publish authoritative `REVIEW` plus ordered reason codes before
  the final graph state reaches output. A rejected candidate narrative must not
  appear to users as the final decision. REVIEW results must not enter pending
  settlement/reflection.
- Follow `docs/testing/test-approval-process.md`: prepare independent offline
  acceptance tests first, get an actual non-D reviewer approval of the exact
  test-only SHA, and only then implement. Do not treat blueprint approval as test
  approval or infer GitHub review from chat.

## Test matrix

See `docs/testing/d-eligibility-test-plan.md`. At minimum test all five allowed
ratings, analyst not-run/failed, missing/not-run/unavailable/unknown evidence,
missing/malformed/future/stale dates, malformed analysis date, invalid rating,
combined failures, standard-mode compatibility, CLI mode and review notice,
graph conflict behavior, all report formats, state-log authority and exclusion
from settlement. Every negative expectation must be literal and independent of
production helper functions. NFR-D permits zero bypasses in the fixed negative
set.

## Actual evidence from the test-first checkpoint

- Local branch `D`, baseline HEAD `825d477`; no remote fetch/pull/push or commit
  occurred in the recorded work.
- Python 3.13.18 full pre-change suite: 1427 passed, 1 skipped, 1 deselected.
- Governance check, Ruff, mypy for `scripts/check_governance.py`, pip check and
  `git diff --check` passed at baseline; post-document governance, Ruff and diff
  checks also passed after correcting a test import-order issue.
- The new evaluator tests currently show the expected collection failure because
  the reserved application module is not implemented. A new team-mode graph test
  currently fails because the graph has not yet gained the proposed mode
  parameter. Existing default graph tests still pass (2 passed).
- At this checkpoint, acceptance tests and ADR remain pending independent review;
  application code is not implemented. Update this skill only with actual later
  test, implementation and review evidence.
