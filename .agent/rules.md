# Project covenant

- Extend the locked upstream; no duplicated application or unapproved runtime deps.
- Freeze public contracts before parallel module work; avoid speculative abstractions.
- Tests use independent expectations and at least one negative case per feature.
- Safety-critical edits require ADR and human approval, including tests before code.
- Every round runs all previous offline tests; never weaken an assertion to pass.
- Update affected requirements, architecture, trace, prompts and rules within one
  sprint of a changed requirement. Reload authoritative constraints after compaction.
- Preserve full original sessions and real interventions; no fabricated approvals,
  contributions, scores, test results, model outputs or transcripts.
