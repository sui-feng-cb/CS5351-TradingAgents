# Significant bugs

## BUG-001 — CI pytest entry point cannot import governance scripts

- Symptom: GitHub Actions fails during collection of
  `test/offline/test_governance_gates.py` with `ModuleNotFoundError: scripts`.
- Reproduction: `.venv/bin/pytest -q test/offline/test_governance_gates.py`
  failed locally with the same collection error before the fix.
- Category/root cause: test configuration and validation gap. The installed src
  packages exclude repository-level `scripts/`. `python -m pytest` adds the
  working directory to the import path; the console `pytest` entry point does not.
  Initialization checked the former, whereas CI runs the latter.
- Fix: set `pythonpath = ["."]` in `[tool.pytest.ini_options]`. Pytest resolves
  this against its project root, independently of the invocation entry point.
  Neither application packaging nor test assertions are changed.
- Evidence: `.venv/bin/pytest -q --disable-warnings` passed with 1415 passed,
  1 skipped, 1 deselected and 100 subtests; `python -m pytest` passed all three
  governance tests. Ruff, mypy and governance validation passed.
- Exposed gap: BASE-01/QUA-01 verification must include the actual CI test command,
  rather than infer console-script behavior from `python -m pytest` success.
- State: locally verified; the user subsequently authorized commit and push.
  Remote CI confirmation remains pending.
