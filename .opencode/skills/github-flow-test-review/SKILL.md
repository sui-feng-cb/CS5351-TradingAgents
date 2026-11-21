---
name: github-flow-test-review
description: Follow the CS5351 same-PR GitHub Flow for test-first changes to any module A–D.
---

# Same-PR test-first review

- Read `docs/testing/test-approval-process.md` and `Prompt.md` for current rules.
- Before application code, use a tests-and-docs-only draft PR and have a non-author
  submit a GitHub Comment review with `Test-Plan-Approved: <full SHA>` and the
  rationale. Keep the tests/fixtures unchanged and link the actual review.
- Run local module and full offline checks. A separate independent approval of
  the final PR head is required; safety changes also include an ADR.
- The local migration is recorded under `GOV-FLOW-001` in `docs/ai-use-log.yaml`;
  local check evidence is in `docs/verification/github-flow.md`. The user applied
  the human-only cleanup of the obsolete registry and permission entries.
- A full OpenCode export and actual human annotation are separate from this skill.
  The workflow migration session requires a human TUI `/export`.
