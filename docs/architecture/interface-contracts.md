# Interface contracts

Status: A-IC-001 is formally frozen. Contract approver and acceptance owner: D.
Plan and tests-first intent approved by member A on 2026-11-23. B–C contracts
remain proposals. The D evaluator and graph interface are implemented and
locally tested against the merged PR #2 test contract. Remote CI, independent
safety review and integration review remain pending.

- A: exactly two distinct tickers, shared canonical date/config; sequentially call
  upstream propagate/save_reports, isolating each run. Return per-ticker status,
  authoritative rating, summary and relative report path, plus a comparison
  report and required `comparison_manifest.json`; input-level validation errors
  produce no artifacts, while per-ticker run failures still produce both
  artifacts (A-IC-001, frozen 2026-11-23; see the A-IC-001 contract and section 7).
- B: 2–3 tickers, window ≤7 days, ≤5 records per ticker. Each record contains a
  run-scoped evidence ID, ticker, published_at, source and title/snippet. Output
  groups reference input IDs; deterministic validation requires ≥2 tickers and
  correct provenance. At most one grouping call; no silent SDK retries in that cap.
- C: versioned manifest records run ID, ticker, date/as-of, start/end, available
  code version, configured providers/models/analysts, status and relative paths.
  Unknowns are explicit. Query is read-only and tolerates individual bad files.
  Storage is one `run_manifest.json` per run directory plus a read-only local
  scan (not a shared index). Contract below is a tests-first proposal awaiting
  non-C approval (`docs/testing/c-manifest-test-plan.md`).

  ### C manifest v1 proposal

  - One manifest per execution attempt; `run_id` is a fresh UUID per attempt.
  - Frozen field whitelist: schema_version, run_id, ticker, asset_type,
    trade_date, as_of, started_at, finished_at, code_version, analysts, models,
    configured_data_vendors, status, reports, error, unknown_fields. Extra
    top-level keys are rejected.
  - `status` is `running | succeeded | failed`; analysis outcome and report-save
    outcome are expressed separately, not as one overloaded field.
  - UTC-aware ISO-8601 timestamps; `trade_date`/`as_of` remain `YYYY-MM-DD`.
  - `models` validates per-tier provider/model; `configured_data_vendors` is the
    source configuration, not per-request provenance.
  - Errors store a fixed code plus safe text; no traceback blob, no secret.
  - `reports` paths are relative to the results root and are the paths
    `save_reports` actually returned; a skipped save is `null`; a reused custom
    save path updates the existing record by explicit run association (team
    confirmation pending).
  - Query is read-only; bad JSON, unknown schema_version, missing declared
    reports and out-of-root paths each warn and the scan continues; no report is
    modified or deleted. A missing-manifest warning is only for recognizable run
    directories.
  - Same-day reruns and checkpoint resumes keep prior records and do not change
    existing checkpoint behavior.
  - Team-confirmation items not yet locked: A/Python run-association interface,
    backtest coverage, and the reused-custom-path policy.
- D: market execution status and snapshot date are machine metadata, not inferred
  from model text. The proposed public mode is `standard` (default; preserve
  upstream behavior) or `team` (apply the qualification gate). A team-mode run
  checks selected/actual market-analyst execution, independently verified
  market-evidence status, snapshot date and the exact five-tier final rating.
  Missing/unavailable/not-run/future/stale evidence or invalid rating yields
  authoritative `REVIEW` plus stable reason codes before any final state is
  streamed, reported or recorded for settlement. `REVIEW` is not queued for
  settlement/reflection. The existing OHLCV stale-data bound
  (`MAX_OHLCV_STALE_DAYS`, currently 10 calendar days) is the proposed freshness
  limit; D tests must pin the boundary and ADR-002 records this reuse.

### D qualification boundary

- Python callers select `decision_mode="team"` on `TradingAgentsGraph`; the CLI
  exposes `--decision-mode standard|team`, defaulting to `standard` for upstream
  compatibility. The mode and selected analysts are run metadata.
- Evidence acquisition returns typed metadata (`valid`, `unavailable`, or
  `not_run`) and a canonical `snapshot_date` when valid. Market-analyst execution
  status is a separate field. It uses deterministic market-data code, not a
  model-generated report. An absent evidence object, unknown status,
  missing/malformed date, date after `trade_date`, or data older than the
  existing 10-calendar-day OHLCV freshness bound fails closed.
- A deterministic graph node runs after the Portfolio Manager and before graph
  completion/publication. It writes authoritative `final_rating`, eligibility
  status and ordered reason codes. Ineligible output replaces the public final
  decision text with a `REVIEW` notice; model candidate prose cannot remain the
  apparent final call. Standard mode passes through the existing flow.
- Team-mode final state exposes `market_analyst_status`,
  `market_evidence_status`, `snapshot_date` and `eligibility_reason_codes`.
  The reason list is empty on an eligible result. Public graph stream frames
  and CLI live decision panels only publish a final rating after qualification.
- Initial reason-code proposal (report all applicable causes in this order):
  `market_analyst_not_run`, `market_analyst_failed`,
  `market_analyst_invalid_status`,
  `market_evidence_missing`, `market_evidence_not_run`,
  `market_evidence_unavailable`, `market_evidence_invalid_status`,
  `market_snapshot_date_missing`, `market_snapshot_date_invalid`,
  `market_snapshot_after_analysis`, `market_snapshot_stale`,
  `analysis_date_invalid`, and `invalid_rating`. The D test plan fixes their expected mappings before
  implementation.

The local D implementation uses a frozen `EligibilityDecision` with
`final_rating`, `eligible`, a tuple of `reason_codes`, and `user_message`.
`evaluate_eligibility` is a team-only evaluator; non-team modes raise `ValueError`
and standard graph runs do not invoke it. Team graph state records
`eligibility_status` (`eligible`/`ineligible`), `eligibility_checked`, the reason
list and `eligibility_message`. Initial statuses are `not_run`, with a null
snapshot date. Actual analyst execution, rather than report claims, updates the
execution status. The trusted snapshot adapter uses the requested ticker/date;
stale-data exceptions expose the actual row date as typed metadata. A valid
evidence status means rows were acquired; the gate separately checks freshness.
Candidate fields are internal, cleared at qualification, and omitted from
`stream_run`. No new manifest schema or A–C feature is introduced here.

PR #3 corrections further require a finite latest Close before the adapter emits
valid evidence. Invalid price content maps to existing unavailable-evidence
handling. Free-text PM candidates in team mode use only complete own-rating
fields with exact five-tier values; missing/invalid/conflicting fields cannot be
rescued by a quoted consensus rating. Standard parsing is unchanged. Public
`stream_run` states withhold the Trader proposal until eligibility has completed
successfully; rejected completion clears it. These rules apply to values and
nested task states and are covered by the expanded graph and team-rating tests.
Pre-fix team checkpoints start a fresh run under the versioned team signature;
standard checkpoint IDs remain unchanged.

For team free text, a CommonMark line break can delimit a rating field. A
newline inside a code span cannot delimit a field. Other lines in the same
paragraph remain subject to exact-rating validation.

Use UTC-aware stored timestamps; analysis dates remain explicit trading dates.
Freeze schema, null semantics, identifiers and errors before parallel coding.
Reserve `test/offline/test_comparison.py`, `test_events.py`, `test_manifest.py`,
`test_eligibility.py` for owners A, B, C, D respectively. Shared CLI/graph/report
files require coordinated integration PRs; no direct private cross-module imports.

## A-IC-001 contract (frozen 2026-11-23)

Status: FROZEN; contract approver and acceptance owner: D (see section 7).
Internal subsections 1–6 belong to A-IC-001. Tests-first is authorized;
implementation waits for approval of the written tests.

### 1. 范围

- 恰好两个不同且有效的 ticker，以及一个共同分析日期。
- 顺序调用上游现有 graph 两次；不新增 provider、不并行、不做组合模拟。
- 每个 ticker 保存自己的完整上游报告；另生成一份比较 Markdown。
- 强制同时生成 `comparison_manifest.json`；它是比较级工件，不是 C 的
  `run_manifest.json`。A 不写、不改 C 的 manifest schema。
- A 只使用上游权威结果，不从模型正文重新解析评级，不把 `REVIEW` 当成运行失败。

### 2. 比较 Markdown 字段与顺序

主表固定为 7 列，顺序不得调整，不得增删列：

| 顺序 | 字段 | 类型 | 规则 |
|---:|---|---|---|
| 1 | `ticker` | string | 已通过 `safe_ticker_component` 的 canonical ticker。 |
| 2 | `analysis_date` | string | 规范化 `YYYY-MM-DD`；两行相同且等于输入日期。 |
| 3 | `status` | enum | 仅 `SUCCESS` 或 `FAILED`，大写。 |
| 4 | `final_rating` | enum/null | `SUCCESS` 时为 `Buy` / `Overweight` / `Hold` / `Underweight` / `Sell` / `REVIEW`；`FAILED` 时为 `null`。 |
| 5 | `summary` | string/null | `SUCCESS` 时非空单行文本；`FAILED` 时为 `null`。 |
| 6 | `report_path` | string/null | `SUCCESS` 时相对 `config["results_dir"]` 的 `complete_report.md` 路径；`FAILED` 时为 `null`。不得为绝对路径、不得含 `..`、不得越出结果根目录。 |
| 7 | `failure_reason` | string/null | `SUCCESS` 时为 `null`；`FAILED` 时为非空稳定原因码字符串。 |

- 表格外可放标题、生成时间等元数据，但不得插入主表列。
- 行顺序与通过校验后的输入 ticker 顺序一致。
- `summary` 必须单行、空白折叠；Markdown 仅做必要转义。
- 结果根目录 = `TradingAgentsGraph.config["results_dir"]`。
- **A 不显式传 `save_path`，统一使用上游 `default_report_path()`**，因此
  `report_path` 固定形如 `reports/{ticker}_{stamp}/complete_report.md`，其中
  `stamp` 来自上游 `%Y%m%d_%H%M%S`。若未来需要显式传 `save_path`，必须另行
  修订本契约，并重新定义 `report_path` 格式；当前契约不支持显式 `save_path`。
- `comparison_report_path` 也相对结果根目录，形如
  `comparisons/{comparison_id}/comparison.md`。
- 测试用 `Path(config["results_dir"]) / report_path` 解析，不依赖机器绝对路径。

### 3. status / rating、空值与 summary

| 场景 | status | final_rating | 说明 |
|---|---|---|---|
| 上游运行完成，评级正常 | `SUCCESS` | 五级评级之一 | 正常结果。 |
| 上游运行完成，权威评级为 `REVIEW` | `SUCCESS` | `REVIEW` | 运行成功；`REVIEW` 是评级，不是失败。 |
| graph 抛错 | `FAILED` | `null` | 运行异常；不保留部分评级。 |
| 报告保存失败/`complete_report.md` 缺失 | `FAILED` | `null` | 结果不完整，整行按失败处理。 |
| 运行完成但没有可用权威评级 | `FAILED` | `null` | 原因码 `MISSING_OR_INVALID_FINAL_RATING`；不得从正文猜评级。 |

- `status=FAILED` 时 `final_rating`、`summary`、`report_path` 必须为 `null`；
  不得填另一 ticker 的评级、旧运行评级或模型正文中的评级。
- 空值统一为 JSON `null`；Markdown 中写字面量 `null`。禁止 `""`、`N/A`、`-`、“无”。
- 失败原因码：`GRAPH_FAILED`、`REPORT_SAVE_FAILED`、
  `MISSING_OR_INVALID_FINAL_RATING`、`INTERNAL_ERROR`；格式
  `<CODE>` 或 `<CODE>: <sanitized detail>`，不得含密钥、凭证 URL、账户数据。
- 摘要提取不得把 `SUCCESS` 改为 `FAILED`；删除 `SUMMARY_UNAVAILABLE` 失败码。

`summary` 来源：final_state 没有独立 summary 字段；只有 `final_trade_decision`
（渲染后的 PM Markdown）和 `final_rating`。按以下顺序提取：

| 模式 | 评级 | 提取顺序 |
|---|---|---|
| team | `REVIEW` | 1. `eligibility_message`（由 `_eligibility_step` 写入）<br>2. 无则取 `final_trade_decision` 首个非空段落（首段截断）<br>3. 仍为空则固定 fallback `"Summary unavailable from upstream final state."` |
| standard | `REVIEW` | 1. 取 `final_trade_decision` 首个非空段落（首段截断）；不假设 `eligibility_message` 存在<br>2. 仍为空则固定 fallback `"Summary unavailable from upstream final state."` |
| 任意 | 五级评级 | 1. 取 `final_trade_decision` 中 `**Executive Summary**:` 段<br>2. 无则取首个非空段落（首段截断）<br>3. 仍为空则固定 fallback `"Summary unavailable from upstream final state."` |

- team-mode `REVIEW` 的 `final_trade_decision` 是 `REVIEW ... Reason codes: ...`
  通知，不含 Executive Summary，因此优先 `eligibility_message`。
- standard-mode `REVIEW` 不保证有 `eligibility_message`，直接走首段截断。
- 提取只做确定性文本处理：不新增 LLM 调用、不跨 ticker、空白折叠、单行、最多
  500 字符；`SUCCESS` 的 `summary` 必须非空。

### 4. `comparison_manifest.json`（强制）

每次输入校验通过的比较，包括部分失败和两项均失败，必须同时写出
`comparison.md` 与 `comparison_manifest.json`。

| 字段 | 类型 | 规则 |
|---|---|---|
| `schema_version` | integer | 本契约为 `1`。 |
| `comparison_id` | string | 本次比较唯一 ID，不透明；不复用 C 的 run ID。 |
| `analysis_date` | string | 与两个 ticker 行相同。 |
| `generated_at` | string | UTC-aware RFC3339。 |
| `overall_status` | enum | `SUCCESS`（两行都成功）、`PARTIAL`（恰好一行失败）、`FAILED`（两行都失败）。 |
| `tickers` | array | 长度 2，顺序与输入一致；每项含上述 7 个字段。 |
| `comparison_report_path` | string | 比较 Markdown 相对结果根目录的路径。 |

- Markdown 与 manifest 由同一份不可变结果派生；Markdown 只做展示与必要转义。
- 两处 7 个字段逐项相等；`null` 在 Markdown 中显示为 `null`。
- 行顺序、`analysis_date`、`report_path`、`summary` 语义值必须一致。
- `overall_status` 必须能由两行 `status` 唯一推导。
- 任一工件写出失败即请求级失败；不得只保留一个并声称成功。

### 5. 输入校验

请求级规则：
- 必须恰好两个 ticker；空输入、单个、超过两个都拒绝。
- 两个 ticker 在归一化并通过 `safe_ticker_component` 后必须不同；相等为
  `DUPLICATE_TICKER`。
- 日期必须满足第 5.2 节的严格性。
- 输入级校验失败不启动任何 graph，不生成比较 Markdown 或 manifest；返回
  `INVALID_TICKER`、`DUPLICATE_TICKER`、`INVALID_DATE` 或 `FUTURE_DATE`。
- 不沿用交互式 `get_ticker` 的“空输入默认 SPY”行为；A 的两个 ticker 均必填。

#### 5.1 ticker 归一化与安全校验

1. 输入必须非空。
2. 调用 `normalize_symbol` 得到 canonical ticker；CLI 边界可用
   `normalize_ticker_symbol`，它委托给 `normalize_symbol`。
3. canonical ticker 必须再通过 `safe_ticker_component`：非空、`max_len=32`、
   仅允许上游 `_TICKER_PATH_RE` 的字符、拒绝纯点号。
4. 任一步抛错 -> 请求级 `INVALID_TICKER`；不启动 graph，不生成工件。
5. 两个 ticker 的“不同”在归一化并通过安全校验后比较。
6. 报告和 manifest 只使用通过安全校验的 canonical ticker。

`normalize_symbol` 对空/非字符串可能原样返回；`safe_ticker_component` 会拒绝
空值。A 不能因 `normalize_symbol` 未报错而跳过安全校验。

#### 5.2 日期严格性

- 最终权威是 `_validate_trade_date`：要求
  `datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value`，且
  `value <= get_current_date()`；不做 `strip()`，不做时区换算。
- `parse_analysis_date` 不能单独作为 A 的严格性依据：它会 `strip()`，并使用
  `strptime` + `isoformat()`；因此 `2026-1-1` 会被接受并变成 `2026-01-01`，
  带首尾空白的值也会被接受。这与 `_validate_trade_date` 的逐字 canonical
  要求不等价。
- A 若预检，必须二选一：
  1. 实现与 `_validate_trade_date` 等价的检查（逐字 canonical + 非未来）；或
  2. 不做预检，直接把原始日期交给 graph 的 `_validate_trade_date`。
- 不得把 `parse_analysis_date` 的宽松结果当作通过，也不得先 `strip()` 再声称
  输入是严格 `YYYY-MM-DD`。
- 失败映射：格式/canonical 失败为 `INVALID_DATE`；未来日期为 `FUTURE_DATE`；
  发生在 graph 运行前，属输入级错误，无工件。

#### 5.3 输入级与运行级边界

**输入级校验错误发生在任何 graph 运行之前，不生成任何比较工件；运行级失败发生在输入校验通过之后，仍必须生成包含 `FAILED` 行的 `comparison.md` 与 `comparison_manifest.json`。**

- 输入级：`INVALID_TICKER`、`DUPLICATE_TICKER`、`INVALID_DATE`、`FUTURE_DATE`。
- 运行级：`GRAPH_FAILED`、`REPORT_SAVE_FAILED`、
  `MISSING_OR_INVALID_FINAL_RATING`、`INTERNAL_ERROR`。
- 工件写出失败是单独的请求级失败，不得伪装成某个 ticker 的 `FAILED` 行，也不得
  声称比较成功。

### 6. 输出示例

成功 + `REVIEW`：

| ticker | analysis_date | status | final_rating | summary | report_path | failure_reason |
|---|---|---|---|---|---|---|
| AAPL | 2026-11-20 | SUCCESS | Buy | 需求与盈利预期支撑，维持建设性观点。 | reports/AAPL_20261120_120000/complete_report.md | null |
| MSFT | 2026-11-20 | SUCCESS | REVIEW | 关键证据不足，最终评级无法确认。 | reports/MSFT_20261120_120500/complete_report.md | null |

部分失败：

| ticker | analysis_date | status | final_rating | summary | report_path | failure_reason |
|---|---|---|---|---|---|---|
| AAPL | 2026-11-20 | SUCCESS | Hold | 多空因素接近平衡，维持中性。 | reports/AAPL_20261120_120000/complete_report.md | null |
| MSFT | 2026-11-20 | FAILED | null | null | null | GRAPH_FAILED: upstream analysis raised |

对应 JSON（相对路径）：

```json
{
  "schema_version": 1,
  "comparison_id": "cmp_01JEXAMPLE0000000000000000",
  "analysis_date": "2026-11-20",
  "generated_at": "2026-11-20T12:34:56Z",
  "overall_status": "PARTIAL",
  "tickers": [
    {
      "ticker": "AAPL",
      "analysis_date": "2026-11-20",
      "status": "SUCCESS",
      "final_rating": "Hold",
      "summary": "多空因素接近平衡，维持中性。",
      "report_path": "reports/AAPL_20261120_120000/complete_report.md",
      "failure_reason": null
    },
    {
      "ticker": "MSFT",
      "analysis_date": "2026-11-20",
      "status": "FAILED",
      "final_rating": null,
      "summary": null,
      "report_path": null,
      "failure_reason": "GRAPH_FAILED: upstream analysis raised"
    }
  ],
  "comparison_report_path": "comparisons/cmp_01JEXAMPLE0000000000000000/comparison.md"
}
```

## 7. A contract approval record (A-IC-001)

| Item | Value |
|---|---|
| Contract ID | A-IC-001 |
| Version | draft-0.3 |
| Contract status | FROZEN — approved by D; plan and tests-first intent approved by member A on 2026-11-23 |
| Contract approver | D |
| Acceptance owner | D |
| Approval date | 2026-11-23 |
| Approval basis | member A 于 2026-11-23 确认验收人与契约批准人均为 D（团队同意），并确认下方六项批准记录。 |
| Reviewed content | A-IC-001 draft-0.3, including the four draft-0.3 revisions: date strictness under `_validate_trade_date`; summary branches for team/standard REVIEW and five-tier ratings; results-root relative `report_path` using upstream `default_report_path()`; canonical ticker `safe_ticker_component` validation. Full clause text is in the A-IC-001 contract above. |
| Formal freeze | Frozen by the approval record below (2026-11-23). |
| Implementation gate | Tests-first authorized. No implementation before the written tests are approved. |

### Approval record (2026-11-23)

member A 于 2026-11-23 确认：

- 批准 FR-A + NFR-A 执行计划；
- 批准第 5 步 tests-first 测试意图；
- INV-A 登记；
- 本 PR 不接 CLI，CLI 另开集成 PR；
- A-IC-001 draft-0.3 由 DRAFT 转为正式冻结；
- 契约批准人：D；验收人：D。

This record is the formal freeze basis. Tests-first is authorized; implementation
remains gated on approval of the written tests.
