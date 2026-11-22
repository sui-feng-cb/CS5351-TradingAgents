# CS5351 process report — working outline

Status: initialization draft, not the completed D6 submission.

## Team and contributions

| Member | Name | Student ID | Effective contribution evidence | Relative weight |
|---|---|---|---|---|
| A | Pending | Pending | Pending | Not assessed |
| B | Pending | Pending | Pending | Not assessed |
| C | Pending | Pending | Pending | Not assessed |
| D | Pending | Pending | Pending | Not assessed |

Final relative weights must average 1.0. Do not assume equal contribution.

## Requirements and ambiguity resolution

Document FR/NFR evolution, source requirements, acceptance and volatility.

### D: eligibility gate design review

The user approved the proposed explicit team decision mode, trusted evidence
derived from the actual market snapshot, and exclusion of `REVIEW` decisions
from the pending settlement/reflection queue. Reviews will distinguish candidate
model ratings from the authoritative result. The feature test suite still needs
independent approval before implementation; no feature results are claimed here.

### D implementation-session blueprint and baseline (2026-11-22)

The user approved the D module execution blueprint and then requested development
to begin. Work is underway on the D test-first stage in the local `D` worktree;
no application feature code or remote synchronization has occurred. The user
subsequently authorized a tests-only commit, non-force push to `origin/D` and
draft PR for independent test review. The user later confirmed that remote D was
removed; a read-only ref check found only `origin/main`. The local commit command
was blocked by the execution environment, so no commit, push or PR is claimed.
The tests-only changes remain staged; details are in
`docs/verification/d-eligibility.md`.
The proposed `standard`/`team` mode, typed evidence status, reuse of the upstream
10-calendar-day OHLCV freshness bound and review-notice behavior are recorded in
[ADR-002](docs/architecture/adr/002-deterministic-eligibility-gate.md) and remain
subject to independent test/safety review. The approved blueprint is not being
treated as approval of these detailed acceptance tests.

Pre-change baseline on the project `.venv` (Python 3.13.18): full pytest reported
1427 passed, 1 skipped, 1 deselected; governance, Ruff, mypy for the governance
script and pip dependency consistency checks passed. The skipped test requires
the optional `langchain_aws` dependency; one live test was deselected. These are
baseline results only, not D feature verification.

The active session has not yet been exported or annotated. The reviewer approval
of D's tests-only change, D implementation/build review, final verification,
independent safety review and integration review remain pending. The actual
tests-only red baseline is recorded in `docs/verification/d-eligibility.md`.
Track the test contract in
[`docs/testing/d-eligibility-test-plan.md`](docs/testing/d-eligibility-test-plan.md)
and actual run records in
[`docs/verification/d-eligibility.md`](docs/verification/d-eligibility.md).

The tests-only draft now includes a pure status/date/rating matrix, CLI mode and
review-message checks, report and settlement assertions, and team-mode graph
conflict cases. The focused acceptance suite reports 32 expected failures and 2
independent checks passed against the absent implementation; the two new graph
team-mode integration tests also fail at the expected missing constructor
contract. The prior offline regression suite passed with only these new
acceptance cases excluded (1427 passed, 1 skipped, 2 deselected, 100 subtests).
This is evidence that the tests detect missing behavior, not feature
verification. The independent test review remains pending before application
code.

## Architecture and integration

Explain alternatives, ADD iterations, boundaries, interface decisions and the
distinction between upstream baseline, layout migration and substantive changes.

## Human–agent supervision

Link real plans, approvals, interventions, rejected outputs and annotated sessions.

### Team-wide process decision (A–D, GOV-01)

During the D planning session, the agent proposed separate test, registry and
implementation PRs. The user rejected manual approval bookkeeping, directed all
four modules to use ordinary GitHub Flow, and authorized the local migration.
Tests and feature code now progress through a single draft-to-ready feature PR.
The test-plan review is recorded first on the test commit; the final GitHub
approval is recorded separately after local verification and passing CI. This
keeps ordinary integration steps while preserving evidence of human
supervision. See the [shared procedure](docs/testing/test-approval-process.md)
and the `GOV-FLOW-001` entry in [the AI-use log](docs/ai-use-log.yaml).

## Verification and process quality

Include actual structural/regression/behavior results, defect trends, cost and
timing measurements, CI blocking evidence and branch-protection evidence.

The [workflow migration verification](docs/verification/github-flow.md) records
local results and the remaining GitHub checks before rollout.

## Co-evolution, rework and lessons

Show how requirements, architecture, code and tests changed together and what
human reviewers caught that the coding agent missed.

## Individual reflections

A, B, C and D each add a genuine 300–500 word reflection with name/student ID.
No reflections or contribution scores have been fabricated at initialization.

Final D6: a single Markdown report, at most 10,000 words excluding diagrams,
more than 15 pages at 12-point single spacing; confirm rendering with the course.
