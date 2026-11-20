# ADR-001: preserve upstream and extend a src layout

Status: proposed; initialization work authorized by the repository setup request.
Feature contracts and safety logic await human approval.

## Alternatives and rationale

Keep root packages (smallest diff but fails target D8 layout), nest a second
repository (duplicate boundaries and deployment ambiguity), or migrate packages
once into src and retain imports (selected). Preserve all upstream regression
assertions, only adapting path-based fixtures and separating the real-API class.

Consequences: editable installs/package discovery and resources must be verified;
Git rename history exposes structural work separately from substantive changes.
Reopen if the course requires a different layout or installation regressions appear.

## AI context design proposal

For B: identity/task, standing constraints, trusted schema and evidence-ID map,
untrusted dated news blocks, bounded session state, then current request. Filter
window, deduplicate, assign IDs, cap 3 tickers × 5 records, trim snippets, prioritize
evidence, budget and assemble. Propose 8,000 input tokens and 1,500 output tokens;
compact at 80% input budget. These values await provider-specific measurement.
Never compact away evidence IDs, date/ticker mapping, invariant rules or schema;
re-inject them after every compaction and reject references to dropped evidence.
No cross-run news memory is required for the MVP.

Coding-agent context starts at AGENTS/Prompt and the requirements/ADR/invariants;
after compaction reload these authoritative files and pending approval state.
Skills are navigational summaries, not substitutes for current specifications.
