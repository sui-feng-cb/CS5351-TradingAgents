# Verification Constraints — B 模块

> **Purpose** (D4)：每个验收标准至少对应一个测试；每个不变量至少一个「违反即失败」测试；测试须引用需求或不变量 ID；每轮验证运行全部此前测试，零回归。

---

## 1. 覆盖规则

| 规则 | 说明 |
|---|---|
| 每个 fit criterion ≥1 测试 | FR-B-1..7、NFR-B-1..3 的每个可测标准至少一个测试 |
| 每个不变量 ≥1 违反即失败测试 | INV-B-1..5 各一个会失败的反例 |
| 测试引用 ID | 每个测试的 docstring/命名引用对应 FR-B/NFR-B/INV-B ID |
| 零回归 | 每次验证运行全部此前测试，禁止回归 |
| offline 默认 CI | `test/offline/` 不调用真实模型/API（mock/fixtures） |
| live 独立 | `test/live/` 需 API，独立标记并说明运行方式 |

---

## 2. 验收标准 → 测试映射

| 需求 ID | 验收标准（fit criterion） | 计划测试 |
|---|---|---|
| FR-B-1 | 2–3 ticker 成功；1/4 ticker、8 天窗口失败 | `test/offline/test_input.py` |
| FR-B-2 | 每 ticker ≤5 条、ID 本次运行唯一、字段齐全 | `test/offline/test_evidence_registry.py`、`test_news_source.py` |
| FR-B-3 | 单次 LLM 调用、传入全量记录 | `test/offline/test_merger_status.py`（mock） |
| FR-B-4 | 输出符合结构化 schema | `test/offline/test_merger_status.py` |
| FR-B-5 | 单一 ticker 事件被降级/未归并 | `test/offline/test_validator.py` |
| FR-B-6 | 无记录 → data_unavailable；有记录无事件 → no_common_event | `test/offline/test_merger_status.py` |
| FR-B-7 | 伪造 ID/错配 ticker/date 被剔除 | `test/offline/test_validator.py` |
| NFR-B-1 | 解析率 100% | `test/offline/test_validator.py` |
| NFR-B-2 | 伪造/跨运行 ID == 0 | `test/offline/test_validator.py` |
| NFR-B-3 | precision ≥0.80 / recall ≥0.70 | `test/offline/test_semantic_eval.py` |

---

## 3. 不变量 → 违反即失败测试映射

| 不变量 | 违反场景 | 断言（必须失败→测试通过） |
|---|---|---|
| INV-B-1 | 注入第二次 LLM 调用 | 断言调用次数被禁止为 >1 |
| INV-B-2 | 单一 ticker 事件 | 断言整事件降级，无单一 ticker 事件输出 |
| INV-B-3 | 伪造 ID/错配字段 | 断言该证据被剔除 |
| INV-B-4 | 仅共享泛化词的两条记录 | 断言不归并，进入 unmerged |
| INV-B-5 | 模型声称合法但实际非法证据 | 断言被确定性层纠正 |

---

## 4. 验证层次（对应 D4）

| 层次 | 检查内容 |
|---|---|
| 结构验证 | import、组件边界、权限、实现是否符合架构约束（`structural-constraints.md`） |
| 回归验证 | 全量既有测试零回归 |
| 行为验证 | 语义质量阈值（NFR-B-3）、零安全逃逸（NFR-B-1/2） |

---

## 5. CI 门禁（对应 v4 §12）

| 门禁 | 通过条件 |
|---|---|
| Schema | `requirements.yaml` 符合 `req-schema.json` |
| 静态分析 | lint、类型、依赖检查通过 |
| Offline 测试 | `pytest test/offline/` 全部通过 |
| 语义评估 | precision ≥0.80 且 recall ≥0.70 |
| 回归 | 全量回归零失败 |
