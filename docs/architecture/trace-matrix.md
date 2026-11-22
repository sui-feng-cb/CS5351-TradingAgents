# Requirement trace matrix

A–C entries remain targets. D's local passing evidence is recorded in
`docs/verification/d-eligibility.md`; remote CI and independent review are pending.

| Requirement | Component / ADR | Planned test/evidence | Runtime observation | State |
|---|---|---|---|---|
| FR-A,NFR-A | comparison / ADR-001 | test_comparison normal and either ticker failing | per-ticker statuses, saved reports | Planned |
| FR-B,NFR-B | events / ADR-001, INV-B | test_events ID/schema negatives; fixed semantic pairs | validated/dropped references | Planned |
| FR-C,NFR-C | manifest / ADR-001 | test_manifest malformed input and 1,000-record timer | query warnings and elapsed time | Planned |
| FR-D,NFR-D | `src/tradingagents/enhancements/eligibility.py`, coordinated graph/evidence/CLI/report/settlement adapters / ADR-002, INV-D | `test/offline/test_eligibility.py`, `test_eligibility_adapter.py`, `test_team_rating.py` and graph cases: status/date/rating matrix, nonfinite prices, exact own ratings, stream publication, checkpoint recovery, CLI/reports/state/settlement | decision mode, evidence status/date, analyst status, final rating and ordered reason codes | PR #3 corrections: 1512 local tests and 100 subtests passed, 1 skip and 1 live deselection; corrected head awaits remote CI and non-D safety/integration review |
| BASE-01 | upstream src / baseline commit | migrated upstream regression suite | upstream date guards | Baseline |
| SEC-01 | metadata/export policy, INV-SECRET | credential-pattern and export review | blocked leak reports | Draft policy |
| GOV-01 | AGENTS/Prompt/CI; [same-PR review](../testing/test-approval-process.md) | test_governance_gates; actual GitHub run and branch protection pending | test-plan review SHA, PR status checks, final approval | Local governance migration |
| QUA-01 | requirement schema / CI | scripts/check_governance.py | schema failure status | Initialized check |
