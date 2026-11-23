# Requirement trace matrix

A–C entries remain targets. D's local passing evidence is recorded in
`docs/verification/d-eligibility.md`; remote CI and independent review are pending.

| Requirement | Component / ADR | Planned test/evidence | Runtime observation | State |
|---|---|---|---|---|
| FR-A,NFR-A,INV-A | comparison / ADR-001 | `test/offline/test_comparison.py`: two successes, either ticker failing, both failing, save failure, input validation, A-XTALK no-cross | per-ticker statuses, saved reports, comparison Markdown/manifest | Planned; contract frozen 2026-11-23; tests-first in progress |
| FR-B,NFR-B | events / ADR-001, INV-B | test_events ID/schema negatives; fixed semantic pairs | validated/dropped references | Planned |
| FR-C,NFR-C | `src/tradingagents/enhancements/manifest.py`, `src/cli/main.py` (lazy `manifest query`), `src/cli/run.py` (run recording), `src/cli/console.py` (team-confirmation: A/Python run-link, backtest coverage, reused custom path) / ADR-001, SEC-01 | `test/offline/test_manifest.py` (47 cases: schema/validation, write, CLI run recording, query, filters, bad-record tolerance, secrets, unsafe paths, result-root boundary scan, CLI startup regression); `test/benchmarks/bench_manifest_query.py` for the 1,000-manifest three-process timing | full offline suite 1579 passed; query warnings/match sets; local WSL 1.889/1.837/1.808 s, 137 matches | Implemented locally; formal NFR-C acceptance (CI runner + ≤2 s) and a few contract confirmations pending |
| FR-D,NFR-D | `src/tradingagents/enhancements/eligibility.py`, coordinated graph/evidence/CLI/report/settlement adapters / ADR-002, INV-D | `test/offline/test_eligibility.py`, `test_eligibility_adapter.py`, `test_team_rating.py` and graph cases: status/date/rating matrix, nonfinite prices, exact own ratings, stream publication, checkpoint recovery, CLI/reports/state/settlement | decision mode, evidence status/date, analyst status, final rating and ordered reason codes | PR #3 corrections: 1512 local tests and 100 subtests passed, 1 skip and 1 live deselection; corrected head awaits remote CI and non-D safety/integration review |
| BASE-01 | upstream src / baseline commit | migrated upstream regression suite | upstream date guards | Baseline |
| SEC-01 | metadata/export policy, INV-SECRET | credential-pattern and export review | blocked leak reports | Draft policy |
| GOV-01 | Prompt/CI; [recommended test-first review](../testing/test-approval-process.md); safety review / ADR-002 / INV-D | `test_governance_gates`; project CI; independent final review; dedicated safety review for safety paths | AI-use log, CI status, independent final approval; same-PR test review is optional evidence | Same-PR test approval is advisory; safety review remains required for safety-critical changes |
| QUA-01 | requirement schema / CI | scripts/check_governance.py | schema failure status | Initialized check |
