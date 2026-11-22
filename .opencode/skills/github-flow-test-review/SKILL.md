---
name: github-flow-test-review
description: Use the recommended CS5351 test-first GitHub Flow for modules A–D; same-PR evidence is advisory.
---

# Recommended test-first review

- Read `docs/testing/test-approval-process.md` and `Prompt.md` for current rules.
- Human approval of the plan and test intent before application code remains
  required by `Prompt.md`.
- A tests-and-docs-only draft PR and non-author GitHub Comment review using
  `Test-Plan-Approved: <full SHA>` are recommended supplementary evidence. This
  same-PR review is not a required CI status and its absence does not block merge.
- Run local module and full offline checks. A separate independent approval of
  the final PR head is required; safety changes also include an ADR and pass the
  dedicated safety-review check.
- The local migration is recorded under `GOV-FLOW-001` in `docs/ai-use-log.yaml`;
  current policy and local validation are recorded in `docs/verification/github-flow.md`;
  historical check results remain unchanged. The user applied the human-only
  cleanup of the obsolete registry and permission entries.
- ADR-003 implementation was verified on Python 3.13.18: governance-focused
  tests 11 passed; full suite 1532 passed, 1 skipped, 1 deselected, 24 warnings
  and 100 subtests; governance, Ruff, mypy, pip check, YAML parsing and diff check
  passed. GitHub's branch-protection and ruleset API reads returned HTTP 403 for
  this private repository, so no remote settings were inspected or changed.
- A full OpenCode export and actual human annotation are separate from this skill.
  The workflow migration session requires a human TUI `/export`.
