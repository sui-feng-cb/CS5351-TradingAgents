---
name: pr7-comparison-review
description: Reuse to review FR-A comparison adapters, partial failure, artifact content and upstream report identity.
---

# Review a same-day comparison

- Pin the PR head and merge base. For a merged PR compare the merge tree with the reviewed head and preserve existing local review edits. PR #7 head `ea49ffb` has the same tree as merge `c75bd98` and is based on `41e1b0b`.
- Read A-IC-001 and ADR-001. Exercise FR-A/NFR-A and INV-A through the public `run_comparison` surface. Use distinct ticker/date markers and inject mismatched state or saved path independently. Include a positive control using the upstream `TradingAgentsGraph.save_reports` implementation and its real filesystem writes.
- For SEC-01, inject synthetic provider and save exceptions containing sentinel credentials and account markers. Assert absence from the returned row, comparison Markdown and JSON. Assert that the successful report survives each injected failure direction.
- Use the upstream Portfolio Manager formatter for multiline summary fixtures. Check the complete selected section and verify folding, maximum length and fallback. Confirm asset routing against the real graph signature using both stock and crypto fixtures once the supported asset scope is confirmed.
- In an isolated worktree, `PYTHONPATH=src:.` selects the reviewed source when the environment's editable install points to the primary checkout. On PR #7, Python 3.13.18 returned 30 targeted passes and 1562 full-suite passes, with 29 pre-existing C failures. Local governance with base, Ruff, governance-script mypy, pip check and Git diff whitespace checks passed.
- See `docs/review-memo.md` and AI-use entry `REVIEW-PR7-001` for the findings and evidence. TUI `/export` is a user action in this tool session. Link the actual export after it exists.

## PR #8 follow-up review — 2026-11-23

- Input: PR #8, base `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`, head `094e2a700f56144551261bfcabc5e15bff3efcac`; A-IC-001 draft-0.4, FR-A/NFR-A/INV-A/SEC-01 and ADR-001/003. User requested local memo and copyable Markdown only.
- Verify attribution on the final resolved path that is actually published. A raw ticker-prefixed directory or `complete_report.md` filename can resolve through directory/file symlinks to another ticker or to `notes.md`. Exercise the public two-row entry and inspect returned rows, Markdown and JSON together, including preservation of the other report.
- For stock-only scope, test non-USD crypto (`BTC-EUR`, `ETH-GBP`, `BTC-JPY`) as well as normalized USD crypto, Forex/Futures/Index controls. A short suffix denylist is not evidence of complete asset classification.
- Outcomes: exception sanitization, state ticker/date rejection and multiline summary repaired; resolved report attribution (P1) and non-USD crypto rejection (P2) still fail. Verdict: CHANGES REQUIRED.
- Actual commands in an isolated pinned worktree using the project Python 3.13.18: `PYTHONPATH=src:. TZ=America/New_York <python> -m pytest test/offline/test_comparison.py -q --tb=line --disable-warnings` gave 38 passed; full default suite with `-q --tb=line --disable-warnings` gave 1570 passed, 29 existing C failures, 1 skipped, 1 deselected and 100 subtests passed. Governance `--base c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`, full Ruff, governance-script mypy, pip check and PR diff whitespace checks passed.
- Independent external probes `/tmp/opencode/test_pr8_review.py`: 5 failing negative cases and 6 passing controls (including actual upstream report writes and summary branches). This temporary file is not a tracked acceptance suite or durable transcript.
- Artifacts: `docs/review-memo.md` PR #8 section and AI-use entry `REVIEW-PR8-001`. No remote comment/review or publication. Full TUI export and actual transcript link remain pending; do not invent an export or D's amendment approval.
