# Requirement trace matrix

All planned feature tests below are targets, **not existing passing evidence**.

| Requirement | Component / ADR | Planned test/evidence | Runtime observation | State |
|---|---|---|---|---|
| FR-A,NFR-A | comparison / ADR-001 | test_comparison normal and either ticker failing | per-ticker statuses, saved reports | Planned |
| FR-B,NFR-B | events / ADR-001, INV-B | test_events ID/schema negatives; fixed semantic pairs | validated/dropped references | Planned |
| FR-C,NFR-C | manifest / ADR-001 | test_manifest malformed input and 1,000-record timer | query warnings and elapsed time | Planned |
| FR-D,NFR-D | eligibility / ADR-001, INV-D | test_eligibility Buy/invalid-evidence conflict | REVIEW reasons in all outputs | Planned |
| BASE-01 | upstream src / baseline commit | migrated upstream regression suite | upstream date guards | Baseline |
| SEC-01 | metadata/export policy, INV-SECRET | credential-pattern and export review | blocked leak reports | Draft policy |
| GOV-01 | AGENTS/Prompt/CI | test_governance_gates; GitHub approval API checks untested remotely | PR status checks | Partial initialization |
| QUA-01 | requirement schema / CI | scripts/check_governance.py | schema failure status | Initialized check |
