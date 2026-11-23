## PR #6 第三轮复审 — CHANGES REQUIRED

- PR：https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6
- 审查 head：`26bd176d5d6264c356a9cd48fd5de3784c8b8c38`
- 上轮 head：`1f57b394e50dd23ad75e682ad1aee29e53e7ec28`
- Base main：`c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`
- GitHub review：`CHANGES_REQUESTED`，2026-11-23，https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6#pullrequestreview-6021522094
- 审查：OpenCode，2026-11-23；范围 FR-B、NFR-B、INV-B、INV-ASOF、BASE-01、GOV-01，以及接口契约和 ADR-001 的扩展边界。

### 第 7 条与 CI 责任归属

本轮用户明确确认：**团队已批准固定语义评估集，并已测试通过**。接受并记录这一人工确认，不再把“数据集尚未获团队批准”列为 B 的阻塞项。本轮未重新调用真实模型；人工确认和仓库中既有评估记录均不表述成本轮独立实测。

全量 CI 的 **29 项失败全部属于既有 C manifest/CLI 契约**，不归因于 B。`safety review` 在共享 `check_governance.py --base` 步骤触发硬编码语义门禁，尚未进入后续独立安全评审检查。团队批准后的共享门禁接入由协调人跟进，不要求 B 绕过或删除检查，也不以这两个 CI 原因作为本轮功能审查不通过的依据。

### 已确认的整改

- 已合入当前远端 main；GitHub compare 为 ahead 9 / behind 0，状态 MERGEABLE。
- B 专项 CI 已限定为 `pytest test/offline/test_events.py -q`，Python 3.13；远端 **39 passed**。
- live 测试的 I001 导入错误已修复；全仓 Ruff 本地和远端均通过。
- main 的共享 rules、接口及上游数据层未被本 PR 覆盖；模块路径符合团队约定，无新增运行时依赖。

### 尚未解决的功能问题

GitHub tree API 与当前源码核对确认：`events.py`、`test_events.py`、固定数据集和评估日志与上轮 head 的 blob SHA 完全相同。live runner 的改动仅为导入格式。因此不能将 CI 范围和格式整改视为下列问题已修复。

1. **P1：未来新闻仍能被发布为已验证事件，输入数量限制仍可绕过。**
   [events.py:465](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L465) 抓取时先截前 5 条，无日期过滤；[merge_once:659](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L659) 无统一输入校验。本轮离线复现：窗口 `2026-11-15..2026-11-22`，每标的前 5 条为 `2026-11-23`、第 6 条为窗口内新闻，最终保留 10 条未来新闻并截掉合法项；其中两条未来证据仍被发布为 `merged`。直接传入每标的 6 条记录也发布全部 12 条。请先过滤有效日期、去重和限量，并在正式归并入口校验 ticker、窗口、记录归属和数量；补独立负例。

2. **P1：正式新闻和模型默认入口仍未接通。**
   [默认 fetcher:431](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L431) 仍抛 `NotImplementedError`；[默认模型:612](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L612) 仍为占位。本轮均已复现。请协调现有数据层和模型客户端适配，并测试真实入口的离线传输替身及无隐藏重试的单次调用边界；若仅交付可注入核心组件，应明确缩小本 PR 验收范围，保留 FR-B 完整集成待办。

3. **P2：输出 schema 仍可导致崩溃或发布空事件。**
   [解析:585](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L585) 仅检查外层列表，[validator:750](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L750) 直接取字段。本轮复现 `{"events":[null]}` 抛 `AttributeError`、`{"events":[{"evidence_ids":[{}]}]}` 抛 `TypeError`；只含两个合法证据 ID、缺 event_id/summary 的事件仍发布为 `merged` 且字段为空。请验证完整类型和必要非空字段，畸形输出进入可观测失败路径，保留 unmerged 记录。

4. **P2：模型异常和解析失败仍被报告为“没有共同事件”。**
   [_fail_closed:601](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/src/tradingagents/enhancements/events.py#L601) 固定返回 `NO_COMMON_EVENT`，不保留失败原因。本轮模型异常、非法 JSON 和默认模型占位均返回该状态。请区分未完成分析、无数据和正常空分组，补相应回归。

### 获批数据集之外的评估工具问题

承认固定数据集获批及团队报告的通过结果，同时保留 runner 的技术缺陷说明：[run_live_eval:198](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/test/live/test_semantic_eval_live.py#L198) 使用单独的 same/different prompt，并跳过 API/解析失败项；[_assert_gate:269](https://github.com/sui-feng-cb/CS5351-TradingAgents/blob/26bd176d5d6264c356a9cd48fd5de3784c8b8c38/test/live/test_semantic_eval_live.py#L269) 只检查 precision/recall。本轮离线向 gate 传入 `TP=1, FP=0, FN=0, attempted=1, failed=23, precision=recall=1`，仍通过。数据集获批不改变该失败处理行为。建议协调人将真实归并流程和完整覆盖检查接入可重放评估；本轮即使不以此单独阻塞，前述功能问题仍足以阻止批准。

### 验证证据

在上述 PR head、项目 Python **3.13.18** 实际执行：

| 检查 | 结果 |
|---|---|
| `TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings` | **1601 passed、29 failed、1 skipped、2 deselected、100 subtests passed**；29 项均为 C 既有契约 |
| `.venv/bin/python -m ruff check .` | 通过 |
| `.venv/bin/python -m mypy scripts/check_governance.py` | 通过；覆盖范围仅治理脚本 |
| `.venv/bin/python -m pip check` | 通过 |
| `git diff --check origin/main...HEAD` | 通过 |
| `.venv/bin/python scripts/check_governance.py --base origin/main` | schema/layout/permissions/基础凭证模式扫描通过，随后共享语义门禁失败 |
| 独立离线 Python 探针 | 复现未来证据、数量越限、schema 崩溃/空字段、失败状态、默认入口占位及评估 gate 漏检；无网络请求 |

远端 [CI run 45166564239](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45166564239) 的全量结果与本地一致；B 专项 39 项、Ruff、clean-install smoke 和 governance 均通过。[Safety run 45166564228](https://github.com/sui-feng-cb/CS5351-TradingAgents/actions/runs/45166564228) 的失败原因如前述。

### 结论

**CHANGES REQUIRED。** 第 7 条的团队批准已确认，既有 C 失败和共享语义门禁均已正确归因；本轮不据此要求 B 返工。但独立复核仍确认时间/数量边界、正式入口、输出 schema 和失败状态缺陷，尚不足以批准当前 head。请修复并补负例，或提交明确缩小的交付范围后再申请通过。

完整会话导出无法通过当前工具执行。请在 OpenCode TUI 执行 `/export` 保存到 `transcripts/raw/`，再补真实链接；本记录不是完整会话导出。
