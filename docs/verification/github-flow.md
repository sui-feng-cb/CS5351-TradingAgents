# Local verification: A–D GitHub Flow migration

- Scope: `GOV-01` and `QUA-01`; same-PR test review, local checks and review
  evidence. The local `D` worktree started at `830fc86`; application code and
  feature acceptance tests were outside this migration.
- Environment: project `.venv`, Python 3.13.18, no live provider calls.

| Check | Local result |
|---|---|
| `.venv/bin/pytest -q` and `.venv/bin/python -m pytest -q --disable-warnings` | Both reported 1427 passed, 1 skipped, 1 deselected, 100 subtests passed. Optional Bedrock dependency was absent; the live DeepSeek test was deselected. |
| Governance cases exercised in the suite | 15 cases. Temporary Git repositories and simulated PR reviews cover approval of a tests-only draft, missing or ineligible reviewers, late review, app code already present, changed tests/fixtures, and safety ADR/current-head review. |
| `.venv/bin/python scripts/check_governance.py --base main` | Passed schema, layout, permission synchronization, local credential-pattern scan and PR check against committed refs. The PR diff check uses Git commits; the subprocess tests exercised nonempty temporary PR histories. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python -m mypy scripts/check_governance.py scripts/check_github_test_approvals.py` | Passed for both scripts. |
| `.venv/bin/python -m pip check` | Passed. |
| Workflow YAML and `git diff --check` | Passed locally. The `same-PR reviews` job is only configured on PR and PR review events. |

The first static round exposed import formatting and a mypy duplicate-module
error after the verifier switched to a package import. Imports were formatted
and `scripts/__init__.py` gives both scripts one module identity. The final
checks above passed with those changes.

Pending rollout: a real GitHub PR run must verify review-event triggering and
the GitHub response shape. A maintainer must confirm required checks (including
`same-PR reviews`) and independent review in branch protection before relying on
the flow. The user removed the legacy approval registry and its obsolete entry
from both OpenCode permission files. Those edits were reviewed in the diff; the
recorded local test results predate the human cleanup and were not rerun at the
user's direction. At handoff, the changes were staged on `D`; OpenCode's explicit
Git command deny blocked the authorized commit, so publication was handed back
to the user. The complete active OpenCode session still requires TUI export and
human annotation.
