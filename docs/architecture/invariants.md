# Invariant Register — B 模块

> **Purpose** (D2 / SA M5.3b)：不变量是不可妥协的规则，验收零容忍。每条含陈述、来源需求、执行组件、验证方法、违反兜底动作。

---

## INV-B-1: 每次归并最多一次 LLM 调用

| Field | Value |
|---|---|
| **Statement** | 每次事件归并最多一次 LLM 调用；不得逐条新闻分别调用模型。 |
| **Source Requirement** | FR-B-3、INV-B-1（requirements.yaml）、v3 §3 B |
| **Enforcing Component** | `src/event_merge/merger.py` — `merge_once()` 作为唯一模型调用入口 |
| **Verification Method** | mock LLM，断言 `merge_once` 恰好调用一次且传入全量 records；违反即失败测试注入第二次调用并断言被禁止 |
| **Fallback if Violated** | 立即阻断合并，标记 CRITICAL，复核 merger 实现，禁止进入生产 |

---

## INV-B-2: 一个事件至少关联两个 ticker

| Field | Value |
|---|---|
| **Statement** | 一个事件至少有两个 ticker 的记录支持。 |
| **Source Requirement** | FR-B-5、INV-B-2、v4 §4 FR-B |
| **Enforcing Component** | `validator.py` 二次检查 — 事件去重 ticker 数 <2 即整事件降级为未归并 |
| **Verification Method** | 注入单一 ticker 事件（违反即失败），断言被降级/剔除，最终输出无单一 ticker 事件 |
| **Fallback if Violated** | 事件移入 `unmerged`，不作为已验证事件输出，记录降级原因 |

---

## INV-B-3: 确定性 validator 是证据合法性的唯一权威

| Field | Value |
|---|---|
| **Statement** | 确定性 validator 是证据合法性的唯一权威；校验失败的证据不得输出为已验证事实。 |
| **Source Requirement** | FR-B-7、NFR-B-1、NFR-B-2、INV-B-3 |
| **Enforcing Component** | `validator.validate()` — `registry.issued_ids` 归属 + ticker/date/source 逐项匹配 |
| **Verification Method** | 负向测试：伪造 ID、错配 ticker、错配 date、跨运行 ID 均被剔除；解析率 100%、伪造/跨运行计数 == 0 |
| **Fallback if Violated** | 证据移入 `dropped_invalid`，不作为已验证事实输出，记录被剔除的字段与原因 |

---

## INV-B-4: 证据不足的记录不强配

| Field | Value |
|---|---|
| **Statement** | 无法确认属于同一事件的记录保留为未归并，不得强行配组。 |
| **Source Requirement** | FR-B-5、INV-B-4、v3 §3 B |
| **Enforcing Component** | `merger.py` + `validator.py` — `unmerged` 路径；prompt 约束不强配泛化词 |
| **Verification Method** | 注入仅共享泛化词的两条记录，断言不被归并；评估集覆盖「不同事件」负向 |
| **Fallback if Violated** | 该记录保留在 `unmerged`，不回填任何事件；触发 prompt 复核 |

---

## INV-B-5: 模型输出不能覆盖确定性边界

| Field | Value |
|---|---|
| **Statement** | 模型输出是建议，确定性代码的判定是权威；模型不能覆盖确定性边界。 |
| **Source Requirement** | FR-B-7、INV-B-5、v4 §1 项目目标 |
| **Enforcing Component** | 分层：`merge_once()` 产出建议 → `validate()` 过滤后产出最终输出 |
| **Verification Method** | 注入模型声称合法但实际非法（伪造/错配）的证据，断言被确定性层纠正 |
| **Fallback if Violated** | 最终输出以 validator 结果为准，模型建议被覆盖；记录覆盖事件用于审计 |

---

## Connection to Other Artifacts

| Invariant | Connected To |
|---|---|
| INV-B-1 | ADR-001（方案 B vs C）、Trace Matrix（FR-B-3）、Runtime Policy（RP-LLM） |
| INV-B-2 | ADR-001、Trace Matrix（FR-B-5）、Runtime Policy（RP-SINGLE-TICKER） |
| INV-B-3 | ADR-001、Trace Matrix（FR-B-7/NFR-B-1/NFR-B-2）、Memory Design（EvidenceRegistry） |
| INV-B-4 | ADR-001、Trace Matrix（FR-B-5）、Evaluation Table（语义标注规则） |
| INV-B-5 | ADR-001、Permission Model（Build 不碰上游）、Trace Matrix（FR-B-7） |
