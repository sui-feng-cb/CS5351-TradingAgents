# Runtime policies

Status: D policies have a local implementation under review; A–C policies remain
proposed. Preserve upstream behavior in standard decision mode.

| Trigger | Action | Evidence |
|---|---|---|
| One A ticker fails | preserve other result; error row for failed ticker | per-ticker status/error code |
| B no data / provider unavailable | distinguish unavailable from no common event; skip model on empty input | source availability |
| B model timeout/invalid schema | return explicit failure; no invented grouping | error, call count |
| B invalid evidence reference | discard unverified group | validation reason |
| C malformed/unsupported manifest | warn and continue query; never modify file | skipped path/reason |
| D standard mode | Preserve upstream behavior; do not apply the team eligibility gate | recorded decision mode |
| D team mode: market analyst not selected/not run/failed | Do not publish a candidate rating; finalize as REVIEW if the graph can complete, otherwise fail closed | analyst status and `market_analyst_not_run` / `market_analyst_failed` |
| D team mode: evidence missing/not run/unavailable, invalid metadata, future/stale snapshot, or invalid rating | Deterministic gate sets authoritative REVIEW before final state publication; replaces final decision text and excludes it from pending settlement/reflection | ordered reason codes, evidence status and snapshot date |
| D team mode: latest critical Close is nonfinite/missing/nonnumeric | Reject the evidence before emitting valid metadata; gate uses existing unavailable-evidence reason | `market_evidence_unavailable`; real-loader and adapter regressions |
| D team mode: free-text own rating missing/invalid/conflicting but consensus quotes an allowed rating | Keep own-field validation exact; do not substitute quoted consensus | `invalid_rating`; team/standard paired regression |
| D public stream before qualification or after rejection | Withhold Trader proposal and internal PM candidate keys; release proposal only on eligible completion | frame-by-frame negative and positive stream tests |
| D team checkpoint made before the PR #3 corrections | Start a fresh run rather than reuse evidence or ratings accepted by the old checks | versioned team signature and SQLite recovery regression |
| Optional analyst unavailable | approved partial-output policy, explicit warning | partial status |
| Credentials detected in shared artifacts | stop publication and human incident review | redacted diagnostic |
