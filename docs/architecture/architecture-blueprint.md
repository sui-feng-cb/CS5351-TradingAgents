# Architecture Blueprint — B 模块：跨标的共同事件归并

> **Purpose** (D2)：范围、驱动因素、系统与组件边界、建议性 vs 权威性决策分界、agent 工作流、权限、验证、可观测性与变更政策。
>
> **Agent constraint**：Plan agent 生成任何代码前必读本文件。B 模块只能在「单次 LLM 归并 + 确定性 validator 权威」架构内提案；不得建议移除 `validator.py` 的权威地位，不得违反文件级权限白名单。

---

## 1. Scope

### What This Module Does

| In Scope | Detail |
|---|---|
| 输入 2–3 个 ticker 与 ≤7 天回看窗口 | `build_window()` 校验并确定日期窗口 |
| 复用上游新闻能力，每 ticker 取 ≤5 条结构化记录 | `news_source.fetch_records()`（只读适配，不改上游） |
| 为每条记录分配本次运行唯一 evidence ID | `EvidenceRegistry`：`ev-{run_id}-{ticker}-{seq}` |
| 将全量记录作为一组交模型归并，最多一次 LLM 调用 | `merger.merge_once()`（单次调用入口） |
| 确定性 validator 校验证据合法性并过滤 | `validator.validate()`（证据合法性唯一权威） |
| 输出状态机：`merged` / `no_common_event` / `data_unavailable` | `merger` 状态机 |

### What This Module Does NOT Do

| Out of Scope | Why |
|---|---|
| 新增新闻供应商 | v3 §3「不增加新闻供应商」 |
| 未来价格预测 / 热度评分 / 影响力排序 / 社交网络趋势 | v4 §4 FR-B 明确排除 |
| 修改上游 `tradingagents/`、`tests/`、`config` 行为 | 复用而非修改（D 协调迁移，`docs/baseline.md` 标注） |
| 跨会话/跨运行持久化 evidence 状态 | NFR-B 证据追溯只要求单次运行内解析率 100% |

---

## 2. Architectural Drivers

> **Source:** `docs/req/requirements.yaml`（FR-B-1..7、NFR-B-1..3、INV-B-1..5）

| ID | Statement (abbreviated) | Fit Criterion (abbreviated) |
|---|---|---|
| FR-B-1 | 输入 2–3 ticker、≤7 天窗口 | 2–3 ticker 成功；1/4 ticker、8 天失败 |
| FR-B-2 | 每 ticker ≤5 条，分配唯一 evidence ID | ID 本次运行唯一、字段齐全 |
| FR-B-3 | 全量记录一组交模型，最多一次 LLM 调用 | 调用次数 == 1 |
| FR-B-4 | 事件输出摘要、ticker、evidence | 符合结构化 schema |
| FR-B-5 | 事件 ≥2 ticker；证据不足留作未归并 | 单一 ticker 事件降级 |
| FR-B-6 | 无记录 / 无共同事件 状态区分 | 状态机三态正确 |
| FR-B-7 | 确定性 validator 校验证据 | 伪造 ID/错配字段被剔除 |
| NFR-B-1 | 证据 ID 解析率 100% | 无法解析 ID 数 == 0 |
| NFR-B-2 | 伪造/跨运行 ID == 0 | 负向测试断言 0 |
| NFR-B-3 | pairwise precision ≥0.80 / recall ≥0.70 | 固定语义评估集 + CI 门禁 |

**Full specifications:** `docs/architecture/trace-matrix.md`

---

## 3. System Boundaries

```
                          ┌────────────── SYSTEM BOUNDARY (src/event_merge/) ──────────────┐
                          │                                                                              │
 tickers + lookback ─────►│  input.build_window()  ─►  news_source.fetch_records()  ─►  EvidenceRegistry │
                          │                                                                              │
                          │  ┌──────────────────────── ADVISORY ────────────────────────┐                │
                          │  │  merger.merge_once()  ─►  LLM 建议层（events / unmerged） │                │
                          │  └──────────────────────────────┬───────────────────────────┘                │
                          │                                 │                                            │
                          │                                 ▼                                            │
                          │  ┌──────────────────── AUTHORITATIVE ─────────────────────┐                  │
                          │  │  validator.validate()  ─► 过滤 → 二次检查(≥2 ticker)   │                  │
                          │  └──────────────────────────────┬───────────────────────────┘                │
                          │                                 ▼                                            │
                          │                      最终输出（merged/no_common_event/data_unavailable）      │
                          └──────────────────────────────────────────────────────────────────────────────┘
```

### Boundary Rules

| Rule | Enforced By |
|---|---|
| 模型输出永不直接成为最终输出，必须先经 validator 过滤 | 流水线顺序：`merge_once()` → `validate()` |
| validator 是证据合法性的唯一权威 | `registry.issued_ids` + ticker/date/source 逐项比对（FR-B-7） |
| 每次归并最多一次 LLM 调用 | `merge_once()` 单次调用入口（INV-B-1） |
| 证据不足不强配，保留为未归并 | validator 二次检查 + `unmerged` 路径（INV-B-4） |
| 无记录/无共同事件与「有归并」严格区分 | `status` 状态机（FR-B-6） |

---

## 4. Major Components

### Component Responsibilities

| Component | Module | Responsibility | Does NOT Do |
|---|---|---|---|
| Input Window | `input.py` | 校验 2–3 ticker、≤7 天，确定窗口 | 不抓取数据 |
| News Adapter | `news_source.py` | 复用上游新闻能力，结构化 ≤5 条/ticker | 不修改上游 vendor，不新增供应商 |
| Evidence Registry | `evidence.py` | 生成/持有本次运行 evidence ID 与映射 | 不跨运行持久化，不判定事件 |
| Schema | `schemas.py` | `NewsRecord`/`MergedEvent`/`MergeInput`/`MergeResult` | 不执行业务逻辑 |
| Merger | `merger.py` | 单次 LLM 归并入口 + 状态机 | 不做证据合法性判定 |
| Validator | `validator.py` | 确定性校验（权威），二次检查 ≥2 ticker | 不调用模型，不抓取新闻 |
| CLI | `src/cli/event_merge_cmd.py` | `merge-events` 命令（可选集成） | 不绕过 validator |

### Data Contracts（冻结自 plan-B-approved.md §b）

- **Evidence ID**：`ev-{run_id}-{ticker}-{seq}`；`run_id = uuid4().hex[:8]`，`seq` 为 ticker 内 0-based 序号。
- **归并输入**：`{run_id, tickers, window_start, window_end, records[]}`。
- **模型建议输出**：`{events[], unmerged_evidence_ids[]}`。
- **最终输出**：`{status, run_id, events[], unmerged[], dropped_invalid[]}`。

---

## 5. Authority Boundaries（建议性 vs 权威性）

> **Source:** ADR-001 + `docs/architecture/invariants.md`

| Layer | Role | Component |
|---|---|---|
| **ADVISORY（建议）** | LLM 根据新闻内容判断记录是否同事件，生成摘要与分组建议 | `merger.merge_once()` → 模型输出 |
| **AUTHORITATIVE（权威）** | 证据合法性判定：ID 归属、ticker/date/source 匹配、≥2 ticker | `validator.validate()` |

### Authority Rules

| Rule | Enforcement |
|---|---|
| 模型输出是建议，validator 判定是权威 | `merge_once()` 返回建议层，最终输出由 `validate()` 过滤后产生 |
| 校验失败的证据不得输出为已验证事实 | 移入 `dropped_invalid`，事件只保留合法证据 |
| 模型不能覆盖确定性边界 | validator 二次检查后事件 ticker <2 即降级（INV-B-5） |

---

## 6. Agent Workflow

### Agent Roles

| Role | Permissions | Constraint |
|---|---|---|
| **Plan Agent** | 只读 `docs/`、`_refs/`；R/W 仅 `docs/architecture/adr/` | 不写代码 |
| **Build Agent** | 写 `src/`、`test/` 白名单路径；写 `docs/` 白名单 | 不碰上游 `tradingagents/`、`tests/`、`prompts/` |
| **Review Agent** | 全文件只读 | 只报告，不修改 |

### Bounded Task Template

```python
task = {
    "goal": "Implement event_merge deterministic core",
    "bounded_by": [
        "ADR-001 single-LLM-call + deterministic validator authority",
        "INV-B-1..5",
        "FR-B-1..7 / NFR-B-1..3"
    ],
    "permissions": "Build in src/ + test/ only; pause for human review per phase",
    "must_not": [
        "modify upstream tradingagents/ behavior",
        "make >1 LLM call per merge run",
        "output unvalidated evidence as verified fact"
    ]
}
```

---

## 7. Permissions

> **Full matrix:** `docs/architecture/permission-model.md`

**Default policy: NO READ, NO WRITE — every path explicitly whitelisted.**

| Path | Plan Agent | Build Agent | Review Agent |
|---|---|---|---|
| `src/event_merge/` | Read | Read/Write | Read |
| `src/cli/event_merge_cmd.py` | Read | Read/Write | Read |
| `test/offline/`、`test/fixtures/` | Read | Read/Write | Read |
| `docs/**` | Read/Write (adr only) | Read | Read |
| `tradingagents/`（上游） | Read | **No access** | Read |
| `tests/`（上游） | Read | **No access** | Read |
| `prompts/` | Read | **No access** | Read |

---

## 8. Verification

> **Source:** `docs/code-governance/verification-constraints.md` + `docs/architecture/trace-matrix.md`

### Test Strategy

| Test Type | Scope | Marker | Runs When |
|---|---|---|---|
| Offline deterministic | window、registry、validator 负向、状态机、mock LLM | `@pytest.mark.offline` | 每次 commit（CI 默认） |
| Semantic eval | 固定评估集 pairwise precision/recall | `@pytest.mark.offline`（mock/fixtures） | CI 门禁 |
| Live API | 真实模型/provider 语义评估 | `@pytest.mark.live` | 需 API，独立运行 |

### CI Gates（对应 v4 §12）

| Gate | Check | Blocks Merge If |
|---|---|---|
| Schema | `requirements.yaml` 符合 `req-schema.json` | 校验失败 |
| Offline tests | `pytest test/offline/` | 任一失败 |
| Semantic eval | precision ≥0.80 且 recall ≥0.70 | 未达阈值 |
| Regression | 全量既有测试 | 任一回归 |

---

## 9. Observability

### 可观测信号

| Signal | Metric | Threshold |
|---|---|---|
| LLM 调用计数 | `llm_call_count` | **MUST == 1**（INV-B-1） |
| 证据解析失败 | `unresolved_evidence_count` | **MUST == 0**（NFR-B-1） |
| 伪造/跨运行 ID | `forged_or_cross_run_id_count` | **MUST == 0**（NFR-B-2） |
| validator 剔除 | `dropped_invalid_count` | 记录，用于审计 |
| 语义评估 | `pairwise_precision` / `pairwise_recall` | ≥0.80 / ≥0.70 |

---

## 10. Change Policy

### When to Re-Open ADR-001

| Trigger | Threshold | Process |
|---|---|---|
| LLM 调用次数 >1 | 任何实例 | 立即 ADR 复核 |
| 伪造/跨运行 ID 通过 validator | 任何实例（>0） | 立即 ADR 复核 + 修复 |
| 语义阈值连续不达标 | 连续 2 次 CI 失败 | 重审 prompt/model/评估集 |
| 引入第二类模型调用（如双 LLM 校验） | 需求变更 | 新 ADR 评估 |

### Artifact Coupling — When One Change Ripples

| If You Change | You Must Also Update |
|---|---|
| `docs/req/requirements.yaml` | Blueprint §2、trace-matrix、tests、req-schema |
| 契约（evidence ID / schema） | Blueprint §4、schemas.py、validator、tests |
| `merger.py`（调用次数/状态机） | ADR-001、invariants、trace-matrix、tests |
| prompt | prompt 版本、evaluation-logbook、ai-use-log、CI 语义评估 |
| validator 规则 | invariants、trace-matrix、负向测试 |

---

## Cross-Reference Index

| Section | Full Details In |
|---|---|
| §2 — Drivers | `docs/req/requirements.yaml`、`docs/architecture/trace-matrix.md` |
| §3 — Boundaries | `docs/architecture/adr/001-event-merge-single-llm-call.md` |
| §4 — Components | `docs/code-governance/structural-constraints.md` |
| §5 — Authority | `docs/architecture/invariants.md` |
| §6 — Agent Workflow | `AGENTS.md`、`docs/architecture/permission-model.md` |
| §7 — Permissions | `docs/architecture/permission-model.md` |
| §8 — Verification | `docs/code-governance/verification-constraints.md`、`docs/architecture/trace-matrix.md` |
| §9 — Observability | `docs/architecture/memory-design.md`、`docs/architecture/runtime-policy-catalog.md` |
| §10 — Change | `docs/architecture/adr/001-event-merge-single-llm-call.md` |
