# CS5351 process report — working outline

Status: initialization draft, not the completed D6 submission.

## D PR #3: independent review and corrective verification — 2026-11-22

The PR #3 review reproduced three INV-D failures at implementation head
`a8d60b6` even though its existing suite passed 1470 tests: an infinite close
was accepted as critical evidence, a free-text Strong Buy or missing own rating
was replaced by a quoted consensus Buy, and the public graph stream exposed
the Trader proposal before qualification. The first two scenarios published
actionable ratings and pending decisions; the third leaked a transient proposal.
The user requested code repairs, testing, staging and template PR text.

Regressions were written before production changes and produced 34 failures and
20 passes across graph/parser suites, including 28 absent-parser cases. The repair
validates finite latest Close at the trusted team adapter, uses exact model-owned
free-text rating fields in team mode while preserving standard heuristic parsing,
and withholds public stream proposals until eligibility succeeds. A positive
finite-price control and eligible stream-release assertion keep the repair from
passing by rejecting or hiding every result. Existing negative assertions were
retained and the original stream check was strengthened frame-by-frame. A
separate SQLite test reproduced `Buy` on resume from a pre-fix checkpoint; a
versioned team signature now forces evidence and candidate checks to run again.

Both final full runs passed **1512 tests and 100 subtests**, with 1 optional AWS
skip, 1 live-test deselection and 24 existing warnings; one run used the console
pytest entry point in America/New_York. Ruff, governance, governance-script mypy,
pip and correction diff checks passed. No prompt/model/runtime dependency was
changed. This provides evidence for the concrete repairs, not a self-approval of
the corrected PR. The original review conclusion remains CHANGES REQUIRED until
re-review, and missing historical approval evidence has not been fabricated or
bypassed. AI-use entry `D-ELIG-PR3-FIX-001`, the D verification log and separate
correction-session annotations track the intervention and actual results.

## D implementation and verification update — 2026-11-22

The user confirmed that the revised tests-only PR #2 was squash-merged into main
and D was updated. The user then approved the concrete implementation blueprint
and requested uninterrupted implementation, D1–D9 records, local validation and
staging, with commit/push left to manual commands. Earlier sections preserve the
historical tests-first work and must not be read as current feature status.

FR-D/NFR-D now have a local deterministic evaluator and team-mode graph integration.
The graph acquires typed snapshot metadata independently of the market analyst,
records actual analyst execution status, stages the Portfolio Manager candidate,
and publishes only the qualification result as the final rating. Missing/invalid
execution, evidence, date or rating produces `REVIEW` with stable ordered reasons.
CLI streaming, completion output, Markdown/HTML reports and JSON state logs use
that result; a rejected Trader action is withheld and a team `REVIEW` does not
enter pending settlement/reflection. Standard remains the default; the team
checkpoint identity is separate. No runtime dependency was added.

Implementation verification exposed two presentation/publication defects first:
the completion notice omitted `REVIEW`, and the blocked full report retained a
Trader Buy proposal. Both were fixed. Full regression then found mode-attribute
compatibility in bare graph fixtures, snapshot-call compatibility and two existing
CLI fixtures whose exact flags needed the new literal default mode. The approved
D acceptance tests were retained unchanged. A final inspection removed a temporary
freshness-bypass option: stale loader exceptions carry only the actual snapshot
date to the gate, while the existing price freshness guard continues to reject
stale rows. Supplemental adapter checks cover those provenance and execution paths.

The final full local run reported **1470 passed, 1 skipped, 1 deselected and
100 subtests passed** on Python 3.13.18. The skip is the optional AWS dependency;
the deselected test is live. The actual CI console pytest entry point also passed
with identical counts in `America/New_York`. Ruff passed; governance, mypy for the governance
script, pip consistency and diff checks are recorded with their actual scope in
`docs/verification/d-eligibility.md`. The fixed tested negative set had zero
observed bypasses; no universal safety claim or remote CI result is inferred.

D1–D9 artifacts and real interventions are cross-linked from `D-ELIG-IMPL-001` in
the AI-use log. The full active-session TUI export is still unavailable through
the tool interface and must be performed by the user; annotations are separate
and are not a substitute transcript. Independent safety, verification and
integration reviews remain pending. AGENTS.md's obsolete build-status wording
could not be refreshed because its edit was denied by the tool permission rules;
that follow-up is recorded without modifying permissions. No new human review,
identity, contribution score or completed export was invented.

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
no application feature code is included. The local changes were staged as a
tests-only draft, and the user subsequently submitted PR #2 at head
`0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`. The read-only review concluded
`CHANGES REQUIRED`; review findings and remote check status are in
`docs/review-memo.md`. The user directed us to address the test findings locally
and provide commit/push commands, not to execute publication.
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

The initial tests-only draft included a pure status/date/rating matrix, CLI mode and
review-message checks, report and settlement assertions, and team-mode graph
conflict cases. The focused acceptance suite reports 32 expected failures and 2
independent checks passed against the absent implementation; the two new graph
team-mode integration tests also fail at the expected missing constructor
contract. The prior offline regression suite passed with only these new
acceptance cases excluded (1427 passed, 1 skipped, 2 deselected, 100 subtests).
This is evidence that the tests detect missing behavior, not feature
verification. The independent test review remains pending before application
code.

### PR #2 review-driven test revision (2026-11-22)

The review requested a valid team-mode graph integration test, proof that the
CLI selection reaches graph construction, a stream-path assertion that catches
pre-gate candidate-rating exposure, and an independent `Buy` conflict case for
each blocked analyst/evidence/date condition. These test corrections and the
corresponding interface/test-plan entries are prepared locally. The new positive
case checks the actual preceding trading day's snapshot date. The CLI mode test
runs the command's real selection/configuration setup and intercepts graph
construction before model/data initialization. Two stream checks verify that
rejected PM candidate content does not escape through graph output or live CLI
decision panels. A fixed-width plain console corrected an unrelated terminal-wrap
false failure while retaining the required report text assertions.

The full revised suite reported 1430 passed, 36 failed, 1 skipped, 1 deselected,
and 100 subtests passed. The 36 failures are all D's acceptance cases against
unimplemented behavior, including an observed live-panel candidate leak; the
prior offline regression suite passed in the same run. Governance, Ruff, mypy
and pip consistency checks passed. Fresh read-only GitHub metadata still shows
PR #2 ready, with no reviews; the test failures belong to its previous published
head, not this uncommitted revision. The original review was preserved, and the
user will commit/push these changes and return the PR to draft. No application feature code is included;
independent non-D approval of the revised tests remains required before
implementation.

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
