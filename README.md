# CS5351 TradingAgents Enhancement

This repository preserves the upstream Tauric Research TradingAgents baseline
and adds four supervised enhancement workstreams. TradingAgents is an AI-based
research and analysis framework; this project does not promise financial returns
or provide broker execution.

## Baseline and scope

- Upstream: https://github.com/tauricresearch/tradingagents
- Baseline commit: `9fa1196fffbcfd9de5146d2dd2869df84ab99838`
- Contribution boundary and source mapping: [`docs/baseline.md`](docs/baseline.md)
- A–D requirements are currently planned, not implemented: see
  [`docs/req/requirements.yaml`](docs/req/requirements.yaml) and
  [`docs/architecture/trace-matrix.md`](docs/architecture/trace-matrix.md).
- Feature implementation is gated on human approval of the relevant plan and
  tests. Initialization is not a claim that feature work or all CI gates are done.

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

The initial A–D scope and course obligations are in
[`docs/reference/project-requirements.md`](docs/reference/project-requirements.md)
and [`docs/reference/module-acceptance.md`](docs/reference/module-acceptance.md).
Full initialization evidence and remaining gaps are in
[`docs/verification/initialization.md`](docs/verification/initialization.md).

## GitHub and gates

The intended team repository is https://github.com/sui-feng-cb/CS5351-TradingAgents.
All four modules use [GitHub Flow and same-PR test review](docs/testing/test-approval-process.md):
develop on a feature branch, validate locally, and merge one reviewed PR after CI
passes. Start with a draft containing tests and documentation. GitHub review history
provides test-first evidence; the project governance workflow checks it before merge.
The semantic evaluation gate still applies where relevant. Configure branch protection
on GitHub to require CI and independent review on `main`, with no direct pushes.

The course code and `demo.mp4` deadline is 2026-11-25 23:59 HKT (UTC+8); submit
the video separately from the project ZIP. The classroom PPT is due internally
on 2026-11-30. Do not include API keys in source, history, reports, transcripts,
slides, video or screenshots.
