---
name: pr3-inline-rating-fix
description: Verify PR 3 corrections for team rating fields beside multiline inline Markdown and recover the dependency-install CI job on the existing mirror.
---

# Team rating regression and PR CI retry

- Follow FR-D, NFR-D, INV-D and ADR-002. Use valid offline market evidence and
  independently assert the graph's final rating, reason codes and pending entries.
- Keep the source spelling of exact rating fields. Record real CommonMark line
  breaks so embedded source newlines in code spans cannot create fields or hide
  other lines. Test both a rejected `Strong Buy` with a later `Buy` and an accepted
  `Hold` in the same paragraph as a multiline example. Track the full range of
  a hard break so that a backslash marker cannot become part of the rating value.
- Check checkpoint recovery when the team qualification policy changes. A v3
  checkpoint reproduced the old `Buy` after the parser repair. Policy v4 reruns
  qualification and the regression expects no pending entry on `REVIEW`.
- When the push job passes on the same SHA and the PR job fails before pytest,
  inspect the dependency step and retry the failed job on the existing index.
  PR #3 run `45025694225` succeeded on attempt 2 using the Tsinghua mirror.

The final local runs recorded 80 focused passes and 1536 full passes, with one
skip, one deselection and 100 subtests in each full run. See
`docs/verification/d-eligibility.md` for commands, review scope and results.

## Review of 9c53f95

`REVIEW-PR3-004` in `docs/ai-use-log.yaml` records the follow-up review. The
CommonMark source-break handling preserves visible rating fields around a
multiline inline code span. In the full offline graph, `Strong Buy` followed by
a later `Buy` returns `REVIEW` with `invalid_rating` and leaves settlement
empty. A single valid `Hold` beside a multiline code example is accepted and
recorded as Hold. Earlier evidence, graph-stream and recovery regressions pass.

Validation on Python 3.13.18: 1536 full-suite passes, 1 skip, 1 deselection
and 100 subtests. The focused multiline/code selection passed 19 tests with
61 deselected. Governance, Ruff, mypy, pip and changed-source whitespace checks
passed. GitHub tests, governance, Ruff and clean-install checks passed on this
head. The approval-related `same-PR reviews` check is outside this code verdict;
this memo is not a submitted GitHub review.
