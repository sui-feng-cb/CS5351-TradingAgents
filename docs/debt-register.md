# Debt register

| ID | Category | Current issue | Action / owner |
|---|---|---|---|
| DEBT-01 | Evaluation | B's human-labeled semantic dataset/runner not built | B/team freeze before prompt changes |
| DEBT-02 | Guardrail | D implemented and locally tested; remote CI and independent safety/integration reviews pending | non-D reviewer/team before merge; evidence in docs/verification/d-eligibility.md |
| DEBT-03 | Governance | Remote branch protection and approval gate not yet configured; GitHub API returned HTTP 403 for branch-protection and ruleset reads on this private repository | D/user when repository plan/settings permit; require CI, independent review and the safety-review status, not same-PR test review |
| DEBT-04 | Human/context | Team identity, contributions and transcripts pending | all members, no fabricated placeholders |
| DEBT-D-01 | Governance/context | AGENTS.md still has obsolete pre-feature status because its edit was denied; active-session full export unavailable through tools | user refresh entrypoint status and use TUI /export; do not bypass permissions or invent export |
| DEBT-D-02 | Integration/process | Resolved by ADR-003: the same-PR test-review validator is no longer a required merge gate; the prior test-first path remains advisory | No retrospective approval evidence required; retain human plan/test approval, independent final review and safety-specific review |
| DEBT-D-03 | Guardrail/evaluation | PR #3 exposed finite-price, own-rating and transient stream gaps despite a green original suite; corrections and 42 added cases (including checkpoint recovery) now pass locally | non-D reviewer recheck corrected head and require remote CI; do not infer universal safety from local counts |

Track prompt rot, hallucinated/hidden dependencies, hard-to-change code, agent bloat,
evaluation, guardrail and cognitive debt with concrete symptoms and review triggers.
