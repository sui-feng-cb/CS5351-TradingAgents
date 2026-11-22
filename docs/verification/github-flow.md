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

## Current policy update (2026-11-23)

The user authorized implementation of ADR-003. The former `same-PR reviews`
workflow has been replaced by a safety-only review workflow: same-PR test-plan
review evidence is advisory, while safety-critical PRs still require an ADR and
an independent approval of the current head. The historical results above record
the workflow that ran at that time; they are not current validation of the
replacement workflow. Current local validation results are recorded after this
section.

| Check | Result for ADR-003 changes |
|---|---|
| `.venv/bin/python -m pytest -q test/offline/test_governance_gates.py` | 11 passed. Includes ordinary feature PRs without same-PR review evidence and safety-specific ADR/current-head review negatives. |
| `.venv/bin/python -m pytest -q` | 1532 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed. The skip requires optional `langchain_aws`; the live test remains deselected. |
| `.venv/bin/python scripts/check_governance.py` | Passed registry/schema, course layout, permission synchronization and credential-pattern scan. |
| `.venv/bin/python -m ruff check .` | Passed. |
| `.venv/bin/python -m mypy scripts/check_governance.py scripts/check_github_safety_reviews.py` | Passed. |
| `.venv/bin/python -m pip check` | Passed. |
| YAML parsing and `git diff --check` | Passed for workflows, requirements/AI-use log and working diff. |
| GitHub branch-protection and ruleset API reads | Both returned HTTP 403 stating the private-repository plan does not enable these features. No remote settings were inspected or changed; rollout remains unresolved. |

Pending rollout: a real GitHub PR run must verify safety-review event triggering
and the GitHub response shape. Remote protection settings remain unverified and
unchanged because GitHub returned HTTP 403 for both branch-protection and ruleset
API reads on this private repository. Once settings are available, remove
`same-PR reviews` from required checks and require the safety-review status and
independent review.

The legacy approval registry and its obsolete entry were removed from both
OpenCode permission files in the earlier workflow migration. Those edits were
reviewed in that migration; its recorded local results predate the human cleanup.
That earlier worktree handoff and export status are historical. The complete
active session for this ADR-003 change still requires a human TUI `/export` and
annotation.
