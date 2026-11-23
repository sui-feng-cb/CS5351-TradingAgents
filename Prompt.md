# Supervised launch instruction

Start by reading AGENTS.md and its required documents. Produce an execution plan
with requirement IDs, architecture/invariant references, interface contracts,
explicit scope and files, approved-test prerequisites, negative cases, regression
strategy, validation commands and ordered implementation steps.

**Stop before generating application code and wait for human plan and test
approval.** Record the actual approval and its rationale in the session. Implement
only the approved scope. Stop again at build review, verification review and
integration review. On unexpected safety, dependency or contract changes, update
the plan/ADR and obtain human direction. Tests must expose failures independently
of implementation rather than mirror it. Never alter acceptance criteria to hide
failures. A failed check is evidence for rework, not permission to bypass a gate.

At session completion, report real results and unresolved issues, update the
AI-use log and a reusable `.opencode/skills/<name>/SKILL.md`, and arrange the
complete OpenCode `/export` transcript with marked human interventions.
