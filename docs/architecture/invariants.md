# Invariant register

Status: target rules awaiting feature implementation; no feature tests yet exist.

| ID / source | Rule | Planned enforcing component | Verification | Fallback |
|---|---|---|---|---|
| INV-B / NFR-B | All published evidence references belong to current inputs and match ticker/date | events validator | fabricated/cross-run ID and metadata mismatch tests | Discard invalid group and return validation error |
| INV-D / FR-D,NFR-D | Invalid critical market evidence cannot publish an actionable rating | eligibility gate and output adapters | model Buy with invalid evidence; CLI/report/result all REVIEW | Publish REVIEW with reasons, prevent actionable downstream use |
| INV-SECRET / SEC-01 | No credentials in shared artifacts | allowlisted metadata, review, CI secret scan | seeded fake credential pattern test and artifact review | Block merge/export and remediate; rotate any real leaked key |
| INV-ASOF / BASE-01 | Preserve upstream date/point-in-time constraints | upstream date_window/tools | upstream date/lookahead regressions | Withhold unsupported/future data |
