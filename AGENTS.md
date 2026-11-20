# CS5351 development entry point

Read `Prompt.md`, `.opencode/rules.md`, `.agent/rules.md`, `docs/baseline.md`,
`docs/req/requirements.yaml`, the architecture blueprint, ADRs, invariants,
interface contracts and verification constraints before planning a change.

## Current build target

This repository initially contains the upstream TradingAgents implementation in
a `src/` layout and draft course artifacts. FR-A through FR-D are **planned**,
not implemented. Initialization is authorized by the user's request; feature
implementation, requirement freezing and publication require subsequent review.
Do not represent this authorization as approval of future feature tests or PRs.

## Ownership and boundaries

| Owner | Planned module | Requirements |
|---|---|---|
| A | `src/tradingagents/enhancements/comparison.py` | FR-A, NFR-A |
| B | `src/tradingagents/enhancements/events.py` | FR-B, NFR-B |
| C | `src/tradingagents/enhancements/manifest.py` | FR-C, NFR-C |
| D | `src/tradingagents/enhancements/eligibility.py` | FR-D, NFR-D; coordination |

These are reserved paths, not empty implementations to be counted as features.
Shared contracts live in `docs/architecture/interface-contracts.md`. Integration
changes to `src/cli/`, graph state or reporting require coordinated review.
Preserve the upstream package names, license, tests and behavior. Every new
module/function documents its applicable requirement, ADR and invariant.

Validate with `python scripts/check_governance.py`, `python -m pytest`,
`python -m ruff check .`, `python -m mypy scripts/check_governance.py`, and
`python -m pip check` using the project Python 3.13 environment. Never invoke
`main.py` as a smoke test: it initiates a model/data analysis.

Do not commit, push or change remote branch protection until the user approves.
The requested future commit message is `Chore: initialize CS5351-TradingAgents`.
Save reusable session outcomes as project skills and preserve complete session
exports as explained in `transcripts/README.md`. Never invent exports or reviews.
