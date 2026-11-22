# Invariant register

Status: target rules awaiting feature implementation; no feature tests yet exist.

| ID / source | Rule | Planned enforcing component | Verification | Fallback |
|---|---|---|---|---|
| INV-B / NFR-B | All published evidence references belong to current inputs and match ticker/date | events validator | fabricated/cross-run ID and metadata mismatch tests | Discard invalid group and return validation error |
| INV-D / FR-D,NFR-D, ADR-002 | In team mode, no invalid/missing critical market evidence or invalid rating can publish an actionable final decision; model prose cannot override the gate | deterministic eligibility graph node, trusted evidence adapter, CLI/report/state adapters and settlement boundary | `test/offline/test_eligibility.py`: each failed precondition and Buy-vs-invalid-evidence conflict must fail if any output is actionable | Set authoritative `final_rating=REVIEW`, replace public decision text with a review notice and ordered reason codes, and omit it from pending settlement/reflection |
| INV-SECRET / SEC-01 | No credentials in shared artifacts | allowlisted metadata, review, CI secret scan | seeded fake credential pattern test and artifact review | Block merge/export and remediate; rotate any real leaked key |
| INV-ASOF / BASE-01 | Preserve upstream date/point-in-time constraints | upstream date_window/tools | upstream date/lookahead regressions | Withhold unsupported/future data |
