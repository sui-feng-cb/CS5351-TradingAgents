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
