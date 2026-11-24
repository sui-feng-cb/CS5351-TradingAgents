# CS5351 TradingAgents Enhancement

This repository preserves the upstream Tauric Research TradingAgents baseline
and adds four supervised enhancement workstreams. TradingAgents is an AI-based
research and analysis framework; this project does not promise financial returns
or provide broker execution.

## Baseline and scope

- Upstream: https://github.com/tauricresearch/tradingagents
- Baseline commit: `9fa1196fffbcfd9de5146d2dd2869df84ab99838`
- Contribution boundary and source mapping: [`docs/baseline.md`](docs/baseline.md)
- FR-D/NFR-D now have a local team-mode eligibility implementation in the D
  branch, and FR-C/NFR-C are implemented locally on the C branch (47 C cases;
  the implementation PR's independent review is pending, and the
  reused-custom-report-directory policy is still to confirm). A and B
  implementation code is merged into `main`; each module's acceptance status
  follows its own record. Local offline regressions pass; remote CI and
  independent review remain pending before merge. See
  [`docs/req/requirements.yaml`](docs/req/requirements.yaml) and
  [`docs/architecture/trace-matrix.md`](docs/architecture/trace-matrix.md).

## Architecture and layout

The Python application is kept in `src/tradingagents/` and `src/cli/`. Course
requirements and architecture are under `docs/`; `test/offline/` contains
deterministic tests, `test/live/` contains explicitly marked API tests, and
`test/fixtures/` contains sanitized samples. The root architecture pointer links
to [`docs/architecture/architecture-blueprint.md`](docs/architecture/architecture-blueprint.md).

## Python 3.13 setup

The project uses the upstream `pyproject.toml` production/dev dependency set.
Runtime dependencies are unchanged; schema validation, type checking and their
YAML/type-stub helpers are additional development-only governance tools.
From the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple -e '.[dev]'
```

Copy `.env.example` to a local, untracked `.env` and configure only the provider
credentials needed for explicitly approved live runs. Never commit credentials.

## Tests and checks

```bash
python scripts/check_governance.py
python -m pytest -q
python -m pytest test/live -m integration  # only when a live test is approved
python -m ruff check .
python -m mypy scripts/check_governance.py
python -m pip check
```

The `pytest` default excludes integration-marked tests. `main.py` starts a real
analysis and is not an offline smoke-test command.

To opt into the deterministic D eligibility gate for a run, use
`tradingagents --decision-mode team`; the default `standard` mode preserves the
upstream decision path. Team mode records trusted market-evidence metadata and
publishes `REVIEW` with stable reason codes when analyst execution, critical
evidence freshness/status or the final five-tier rating fails qualification.
Python callers use `TradingAgentsGraph(decision_mode="team", ...)`. The pure
`evaluate_eligibility` function is team-only and returns an immutable decision.
Detailed contracts and actual validation results are in
[`docs/architecture/interface-contracts.md`](docs/architecture/interface-contracts.md)
and [`docs/verification/d-eligibility.md`](docs/verification/d-eligibility.md).

The initial A–D scope and course obligations are in
[`docs/reference/project-requirements.md`](docs/reference/project-requirements.md)
and [`docs/reference/module-acceptance.md`](docs/reference/module-acceptance.md).
Full initialization evidence and remaining gaps are in
[`docs/verification/initialization.md`](docs/verification/initialization.md).

### Run manifests and local query (FR-C)

Status: implemented locally on this branch (47 C acceptance cases); the
implementation PR still needs an independent non-C review, and the
reused-custom-report-directory policy remains to be confirmed.

Every CLI analysis attempt writes one `run_manifest.json` to its own attempt
directory under the results root:

```
<results_dir>/<ticker>/<YYYY-MM-DD>/runs/<uuid>/run_manifest.json
```

A same-day rerun gets a new UUID and its own directory, so both records are
kept. Report paths inside the manifest are **relative to the results root** (or
`null` when no report was saved). A read-only query lists runs by ticker and/or
date:

```
tradingagents manifest query --results-dir ~/.tradingagents/logs \
  --ticker NVDA --date 2026-09-23 --json
```

`--json` prints one object with `matches` (each carrying `ticker`, `trade_date`,
`status`, `reports`, `manifest_path`) and `warnings` (per-file problems it
skipped). The query is read-only: it never starts an analysis, backtest or data
vendor, and never modifies or deletes a report. A declared-but-missing report is
reported in `warnings` while the record is still returned. The machine-readable
schema is
[`docs/architecture/run-manifest-v1.schema.json`](docs/architecture/run-manifest-v1.schema.json)
and the contract is in
[`docs/architecture/interface-contracts.md`](docs/architecture/interface-contracts.md).

FR-C is implemented locally on this branch (47 C acceptance cases). Local
verification and the NFR-C local timing baseline are in
[`docs/verification/c-manifest.md`](docs/verification/c-manifest.md). The
implementation PR still needs an independent non-C review, and the
reused-custom-report-directory policy remains to be confirmed.

## GitHub and gates

The intended team repository is https://github.com/sui-feng-cb/CS5351-TradingAgents.
All four modules use [GitHub Flow with recommended test-first review](docs/testing/test-approval-process.md):
develop on a feature branch, validate locally, and merge one independently reviewed PR
after required CI passes. Human approval of the plan/test intent before application
implementation remains part of the supervised workflow. A same-PR GitHub test-plan
review is useful evidence but is not a required CI check. Safety-critical changes
still require an independent current-head review and an ADR. The intended `main`
branch protection policy requires project CI, independent review and the
safety-review check, with no direct pushes. Remote settings remain unverified;
their availability depends on the repository plan.
