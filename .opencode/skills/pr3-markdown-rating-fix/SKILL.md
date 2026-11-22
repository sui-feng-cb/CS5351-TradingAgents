---
name: pr3-markdown-rating-fix
description: Recheck the D team free-text rating boundary and checkpoint policy after the PR #3 Markdown review repairs.
---

# PR #3 Markdown rating repair

Read ADR-002, INV-D and `docs/review-memo.md` before changing this path. The user
directed repairs for the re-review at `a99b017` and requested manual commit/push
commands. This skill records validation, not independent review approval.

- Use the existing CommonMark parser to distinguish prose from code, including
  nested list code and mixed, short or malformed fence closers. Keep the exact
  rating check in `src/tradingagents/agents/rating.py` and the standard parser
  unchanged. The ordinary Markdown block must supply a complete own field.
- Full offline graph cases distinguish valid-evidence code-only `REVIEW` with
  no pending entries from a real `Hold` that qualifies. Version the team
  checkpoint signature when changing which candidates can qualify; v3 starts
  fresh for v1/v2 checkpoints. Standard checkpoint IDs stay stable.
- The targeted pre-fix run had 12 failures, including both review reproducers
  and SQLite v2 recovery. The repaired focused suite passed 72 cases. Two full
  runs passed 1528 tests and 100 subtests, with 1 skip and 1 live deselection.
  Exact commands are in `docs/verification/d-eligibility.md`.
- The existing PR #3 body was changed only to correct the PR #2 URL. GitHub
  confirmed the old URL is absent. The code was not committed or pushed by the
  agent. A complete active-session export still requires TUI `/export`; do not
  substitute this note for the export.
