# Requirement trace matrix

All planned feature tests below are targets, **not existing passing evidence**.

| Requirement | Component / ADR | Planned test/evidence | Runtime observation | State |
|---|---|---|---|---|
| FR-A,NFR-A | comparison / ADR-001 | test_comparison normal and either ticker failing | per-ticker statuses, saved reports | Planned |
| FR-B,NFR-B | events / ADR-001, INV-B | test_events ID/schema negatives; fixed semantic pairs | validated/dropped references | Planned |
| FR-C,NFR-C | `src/tradingagents/enhancements/manifest.py`, coordinated CLI/graph/report adapters (team-confirmation: A/Python run-link, backtest coverage, reused custom path) / ADR-001, SEC-01 | `test/offline/test_manifest.py`: two fixed samples schema, success/failure write, CLI error, null/missing report, same-day rerun, filters + no match, bad JSON/unknown version resume, secrets, unsafe path, real Typer query with no analysis/vendor; `test/benchmarks/bench_manifest_query.py` for 1,000-manifest three-process timing (<=2s proposed) | query warnings, match sets and per-run elapsed time | Test contract pending independent non-C review; implementation planned |
| FR-D,NFR-D | `src/tradingagents/enhancements/eligibility.py`, coordinated graph/evidence/CLI/report/settlement adapters / ADR-002, INV-D | `test/offline/test_eligibility.py`: pure status/date/rating matrix and Buy-vs-invalid-evidence conflict; graph, report, CLI and settlement boundary | decision mode, evidence status/date, analyst status, final rating and ordered reason codes | Test contract pending independent review; implementation planned |
| BASE-01 | upstream src / baseline commit | migrated upstream regression suite | upstream date guards | Baseline |
| SEC-01 | metadata/export policy, INV-SECRET | credential-pattern and export review | blocked leak reports | Draft policy |
| GOV-01 | AGENTS/Prompt/CI; [same-PR review](../testing/test-approval-process.md) | test_governance_gates; actual GitHub run and branch protection pending | test-plan review SHA, PR status checks, final approval | Local governance migration |
| QUA-01 | requirement schema / CI | scripts/check_governance.py | schema failure status | Initialized check |
