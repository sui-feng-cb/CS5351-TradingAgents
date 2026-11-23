# GitHub Flow and recommended test-first review

Use a feature branch from `main`, validate locally and in CI, and merge one
independently reviewed PR for each feature. Human approval of the plan and test
intent before application implementation remains required by `Prompt.md`.

The following GitHub process is recommended supplementary evidence. Its absence
does not fail CI or block merge:

1. Open a draft PR with tests and documentation. Include requirement IDs, test
   intent, positive and negative cases, independent expected outcomes, and the
   baseline result for a representative failing case. Put deterministic tests in
   `test/offline/`.
2. Before implementation, a non-author may submit a GitHub **Comment** review on
   the test-plan commit, using `Test-Plan-Approved: <full SHA>` as the first line
   and a rationale below. Link the review in the PR, AI-use log and session
   evidence when available. This is distinct from the required independent final
   PR approval.
3. Keep approved tests and fixtures stable during implementation where practical.
   If acceptance changes, update and review the test plan. Run module checks and
   all offline tests locally and in CI.
4. Before merge, obtain independent final review of the current PR head. D safety
   changes require a non-D review and a corresponding ADR. GitHub branch
   protection requires project CI and independent final review; it does not
   require a same-PR test-plan review status.

The `Project safety reviews` workflow is separate from this advisory test-first
process. It validates the ADR and current-head independent review for safety-
critical paths only. Review events re-run that safety check; no workflow checks
for a `Test-Plan-Approved` marker or a review of a tests-only commit.
