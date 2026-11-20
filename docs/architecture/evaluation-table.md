# Candidate architecture evaluation

Qualitative design comparison; no experimental scores are fabricated.

| Candidate | Upstream preservation | D8 layout | Integration effort | Decision |
|---|---|---|---|---|
| Keep packages at root | Good | Does not match target src | Low | Not selected |
| Nested full upstream repository | Ambiguous duplicate boundaries | Poor | High deployment ambiguity | Rejected |
| Single src layout and narrow extensions | Good, imports retained | Matches | Requires install/path/resource regression | Proposed, ADR-001 |

Reassess after migration regression evidence, course clarification or measured
dependency/installation issues. Human approval and actual evidence belong in the
review log, not inferred from this comparison.
