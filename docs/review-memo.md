# PR Reviews

For each actual PR, record the reviewer, repository, PR URL and number, base/head
commits, scope, requirement and architecture alignment, code/test quality,
operational metadata, safety, efficiency and verification evidence. Findings must
be ordered by severity and include file/line references where applicable. Finish
with exactly one of `APPROVE`, `CHANGES REQUIRED` or `REJECT`, together with the
rationale. Do not self-approve safety changes or backdate approval to satisfy CI.

## PR #2

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2
- **Reviewer:** OpenCode, read-only review requested by the user
- **Reviewed head:** `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`
- **Base:** `main`
- **Date:** 2026-11-22
- **Scope:** Tests-first D eligibility-gate contract covering FR-D, NFR-D,
  INV-D and GOV-01. No application implementation is included in the PR.

### Alignment

The PR is aligned with the proposed team-mode eligibility boundary and adds a
literal status/date/rating test matrix, graph safety cases, CLI/report/state
expectations and process documentation. The intended boundary is consistent with
ADR-002, the interface contract proposal and INV-D. The PR correctly leaves the
application module unimplemented pending independent test-plan approval.

### Findings

1. **P1: Required independent test-plan approval is absent.** The PR is marked
   ready rather than draft, has no GitHub reviews, and its own description says
   that non-D review is pending. The documented flow requires a review whose first
   line is `Test-Plan-Approved: <full SHA>` before implementation or final review.

2. **P1: No positive team-mode graph integration test exists.** The test plan
   specifies D-INT-01, but the PR only adds unavailable-evidence and missing-market-
   analyst cases. Both new team-mode graph tests fail at construction because
   `TradingAgentsGraph` does not yet accept `decision_mode`; there is no test that
   valid evidence and an allowed rating pass through the graph and become the
   authoritative final result.

3. **P1: CLI tests do not prove that `decision_mode` reaches the graph.** The
   assertion in `test/offline/test_eligibility.py` only checks the `flags` passed to
   `run_analysis`. It does not check `TradingAgentsGraph` construction or the run
   configuration, so the option could be discarded after the CLI callback.

4. **P1: The stream path is not tested for candidate-rating leakage.** The
   eligibility contract requires gating before publication, but the fake graph in
   `test/offline/test_eligibility.py` emits only one final state. It cannot detect
   a `Buy` candidate being displayed in an earlier stream chunk before the gate
   replaces it with `REVIEW`.

5. **P1: The Buy-conflict negative matrix is incomplete.** The verification rules
   require a model `Buy` paired independently with each blocked analyst, evidence
   and snapshot-date condition. The PR covers one combined pure case and one
   unavailable-evidence graph case, but not every blocked condition.

6. **P2: The verification record is stale.**
   `docs/verification/d-eligibility.md` still states that `gh` was unavailable and
   that no commit, push or PR existed, although PR #2 and its head commit now
   exist. The record needs a follow-up entry with the actual PR and CI state.

### Verification evidence

- `.venv/bin/python scripts/check_governance.py`: passed.
- `.venv/bin/python -m pytest test/offline/test_eligibility.py -q`: `32 failed,
  2 passed` against the intentionally absent implementation.
- New team-mode graph tests: both failed at the missing `decision_mode` constructor
  parameter.
- Prior offline regression excluding the deliberately red new cases: `1427
  passed, 1 skipped, 2 deselected, 100 subtests passed`.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check`: passed.
- Remote governance, same-PR reviews, clean-install and Ruff checks: passed.
- Remote `tests (py3.13, America/New_York)` checks: failed.

### Decision

**CHANGES REQUIRED.** The tests-first scope is directionally appropriate, but the
PR cannot proceed as a ready PR until independent test-plan approval is recorded,
the missing positive and boundary tests are added, stale verification metadata is
corrected, and the required checks are green or the deliberately red tests-only
stage is explicitly kept as a draft under the documented workflow.

## PR #2 Re-review

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2
- **Reviewer:** OpenCode, read-only re-review requested by the user
- **Reviewed head:** `f4be027ebbc43c3226c63209b743cf7482711556`
- **Previous reviewed head:** `0448de2b0e7ff1aa06f1ed2a61f91dca292a81db`
- **Base:** `main`
- **Date:** 2026-11-22
- **Scope:** Re-review of the tests-only corrections for FR-D, NFR-D, INV-D and
  GOV-01. No application implementation is included.

### Re-review result

The previous implementation/test findings are resolved within the approved
tests-first scope:

1. A positive team-mode graph case now verifies valid evidence, the actual
   preceding-trading-day snapshot, an allowed rating and an empty reason list in
   `test/offline/test_graph_end_to_end.py:158-176`.
2. CLI forwarding is covered from command invocation through
   `TradingAgentsGraph` construction in `test/offline/test_eligibility.py:162-215`,
   including the standard-mode control and the `team` value.
3. Candidate-rating leakage is covered both at the real graph stream boundary in
   `test/offline/test_graph_end_to_end.py:228-255` and at the CLI live-display
   boundary in `test/offline/test_eligibility.py:218-307`.
4. The negative matrix now pairs candidate `Buy` independently with all 16
   analyst, evidence, snapshot-date and analysis-date failure variants in
   `test/offline/test_eligibility.py:53-83`.
5. The verification record now distinguishes historical initial-PR facts from
   the latest PR metadata and records the revised local validation in
   `docs/verification/d-eligibility.md:90-127`.

No new code-quality or test-design blocker was found in the revised tests-only
change. The intentionally failing acceptance tests are appropriate for a
tests-first contract because `src/tradingagents/enhancements/eligibility.py` and
the coordinated graph/CLI integration have not yet been implemented.

### Verification evidence

- `.venv/bin/python -m pytest -q --tb=no --disable-warnings`: `36 failed, 1430
  passed, 1 skipped, 1 deselected, 100 subtests passed`; all failures are in the
  new D tests-first cases.
- `.venv/bin/python scripts/check_governance.py --base main`: passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check`: passed.
- Remote governance, same-PR reviews, clean-install and Ruff checks: passed.
- Remote `tests (py3.13, America/New_York)` checks: failed only on the expected
  unimplemented D acceptance cases.
- The PR remains tests-only; no application stub, skip, expected-failure marker or
  CI exclusion was added to hide the unimplemented behavior.

### Decision

**APPROVE.** The revised tests-only contract satisfies the findings from the
previous review and is ready for the next tests-first workflow step. This approval
is limited to the revised test contract and its supporting evidence. It is not an
approval of application implementation, the proposed safety behavior, merge, or
settlement integration.

The repository still requires the documented independent non-D GitHub Comment
review with the exact first line `Test-Plan-Approved: f4be027ebbc43c3226c63209b743cf7482711556`.
The current GitHub PR has no submitted reviews, so this memo entry must not be
used as a substitute for that human approval or represented as a GitHub approval.

## PR #3 · D 模块决策资格门

- 仓库与审查对象 [sui-feng-cb/CS5351-TradingAgents #3](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/3)
- 审查人 OpenCode，2026-11-22
- 基线 `main` / `b5e6663c790b244b099051aee46549e1a9e51069`
- 审查提交 `D` / `a8d60b660251b83c886bbf00b30ddd75f83bf528`
- 范围 FR-D、NFR-D、INV-D、BASE-01，覆盖行情证据、图与 CLI 输出、报告、状态日志及结算边界。

### 架构与测试

纯资格判断、显式 `team` 模式和复用现有 10 日时效政策均符合 ADR-002 的设计方向。`standard` 仍为默认模式，无新增运行时依赖。PR #2 的两份验收测试文件保持原样。现有负例主要覆盖状态与日期以及 Portfolio Manager 候选字段，下面三个离线场景补充了真实加载器、非结构化模型输出与公开图流的边界覆盖。

### 审查发现

1. **P1 — 无效收盘价可通过关键证据检查。** 用当天收盘价为 `+inf` 的模拟供应商响应走真实 `load_ohlcv`，`dropna` 保留了该值，快照适配器仅凭行日期返回 `valid`。完整团队模式运行输出权威 `Buy`，并产生 1 条待结算记录。请在生成有效证据状态前校验关键行情值，明确拒绝非有限收盘价，并补充从加载器到 `REVIEW`、待结算条目为零的回归用例。 [行情加载器](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a8d60b660251b83c886bbf00b30ddd75f83bf528/src/tradingagents/dataflows/vendors/yahoo/ohlcv.py#L252) · [证据适配器](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a8d60b660251b83c886bbf00b30ddd75f83bf528/src/tradingagents/dataflows/vendors/yahoo/snapshot.py#L78)
2. **P1 — 自由文本回退把不合规评级转换成可交易评级。** 在行情有效、模型不支持结构化输出时，Portfolio Manager 首行给出 `Rating: Strong Buy`，后文引用 `Consensus rating: Buy`。上游启发式解析返回 `Buy`，资格门收到的已是合法值。离线运行发布 `Buy`，理由为空，并写入 1 条待结算记录。请保留 `standard` 的兼容解析，并让 `team` 校验模型自己的确切评级字段。缺失或不合规时应产生 `REVIEW` 和 `invalid_rating`，同时覆盖正文引用合法评级的负例。 [自由文本回退](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a8d60b660251b83c886bbf00b30ddd75f83bf528/src/tradingagents/agents/managers/portfolio_manager.py#L85) · [团队候选节点](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a8d60b660251b83c886bbf00b30ddd75f83bf528/src/tradingagents/graph/setup.py#L199)
3. **P1 — 公开图流提前发出 Trader 的买入提案。** `stream_run()` 在团队模式中过滤了 Portfolio Manager 的候选键，但直接转发 `trader_investment_plan`。离线模拟证据不可用时，公开流在 `eligibility_checked=False` 的帧中发出 `**Action**: Buy`，最后一帧才返回 `REVIEW` 并清空该字段。直接订阅 Python 图流的调用方已经收到了可执行提案。请在图流边界暂扣该字段，只在资格通过后发布，并扩展现有图流测试逐帧检查。 [公开图流](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a8d60b660251b83c886bbf00b30ddd75f83bf528/src/tradingagents/graph/trading_graph.py#L520)

### 验证与交付记录

- `gh pr checkout 3 --repo sui-feng-cb/CS5351-TradingAgents --detach` 拉取的提交与远端 PR head 一致。`gh pr checks 3 --repo sui-feng-cb/CS5351-TradingAgents` 显示 Python 3.13 测试、治理、全仓 Ruff、干净安装均通过。按本次委托，`same-PR reviews` 不计入代码审查结论。该检查的日志显示缺少实现前的独立测试评审记录。 [CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45018083314) · [评审检查日志](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45018083313/job/137194642929)
- 本地 Python 3.13.18，`TZ=America/New_York .venv/bin/python -m pytest -q --tb=short` 得到 1470 passed、1 skipped、1 deselected、100 subtests passed。以 PR 基线运行 `scripts/check_governance.py --base` 通过，`ruff check .`、`mypy scripts/check_governance.py` 和 `pip check` 均通过。
- 完整 PR 的 `git diff --check` 仅在原始 transcript 中报告行尾空白与文件末尾空行，排除 `transcripts/raw/` 后通过。发布记录可顺手把 PR 描述里的 `CS5531` 链接修正为实际仓库，并交叉链接已上传的原始会话与对应注释。 [PR #2](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2)

### 决定

**CHANGES REQUIRED**。请修复上述三项 P1 并增加独立的离线回归覆盖。前两项会给出不应发布的权威评级并写入结算队列，第三项会在资格结果发布前暴露交易提案。

## PR #3 implementation response — 2026-11-22

This is the author's repair record requested by the user, not an independent
re-review or a replacement verdict. The original CHANGES REQUIRED above remains
the last review conclusion until the corrected head is reviewed.

1. Finding 1: the team snapshot metadata adapter now rejects a nonfinite or
   unusable latest Close. Regressions retain the real OHLCV loader, inject vendor
   history with positive/negative infinity and assert REVIEW plus zero pending
   entries. A finite-price control verifies that eligible Buy still succeeds.
2. Finding 2: team PM free-text fallback now uses complete own-rating fields with
   exact five-tier values; quoted consensus cannot replace a missing or invalid
   own rating. Paired full-graph standard controls retain the upstream heuristic.
3. Finding 3: public `stream_run` withholds Trader proposals in values/task states
   until successful qualification. The original negative stream test is
   strengthened frame-by-frame; a positive case requires release after the gate.

The new regressions reproduced the findings before fixes. A separate SQLite
regression also reproduced reuse of a pre-fix Buy candidate on resume; versioning
the team checkpoint signature prevents that reuse. The current full local suite
reports 1512 passed, 1 skipped, 1 deselected and 100 subtests passed; final
commands/results and session references are in `docs/verification/d-eligibility.md`.
The updated PR text uses the correct CS5351 repository URL. Existing raw exports
are indexed separately from the current correction session, whose complete TUI
export remains pending; no export or approval is fabricated. No remote review,
PR edit, push or merge was performed by this correction task.

## PR #3 复审 · 2026-11-22

- 审查人 OpenCode。范围为 FR-D、NFR-D、INV-D、BASE-01 和 ADR-002。 [PR #3](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/3)
- 基线 `b5e6663c790b244b099051aee46549e1a9e51069`，上轮提交 `a8d60b660251b83c886bbf00b30ddd75f83bf528`，本轮提交 `a99b017c7f65e7d0792b0b28dff20a9e136acc73`。

### 上轮问题复验

- 真实 OHLCV 加载器路径上的正负无穷收盘价均得到 `REVIEW`，没有待结算条目。正常收盘价的对照仍输出 `Buy`。
- `Strong Buy` 或缺少自身评级的输出，即使引用 `Consensus rating: Buy`，在 `team` 模式也得到 `REVIEW` 和 `invalid_rating`。`standard` 对照仍使用上游兼容解析。
- 公开图流在证据不可用时逐帧隐藏 Trader 提案，在资格通过后才发布提案。SQLite 回归也验证了新版不会沿用旧检查点的未校验候选评级。

### 本轮发现

1. **P1 — Markdown 代码示例仍可被当作 Portfolio Manager 自己的评级。** 当输出没有自身评级、只在四空格缩进的代码块里示例 `Rating: Buy` 时，正则允许前导空白并把它识别为评级。围栏实现也只切换布尔状态，外层波浪号围栏内的反引号行会被误当作结束标记。用 CommonMark 确认两种输入均是代码块后，以有效行情和非结构化模型走完整离线图。两例都发布了权威 `Buy`，理由为空，并各生成 1 条待结算记录。普通围栏示例的对照返回 `REVIEW`，真实评级行的对照继续通过。请将评级提取限制在可作为正式评级的字段，排除缩进代码块并按围栏字符和长度识别闭合。两种负例均应返回 `REVIEW` 和 `invalid_rating`，且待结算条目为零。 [评级解析器](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/a99b017c7f65e7d0792b0b28dff20a9e136acc73/src/tradingagents/agents/rating.py#L106)
2. **P2 — 远端 PR 描述的仓库链接仍有笔误。** 作者修复记录称 PR 描述已更正。`gh pr view` 读到的远端描述仍将 PR #2 链接指向 `CS5531-TradingAgents`，请更新为正确的仓库地址。 [PR #3](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/3) · [正确的 PR #2 链接](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/2)

### 验证结果

- `gh pr checkout 3 --repo sui-feng-cb/CS5351-TradingAgents --detach` 拉取并确认了本轮提交。`gh pr checks 3 -R sui-feng-cb/CS5351-TradingAgents` 显示测试、治理、Ruff 与干净安装通过。按委托，`same-PR reviews` 不计入结论。该任务日志报告缺少实现前的独立测试评审记录。 [CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45022313068) · [评审任务](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45022313094/job/137207717515)
- Python 3.13.18 下使用 `TZ=America/New_York .venv/bin/python -m pytest -q --tb=short --disable-warnings` 得到 1512 项通过、1 项跳过、1 项未选中、100 个子测试通过。对 `test_team_rating.py`、`test_eligibility_adapter.py`、`test_graph_end_to_end.py` 使用 `-k 'team or typed'` 得到 46 项通过、19 项未选中。
- 以 PR 基线运行 `.venv/bin/python scripts/check_governance.py --base b5e6663c790b244b099051aee46549e1a9e51069` 通过。全仓 Ruff、治理脚本 mypy、`pip check` 和本轮提交差异的 `git diff --check` 均通过。

### 决定

**CHANGES REQUIRED**。上轮的具体复现均已解决，代码示例仍可产生权威 `Buy` 并进入待结算队列，违反 FR-D 和 INV-D。请修复这一评级来源问题并补充完整图回归。

## PR #3 re-review repair response

The user requested fixes for the findings at `a99b017`. The team parser now uses
CommonMark block structure instead of toggling a fence flag. Both reported
code-only inputs return `REVIEW` with `invalid_rating` and zero pending entries
in the full offline graph; an actual `Hold` after a closed example still qualifies.
Team checkpoint policy v3 also prevents reuse of candidates from the old parser.

The remote PR #3 description's PR #2 URL was corrected in place. GitHub returned
the correct `CS5351-TradingAgents` link and confirmed the old URL is absent.
Local verification is recorded in `docs/verification/d-eligibility.md`. This
author response does not replace the recorded re-review verdict.

## PR #3 复审 · `29ce124` · 2026-11-22

- 审查范围为 FR-D、NFR-D、INV-D、BASE-01 和 ADR-002。基线为
  `b5e6663c790b244b099051aee46549e1a9e51069`，审查提交为
  `29ce124e3096e6ee4972bed0248a0df78e74d77d`。
  [GitHub 复审评论](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/3#issuecomment-7079866044)
- 上轮的缩进代码块和混合围栏用例均得到 `REVIEW`、`invalid_rating` 和零待结算条目。
  PR 描述中的 PR #2 链接已更正。
- **P1** `rating.py` 跳过含跨行行内代码的整段。有效行情下，第一段的
  `Rating: Strong Buy` 被跳过，后续段落的 `Rating: Buy` 成为权威评级并新增一条待结算记录。
- **CHANGES REQUIRED**。保留同段可见的评级字段，并用完整图覆盖冲突拒绝和合法评级通过。

### 本轮修复记录

CommonMark 解析现在保留真实换行的源位置，并屏蔽行内代码消耗的源换行。
冲突场景返回 `REVIEW` 和 `invalid_rating`，待结算条目为零。合法 `Hold` 对照通过并生成一条待结算记录。
团队检查点升级至 v4，旧候选评级会重新计算。完整本地结果与远端 CI 重跑记录见
[D 验证日志](verification/d-eligibility.md)。以上是本地修复证据，修复后的提交待独立复审。

## Future review records

Every subsequent PR review must append a dated section using the same structure:

1. Repository, PR URL/number, reviewer, base commit and reviewed head SHA.
2. Scope plus requirement, ADR, invariant and architecture alignment.
3. Findings ordered by severity, with file/line references and concrete fixes.
4. Code/test quality, operational metadata, safety and efficiency observations.
5. Exact local and remote verification commands with real results.
6. A final `APPROVE`, `CHANGES REQUIRED` or `REJECT` decision and rationale.

Review conclusions must be recorded here after each actual PR review. GitHub review
submission, approval and merge remain separate actions and must not be implied by
this memo.
