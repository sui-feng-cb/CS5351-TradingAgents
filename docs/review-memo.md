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

## PR #8 · A 比较模块修复复审 · 2026-11-23

- **Repository:** `sui-feng-cb/CS5351-TradingAgents`
- **PR:** #8 — https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/8
- **Reviewer:** OpenCode（按用户请求进行非作者复审）
- **Base:** `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`
- **Reviewed head:** `094e2a700f56144551261bfcabc5e15bff3efcac`
- **Date:** 2026-11-23
- **Scope:** FR-A、NFR-A、INV-A、SEC-01；ADR-001、ADR-003、A-IC-001 draft-0.4

### 上轮整改核对

- 异常原文泄露已修复：稳定错误码 + 固定安全文案，三个公开输出无敏感标记。
- 状态身份校验已生效：错 ticker/错日期在保存前返回
  `RESULT_IDENTITY_MISMATCH`，三个结果字段为 `null`。
- 多行 Executive Summary 已修复：完整提取到下一节，再折叠/截断。
- stock-only 常见输入已拒绝，但非美元 crypto 仍有遗漏。

### 本轮发现

1. **P1 — 报告归属检查先于路径解析，仍可发布另一 ticker 的报告。**
   - `run_one` 只在原始 `saved_path` 上检查文件名和父目录前缀，
     `_relative_report_path` 随后才 `resolve()`，最终发布路径未重新校验。
   - 目录符号链接 `reports/AAPL_<stamp>` → `reports/MSFT_<stamp>` 时，AAPL
     仍为 `SUCCESS`。
   - 文件符号链接 `AAPL/complete_report.md` → `MSFT/notes.md` 时，公开路径
     变成 MSFT 的 `notes.md`。
   - 要求对 resolved 后路径统一检查结果根、精确
     `reports/{ticker}_{stamp}/complete_report.md` 结构和归属。
2. **P2 — stock-only 预检漏掉非美元计价 crypto。**
   - `BTC-EUR`、`ETH-GBP`、`BTC-JPY` 通过预检并以 `asset_type="stock"`
     写入成功工件。
   - 要求补齐 crypto base + quote 识别，或与 D 明确可确定验证的股票输入范围；
     测试需覆盖两个输入位置、零 graph/save 调用和零工件。

### 验证

- 审查 head：A 专项 38 passed；全量 1570 passed、29 failed、1 skipped、
  1 deselected、100 subtests passed；29 项均为 C `test_manifest.py` 预期红测。
- 独立探针：5 failed、6 passed；失败对应目录/文件符号链接和非美元 crypto。
- 修复后：A 专项 40 passed；`py_compile`、Ruff、治理、`git diff --check`
  通过；完整 CI 待新 head 重跑。
- 29 项 C 基线红测不归因于 A，C 测试未被修改。

### 决定

**CHANGES REQUIRED。**

符号链接归属和 non-USD crypto 两项修复已在
`feature/A-comparison-review-fixes` 实现，A 的 40 项测试本地通过，契约/追踪/
bug diary/AI 日志已更新。当前等待独立非作者复审；新 head 通过复审前不得合并。
**PENDING — reviewer to fill.** 评审人须给出 `APPROVE`、`CHANGES REQUIRED` 或 `REJECT`。
## PR #6 · B 分支同步与提交边界审查 · 2026-11-23

- **仓库 / PR：** [sui-feng-cb/CS5351-TradingAgents #6](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6)
- **审查人：** OpenCode，按用户要求审查分支同步、权限边界与重新送审条件。
- **Base：** `main` / `41e1b0b5f0717d349dab5a688634a32a388b7466`
- **Head：** `B-60284898` / `9a50f83f97afa8f4fb4607e5372c035c2f50f5e2`
- **共同祖先：** 上游基线 `9fa1196fffbcfd9de5146d2dd2869df84ab99838`。
- **范围：** FR-B、NFR-B、INV-B、BASE-01、GOV-01、QUA-01；依据 ADR-001、
  ADR-003、`AGENTS.md:15-28`、共享接口契约及当前生效的 OpenCode 权限配置。
  本轮是同步与集成前置审查，B 的完整功能、模型质量与性能验收仍待同步后进行。

### 审查发现（按严重程度排序）

1. **P1 — 分支从上游基线直接开发，未纳入团队 main，当前不可合并。**
   GitHub compare 和本地提交图均确认 B 落后 main **8 个提交**、独有 **1 个提交**；
   PR 状态为 `CONFLICTING / DIRTY`。当前 PR 的 42 个文件、4,994 行新增包含
   `AGENTS.md`、`Prompt.md`、两份 rules、需求注册表及多份共享架构文档的重新创建，
   与 main 已有文件形成冲突。请先在 **B 自己的本地开发分支** 合并最新
   `origin/main`，逐项解决冲突，保留 main 的 src 布局、D 实现、安全修复、
   C 测试契约及治理历史。不得整批选择 B 版本覆盖共享文件。
   注意：`git diff main B` 显示的缺失/回退是两棵分支树的差异，不能直接称为
   B 本次 PR 主动删除这些文件；真正需要审查的是合并后的 PR diff。

2. **P1 — 共享治理文件与权限边界必须由 B 自查，不能通过放宽配置消除拒绝。**
   PR 同时新增 `.opencode/rules.md`、`.agent/rules.md`、`AGENTS.md`、
   `Prompt.md`，并修改 `.github/workflows/ci.yml`。
   main 的 `.opencode/opencode.json:8-14,23` 和
   `.opencode/permissions.jsonc:4-10` 规定：
   - `plan` agent 禁止所有编辑；需按人工批准流程进入适当阶段。
   - `.opencode/rules.md` 明确 `deny` 且由人类维护；`AGENTS.md`、
     `Prompt.md`、`.agent/rules.md` 不在编辑白名单内，落入默认 `deny`。
   - `src/**`、`test/**`、`docs/**`、`scripts/**`、`prompts/**`、
     `.github/**` 等是逐次确认的 `ask`，不等于模块负责人可任意修改共享文件。
   请 B 对照合并后的配置与自己真实会话中的拒绝记录，列出
   **路径、拒绝操作/原因、实际是否改动、是否属于 B 范围、处理方式、人工批准依据**。
   非 B 范围的重建/覆盖应清理；确需修改的共享文件交协调人或人类按流程处理。
   不得改权限、改 rules 或换 shell/脚本绕过拒绝。当前未取得 B 的本地拒绝日志，
   上述是配置核对结果，不能冒称已确认 B 实际遇到了哪些拒绝。

3. **P1 — 实现位置偏离约定，测试导入方式不能证明安装后可用。**
   PR 新增 `src/event_merge/`，而 B 的约定入口为
   `src/tradingagents/enhancements/events.py`（`AGENTS.md:20`）。
   main 的 `pyproject.toml:56-58` 仅打包 `tradingagents*` / `cli*`；
   B 的 `test/conftest.py:14-16` 手动把 `src/` 放入 `sys.path`，可能掩盖包未交付的问题。
   合并后请按既有包与接口契约收敛实现，或先取得团队对路径/契约调整的明确批准；
   使用干净安装验证正式导入，不能仅凭测试目录中的导入通过判定交付成功。

4. **P2 — 验证记录仍是旧分支口径，需按新 head 重跑并更正声明。**
   PR 描述的 `50 passed` 仅覆盖 B 旧分支的 `test/offline/`，不能代表团队全量回归。
   新增 CI 作业使用 Python **3.12**（`.github/workflows/ci.yml:76-78`），
   与 main 的 Python 3.13 要求不一致，合并后 editable install 会不满足版本要求。
   `test/offline/test_semantic_eval.py::_run_gate` 使用按标签构造的 mock 分组验证
   指标及阈值逻辑，不能作为真实模型 precision/recall 的质量证明。
   请在重新送审时提供新 head、完整命令/结果、CI 链接，并区分 mock 门禁验证与
   可重放的真实模型评估证据；未验证或未获人工确认的结果/数据冻结状态不得写成已完成。

### B 重新申请 review 前的处理顺序

1. 保存并核对自己的工作区，确认位于 `B-60284898`；获取最新远端后，在本地执行
   `git merge origin/main`。逐文件处理冲突，确保 main 的团队成果完整保留。
2. 重新读取 main 的入口、接口、ADR、权限配置和规则；完成上述权限拒绝项清单。
   清理共享文档的重复初始化，只保留经批准、可追踪的 B 增量。
3. 核对 `git diff --name-status origin/main...HEAD`、
   `git diff origin/main...HEAD`、`git diff`、`git diff --cached` 及
   `git status --short`，同时检查未暂存、已暂存和未跟踪文件。
   如有合并冲突，可用 `git diff --name-only --diff-filter=U` 核对剩余未解决项。
4. 用项目 Python 3.13 执行：

   ```bash
   .venv/bin/python scripts/check_governance.py --base origin/main
   TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
   .venv/bin/python -m ruff check .
   .venv/bin/python -m mypy scripts/check_governance.py
   .venv/bin/python -m pip check
   git diff --check origin/main...HEAD
   git diff --check
   git diff --cached --check
   ```

   当前治理脚本仍会阻止尚未接入获批评估的 `events.py` / 运行时 prompt 语义变更
   （`scripts/check_governance.py:120-121`）。若触发，应协调完成获批评估与门禁接入，
   不得改名绕过或删掉检查。保留所有既有测试与断言。
5. 完成人工批准的提交后，再核对最终提交及 `origin/main...HEAD` 全量 diff，
   确认提交内容与已验证工作区一致；更新 PR 描述、AI-use 日志和真实会话证据。
   推送更新到原 PR 后确认无冲突、CI 已运行，再附 **新 head SHA、同步的 main SHA、
   权限自查清单和验证摘要** 重新申请 review。

### 本轮证据与验证边界

- 只读查询：`gh pr view 6 --repo sui-feng-cb/CS5351-TradingAgents --json ...`、
  `gh api repos/sui-feng-cb/CS5351-TradingAgents/compare/main...9a50f83f97afa8f4fb4607e5372c035c2f50f5e2`。
  GitHub 返回 ahead 1 / behind 8、`CONFLICTING / DIRTY`，`reviews` 与
  `statusCheckRollup` 均为空；因此没有可据以认定通过的远端检查结果。
- 本地 `git rev-list --left-right --count main...origin/B-60284898` 返回 `8 1`；
  `git merge-base` 返回上述上游基线。已确认本地 B 远端跟踪引用与 PR head 一致。
- 本轮保持在 main，以 Python **3.13.18** 运行完整默认离线套件：
  **1532 passed、29 failed、1 skipped、1 deselected、100 subtests passed**。
  29 个失败全部来自已合并的 C tests-first 契约（manifest 模块/CLI 尚未实现），
  是 B 同步前的 main 基线，不归因于 B，也不能用删除/跳过 C 测试来消除。
  B 同步后应报告相对该基线的新增失败；必需检查仍为红色时不能宣称 merge-ready。
- main 上 `.venv/bin/python scripts/check_governance.py`、
  `.venv/bin/python -m ruff check .`、
  `.venv/bin/python -m mypy scripts/check_governance.py`、
  `.venv/bin/python -m pip check` 均通过。
  未运行 B head 的测试或真实模型评估；PR 描述中的 B 测试与质量数字未经本轮复现。
- 本轮只更新本地 review/session 文档；未替 B 合并、修复或提交，也未向 GitHub 提交 review。

### 结论

**CHANGES REQUIRED。** 请 B **先在本地 merge 最新 main → 自查权限拒绝与共享文件边界
→ 清理并逐项核对最终 diff → 按新 head 验证并复核提交 → 更新原 PR 后重新申请 review**。
当前分支存在合并冲突，且实现路径、共享治理文件与验证口径尚未对齐，不进入批准阶段。

## PR #6 复审 · `1f57b39` · 2026-11-23

- **仓库 / PR：** [sui-feng-cb/CS5351-TradingAgents #6](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6)
- **审查人：** OpenCode，按用户请求复审更新后的实现与测试。
- **Base：** `main` / `41e1b0b5f0717d349dab5a688634a32a388b7466`
- **上轮 head：** `9a50f83f97afa8f4fb4607e5372c035c2f50f5e2`
- **本轮 head：** `B-60284898` / `1f57b394e50dd23ad75e682ad1aee29e53e7ec28`
- **范围：** FR-B、NFR-B、INV-B、INV-ASOF、BASE-01、GOV-01、QUA-01；
  ADR-001（团队布局）、ADR-003、B 新增 ADR 与接口契约 B 条款。
  核对了 PR 的 7 个提交历史，并审查相对 main 的最终 9 文件 diff；未调用真实模型/供应商。

### 上轮整改核对

- **main 同步与冲突已解决。** 合并提交 `9a6882a` 包含上述 main；
  `git rev-list --left-right --count main...HEAD` 为 `0 7`，GitHub 为
  `MERGEABLE / UNSTABLE`。当前状态不再是上轮的分支冲突。
- **共享文件覆盖已清理。** `AGENTS.md`、`Prompt.md`、两份 rules、权限配置、
  需求注册表、共享接口、`pyproject.toml` 和 `test/conftest.py` 相对 main 无差异。
  D 实现、安全修复及 C 契约均保留。PR 增补了文件处理清单；它仍不是完整的
  本地拒绝操作/原因/批准记录，因此不推断作者的历史操作或声称审批已核实。
  `.github/workflows/ci.yml` 仍有新增 B 作业，PR 的“未修改团队共享文件”表述应准确说明该例外。
- **模块路径已纠正。** 最终 diff 不再包含 `src/event_merge/` 或 `sys.path` 注入，
  改为 `src/tradingagents/enhancements/events.py`。本轮 `python -I` 下从现有
  editable install 正式命名空间导入成功；远端 clean-install smoke 通过，但其命令
  只导入 package/CLI，不能冒称专门验证了 events 的非 editable 安装。
- **Python 版本已纠正为 3.13，验证尚未全部通过。** 作者已区分 C 既有失败及
  语义治理阻断；Ruff 仍有可复现的新失败，完整语义评估和真实业务接入仍缺失。

### 审查发现（按严重程度排序）

1. **P1 — 默认新闻与模型入口仍是占位，FR-B 的真实新闻归并流程未交付。**
   `src/tradingagents/enhancements/events.py:431-446` 的默认 fetcher 一律抛
   `NotImplementedError`；`:612-626` 的默认模型也一律抛错，且会被归并入口吞掉。
   当前所有成功用例都靠调用方注入 fetcher/llm。测试注入是合理的，但没有已接入的
   上游数据/模型适配器与公开调用链，不能据此称 FR-B 已完成。
   请协调 dataflows 的结构化新闻接口并接入现有模型客户端，保持供应商边界和
   最多一次真实归并请求（包括禁用隐藏 SDK 重试），补充走正式入口、仅在供应商/
   模型传输层 mock 的离线集成测试。接口变化先经协调批准；不要通过恢复业务层直连
   vendor SDK 来绕过分层约束。若只交付可注入的核心组件，应明确缩小 PR 完成声明，
   并保留 FR-B 整体未完成状态。

2. **P1 — 时间窗口和数量限制未形成确定性输入边界，可发布窗口外证据。**
   `events.py:465-478` 先取原始前 5 条，没有解析/过滤发布日期；`:659-675`
   又直接接受调用者的 records/tickers/window，没有验证日期、窗口或每 ticker 上限。
   独立离线复现：请求 `2026-11-15..2026-11-22`，每 ticker 的前 5 条为
   `2026-11-23`、第 6 条为窗口内新闻，结果返回 **10 条未来记录**，合法记录被截掉；
   将两个未来记录交给 `merge_once`，模型引用输入 ID 后仍得到 `merged` 与已验证证据。
   另以每 ticker 6 条直接调用，12 条均可交给模型并被接受。
   请在分配 ID/限量前按可信时间过滤，拒绝缺失/非法日期；在正式归并入口统一校验
   2–3 个有效不同 ticker、≤7 天窗口、记录归属和每 ticker ≤5 条，非法输入应在
   模型调用前拒绝或按获批契约明确降级。补充未来/过期/缺日期、过滤后限量及直接入口越限负例。

3. **P1 — 语义评估没有评估生产归并流程，且失败样例可被跳过后错误通过门禁。**
   `test/live/test_semantic_eval_live.py:149-170,197-249,268-276` 用另一套
   “same/different”两条新闻判别 prompt 逐对调用模型，未经过 `merge_once`、
   实际分组 prompt、结构解析与 validator，因此其数字不能证明 FR-B 实际分组质量。
   同时，调用失败/无法解析的 pair 不进入 FN/FP，`_assert_gate` 不检查失败数或覆盖率。
   本轮把模型替换为完全离线 stub：24 对中仅 s01 返回正确 `same`，其余 23 对抛错，
   得到 **TP=1、FP=0、FN=0、failed=23、precision=recall=1.0，门禁仍 PASS**。
   请用获批固定、版本化数据走真实批次归并代码，再从最终分组计算 pairwise 指标；
   API/解析失败必须阻断验收或按事先批准的保守规则计入，不能缩小分母后报告通过。
   保存模型/provider、实际 prompt/数据版本或哈希、逐项输出及全量统计，并在 CI 接入
   可重放验证。`.github/workflows/ci.yml:74-87` 当前仅重复运行 offline 套件，
   没有语义质量门禁；`scripts/check_governance.py:120-121` 的阻断仍需团队协调解决，
   不能仅删除检查或改名绕过。日志中 23/24 成功的既有 PASS 不能视为完整评估验收。

4. **P2 — JSON 能解析不等于 schema 合法，畸形输出可崩溃或发布空事件。**
   `events.py:585-598` 只检查最外层 list，`:687` 在异常处理之外调用 validator；
   `:750-757` 默认信任 event/claim 类型，`:789-795` 不验证必要事件字段。
   离线复现 `{"events":[null]}` 抛 `AttributeError`，
   `{"events":[{"evidence_ids":[{}]}]}` 抛 `TypeError`；
   仅提供两个有效 ID、缺少 event_id/summary 的事件则被发布为 `merged`，摘要为空。
   请验证完整输出形状、字段类型和必要非空值，畸形模型结果走可观测的失败路径，
   保留输入为未归并并保证不发布无效事件；覆盖上述字面负例和正常分组对照。

5. **P2 — 模型不可用/解析失败被报告为“没有共同事件”。**
   `events.py:601-609,677-685` 把异常统一变成 `no_common_event`，没有失败原因；
   默认未接入模型也会走这条路径。独立抛错 stub 复现了这一结果。
   “未成功分析”不能作为“分析后没有共同事件”的结论，违反
   `docs/reference/module-acceptance.md:46-52` 的失败语义。
   请协调明确失败状态/原因或受控异常契约，并独立测试无新闻、真实空分组、
   模型异常和 schema/JSON 错误的区别，同时保持不发布未验证事实。

6. **P2 — Ruff 必需检查仍失败，PR 的全通过描述不符合当前 head。**
   `test/live/test_semantic_eval_live.py:23-35` 存在 `I001` 导入块格式错误；
   本地全仓 Ruff 与远端对应 head 结果一致。请修正后运行全仓检查，再更新
   PR/AI-use 验证记录，不要继续沿用“ruff 全部通过”的旧口径。

### 文档与证据整理

- 新增 B ADR 的编号仍为 `ADR-001`，与团队布局 ADR 重复；正文引用
  `FR-B-1..7` / `NFR-B-1..3` / `INV-B-1..5`，但当前权威注册表仅有
  FR-B、NFR-B、INV-B。请使用唯一 ADR 编号并提供子项到权威 ID 的明确映射。
- `docs/architecture/evaluation-logbook.md:32-40` 和 live 文件开头仍引用已删除的
  分散测试及不存在的 B evaluation-table 章节；B ADR 的 snippet 截断声明也未由
  `events.py` 实现。请按当前结构和真实边界修订。保留历史结果时标明对应版本。
- 当前数据集写“成员 B 冻结”，本轮没有取得团队共同冻结证据或逐项模型原始输出；
  不替作者补造批准、来源核实或模型测量结果。完整会话仍需真实 `/export`。

### CI 失败分类

最新 head 的 `pull_request` run
[45153885882](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45153885882)
和 `push` run
[45153868055](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45153868055)
各有 tests、B-module、Ruff 失败；另有 safety review 失败：

| 检查 | 已核实原因 / 影响 |
|---|---|
| tests / B-module | 所读 pull_request 日志均为 29 个 C manifest/CLI 既有失败，1601 passed、1 skipped、100 subtests passed（全量另有 2 deselected）；B-module 实际运行整个 offline 目录，不是 B 的 39 项失败。保留 C 测试，不能归因于 B 或删除以转绿；必需检查红色仍影响合并。 |
| Ruff | B 新增 live 文件的 I001，可修复的新失败。 |
| safety review | [run 45153885727](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45153885727) 在 `Check PR changes` 因未接入获批语义评估而失败，尚未进入后续安全 review 检查；不是本轮查证到的“缺少同 PR 测试批准”。 |
| governance / clean-install smoke | 两次触发均显示通过；基础治理检查通过不等于带 `--base` 的语义变更门禁通过。 |

### 本地验证（固定本轮 head，Python 3.13.18）

- `TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings`：
  **1571 passed、29 failed、1 skipped、2 deselected、100 subtests passed**。
  失败仅在既有 C `test_manifest.py`；相对上轮 main 的 1532 passed 增加 B 的 39 项。
  远端通过数为该 CI 环境实际报告值，不将本地/远端不同数字混称为同一次测量。
- `.venv/bin/python -m pytest -q --tb=short --disable-warnings
  test/offline/_pr6_review_probe.py test/offline/test_events.py`：
  **7 failed、39 passed**；7 个独立审查负例分别暴露窗口过滤、数量边界、两种 schema
  崩溃、空摘要发布、异常状态混淆、评估跳过失败仍通过。
  追加未来证据发布负例后单独运行该 case，再得到 **1 failed**，证实未来新闻可成为
  verified event。临时 probe 文件已删除，生产代码与作者测试未修改。
- `.venv/bin/python scripts/check_governance.py --base main`：基础 registry/schema/
  布局/权限同步和扫描通过，语义变更检查失败（与远端 safety job 相同）。
- `.venv/bin/python -m ruff check .`：失败，1 个 I001。
- `.venv/bin/python -m mypy scripts/check_governance.py`、
  `.venv/bin/python -m pip check`、`git diff --check main...HEAD`：均通过。
- `.venv/bin/python -I -c "from tradingagents.enhancements import events; print('installed namespace import:', events.__name__)"`：成功。
- 远端只读核对使用 `gh pr view 6 --repo sui-feng-cb/CS5351-TradingAgents --json ...`、
  `gh run view 45153885882 --repo sui-feng-cb/CS5351-TradingAgents --log-failed`，
  并单独读取该 run 的 Ruff job `137621829621`、B job `137621830338` 及
  safety run `45153885727` 的失败日志。未提交 GitHub review。
- 为保护上轮未提交的 review 文档，先仅暂存到 stash，detach 到审查 head 验证，
  再返回 main 恢复原文档。当前只追加 review/session 记录；没有应用修复、提交、推送或合并。

### 结论

**CHANGES REQUIRED。** 上轮要求的 main 同步、共享文件清理、路径迁移和 Python 版本
已落实，应予确认；本轮发现的真实入口缺失、输入时间/数量边界、语义验收有效性及输出
schema/失败状态缺陷仍阻止批准。请先补充独立回归并修复上述问题、完成团队评估接入，
更正当前 head 的验证记录后再申请复审。已有 39 项 B 测试通过不等于 FR-B/NFR-B 完整验收通过。

## PR #7 · A 同日双标的比较代码审查 · 2026-11-23

- 审查人 OpenCode。范围为 FR-A、NFR-A、INV-A、SEC-01，以及 A-IC-001 和 ADR-001 的扩展边界。合并流程按本轮委托暂缓评估。 [GitHub PR #7](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/7)
- 合并前 `main` 为 `41e1b0b5f0717d349dab5a688634a32a388b7466`。审查 head 为 `ea49ffba50c43ea2def802bec21a70fac6f2c38a`，与合并提交 `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e` 内容一致。
- API 顺序复用两次上游分析和报告保存，沿用现有依赖，比较级 manifest 单独落盘。现有测试覆盖两个单失败方向及 `REVIEW` 报告保留。CLI 属后续协调集成范围。

### 审查发现

1. **P1 — 上游异常原文进入公开结果和工件。** `_failure_reason` 仅对 `str(exc)` 去除首尾空白。离线给分析异常和保存异常注入合成凭证 URL、token 和账户标记，均复现泄露至返回的失败原因。该字段直接写入 Markdown 和 JSON，分析异常的落盘也已复现。违反 A-IC-001 §3 和 SEC-01。请公开稳定原因码及固定安全文案，并断言 `PARTIAL` 下另一标的的报告保留，三个输出均无敏感标记。 [异常处理](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/ea49ffba50c43ea2def802bec21a70fac6f2c38a/src/tradingagents/enhancements/comparison.py#L145-L164)
2. **P1 — 结果身份和报告归属缺少校验。** `run_one` 用输入 ticker 标记行，却直接采信 graph 返回的状态。报告路径检查只确认文件存在且位于结果根内。离线让 AAPL 收到 MSFT 状态并返回 MSFT 报告，AAPL 仍被标记 `SUCCESS` 并发布 `Sell`。只替换报告返回值时，MSFT 目录下的 `notes.md` 也被当成 AAPL 完整报告。请在保存前核对状态里的 ticker 和分析日期，在发布前核对完整报告名称和归属。补错标的、错日期和错误报告路径负例，断言错误行三个结果字段均为 `null`，另一标的的报告保持正确。 [状态与路径处理](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/ea49ffba50c43ea2def802bec21a70fac6f2c38a/src/tradingagents/enhancements/comparison.py#L214-L269)
3. **P2 — 多行 Executive Summary 只保留首行。** 用上游 `render_pm_decision` 渲染两行结构化摘要，比较结果丢掉第二行的风险条件。A-IC-001 §3 要求提取摘要段并折叠空白。请在下一节之前提取完整摘要段，再折叠和截断。补连续多行、标题后换行及缺省摘要回退测试。 [摘要提取](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/ea49ffba50c43ea2def802bec21a70fac6f2c38a/src/tradingagents/enhancements/comparison.py#L176-L211)
4. **P2 — 接受加密标的后使用股票分析管线。** 归一化测试明确接受 `btcusd` 并断言向 graph 传入 `BTC-USD`，同时把 `asset_type` 锁定为 `stock`。真实 `propagate` 依赖调用方显式选择 `crypto`。请和 D 确认 A 的资产范围。范围含加密标的时，应传递正确资产类型并增加混合资产离线测试。范围限于股票时，应在预检拒绝超范围标的并同步契约。 [现有测试](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/ea49ffba50c43ea2def802bec21a70fac6f2c38a/test/offline/test_comparison.py#L567-L580) · [上游 API](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/ea49ffba50c43ea2def802bec21a70fac6f2c38a/src/tradingagents/graph/trading_graph.py#L185-L208)

### 验证与后续交付

- Python 3.13.18 在隔离工作树运行 `PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -q --tb=line --disable-warnings`，结果为 **1562 passed、29 failed、1 skipped、1 deselected、100 subtests passed**。A 的 **30 项通过**。29 项均为基线已有的 C manifest/CLI 验收失败。两个远端测试作业的计数和失败归属一致，治理、Ruff、干净安装和 safety review 检查通过。 [PR CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45145996269) · [Push CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45145989349)
- 本地治理检查 `--base 41e1b0b`、全仓 Ruff、治理脚本 mypy、`pip check` 和 PR 差异空白检查均通过。临时离线探针复现前 3 项中的异常、状态／报告错配和多行摘要问题，使用真实上游报告写入器的双成功对照通过。
- 请补 `run_comparison` 的 Python 调用示例和相对路径解析说明，同步追踪矩阵与实际验证结果。A-IC-001 §7 记录了 A 确认的测试意图和 D 的角色。文档同时写有 D 已批准和书面测试待批准，请核对两项批准的实际会话引用并澄清状态。

### 结论

**CHANGES REQUIRED。** 请从当前 `main` 开后续修复 PR，先解决异常脱敏及结果归属校验，再补摘要和资产范围回归并重新送审。保留 C 的既有验收测试，随集成进度重跑完整 CI。

## PR #6 · 第三轮复审 · 2026-11-23

- PR：https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6
- GitHub review：`CHANGES_REQUESTED`，https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6#pullrequestreview-6021522094
- Reviewer：OpenCode；范围 FR-B、NFR-B、INV-B、INV-ASOF、BASE-01、GOV-01。
- Head：`26bd176d5d6264c356a9cd48fd5de3784c8b8c38`；base：`c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`。
- 本轮用户确认团队已批准固定语义评估集并测试通过；接受此确认。
  29 项 C 基线失败及共享语义门禁均不作为要求 B 返工的依据。
- 已确认 B 专项 CI 范围与 Ruff 修复；events.py 和 B 离线测试与上轮 blob 相同。
  当前 head 的独立负例仍复现未来证据发布、每标的 6 条越限、schema 崩溃及空事件、
  模型失败标为无共同事件、默认入口占位。评估 runner 的失败覆盖缺陷另行说明。
- 本地 Python 3.13.18 全量：1601 passed、29 C-only failed、1 skipped、2 deselected、
  100 subtests passed。Ruff、mypy、pip check、PR diff 检查通过；带 base 的治理检查
  停在共享语义门禁。无真实模型调用；完成验证后回到原 main。
- 完整反馈、源码行链接、CI 链接及验证记录见
  [本轮审查记录](verification/pr6-review-003.md)。完整 TUI `/export` 待人工执行。

**CHANGES REQUIRED。** 团队批准和 CI 归因已确认，但当前 head 的功能缺陷仍存在。

## PR #6 · 第四轮复审 · 2026-11-23

- PR：https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6
- Head：`4a9afc4fc017ef9dbbd720ff86541491c06a99fd`；base：`c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`。
- 简化验收项已基本落实：可注入核心范围已声明、B 专项 53 项通过、schema/失败状态/evidence 负例通过、评估失败覆盖门禁已增加。
- 尚有一个 P1：`merge_once` 直接入口未检查各记录日期在窗口内。本轮复现未来日期和过期日期记录均能产生 `merged` 事件。
- 全量 1615 passed、29 个 C-only failures、1 skipped、2 deselected、100 subtests；Ruff、mypy、pip check、diff check 通过。远端结果对齐。
- GitHub review：`CHANGES_REQUESTED`，https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6#pullrequestreview-6022342508。完整记录：[PR #6 第四轮复审](verification/pr6-review-004.md)。

**CHANGES REQUIRED。** 只需修复直接归并入口的日期窗口校验并增加负例，再针对最新 head 复审。

## PR #8 · A 比较模块修复复审 · 2026-11-23

- **仓库 / PR：** [sui-feng-cb/CS5351-TradingAgents #8](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/8)
- **审查人：** OpenCode，按用户请求复核 PR #7 的整改及相关回归。
- **Base：** `main` / `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`。
- **Reviewed head：** `094e2a700f56144551261bfcabc5e15bff3efcac`；核对了本 PR 的两个提交及相对 base 的全部 7 文件 diff。
- **范围：** FR-A、NFR-A、INV-A、SEC-01；依据 ADR-001、ADR-003 和 A-IC-001 draft-0.4 修订。
- 主工作区保持在 `main` / `ed6a8c9`，在隔离工作树验证 PR head。本轮没有提交 GitHub 评论/review，也没有提交、推送或合并。

### 上轮整改核对

- **异常原文泄露已修复。** 分析/保存异常均映射为稳定代码和固定安全文案；新增测试检查返回值、Markdown 和 JSON 中无合成敏感标记，并保留另一标的报告。
- **状态身份校验已生效。** 错 ticker、错日期会在保存前返回 `RESULT_IDENTITY_MISMATCH`，三个结果字段均为 `null`。直接返回 MSFT 报告目录或 `notes.md` 的原始负例也会被拒绝，但解析后的报告归属仍有下述缺口。
- **多行摘要已修复。** 连续多行会提取至下一节，再折叠空白。补充离线探针确认标题后换行、空正文 fallback 及真实上游报告写入器的正常双股票路径均通过。
- **stock-only 方向已明确，拒绝范围仍不完整。** `BTCUSD`、`EURUSD`、`GC=F`、`SPX500` 的预检拒绝对照通过；非美元 crypto 仍被接受。
- Python 调用示例、相对路径说明及追踪矩阵已补充。draft-0.4 明确保留 D 对修订的确认要求，不能将本次代码审查视为该确认已发生。

### 审查发现（按严重程度排序）

1. **P1 — 报告归属校验先于路径解析，仍可发布另一 ticker 的报告。**
   `run_one` 在原始 `saved_path` 上检查文件名和父目录前缀，随后 `_relative_report_path` 才执行 `resolve()`，并直接发布解析后的路径，没有重新检查归属。
   离线通过 `run_comparison` 复现两种情况：
   - `reports/AAPL_<stamp>` 是指向 `reports/MSFT_<stamp>` 的目录符号链接；AAPL 行仍为 `SUCCESS / Buy`，两行的 `report_path` 都变为 MSFT 的 `complete_report.md`。
   - AAPL 目录里的 `complete_report.md` 是指向 MSFT `notes.md` 的文件符号链接；AAPL 行仍为 `SUCCESS`，公开路径直接变为 `reports/MSFT_<stamp>/notes.md`。
   两种错误引用均进入返回值、比较 Markdown 和 manifest，违反 FR-A / INV-A。请对**最终发布的解析后路径**统一检查结果根、`reports/{精确 ticker}_{合法 stamp}/complete_report.md` 结构和归属，不能仅凭原始路径的字符串前缀通过。补目录链接、文件链接及正常路径对照；错误行应为 `FAILED`，评级/摘要/路径为 `null`，比较为 `PARTIAL`，另一标的报告及内容保留。
   [原始路径检查](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/094e2a700f56144551261bfcabc5e15bff3efcac/src/tradingagents/enhancements/comparison.py#L299-L313) · [解析和发布路径](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/094e2a700f56144551261bfcabc5e15bff3efcac/src/tradingagents/enhancements/comparison.py#L249-L260)

2. **P2 — stock-only 预检漏掉非美元计价的 crypto，仍沿用股票分析管线。**
   `_is_stock_symbol` 只排除五种 crypto 后缀；`normalize_symbol` 不会将 `BTC-EUR`、`ETH-GBP`、`BTC-JPY` 转成这些后缀。这三个输入在离线正式入口中均被接受，graph 调用记录的 `asset_type` 均为 `stock`，并写出了成功比较工件，未实现 draft-0.4 的非股票预检拒绝约定。
   请补齐受支持 ticker 语法下的非股票识别，或与 D 明确一个可确定验证的股票输入范围；不要仅补一个示例后缀。增加非美元 crypto 在两个输入位置的负例，断言 `UNSUPPORTED_ASSET_TYPE`、零 graph/save 调用和零比较工件，并保留合法股票符号的正例。
   [资产预检](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/094e2a700f56144551261bfcabc5e15bff3efcac/src/tradingagents/enhancements/comparison.py#L139-L158) · [后缀集合](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/094e2a700f56144551261bfcabc5e15bff3efcac/src/tradingagents/enhancements/comparison.py#L41)

### 代码、元数据与验证

- 无新增运行时依赖；继续顺序复用上游两次分析及报告保存，无额外模型调用。比较 ID 和 UTC 生成时间、不可变结果及双工件派生方式保持原设计；C 的 `test_manifest.py` 相对 base 未改。
- 本地使用 Python **3.13.18**。在隔离工作树设 `PYTHONPATH=src:.`，确保加载审查 head；下列 `<项目 Python>` 指主仓库 `.venv/bin/python`：

  ```bash
  PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest test/offline/test_comparison.py -q --tb=line --disable-warnings
  PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -q --tb=line --disable-warnings
  <项目 Python> scripts/check_governance.py --base c75bd9850daf89fcf6969972c1bc7b8e0c8f277e
  <项目 Python> -m ruff check .
  <项目 Python> -m mypy scripts/check_governance.py
  <项目 Python> -m pip check
  git diff --check c75bd9850daf89fcf6969972c1bc7b8e0c8f277e...HEAD
  ```

- **A 专项：38 passed。全量：1570 passed、29 failed、1 skipped、1 deselected、100 subtests passed。** 29 项全部属于已有 C manifest/CLI 未实现验收；没有新增的既有套件失败。治理、全仓 Ruff、治理脚本 mypy、`pip check` 和 PR 差异空白检查均通过；该 mypy 命令不覆盖 `comparison.py`。
- 另用仓库外临时探针 `/tmp/opencode/test_pr8_review.py` 运行：`PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -c pyproject.toml /tmp/opencode/test_pr8_review.py -q --tb=short --disable-warnings`，得到 **5 failed、6 passed**。5 个失败对应上述两种链接归属及三种非美元 crypto；6 个通过包括四种非股票拒绝对照、真实上游报告写入和摘要分支对照。这些是审查新增负例，不计入 PR 自带 38 项结果，未修改生产代码或正式测试。
- 远端 [PR CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45183810386) 与 [Push CI](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45183800283) 的失败日志均为 **29 failed、1570 passed**，失败归属与本地一致。治理、全仓 Ruff、clean-install smoke 和 safety review 检查通过。PR 当前为 draft、`MERGEABLE / UNSTABLE`，无已提交的 GitHub review；不能据此宣称完整 CI 通过或已获批准。
- 人工指令记录：用户要求本地落盘并提供可复制 Markdown，不代发回复；本轮遵守该边界。完整 TUI `/export` 无工具入口，待人工导出到 `transcripts/raw/` 后补实际链接；未合成 transcript。

### 结论

**CHANGES REQUIRED。** 上轮异常脱敏、状态身份与多行摘要的具体问题已修复，报告归属和资产范围仍存在可复现的边界遗漏。请修复上述 P1/P2 并补正式入口回归，在新 head 重新送审。29 项 C 基线红测不归因于 A；本轮返工依据是这两项独立复现的问题。

## PR #6 · 第五轮复审 · 2026-11-23

- PR：https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6
- Reviewed head：`771cf1a00c622fe05e98166dfba80909eab1e0e1`；base：`c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`。
- 仅复核第四轮提出的直接 `merge_once` 日期窗口问题。当前实现会在模型调用前拒绝未来、过期、缺失和非法日期，并保留窗口起止日合法输入；新增负例通过。
- B 专项：56 passed；Ruff、治理脚本 mypy、pip check、diff check 通过。远端 B 专项通过。全量 29 项失败属 C manifest/CLI；safety review 停在共享语义门禁。
- 本轮按用户要求**未向 GitHub 发布 comment 或 review**。完整验证见[本轮复审记录](verification/pr6-review-005.md)。TUI `/export` 待人工执行。

**APPROVE。** 上一轮唯一未解决项已修复。此意见仅针对 PR 当前 head 的 B 代码审查范围，不代表全量 CI 全绿，也未执行合并。

## PR #8 · 第二轮复审 · `7242599` · 2026-11-23

- **仓库 / PR：** [sui-feng-cb/CS5351-TradingAgents #8](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/8)
- **审查人：** OpenCode，按用户要求针对本次提交代码复审；未向 GitHub 发布 comment 或 review。
- **Base：** `c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`；上轮 head：`094e2a700f56144551261bfcabc5e15bff3efcac`。
- **Reviewed head：** `72425994e6b923aeb78ce2b505564e7978c0aa25`。
- **范围：** FR-A、NFR-A、INV-A、SEC-01，ADR-001/003，A-IC-001 draft-0.4。核对本 PR 三个提交、相对 base 的全部 7 文件差异，重点审查新增提交 `7242599`。
- **人工限定：** 暂时忽略未同步 main 导致的两个文档冲突，不以此要求本轮代码返工。主工作区保持 `main` / `0a48402`，在隔离工作树验证固定 PR head。

### 上轮发现复验

1. **P1 报告归属问题已修复。** `_relative_report_path` 拒绝报告文件和直接父目录符号链接，使用 `resolve(strict=True)` 后检查结果根、三段相对路径、精确 ticker 与时间戳格式以及 `complete_report.md` 文件名。上轮目录链接到 MSFT 报告、文件链接到 MSFT `notes.md` 的负例均返回 `FAILED / REPORT_ATTRIBUTION_FAILED`，评级、摘要、路径为 `null`；比较为 `PARTIAL`，另一标的报告保留。独立探针还确认另一标的报告内容正确。
   [实现](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/72425994e6b923aeb78ce2b505564e7978c0aa25/src/tradingagents/enhancements/comparison.py#L269-L295) · [正式入口回归](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/72425994e6b923aeb78ce2b505564e7978c0aa25/test/offline/test_comparison.py#L966-L986)
2. **P2 非美元 crypto 问题已修复。** 增加已知 crypto base 与常见报价币种组合识别。`BTC-EUR`、`ETH-GBP`、`BTC-JPY` 均在预检返回 `UNSUPPORTED_ASSET_TYPE`；正式测试覆盖两个输入位置、零 graph/save 调用和零比较工件，`BRK-B` 股票对照通过。实现与本次 draft-0.4 明列的符号识别范围一致。
   [实现](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/72425994e6b923aeb78ce2b505564e7978c0aa25/src/tradingagents/enhancements/comparison.py#L154-L178) · [输入回归](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/72425994e6b923aeb78ce2b505564e7978c0aa25/test/offline/test_comparison.py#L989-L1010)
3. **此前修复未回归。** 异常固定安全文案、错 ticker/日期拒绝、多行摘要、REVIEW 成功语义及两个单失败方向的报告保留测试继续通过。真实上游报告写入器的正常双股票对照、摘要标题后换行和空正文 fallback 对照也通过。

### 本轮代码审查意见

**未发现新的阻塞性代码问题。** 路径归属判断集中到最终路径处理函数，专用异常映射为固定公开原因；输入预检仍在任何 graph 调用和工件写入之前。新增正式回归使用真实符号链接和公开比较入口。继续复用上游分析及报告保存，无新增运行时依赖、provider 或模型调用，比较 ID、UTC 时间和不可变结果派生 Markdown/manifest 的方式保持一致。C 的验收文件相对 base 未变。

非阻塞记录：远端 PR 描述仍写 38 项旧专项结果，可更新为新 head 的 40 项及本轮验证摘要；这不影响本轮代码通过结论。

### 验证证据

在隔离工作树 `/tmp/opencode/pr8-review-7242599` 使用项目 Python 3.13.18；`<项目 Python>` 为主仓库 `.venv/bin/python`：

```bash
PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest test/offline/test_comparison.py -q --tb=line --disable-warnings
PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -c pyproject.toml /tmp/opencode/test_pr8_review.py -q --tb=short --disable-warnings
PYTHONPATH=src:. TZ=America/New_York <项目 Python> -m pytest -q --tb=line --disable-warnings
<项目 Python> scripts/check_governance.py --base c75bd9850daf89fcf6969972c1bc7b8e0c8f277e
<项目 Python> -m ruff check .
<项目 Python> -m mypy scripts/check_governance.py
<项目 Python> -m pip check
git diff --check c75bd98...HEAD
git diff --quiet c75bd98 HEAD -- test/offline/test_manifest.py
```

- **A 专项 40 passed；上轮独立探针 11 passed（上轮为 5 failed、6 passed）。**
- **完整默认离线套件：1572 passed、29 failed、1 skipped、1 deselected、100 subtests passed。** 29 项全部来自 C manifest 模块/CLI 尚未实现的既有验收，没有 A 或其他既有套件新增失败。
- 带 base 的治理、全仓 Ruff、治理脚本 mypy、`pip check`、PR 差异空白及 C 测试未改检查通过；mypy 仅覆盖治理脚本。
- 远端最新 [CI run 45195153994](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45195153994) 的测试任务同样为 **29 failed、1572 passed**，逐项失败均属于 `test_manifest.py`；治理、Ruff、clean-install smoke 通过。读取命令：`gh run view 45195153994 --job 137763507575 -R sui-feng-cb/CS5351-TradingAgents --log-failed`。
- 当前 GitHub 无已提交的 review。完整 TUI `/export` 仍需人工导出并补实际链接；本轮只记录真实验证和人工限定，没有生成替代 transcript。

### 结论

**APPROVE。** 上轮两个未解决项均已修复并通过原独立负例，新增正式回归与完整回归结果支持本轮代码通过。建议通过 PR #8 当前 head 的代码审查。按委托，两个文档冲突暂不纳入本轮判断；此结论限于上述提交代码，不表示当前冲突已解决、完整 CI 已全绿、D 的契约确认已完成或 GitHub 已获批准。未执行提交、推送或合并。

## PR #9 · C 保存失败记录修复复审 · 2026-11-24

- **仓库 / PR：** [sui-feng-cb/CS5351-TradingAgents #9](https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/9)
- **审查人：** OpenCode，按用户要求进行本地复审。
- **Base：** `6ad32855d84cb9e77f03ee9e1cf3661a916572db`；上轮 head：`ac2c5ca33d7298669f434a23b9bdf608a4c5a1c0`。
- **Reviewed head：** `2a245507a77839823f9e380335f45214d0d7544d`；重点核对该修复提交的 9 文件差异及 `f8722e0` 同步后的状态。
- **范围：** 仅复核上轮 P2“保存失败与主动跳过写出相同清单”，依据 FR-C、SEC-01 / INV-SECRET、ADR-001/003 和 C v1 契约；按本轮指令不扩大审查或新增要求。
- **人工确认：** 用户在本次对话中明确同意保留 v1 字段结构：`status` 表达分析结果，分析成功但报告保存失败时仍为 `succeeded`，通过已有 `error` 写入固定的 `report_save_failed` / `Report save failed.`；查询保留匹配记录并给出 warning。

### 上轮发现复验

1. **保存失败已与主动跳过区分。** `_offer_reports` 返回内部 `save_failed` 标记，调用方将其转换为已有 `error` 字段；该标记不进入公开 manifest。分析成功、保存异常时记录 `status="succeeded"`、固定错误码和文案以及 null 报告路径；主动跳过保存时保持 `error=null`。
   [运行记录](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/2a245507a77839823f9e380335f45214d0d7544d/src/cli/run.py#L514-L532)
2. **查询保留记录并提示失败。** `_load_one` 识别 `report_save_failed` 后追加固定 warning，仍返回匹配记录；真实 Typer JSON 查询回归同时验证保存失败提示和跳过保存无此提示。
   [查询处理](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/2a245507a77839823f9e380335f45214d0d7544d/src/tradingagents/enhancements/manifest.py#L375-L390)
3. **错误安全性与既有行为通过。** 保存异常使用固定终端提示，不保存异常原文；测试断言 manifest 和查询输出不含合成敏感标记、异常类型或 traceback，并验证保存失败后仍显示报告。正常保存的实际相对路径、主动跳过、分析异常及原有 C 回归均通过。
4. **契约与 schema 已同步。** v1 顶层字段与查询 JSON 结构保持原样；接口契约、schema 描述、测试计划、追踪和验证记录已更新到用户确认的 status/error 语义。

### 验证证据

在固定 head 使用项目 Python **3.13.18** 执行：

```bash
TZ=America/New_York .venv/bin/python -m pytest -q test/offline/test_manifest.py --tb=short --disable-warnings
TZ=America/New_York .venv/bin/python -m pytest -q test/offline/test_manifest.py -k 'report_save_failure or skipped_save_control or save_then_show or saved_report_path' --tb=short --disable-warnings
TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
.venv/bin/python scripts/check_governance.py --base 6ad32855d84cb9e77f03ee9e1cf3661a916572db
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy scripts/check_governance.py
.venv/bin/python -m pip check
git diff --check 6ad3285...HEAD -- . ':!transcripts/raw'
git diff --check 2a245507^ 2a245507
```

- **C 专项：50 passed；本轮定向回归：5 passed、45 deselected。** 新增三项测试覆盖保存失败、主动跳过及真实 CLI 查询告警，预期值使用固定字面量。
- **完整默认离线套件：1678 passed、1 skipped、2 deselected、24 warnings、100 subtests passed。** 治理、全仓 Ruff、治理脚本 mypy、依赖一致性和上述差异空白检查均通过；mypy 命令只覆盖治理脚本。
- 只读查询 `gh run view ... --json headSha,event,conclusion` 确认 [PR CI 45218398337](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45218398337) 与 [push CI 45218380901](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45218380901) 均属于本轮 head 且为 SUCCESS。`gh pr checks 9 -R sui-feng-cb/CS5351-TradingAgents` 显示测试、B 专项、治理、Ruff、clean-install smoke 和 safety review 全部通过。
- 最新 PR 状态为 `MERGEABLE`，GitHub 已提交 reviews 仍为空。本轮仅本地记录批准建议，未向 GitHub 发布 comment/review，未提交、推送或合并。
- 主工作区从干净的 main 临时 detach 至审查 head，验证后已恢复原 `main` / `6ad32855d84cb9e77f03ee9e1cf3661a916572db`。未编辑应用代码或正式测试。会话按 `session-artifacts` 工作流记录；完整 TUI `/export` 无工具入口，待人工导出至 `transcripts/raw/` 后补实际链接，未合成 transcript。

### 结论

**APPROVE。** 上轮唯一未解决项已按用户确认的 v1 语义修复，保存失败与主动跳过可明确区分，查询告警及记录保留行为符合约定，专项、完整回归和最新 head CI 全部通过。建议通过 PR #9 当前 head 的代码审查。本轮不增加其他要求；该结论是本地复审意见。

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
