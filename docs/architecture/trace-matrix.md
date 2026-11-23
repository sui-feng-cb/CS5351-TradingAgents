# Trace Matrix — B 模块

> **Purpose** (D2 / SA S56)：需求 → 执行组件 → 测试/证据 → 运行时监控 的映射。随实现与验证持续更新。
>
> **Source:** `docs/req/requirements.yaml` + `_refs/plan-B-approved.md` §a
>
> **Status 说明：** 本表在阶段 0 冻结计划，阶段 1–3 实现与验证后回填「Test / Evidence」实际测试名。

## Column Legend

| Column | Meaning |
|---|---|
| REQ ID | 需求标识（requirements.yaml） |
| Type | functional / invariant / quality |
| Enforcing Component | 执行组件（src/ 下模块） |
| Test / Evidence | 计划测试（阶段 0 按计划填，实现后替换为真实测试名） |
| Runtime Monitor | 运行时监控指标 |

---

## FR-B — Functional

| REQ ID | Type | Enforcing Component | Test / Evidence | Runtime Monitor |
|---|---|---|---|---|
| FR-B-1 | functional | `input.py — build_window()` | `test/offline/test_input.py`：2–3 ticker 成功、1/4 ticker 失败、8 天窗口失败（引用 FR-B-1） | `input_reject_count` |
| FR-B-2 | functional | `news_source.py — fetch_records()` + `evidence.py — EvidenceRegistry` | `test/offline/test_evidence_registry.py`、`test_news_source.py`：每 ticker ≤5 条、ID 本次运行唯一、字段齐全（FR-B-2, NFR-B-1） | `records_per_ticker`、`evidence_id_collision_count` |
| FR-B-3 | functional | `merger.py — merge_once()` | `test/offline/test_merger.py::test_single_llm_call`、`::test_inv_b1_second_call_is_forbidden`（FR-B-3, INV-B-1） | `llm_call_count` **MUST == 1** |
| FR-B-4 | functional | `schemas.py — MergedEvent` | `test/offline/test_merger.py::test_legal_merge_is_accepted`（FR-B-4） | `schema_violation_count` |
| FR-B-5 | functional | `merger.py` + `validator.py`（事后过滤） | `test/offline/test_validator.py::test_single_ticker_event_is_degraded`（FR-B-5, INV-B-2） | `single_ticker_event_count` **MUST == 0** |
| FR-B-6 | functional | `merger.py`（status 状态机） | `test/offline/test_merger.py::test_no_records_data_unavailable`、`::test_records_but_no_events_no_common_event`（FR-B-6） | `status` 分布计数 |
| FR-B-7 | functional | `validator.py — validate()` | `test/offline/test_validator.py`：伪造 ID / 错配 ticker / 错配 date 负向（FR-B-7, NFR-B-2） | `dropped_invalid_count` |

---

## NFR-B — Non-Functional

| REQ ID | Type | Enforcing Component | Test / Evidence | Runtime Monitor |
|---|---|---|---|---|
| NFR-B-1 | quality | `validator.py` + `EvidenceRegistry` | `test/offline/test_validator.py`：全部合法输出解析率 100%（NFR-B-1） | `unresolved_evidence_count` **MUST == 0** |
| NFR-B-2 | invariant | `validator.py`（registry.issued_ids 权威） | `test/offline/test_validator.py`：跨运行 ID 负向，计数 == 0（NFR-B-2） | `forged_or_cross_run_id_count` **MUST == 0** |
| NFR-B-3 | quality | prompt + `test/offline/test_semantic_eval.py` | `test/fixtures/semantic_eval.json`（v1，≥20 对）+ `mock_model_outputs.json`；`test_semantic_eval.py::test_perfect_model_precision_recall_are_one` / `::test_wrong_model_*_blocks_*`；CI 阈值 precision ≥0.80 / recall ≥0.70 阻断（NFR-B-3） | `pairwise_precision` / `pairwise_recall` |

---

## INV-B — Invariants

| REQ ID | Type | Enforcing Component | Test / Evidence | Runtime Monitor |
|---|---|---|---|---|
| INV-B-1 | invariant | `merger.py — merge_once()` | 违反即失败：注入第二次调用断言被禁止（引用 INV-B-1） | `llm_call_count` **MUST == 1** |
| INV-B-2 | invariant | `validator.py` 二次检查 | 违反即失败：单一 ticker 事件断言降级（引用 INV-B-2） | `single_ticker_event_count` **MUST == 0** |
| INV-B-3 | invariant | `validator.py — validate()` | 违反即失败：伪造 ID/错配字段断言剔除（引用 INV-B-3） | `dropped_invalid_count` |
| INV-B-4 | invariant | `merger.py` + `validator.py` | 违反即失败：共享泛化词不强配（引用 INV-B-4） | `forced_merge_count` **MUST == 0** |
| INV-B-5 | invariant | `merger.py` + `validator.py` 分层 | 违反即失败：模型非法证据被确定性层纠正（引用 INV-B-5） | `authority_override_attempt_count` **MUST == 0** |

---

## Enforcement Coverage Summary

| Group | Count | Enforcing Component 已规划 | Test 已规划（阶段 0） | 说明 |
|---|---|---|---|---|
| FR-B | 7 | 7/7 | 7/7 | 阶段 1–2 落地，阶段 3 回填真实测试名 |
| NFR-B | 3 | 3/3 | 3/3 | NFR-B-3 阶段 3 落地：`semantic_eval.json` v1 + 语义评估门禁 |
| INV-B | 5 | 5/5 | 5/5 | 每个不变量 ≥1 违反即失败测试 |

## Governance / CI Mapping

| Concern | Enforcing Artifact | CI Gate |
|---|---|---|
| 需求注册表 schema 校验（D1） | `docs/req/requirements.yaml` vs `docs/req/req-schema.json` | `test/offline/test_requirements_schema.py`（CI step a） |
| 全量离线测试 | `test/offline/`（无网络/API） | `pytest test/offline/ -q`（CI step b） |
| 语义评估阈值阻断（NFR-B-3） | `test/offline/test_semantic_eval.py`（`__main__` gate） | `python3 test/offline/test_semantic_eval.py`（CI step c，precision<0.80 或 recall<0.70 即失败） |
