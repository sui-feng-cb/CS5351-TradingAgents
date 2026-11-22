# ADR-003: make same-PR test-first review advisory

- Status: implemented and locally verified; GitHub branch-protection/ruleset API
  reads returned HTTP 403, so remote rollout remains unresolved.
- Requirements: GOV-01, QUA-01.
- Related decisions: ADR-002; `Prompt.md` human plan/test approval gate.

## Context

The project previously required a GitHub Comment review of a tests-only commit
before application implementation and enforced its presence with a PR status
check. The check coupled test-first review to a particular PR history and review
marker. The team requests that this specific GitHub evidence not be a hard merge
condition, while retaining human supervision, independent final review, CI and
additional safety review for safety-critical changes.

## Decision

1. Human approval of the development plan and test intent before application
   implementation remains required by `Prompt.md`. This may be recorded in the
   actual agent session; it need not be represented by a same-PR GitHub Comment.
2. Keep the test-only draft PR and independent pre-implementation review as
   recommended practice. Missing same-PR test-review evidence must not fail CI or
   block merge.
3. Replace the combined `same-PR reviews` workflow with a dedicated safety-review
   workflow. It runs for safety-relevant application changes, requires the
   corresponding ADR and an independent approval of the current PR head, and does
   not validate pre-implementation test approvals.
4. Require ordinary project CI and independent final PR approval through GitHub
   branch protection. Retain the safety-review status as an additional check.

## Consequences

- GOV-01 and process documentation distinguish required human supervision and
  final review from optional same-PR test-review evidence.
- A separate safety-review check preserves the existing safety-specific review
  boundary without making test-only review timing a merge condition.
- GitHub branch protection must stop requiring the old `same-PR reviews` status
  and require the safety-review status and ordinary CI/review protections. This
  remote setting is verified during rollout; local workflow changes alone do not
  prove the remote merge policy.
- Attempted API reads of branch protection and repository rulesets returned HTTP
  403 with a plan-feature message. No remote protection configuration was read or
  changed in this session.
- Historical PR reports and verification logs continue to describe the checks
  that actually ran at that time.

## Reconsider if

- Human review finds the plan/test supervision boundary is no longer adequate.
- GitHub changes prevent branch protection from requiring the dedicated safety
  status for safety-critical paths.
- A less brittle, independently approved workflow can preserve the same
  distinction without coupling test review to PR status checks.
