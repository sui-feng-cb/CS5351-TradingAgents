# GitHub Flow and test-first review for modules A–D

Use a feature branch from `main`, verify locally and in CI, and merge a single
reviewed PR for each feature. GitHub holds the approval evidence.

1. Open a draft PR from the feature branch with the tests and documentation.
   Include requirement IDs, intent, positive and negative cases, independent
   expected outcomes, and the actual baseline result for a representative failing
   case. Put deterministic tests in `test/offline/`. Keep a test-only prefix in
   branch history; use `test/`, `docs/`, `README.md` and `Report.md` at this stage.
   CI runs normally. A new failing acceptance test can leave the draft red.
2. Before implementing, a human team member other than the author uses **Files
   changed → Review changes → Comment** on that head, with the exact first line
   `Test-Plan-Approved: <full SHA>` and a rationale below. Paste the review
   permalink in the PR and link it from the AI-use log and session evidence. This
   is a submitted GitHub review, not an ordinary conversation comment. Use a new
   review for corrections. This keeps test approval separate from GitHub's final
   **Approve** decision, which may become stale after a later push.
3. After that review, commit the implementation on the same branch. Keep the
   approved tests and fixtures unchanged. If acceptance changes, review the
   revised tests before implementation; present the revised tests on a clean
   tests-only prefix and use a replacement draft PR if necessary. Preserve the
   prior review and the reason for rework. Run module checks and all offline
   tests locally; push to the same PR in the normal case.
4. Make the passing PR ready for review. A non-author reviews the final head;
   D's safety changes require a non-D review and an ADR. The authorized
   maintainer merges after all required checks and independent review pass.
   Configure branch protection on GitHub to require the `same-PR reviews`
   check alongside the regression and project governance checks, require
   up-to-date approval, and disallow direct pushes to `main`.

The governance job reads the same PR's review history. It requires a team
review of a tests-only commit in the branch's history, compares its GitHub
review timestamp with the first application commit's Git committer time, and
checks that the reviewed test files match the final PR, including changes under
`test/fixtures/`. CI can check the published evidence; Git commit timestamps do
not prove when code was first written locally. Keep the plan/test approval in
the actual agent session as well. Review submissions and dismissals trigger the
PR-only check, which keeps a push-only CI run from substituting for review
verification. Use **Re-run jobs** if a completed check needs re-verification.
