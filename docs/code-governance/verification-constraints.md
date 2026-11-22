# Verification constraints

Every fit criterion has a test; every invariant has a violation-triggered failing
test. New tests name requirement/invariant IDs. Feature tests must be approved
before implementation. Keep expected outcomes independent of production logic.
Modules A–D follow the same [GitHub Flow](../testing/test-approval-process.md):
record test evidence on the draft PR before application code, run all offline
tests locally and in CI, and require independent final review before merging.

1. Structural: package/CLI imports, resource discovery, dependency/module boundary,
   permissions and requirement schema validation.
2. Regression: all previously established offline suites must pass each round.
3. Behavioral: frozen evidence-ID, REVIEW safety, recovery, timing and semantic
   grouping thresholds. Mock model output tests cannot prove real model quality.

B needs at least 20 human-labeled news pairs (10 positive/10 negative), pairwise
precision ≥0.80 and recall ≥0.70 under the approved model/evaluation procedure.
The evaluation dataset/runner and live credentials are not present at initialization;
model/prompt changes fail closed until approved, replayable evidence exists.
Feature acceptance tests, mutation checks and performance results are not claimed.

## D eligibility-gate test approval target

Before D application code, a non-D reviewer must approve the tests-only change as
described in [the shared GitHub Flow](../testing/test-approval-process.md). The
fixed negative matrix in `test/offline/test_eligibility.py` must include analyst
not-run/failure, absent/unknown/unavailable evidence, missing/malformed/future/
stale snapshot dates, invalid rating, multiple simultaneous failures, and a model
`Buy` conflicting with each blocked-evidence case. Expected ratings, reason-code
ordering and user-visible status are literals in tests, independent of production
helpers. Integration cases must assert graph output, CLI, Markdown/HTML, state-log
authority and exclusion of `REVIEW` from pending settlement/reflection. At least
one valid-rating/evidence case proves the gate permits eligible results; standard
mode proves baseline behavior is preserved. NFR-D passes only when the fixed
negative set reports zero actionable outputs and zero REVIEW settlement entries.

The proposal reuses the existing 10-calendar-day Yahoo OHLCV stale-data guard;
the tests pin 10 days as accepted and 11 days as stale. If ADR review changes this
boundary, revise and reapprove the tests before writing application code.

Record the baseline before moving packages and the migrated suite afterward.
Initialization authorizes structural path changes only. CI bootstrap checks do not
prove every D7 gate or remote branch protection is already operational.
