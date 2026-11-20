---
name: pytest-entrypoint-imports
description: Use when pytest console collection cannot import repository scripts while python -m pytest succeeds in the CS5351 src-layout project.
---

# Repository scripts and pytest entry points

## Cause and fix

The installed src packages include `tradingagents` and `cli`, not repository
maintenance `scripts`. `python -m pytest` places the current directory on the
import path; the `pytest` console script need not do so. In this project, declare
`pythonpath = ["."]` under `[tool.pytest.ini_options]` so repository imports work
with both entry points. This setting affects tests only, not application packaging.

## Actual verification

- Before the fix, `.venv/bin/pytest -q test/offline/test_governance_gates.py`
  reproduced `ModuleNotFoundError: scripts`.
- After the fix, `.venv/bin/pytest -q --disable-warnings`: 1415 passed,
  1 skipped, 1 deselected, 100 subtests passed.
- `.venv/bin/python -m pytest -q test/offline/test_governance_gates.py`: 3 passed.
- Ruff, mypy for both governance scripts and the governance validator passed.

Always verify with the command used by CI; do not only change CI to conceal a
different local entry-point behavior. The remote rerun is pending publication.
See BUG-001, BASE-01, QUA-01 and `docs/verification/initialization.md`.

## Session evidence

The complete native session checkpoint is retained locally at
`transcripts/raw/initialization-session.json` and refreshed at session completion.
It is ignored pending privacy review; final TUI `/export` and human annotations
remain separate. The user first requested a local-only repair and subsequently
explicitly authorized commit and push.
