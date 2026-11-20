# Initialization verification log

Status: initialization validation record, pending human review. A passing setup
check is not feature acceptance or proof of remote CI/branch protection.

## Environment

- Target: Python 3.13.18 installed in project-local `.python` and `.venv`.
- Baseline commit: `9fa1196fffbcfd9de5146d2dd2869df84ab99838`.
- Team remote configured locally as `origin` at the requested GitHub URL.
- Official source remote configured locally as `upstream`.

## Commands and current state

| Command/check | Result |
|---|---|
| `git fetch --unshallow upstream` | Completed; upstream history and tags fetched. |
| `python3.13` availability | Installed locally as Python 3.13.18 through project-local uv. |
| `.venv/bin/python --version` | Python 3.13.18. |
| `uv sync --frozen --extra dev` | Installed locked project dependencies using the project-configured Tsinghua PyPI index. |
| `python scripts/check_governance.py` | Passed registry/schema, required layout, package path and OpenCode permission synchronization; credential-pattern scan found no matches. |
| Upstream original-layout suite using project interpreter | **1412 passed, 1 skipped, 1 deselected**, 100 subtests passed; measured after migration against untouched upstream checkout with the same interpreter/dependencies. It was not a pre-migration test run. |
| Migrated upstream suite | **1412 passed, 1 skipped, 1 deselected**, 100 subtests passed. Optional `langchain_aws` skip and the live DeepSeek deselection preserve upstream behavior. |
| Migrated suite including bootstrap governance tests | **1415 passed, 1 skipped, 1 deselected**, 100 subtests passed. |
| Byte comparison against baseline | All **95** upstream production package/resource files match their relocated copies exactly. |
| `.venv/bin/tradingagents --help`, import and resource smoke | Passed; CLI welcome text and package logo were found. No analysis/API call started. |
| Wheel build and clean installation | Built `tradingagents-0.7.1-py3-none-any.whl`, installed without dev extras in a separate project-local smoke venv via Tsinghua, and verified package/CLI imports plus both packaged resources. |
| Live test collection | One genuine DeepSeek integration test collected; not executed. |
| `python -m ruff check .` | Passed with upstream lint rule set and Python 3.11 target. |
| `python -m mypy scripts/check_governance.py scripts/check_github_test_approvals.py` | Passed. |
| Dependency consistency | `uv pip check --python .venv/bin/python` passed for 103 packages; pip was seeded into the project venv from the Tsinghua index. |
| `opencode debug config` | Project config resolved with project instruction files, default agent `plan`, sharing disabled and deny/ask tool rules. |
| `opencode debug skill` | Project `session-artifacts` skill discovered. |
| Native session export | `opencode export ses_e0ab8ff10ffe92mYjsfDqVYjYY` saved a complete native JSON snapshot to `transcripts/raw/initialization-session.json` (local/ignored pending privacy review). This is the session through export time; final TUI `/export` Markdown and human annotations remain pending. |
| remote GitHub read | No permission error observed during initial `git ls-remote`; no push attempted. |
| remote branch protection | Not checked/configured; requires GitHub administration. |

The root `.python-version` and project metadata target Python 3.13; the upstream
Ruff Python 3.11 target is retained deliberately so initialization does not force
style-only rewrites of baseline source. New development-only dependencies are
jsonschema, mypy, PyYAML and their stubs. Production dependencies are unchanged.
`pyproject.toml`/`uv.lock`, local venv pip.conf and workflow PIP_INDEX_URL use the
Tsinghua index; server/global pip configuration was not edited.

## Known migration work

The package/CLI were moved once from root paths to `src/tradingagents` and
`src/cli`; upstream tests were moved to `test/offline`, with the genuine DeepSeek
API test separated into `test/live/` while preserving its assertion. Three
path-sensitive upstream tests were adapted without changing their assertions.
Production package files retain exact baseline bytes. No application feature is
implemented. New bootstrap governance tests cover schema/config and two negative
PR cases. One intermediate bootstrap run failed because mock Git output used
newline delimiters after the scanner switched to NUL-separated paths; fixing the
test fixture's delimiter restored the checks without weakening production logic.

## Limitations requiring human review

- Features A–D, their approved test plans and module interfaces remain planned.
- Semantic prompt/model changes are blocked until the human-reviewed dataset and
  actual evaluation runner are connected; no synthetic benchmark is asserted.
- Type checking covers the two new governance scripts, not all upstream code.
- Permission JSON and resolved configuration were checked; no adversarial harness
  containment test has been run. Shell remains subject to human approval.
- GitHub API approval checks/workflows have not run on the remote; no PR, human
  review or branch-protection setting is claimed. The approval-registry procedure
  needs team review before feature PRs begin.
- Report.md is an outline; student identities, reflections, contribution weights
  and five annotated session records must be completed by the actual team.
