## PR #6 第四轮复审 — CHANGES REQUIRED

- PR：https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6
- 审查 head：`4a9afc4fc017ef9dbbd720ff86541491c06a99fd`
- Base main：`c75bd9850daf89fcf6969972c1bc7b8e0c8f277e`
- GitHub review：`CHANGES_REQUESTED`，https://github.com/sui-feng-cb/CS5351-TradingAgents/pull/6#pullrequestreview-6022342508
- 范围：简化验收标准中的时间/数量边界、schema/失败处理、证据校验及范围声明。

### 已确认

- PR 明确限定为可注入核心组件，默认 fetcher/model 的待办没有冒充完整生产实现。
- `fetch_records` 先过滤窗口日期，再去重和限量；每 ticker 上限为 5。
- 模型异常、非法 JSON 和畸形 schema 现在进入 `ANALYSIS_INCOMPLETE`，保留失败原因及未归并记录。
- validator 对伪造/跨运行 evidence、声明的 ticker/date/source 不匹配，以及事件必需字段有校验。
- 语义评估门禁增加零失败和完整覆盖要求。
- B 专项测试 53 项通过；Ruff、治理脚本 mypy、pip check 和 diff check 通过。

### 阻塞问题

**P1：`merge_once` 直接入口没有验证每条记录的日期是否落在窗口内。**

`src/tradingagents/enhancements/events.py` 的 `_validate_merge_input` 检查 ticker 数量、窗口跨度、run/evidence 所属及每 ticker 数量，但没有校验记录自身的日期。

当前 head 的离线复现：窗口 `2026-11-15..2026-11-22` 下，直接传入两条 `2026-11-23` 记录，返回 `merged` 并发布未来证据；传入两条 `2026-11-01` 过期记录也返回 `merged`。因此直接归并入口仍违反简化标准的“只接受窗口内新闻”。请验证每条记录日期存在、可解析且在窗口内，并补直接调用的未来、过期、缺失/非法日期负例。

### 验证证据

- `TZ=America/New_York .venv/bin/python -m pytest test/offline/test_events.py -q`：**53 passed**。
- `TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings`：**1615 passed、29 failed、1 skipped、2 deselected、100 subtests passed**；29 项均为既有 C manifest/CLI 契约。
- `.venv/bin/python -m ruff check .`：通过。
- `.venv/bin/python -m mypy scripts/check_governance.py`：通过。
- `.venv/bin/python -m pip check`：通过。
- `git diff --check c75bd9850daf89fcf6969972c1bc7b8e0c8f277e...HEAD`：通过。
- `.venv/bin/python scripts/check_governance.py --base origin/main`：schema/layout/permissions 基础检查通过；随后被团队协调中的共享语义门禁阻断。此项不归因于 B。
- 远端 B 专项 CI：53 passed；远端全量作业同样只有 29 项 C 失败。无真实模型/API 请求。

### 结论

**CHANGES REQUIRED。** 简化验收项基本完成，但直接入口仍能把窗口外新闻发布为有效事件。修复日期校验并补负例后，在最新 head 上复审；其余已通过项无需重复整改。
