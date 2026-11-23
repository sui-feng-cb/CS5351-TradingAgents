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

## PR #3 复审 · `9c53f95` · 2026-11-22

- 审查范围 FR-D、NFR-D、INV-D、BASE-01 和 ADR-002。基线为
  `b5e6663c790b244b099051aee46549e1a9e51069`，审查 head 为
  `9c53f95fae53ed75a984568a4e0007fd06ed4764`。
- **上一轮评级误判已修复。** 评级解析保留 CommonMark 可见换行的源位置，不再因跨行行内代码跳过整段。含冲突字段 `Rating: Strong Buy` 和后续 `Rating: Buy` 的完整离线图返回 `REVIEW`、`invalid_rating`，待结算记录为零。合法 `Rating: Hold` 与跨行代码示例并存时通过资格门，且只记录 `Hold`。
- 已覆盖普通与反斜线硬换行、多行代码值、行内注释及代码块之后的正式评级。团队检查点升级至 v4，避免复用旧解析策略保存的候选结果。上轮非有限价格、共识评级回退和图流提案提前发布问题均未回归。PR 描述中的 PR #2 链接正确。

### 验证结果

- Python 3.13.18，全量离线套件 `TZ=America/New_York .venv/bin/python -m pytest -q --tb=short --disable-warnings`：1536 passed、1 skipped、1 deselected、100 subtests passed。聚焦命令 `TZ=America/New_York .venv/bin/python -m pytest -q --tb=short test/offline/test_team_rating.py test/offline/test_graph_end_to_end.py -k 'multiline or code'`：19 passed、61 deselected。
- `.venv/bin/python scripts/check_governance.py --base b5e6663c790b244b099051aee46549e1a9e51069`、全仓 Ruff、`.venv/bin/python -m mypy scripts/check_governance.py`、`.venv/bin/python -m pip check`，以及源码、测试、文档变更的 `git diff --check` 均通过。
- GitHub 对应 head 的 Python 3.13 测试、治理、Ruff 和干净安装检查均通过。按此前约定，`same-PR reviews` 失败不计入代码结论。GitHub 当前没有已提交的 review；本备忘录记录的是本地复审判断。

### 决定

**APPROVE**。上一轮发现已修复，新增加的评级来源与硬换行回归通过，FR-D/NFR-D/INV-D 范围内未发现其他阻塞问题。此结论限于上述 PR head 的代码复审。

## PR #5 · C manifest/query tests-first review · 2026-11-23

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/5
- **Reviewer:** OpenCode，按用户请求进行只读代码/测试审查
- **Base:** `main` / `ecc2ff48d3575aa8c897b42ce0b50e8d7a51d92f`
- **Reviewed head:** `C` / `64f7bec36e91b83f976708ff5310966530596010`
- **Scope:** tests-and-docs-only pre-implementation contract for FR-C, NFR-C,
  SEC-01 and GOV-01. The PR contains no `src/tradingagents/enhancements/manifest.py`
  implementation and no CLI manifest command.

### Alignment and review boundary

The proposed API, v1 field list, per-run storage model, local read-only query,
warning-and-continue behavior, secret exclusion and versioned benchmark dataset
are aligned with FR-C/NFR-C, the C section of
`docs/architecture/interface-contracts.md`, INV-SECRET, ADR-001 and the C test
plan. Keeping application code out of this head is correct for the tests-first
stage. The 20 C failures are therefore expected reds and are not treated as
implementation defects.

The test contract is not yet strong enough for implementation or final approval.
The following findings are ordered by severity.

### Findings

1. **P1 — The unsafe-report-path test does not prove that an escaping path is
   not followed.** `test/offline/test_manifest.py:550-575` checks the returned
   ticker list, warning text and the returned match paths, but never observes
   access to `outside_secret.md`. An implementation can read the out-of-root
   file, then discard the record and return the expected AAPL match, and the
   test still passes. A review-only probe did exactly that and passed the test.
   Also, the declared `../../../outside_secret.md` does not resolve to the
   fixture file when resolved from the results root as the contract requires;
   `../outside_secret.md` would. Correct the fixture path and instrument the
   outside target (or use a failing read/open sentinel), asserting that no
   out-of-root file is opened while valid records and warnings remain checked.

2. **P1 — The CLI read-only contract is not tested.**
   `test/offline/test_manifest.py:582-612` checks exit status and output only;
   it does not snapshot the manifest/report bytes, modification times, or
   directory entries before and after the query. A command that overwrites the
   referenced report still passed the current test in a review-only probe. Add
   before/after content and filesystem-operation assertions, including that a
   query cannot write, delete, rename or rewrite a manifest/report.

3. **P2 — The schema tests do not test rejection of malformed records.**
   `test/offline/test_manifest.py:99-110` only validates the two fixed positive
   samples; the sole negative schema case at `:126-133` changes `status`.
   Consequently, a `validate_manifest` implementation that accepts extra or
   missing top-level fields, a non-UUID `run_id`, malformed dates/timestamps, or
   invalid `reports`/`error` shapes can still satisfy this suite. This does not
   independently enforce the frozen whitelist and type rules in
   `docs/architecture/interface-contracts.md:25-40` and
   `docs/testing/c-manifest-test-plan.md:25-47`. Add literal negative cases for
   at least an unknown key, a missing required key, malformed UUID/date/time,
   and invalid report/error shape; assert `ValueError` (or the approved public
   validation exception) for each. A review-only mutation probe confirmed that
   both fixed-sample tests pass with a no-op validator.

4. **P2 — Failed-run error-code and safe-message requirements are not asserted.**
   `test/offline/test_manifest.py:347-355` checks only that a file exists and
   has `status == "failed"`; it does not check the required fixed error code,
   safe message, or absence of traceback text. The test-plan row at
   `docs/testing/c-manifest-test-plan.md:73-75` explicitly requires those
   properties, and the interface contract forbids traceback blobs. A fake
   manifest containing only `{"status": "failed"}` passed the current test
   in review. Assert the exact approved error code, a safe bounded message, and
   that exception details/credential values are absent.

5. **P2 — CLI filter wiring is under-tested.** The only real Typer invocation,
   `test/offline/test_manifest.py:605-612`, passes `--ticker` and does not pass
   `--date`; the date and combined-filter cases at `:443-464` call the Python
   query function directly. A CLI implementation that ignores `--date` or
   mishandles the combined filter can therefore pass the current tests despite
   violating FR-C (`docs/reference/project-requirements.md:59`). Add real CLI
   invocations for ticker-only, date-only, combined and no-match filters, and
   assert warning rendering for a bad record.

6. **P2 — Successful report-path integration is not covered.** The direct
   writer test at `test/offline/test_manifest.py:140-151` uses `_write_manifest`
   rather than the CLI/report-save lifecycle. The only successful end-to-end
   rerun at `:395-413` disables report saving, so it checks only two null report
   paths. No test proves that a successful saved report records the exact paths
   returned by `save_reports`, relative to the results root, as required by
   `docs/architecture/interface-contracts.md:34-36`. Add a successful CLI run
   with saving enabled and assert both the on-disk report and manifest paths.

### Code/test quality, operational metadata and verification

- The test module has independent stdlib-written malformed/unknown-version and
  traversal fixtures, explicit negative status coverage, same-day rerun coverage,
  and a deterministic 1,000-manifest generator. The generator's byte-stable
  design and the benchmark's three fresh subprocesses are good foundations for
  NFR-C.
- NFR-C is correctly left unclaimed: the 2-second threshold is still proposed,
  and no implementation-phase timing result is present. The benchmark tool
  returns failure against the absent command, which is baseline evidence rather
  than a performance pass.
- No runtime dependency, credential, live API call or upstream production module
  was added by this PR. The remote PR has no submitted reviews; the documented
  independent final review remains pending and is not replaced by this local
  memo. ADR-003 makes a same-PR `Test-Plan-Approved` marker advisory; its absence
  is not a finding. Required human plan/test approval before application code
  remains separate.
- `docs/verification/c-manifest.md:108-123` predates the merge from main and
  describes D as absent. The current checkout has the D implementation and all
  existing tests pass. Append the current-head results and PR metadata to avoid
  presenting that historical baseline as the present branch state.

### Verification evidence

- `TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings`:
  **1532 passed, 20 failed, 1 skipped, 1 deselected, 100 subtests passed**.
  All 20 failures are the expected missing C module/CLI acceptance reds.
- `.venv/bin/python scripts/check_governance.py --base
  ecc2ff48d3575aa8c897b42ce0b50e8d7a51d92f`: passed.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check main...HEAD`: passed.
- GitHub PR metadata at review time: head `64f7bec`; governance, safety review,
  Ruff and clean-install checks passed; both Python 3.13 test jobs failed only
  on the expected unimplemented C tests. Both job logs report 20 failed and
  1532 passed, with no non-C failures. Read-only commands used:
  `gh pr view 5 --repo sui-feng-cb/CS5351-TradingAgents --json number,url,title,body,baseRefName,baseRefOid,headRefName,headRefOid,isDraft,state,reviews,statusCheckRollup`,
  `gh run view 45057579345 --job 137316120880 --repo sui-feng-cb/CS5351-TradingAgents --log-failed`
  and `gh run view 45057575170 --job 137316108076 --repo sui-feng-cb/CS5351-TradingAgents --log-failed`.
  No GitHub review was submitted.
- Review-only mutation probes were run from a temporary test file and removed
  afterward; they produced evidence for findings 1–4 and did not modify
  production code or the PR test suite.

### Decision

**CHANGES REQUIRED.** This is a useful tests-first foundation and correctly
defers application implementation, but the current contract leaves schema
validation, failed-run sanitization, path containment, CLI read-only behavior,
and CLI filter wiring insufficiently protected. Resolve the two P1 safety-test
gaps and the P2 acceptance-contract gaps before approving the C test plan or using
it as the implementation acceptance boundary. This local conclusion is not a
GitHub approval, merge authorization or approval of the future application
implementation.

## PR #5 re-review · C manifest/query tests-first corrections · 2026-11-23

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **URL:** https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/5
- **Reviewer:** OpenCode, re-review requested by the user
- **Base:** `main` / `ecc2ff48d3575aa8c897b42ce0b50e8d7a51d92f`
- **Previously reviewed head:** `64f7bec36e91b83f976708ff5310966530596010`
- **Reviewed head:** `677e9f396e9ae3498d218a42d1a49f1e8270af48`
- **Scope:** tests-and-docs-only corrections for FR-C, NFR-C and SEC-01.
  No manifest application module or CLI implementation was added.

### Previous findings rechecked

The changes at `677e9f3` address the six findings from the prior review:

1. The unsafe path is now `../outside_secret.md` relative to `results_root`; the
   test asserts the resolved target and uses `_OpenSpy` to fail if the external
   report is opened (`test/offline/test_manifest.py:854-889`).
2. The CLI query test snapshots files/directories and instruments write, delete,
   rename, replace and copy operations under the results root
   (`test/offline/test_manifest.py:165-285, 920-936`).
3. Eight schema-negative variants cover invalid status, extra/missing fields,
   UUID, date, naive timestamp and invalid reports/error structures
   (`test/offline/test_manifest.py:319-342`).
4. The failed-run test checks the candidate fixed code/message and rejects raw
   exception text and traceback details (`test/offline/test_manifest.py:618-635`).
5. New real Typer invocations check ticker, date, combined and no-match queries,
   parse JSON stdout, and require a corrupt manifest warning
   (`test/offline/test_manifest.py:939-1024`).
6. A successful CLI save test checks a non-default report returned by
   `save_reports` is what the manifest records, relative to the results root
   (`test/offline/test_manifest.py:454-482, 638-658`).

The updated verification log distinguishes this 29-test baseline from the
previous 20-test snapshot and labels the old D baseline as historical.

### CI failures and impact

Both failed checks are the same test-suite failure on the same head SHA, triggered
twice by GitHub events:

- `pull_request`: [run 45119343357](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45119343357)
- `push`: [run 45119338252](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45119338252)

Each reports **29 failed, 1532 passed, 1 skipped, 1 deselected, 100 subtests
passed**. All 29 failures are in `test/offline/test_manifest.py` and result from
the tests-first state: `tradingagents.enhancements.manifest` is not implemented,
the `manifest query` CLI command is absent (`No such command 'manifest'`), and
the real CLI success/failure cases consequently find no `run_manifest.json`.
There are no failures in the pre-existing non-C test suite. Governance,
`safety review`, Ruff and `clean-install smoke` passed in both runs.

These are expected C acceptance reds, not an unrelated regression. They are still
material to merge readiness: the required test status is red, so the PR cannot
be merged while that check is required. Do not suppress or skip the new tests;
after implementation lands, rerun the full suite and require these 29 to pass.

### Remaining non-blocking contract/documentation notes

1. `docs/testing/c-manifest-test-plan.md:12` still says the suite has 20 cases;
   this head collects 29. Update the count for accuracy.
2. The CLI JSON envelope and fixed `analysis_failed` / `Analysis failed.` values
   are explicitly described as pending human/team confirmation, although tests
   currently assert them. Confirm these proposed public values before C
   implementation; this review does not silently freeze them.
3. NFR-C's proposed 2-second target remains pending approval and has not been
   measured against an implemented query.

### Verification evidence

- Current-head local full suite, run with Python 3.13.18 and
  `TZ=America/New_York`: **29 failed, 1532 passed, 1 skipped, 1 deselected,
  100 subtests passed**. Failures were all the expected absent C implementation
  and CLI acceptance cases.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python scripts/check_governance.py --base
  ecc2ff48d3575aa8c897b42ce0b50e8d7a51d92f`: passed.
- `.venv/bin/python -m mypy scripts/check_governance.py`: passed.
- `.venv/bin/python -m pip check`: passed.
- `git diff --check ecc2ff48d3575aa8c897b42ce0b50e8d7a51d92f...HEAD`: passed.
- PR metadata confirms head `677e9f396e9ae3498d218a42d1a49f1e8270af48`, no
  application implementation, and no prior submitted reviews.
- Submitted GitHub review **APPROVE** for this tests-and-docs scope only:
  https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/5#pullrequestreview-6017260315
  (`2026-11-23T06:11:54Z`). GitHub started a safety-review rerun after the review;
  it was pending at the last status check. No merge was performed.

### Decision

**APPROVE — tests-and-docs scope only.** The previous functional test-design
findings are resolved in this head. The two CI failures are explained by the
deliberately unimplemented C module/CLI, with the rest of the offline suite
passing. This approval is not a claim that CI is green or the PR is merge-ready;
the required suite must pass after implementation. The pending candidate contract
values and NFR-C target remain subject to team confirmation. This review does not
approve application implementation or merge.

## FR-A / NFR-A 同日双标的比较 PR · 2026-11-23

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **PR:** #7 — https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/7
- **Reviewer:** OpenCode（按用户请求进行非作者代码审查）
- **Base:** main / `41e1b0b5f0717d349dab5a688634a32a388b7466`
- **Reviewed head:** `ea49ffba50c43ea2def802bec21a70fac6f2c38a`
- **Merge commit:** `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`（审查 head 与其内容一致）
- **Date:** 2026-11-23
- **Scope:** FR-A、NFR-A、INV-A、SEC-01；A-IC-001、ADR-001
- **Files:** `src/tradingagents/enhancements/comparison.py`、
  `test/offline/test_comparison.py`、`docs/architecture/interface-contracts.md`、
  `docs/architecture/invariants.md`、`docs/architecture/trace-matrix.md`、
  `docs/req/requirements.yaml`、`docs/bug-diary.md`、`docs/ai-use-log.yaml`

### 需求与架构对齐

- FR-A：两个不同 ticker、同一 canonical 日期、顺序调用上游；
  输出比较 Markdown + 强制 manifest；draft-0.3 字段顺序。
- NFR-A：任一 ticker 失败时另一成功报告保留；失败行 rating/summary/report_path
  为 null；不跨 ticker 回填。
- INV-A：已登记；A-FAIL/A-XTALK 覆盖。
- SEC-01：失败原因不得泄露上游异常原文或凭证。
- 未改 graph/agents/eligibility/CLI/provider/prompt；不触发 safety-critical
  路径的 ADR+独立安全评审要求，但仍需非作者最终评审。

### 审查发现

1. **P1 — 上游异常原文进入公开结果和工件。** `_failure_reason` 拼接
   `str(exc)`，导致 synthetic credential URL/token/账户标记进入
   `failure_reason`、Markdown 和 JSON。违反 A-IC-001 §3 与 SEC-01。要求固定
   错误码和安全文案，并断言 PARTIAL 下另一报告保留、三处输出无敏感标记。
2. **P1 — 结果身份和报告归属缺少校验。** `run_one` 直接采信 graph 返回状态；
   AAPL 收到 MSFT 状态仍可 SUCCESS 并发布 Sell；MSFT 目录报告或 `notes.md`
   也可被当成 AAPL 完整报告。要求在保存前核对 ticker/date，在发布前核对
   `complete_report.md` 文件名和 ticker 目录归属，错误行三字段为 null。
3. **P2 — 多行 Executive Summary 只保留首行。** 需要提取到下一节之前的完整
   摘要段，再折叠、单行化、截断 500 字符，并补多行/标题后换行/缺省回退测试。
4. **P2 — 接受 crypto 标的后使用股票管线。** `btcusd`/`BTC-USD` 被接受但
   `propagate` 使用默认 stock。A 范围随后限定为仅股票，要求预检拒绝
   Crypto/Forex/Futures/Index 并同步契约和测试。

### 代码与测试

- 仅新增编排/汇总；无新增运行时依赖；CLI 属后续协调集成。
- 审查 head：30 个 comparison 测试通过；修复分支：38 个 comparison 测试通过。
- 修复后覆盖异常脱敏、身份/归属校验、多行摘要、stock-only 拒绝、两成功、
  REVIEW、第一/第二/双失败、save 失败、MISSING rating、输入错误、XTALK、
  manifest 一致性。
- 本地缺少 yfinance，完整 conftest/全回归未在本地完成；以 CI Python 3.13 为准。

### 运行元数据

- `comparison_id = cmp_<uuid4 hex>`；`generated_at` 为 UTC RFC3339 `Z`。
- `report_path` 相对 `config["results_dir"]`，使用上游 `default_report_path()`。
- Markdown/manifest 由同一不可变结果派生。

### 安全

- 未改 `src/tradingagents/graph/`、`src/tradingagents/agents/`、
  `eligibility.py`。
- 输入校验先于任何 graph 运行；失败项不携带有效评级。
- 修复后失败原因只含固定安全文案；无密钥、凭证 URL 或账户数据进入报告。

### 效率

- 顺序执行两次上游分析；无额外 LLM 调用。
- 摘要提取为确定性文本处理；无新增 provider 调用。
- `comparison_manifest.json` 为小型本地产物。

### 验证证据

- 审查 head 隔离运行：
  `PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -q --tb=line --disable-warnings`
  → 1562 passed、29 failed、1 skipped、1 deselected、100 subtests passed；
  29 个失败均为 C `test_manifest.py` 预期红测，A 的 30 项通过。
- 修复分支：
  `PYTHONPATH=src:. python -m pytest test/offline/test_comparison.py -q --confcutdir=test/offline`
  → 38 passed。
- 本地治理检查 `--base 41e1b0b`、全仓 Ruff、治理脚本 mypy、pip check、
  `git diff --check` 均通过；PR/push CI 的治理、Ruff、干净安装和 safety review
  通过，测试作业失败仅来自 C 红测。
- 临时离线探针复现前 3 项问题；真实上游报告写入器的双成功对照通过。

### 决定

**CHANGES REQUIRED。**

修复状态：P1 异常脱敏、P1 身份/归属校验、P2 多行摘要、P2 stock-only 范围已在
`feature/A-comparison-review-fixes` 实现，38 个 A 测试本地通过；契约/追踪矩阵/
bug diary/AI 日志正在更新到 draft-0.4。当前等待独立非作者复审；在新 head 通过
复审前不得合并。

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
