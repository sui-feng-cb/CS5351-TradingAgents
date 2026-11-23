# Invariant register

Status: INV-D has a local implementation and passing offline regression;
remote CI and independent safety review remain pending. Other planned features
remain unimplemented unless separately recorded.

| ID / source | Rule | Planned enforcing component | Verification | Fallback |
|---|---|---|---|---|
| INV-A / NFR-A | For input-valid same-day two-ticker comparisons, a failure in either ticker must not remove or overwrite the other ticker's successful report; the failed row must not carry an actionable rating; ticker-specific data must not cross rows | `src/tradingagents/enhancements/comparison.py` | `test/offline/test_comparison.py` A-FAIL/A-XTALK; tests name INV-A | Set failed row `final_rating`/`summary`/`report_path` to null; preserve the successful row; do not fill from another ticker |
| INV-B / NFR-B | All published evidence references belong to current inputs and match ticker/date | events validator | fabricated/cross-run ID and metadata mismatch tests | Discard invalid group and return validation error |
| INV-D / FR-D,NFR-D, ADR-002 | In team mode, no invalid/missing critical market evidence or invalid rating can publish an actionable final decision; model prose cannot override the gate | deterministic eligibility graph node, trusted evidence adapter, CLI/report/state adapters and settlement boundary | `test/offline/test_eligibility.py`, `test_eligibility_adapter.py` and team-mode graph integration cases; local results in `docs/verification/d-eligibility.md`; independent review pending | Set authoritative `final_rating=REVIEW`, replace public decision text with a review notice and ordered reason codes, and omit it from pending settlement/reflection |
| INV-SECRET / SEC-01 | No credentials in shared artifacts | allowlisted metadata, review, CI secret scan | seeded fake credential pattern test and artifact review | Block merge/export and remediate; rotate any real leaked key |
| INV-ASOF / BASE-01 | Preserve upstream date/point-in-time constraints | upstream date_window/tools | upstream date/lookahead regressions | Withhold unsupported/future data |
