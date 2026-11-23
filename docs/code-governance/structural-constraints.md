# Structural constraints

ADR-001: one upstream application copy under src; CLI imports public services,
domain agents use existing dataflows rather than importing vendor SDKs directly.
Each new architecture element has exactly one owning module, defined in AGENTS.
New modules/functions reference requirement/ADR/invariant IDs in docstrings or
adjacent documentation. No cyclic imports or copy-pasted upstream replacements.

INV-D / ADR-002 require the team-mode gate to set the authoritative final
structured rating before the graph publishes its final state; adapters may not
re-derive a rating from candidate prose. The pure D evaluator belongs to
`src/tradingagents/enhancements/eligibility.py`; coordinated graph, CLI, state,
report and settlement integration remains subject to independent review.
The local implementation adds typed snapshot provenance in the Yahoo snapshot
module, a team-only graph evidence/gate path, CLI stream filtering, report
metadata, state-log fields and exclusion of team-mode `REVIEW` from pending
memory settlement. These additions do not replace upstream behavior in standard
mode and remain under build/integration review.
INV-B requires source metadata to be authoritative over model citations. The
upstream layering regression remains mandatory; relocating tests must not make it
silently inspect an empty directory. Interface and security changes need ADRs and
human review. Packaging moves preserve CLI resource files and test assertions.
