---
name: repository-initialization
description: Use when creating or reviewing the CS5351-TradingAgents repository baseline, D1-D9 scaffolding, Python 3.13 environment, or upstream src/test migration.
---

# CS5351 repository initialization

## Scope

Create a reviewable, single-history upstream baseline plus clearly labeled course
scaffolding. Do not implement FR-A–D, record fictional approvals or evidence,
commit or push before explicit human approval.

## Baseline and layout

- Upstream: `https://github.com/tauricresearch/tradingagents`
- Baseline: `9fa1196fffbcfd9de5146d2dd2869df84ab99838`
- Team remote: `https://github.com/sui-feng-cb/CS5351-TradingAgents`
- Preserve all original Git history; configure upstream and origin locally.
- Relocate the sole packages to `src/tradingagents` and `src/cli`; tests to
  `test/offline`, with genuine API-only checks in `test/live`.
- Keep upstream README in `docs/upstream/README.md`; update local image paths.
- Use Python 3.13 and the upstream runtime/development dependency set. Resolve
  and install using the repository's Tsinghua PyPI index and `uv.lock`.

## Initialized artifacts

The repository has D1 registry/schema; D2 architecture, ADR, contracts, invariants,
trace matrix, memory, permissions, runtime policy and evaluation table; D3 rules,
manifest and loaded OpenCode project config; D4 verification, review/debt/bug logs;
D5 transcript instructions; D6 report outline; D7 upstream CI plus project
governance workflow; D8 source/test layout; D9 Prompt.md. These are scaffolding,
not evidence that features, remote branch protection, student contribution records,
or D5 submissions are complete.

## Actual checks recorded

- Python 3.13.18 local interpreter and `.venv` created.
- Dependencies resolved from `https://pypi.tuna.tsinghua.edu.cn/simple/`.
- `python scripts/check_governance.py`: passed registry/schema/layout/config checks
  and the basic credential-pattern scan.
- `uv pip check --python .venv/bin/python`: 103 packages compatible.
- Original upstream suite: 1412 passed. Migrated suite plus 3 bootstrap governance
  cases: 1415 passed, 1 skipped (optional Bedrock dependency), 1 deselected (live
  DeepSeek API test), 100 subtests passed. All 95 relocated production files
  match baseline bytes. CLI/import/static-resource smoke passed.
- Ruff passed; mypy passed for both governance scripts.
- Wheel build and a production-only clean wheel install passed import/resource
  smoke checks in a separate project-local venv.
- `opencode debug config` resolved the project configuration and instructions;
  default agent is plan and project sharing is disabled. `opencode debug skill`
  found this skill and the session-artifacts skill.
- Initial `git ls-remote origin` returned without a permission error and no refs;
  no push, commit or branch-protection changes were attempted.
- A native `opencode export` snapshot exists locally in
  `transcripts/raw/initialization-session.json`, excluded from Git pending privacy
  review. Final TUI Markdown `/export` and human annotations remain to be completed;
  do not relabel the native JSON backup as a TUI Markdown export.

See `docs/verification/initialization.md` for the validation record and
remaining checks. Update this skill only from actual future results.

## Publication authorization

The user subsequently approved upload with “批准上传”. Commit the reviewed
initialization using `Chore: initialize CS5351-TradingAgents` and push only main
to the specified origin. Inspect staged scope, secret scan, remote refs and Git
identity first; verify local/remote hashes afterward. Do not publish the ignored
native session backup or environment/tooling directories.
