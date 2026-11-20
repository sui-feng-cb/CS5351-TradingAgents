# Runtime policies

Status: proposed for enhancements; preserve upstream error handling meanwhile.

| Trigger | Action | Evidence |
|---|---|---|
| One A ticker fails | preserve other result; error row for failed ticker | per-ticker status/error code |
| B no data / provider unavailable | distinguish unavailable from no common event; skip model on empty input | source availability |
| B model timeout/invalid schema | return explicit failure; no invented grouping | error, call count |
| B invalid evidence reference | discard unverified group | validation reason |
| C malformed/unsupported manifest | warn and continue query; never modify file | skipped path/reason |
| D critical evidence not run/missing/unavailable/future, invalid rating | authoritative REVIEW in CLI, report and structured result | reason codes |
| Optional analyst unavailable | approved partial-output policy, explicit warning | partial status |
| Credentials detected in shared artifacts | stop publication and human incident review | redacted diagnostic |
