# Test-first approval process

The code PR cannot approve its own tests. Use this sequence:

1. Open a test-only PR with requirement IDs, test intent, positive/negative
   cases, independent expected outcomes, fixtures, and test files. Do not modify
   application source in this PR.
2. Obtain a GitHub APPROVED review from a reviewer other than the test author and
   merge the test-only PR. The review timestamp and merge commit are retained by
   GitHub.
3. In a separate human-reviewed registry PR, record the test-only PR number,
   registry PR number, merged test commit (approval_commit), requirement IDs,
   the test PR reviewer's login and exact submitted_at timestamp, frozen test
   paths and Git blob IDs, plus narrowly scoped implementation path patterns, in
   `docs/test-approvals.json`. Merge the registry change only after the test PR
   is merged.
4. The subsequent implementation PR must use those exact test blobs; CI queries
   GitHub to confirm both prior PRs merged to the same base, both had an
   independent human approval before merge, the test PR contained no application
   code, and the tests remain unchanged in the implementation base. Every changed
   application file must be covered by an approved implementation path pattern.

No test plan or approval record is presently approved. `docs/test-approvals.json`
starts empty. GitHub Actions branch protection must require both CI and human
review. A JSON field alone is not proof of approval; CI verifies it against the
GitHub PR/review API when credentials are available.
