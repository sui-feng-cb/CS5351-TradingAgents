# Evaluation Logbook — B 模块

> **Purpose** (SA S59)：架构与语义评估证据随时间累积。语义评估实测记录（model/provider、样例版本、precision/recall）见 §4。
> **范本：** `_refs/docs_example/docs/architecture/evaluation-logbook.md`

---

## 1. Architecture Exploration Evidence

### Candidate Reviews

**Date:** 2026-11-22

三个候选架构在 6 个判据下比较，完整证据见 `evaluation-table.md` §1。

| Candidate | Verdict | Key Evidence |
|---|---|---|
| A: 逐条/逐对调用 | **Rejected** | 违反 INV-B-1（单次 LLM 调用零容忍）；N×M 次调用 |
| B: 单次 LLM + 确定性 validator（选定） | **Chosen** | 通过全部 Critical 项；复用上游新闻；复杂度可控 |
| C: 双 LLM 校验 | **Rejected** | 违反单次调用硬约束（==2） |

Decision: `adr/001-event-merge-single-llm-call.md`

---

## 2. Test Evidence

### Offline Test Coverage (阶段 1–3)

**Source:** `test/offline/`（无网络/API，CI 默认运行）

| File | Covers |
|---|---|
| `test_input.py` | FR-B-1：2–3 ticker 成功、1/4 ticker 失败、>7 天窗口失败 |
| `test_evidence_registry.py` | FR-B-2 / NFR-B-1：ID 格式、本次运行唯一、resolve |
| `test_news_source.py` | FR-B-2：每 ticker ≤5 条、字段齐全、上游形状归一化 |
| `test_merger.py` | FR-B-3/4/6 + INV-B-1/4：单次调用、状态机、fail-closed |
| `test_validator.py` | FR-B-5/7 + NFR-B-1/2 + INV-B-2/3/5：伪造/错配/跨运行剔除 |
| `test_requirements_schema.py` | D1：`requirements.yaml` 对 `req-schema.json` 校验 |
| `test_semantic_eval.py` | NFR-B-3：pairwise precision/recall 指标 + 阈值门禁 |

阶段 2 验收基线：40 个 offline 测试通过。阶段 3 新增语义评估与 schema 校验测试。

---

## 3. Structural Findings

无已知缺陷（阶段 1–3 实现期内）。上游代码零修改。

---

## 4. Semantic Evaluation Evidence

### Pairwise Precision / Recall（离线 mock 参考值）

**样例集：** `test/fixtures/semantic_eval.json`，版本 `v1`（≥20 对：11 同事件 / 13 不同事件 + 4 类干扰项）。

> 说明：以下数值由**离线 mock 模型**在固定评估集上测得，用于验证指标计算与阈值门禁逻辑；**不是真实 LLM 的语义质量测量**。真实模型评估待 live（需 API/密钥），待 `test/live/` 接入后回填。

| Model / Provider | Sample Version | Model Type | precision | recall | Threshold (p/r) | Verdict |
|---|---|---|---|---|---|---|
| deepseek-v4-pro | v1 | 完美 mock（按标签归并） | 1.0000 | 1.0000 | ≥0.80 / ≥0.70 | ✅ PASS（参考） |
| deepseek-v4-pro | v1 | 错误 mock（全部归并） | 0.5000 | 1.0000 | ≥0.80 / ≥0.70 | ❌ BLOCKED（precision） |
| deepseek-v4-pro | v1 | 错误 mock（不归并） | 0.0000 | 0.0000 | ≥0.80 / ≥0.70 | ❌ BLOCKED（recall） |
| deepseek-v4-pro | v1 | **真实 LLM（待 live）** | 待测 | 待测 | ≥0.80 / ≥0.70 | 🟡 To be measured |

**阈值来源：** v3 §3 B 完成标准（precision ≥0.80、recall ≥0.70）；见 `evaluation-table.md` §3。

**测量定义：** TP = 标签同事件且归入同一事件；FP = 标签不同事件但被归并；FN = 标签同事件但未归并（冻结自 plan §d.3）。

---

## 5. Overrides

None recorded — 阶段 1–3 实现期内无确定性边界被覆盖。

---

## 6. Architecture Revisions

None recorded — v1 of the single-LLM + deterministic-validator architecture.

**Monitored triggers** (from ADR-001):
- `llm_call_count != 1`
- `single_ticker_event_count > 0`
- `forged_or_cross_run_id_count > 0`
- `pairwise_precision < 0.80` or `pairwise_recall < 0.70`

---

## 7. Future Evidence Sources

| Source | What It Will Produce | When |
|---|---|---|
| `test/live/`（真实 LLM） | 固定评估集上的真实 precision/recall、model/provider 记录 | 接入 API 后 |
| CI 语义评估门禁 | 每次 push/PR 的阈值阻断结果 | 持续 |
| 人工标注集复审 | `semantic_eval.json` 版本演进（v1 → vN） | 标注规则变化时 |


---


## Live Semantic Eval — Real Model (re-annotated set, 2026-11-23)

> 标注集 `test/fixtures/semantic_eval.json` 已由成员 B 人工重新标注（日期经真实事件检索核实；s12 由「same」改为「different」）。以下为真实模型（deepseek-v4-pro）在该人工标注集上的实测。

| Field | Value |
|---|---|
| model | deepseek-v4-pro |
| provider | personal-deepseek (https://api.deepseek.com) |
| sample version | v1（人工标注，24 对：11 同事件 / 13 不同事件） |
| pairs attempted / failed | 23 / 1（d05 模型返回空，跳过） |
| TP / FP / FN | 8 / 0 / 3 |
| precision | 1.0000（≥ 0.80 ✅） |
| recall | 0.7273（≥ 0.70 ✅） |
| gate | PASS |

### 3 个 false negative（标签 same，模型判 different）

| pair | 记录 A vs 记录 B | 说明 |
|---|---|---|
| s04 | JPMorgan vs Goldman Sachs 各自因 Fed 降息调整展望 | 同一 Fed 决策、两家各自独立反应 |
| s07 | Wells Fargo vs Citigroup 各自 MOVEit 漏洞数据泄露 | 同一漏洞、两家独立安全事件 |
| s08 | Toyota vs Honda 各自 Takata 气囊召回 | 同一缺陷、各自独立召回 |

### 结论

- `precision = 1.0`：模型从不把「不同事件」强行归并（INV-B-4 达成）。
- `recall = 0.727`：达到阈值；剩余 3 个漏报均为「共享同一原因但不同主体的独立实例」（模型偏保守，属真实模型行为而非标注错误）。
- 重新标注后 s12（Google 撤销投诉 vs 微软受查）已正确标为 different，模型判断一致。
