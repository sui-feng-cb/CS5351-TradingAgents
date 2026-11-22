# Significant bugs

## BUG-D-003 — PR #3 found three qualification bypasses beyond the original suite

- Requirements: FR-D, NFR-D, INV-D, BASE-01; ADR-002.
- Review baseline: `a8d60b660251b83c886bbf00b30ddd75f83bf528`.
- Evidence validity: `dropna` retains infinite Close values; an adapter using only
  the row date marked them valid. Real-loader graph regressions with `+inf` and
  `-inf` reproduced actionable Buy. The adapter now requires a finite critical
  Close before valid metadata; finite-price control preserves the positive path.
- Rating authority: the upstream free-text heuristic skipped invalid/missing own
  ratings and accepted consensus Buy. Team mode now validates complete own fields
  exactly; paired standard-mode tests preserve upstream heuristic behavior.
- Publication: the public stream filtered PM candidates but forwarded Trader Buy
  before qualification. Both values/task projections now withhold that proposal
  until eligible completion; strengthened negative and positive stream tests
  prevent the transient leak and an always-withhold implementation.
- Recovery: a pre-fix SQLite checkpoint could resume at the gate with an old Buy
  candidate and trusted-looking evidence. The new team signature forces fresh
  qualification; the recovery regression reproduced Buy before the signature fix.
- Tests were added before fixes. The initial graph/parser run reported 34 failed,
  20 passed (28 failures were the absent exact parser). The first repaired D
  subset passed 93 tests. After finite-price control and invalid-price adapter
  coverage and the checkpoint regression, the full suite passed 1512 tests and 100 subtests. Details and final
  static checks are recorded in the D verification log; re-review is pending.

## BUG-D-001 — secondary proposal and completion notice obscured REVIEW

- Requirements: FR-D, NFR-D, INV-D; ADR-002.
- Reproduction: the first implementation run of `python -m pytest
  test/offline/test_eligibility.py test/offline/test_graph_end_to_end.py -q`
  reported 2 failed, 52 passed. The completion notice contained only "Review"
  instead of the authoritative `REVIEW`; the complete report retained the
  Trader's structured Buy action after gate rejection.
- Root cause: the new gate changed the final PM fields, while two existing
  presentation paths still presented upstream output semantics.
- Fix: completion output explicitly shows `REVIEW` and reasons; rejected team
  results clear the public Trader proposal and reports/CLI withhold it.
- Evidence: original D assertions remained unchanged; focused run subsequently
  passed all 54 cases, and full local regression later passed 1470 tests and
  100 subtests. Remote CI and independent review pending.

## BUG-D-002 — standard-path compatibility during team-mode integration

- Requirements: BASE-01, FR-D; ADR-001/002.
- The initial full implementation run had 25 failures: bare graph fixtures
  lacked the new attribute, snapshot calls added an unnecessary keyword, and
  two exact CLI flag dictionaries did not yet include the new default mode.
- Fix: preserve standard defaults for old/bare instances and normal loader call
  shape; add the literal `decision_mode: standard` to the two legacy CLI
  expectations without removing existing assertions. The original D acceptance
  files remain unchanged. A 208-test affected regression subset passed, followed
  by full local regression. See the D verification log for actual commands.

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
