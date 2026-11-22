# Debt register

| ID | Category | Current issue | Action / owner |
|---|---|---|---|
| DEBT-01 | Evaluation | B's human-labeled semantic dataset/runner not built | B/team freeze before prompt changes |
| DEBT-02 | Guardrail | D implemented and locally tested; remote CI and independent safety/integration reviews pending | non-D reviewer/team before merge; evidence in docs/verification/d-eligibility.md |
| DEBT-03 | Governance | Remote branch protection and approval gate not yet configured | D/user after publication approval |
| DEBT-04 | Human/context | Team identity, contributions and transcripts pending | all members, no fabricated placeholders |
| DEBT-D-01 | Governance/context | AGENTS.md still has obsolete pre-feature status because its edit was denied; active-session full export unavailable through tools | user refresh entrypoint status and use TUI /export; do not bypass permissions or invent export |
| DEBT-D-02 | Integration/process | D's acceptance tests were merged in PR #2 before the implementation PR, while the existing validator expects same-PR test-review history | team account for genuine approval evidence in the future PR; no validator relaxation or fabricated review in this session |

Track prompt rot, hallucinated/hidden dependencies, hard-to-change code, agent bloat,
evaluation, guardrail and cognitive debt with concrete symptoms and review triggers.
