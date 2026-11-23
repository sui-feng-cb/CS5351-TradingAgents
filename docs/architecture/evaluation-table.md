# Candidate Evaluation Table — B 模块

> **Purpose** (D2 / SA S61)：候选架构比较、评价依据、设计取舍；并记录语义评估集标注规则与阈值依据。

---

## 1. 候选架构比较

### Evaluation Criteria

| Criterion | What It Measures |
|---|---|
| 调用次数约束 | 能否保证每次归并最多一次 LLM 调用（INV-B-1） |
| 证据权威分离 | 模型建议与确定性校验是否清晰分层（INV-B-3/5） |
| 证据可追溯 | 能否保证解析率 100%、伪造/跨运行 ID = 0（NFR-B-1/2） |
| 语义质量可控 | 能否满足 pairwise precision/recall 阈值（NFR-B-3） |
| 复用与边界 | 是否复用上游新闻且不修改上游行为 |
| 实现复杂度 | 代码、协调、验证成本 |

### Candidate Comparison

| Criterion | A: 逐条/逐对调用 | B: 单次 LLM + validator（选定） | C: 双 LLM 校验 |
|---|---|---|---|
| 调用次数约束 | Weak（N×M 次） | **Strong（==1）** | Weak（==2，违反） |
| 证据权威分离 | Weak | **Strong** | Medium |
| 证据可追溯 | Weak | **Strong** | Strong |
| 语义质量可控 | Medium | **Strong（评估集+门禁）** | Strong |
| 复用与边界 | Strong | **Strong** | Strong |
| 实现复杂度 | Low | **Medium** | High |

### Weighting

| Criterion | Weight | Reason |
|---|---|---|
| 调用次数约束 | **Critical** | INV-B-1 零容忍 |
| 证据权威分离 | **Critical** | INV-B-3/5，v4 §1 模型不能覆盖确定性边界 |
| 证据可追溯 | **Critical** | NFR-B-1/2 零容忍 |
| 语义质量可控 | High | NFR-B-3 阈值门禁 |
| 复用与边界 | High | v3 §3 不修改上游、不新增供应商 |
| 实现复杂度 | Medium | 低优先，但不得牺牲 Critical 项 |

### Weighted Assessment

| Criterion | Weight | A | B | C |
|---|---|---|---|---|
| 调用次数约束 | Critical | ❌ | ✅ | ❌ |
| 证据权威分离 | Critical | ❌ | ✅ | ⚠️ |
| 证据可追溯 | Critical | ❌ | ✅ | ✅ |
| 语义质量可控 | High | ⚠️ | ✅ | ✅ |
| 复用与边界 | High | ✅ | ✅ | ✅ |
| 实现复杂度 | Medium | ✅ | ⚠️ | ❌ |

**A** 在调用次数约束上直接违反 INV-B-1 → 排除。
**C** 违反单次调用硬约束 → 排除。
**B** 通过全部 Critical 项，复杂度可控 → 选定。

## Decision

**Chosen: 方案 B — 单次 LLM 归并 + 确定性 validator 权威。**

---

## 2. 语义评估集标注规则（编码前冻结）

> 对应 v3 §3「团队应在编码前共同审阅并冻结标注集」；规则写入本表与 fixtures README。

### 标注单元

- 固定语义评估集 `test/fixtures/semantic_eval.json`，版本号 `v1`。
- ≥20 对人工标注的新闻记录：≥10 对同一事件、≥10 对不同事件。
- 每对含两条 `NewsRecord` 与标签 `same_event: bool`。

### 「同一事件」判据（人工标注，冻结）

1. 两条记录描述同一底层事实/事件（如「同一家央行同日宣布同一政策」「同一并购交易」）。
2. 允许不同来源、不同措辞、不同 ticker 视角；关键事实（主体、动作、时间）一致即判同事件。
3. 同标的重复报道（同 ticker 同事件多来源）视为「同标的重复报道」干扰项，不单独构成跨 ticker 同事件。

### 「不同事件」判据

1. 仅共享泛化词（如都含「加息」「芯片」「监管」）而无共同具体事实者，判不同事件。
2. 时间窗口外报道、无数据、证据不足等作为负向干扰项。

### 干扰项（额外覆盖）

| 类型 | 说明 |
|---|---|
| 同标的重复报道 | 同 ticker 多来源同事件，不得误判为跨 ticker |
| 时间窗口外报道 | 应被窗口过滤剔除 |
| 无数据 | 触发 data_unavailable |
| 证据不足 | 保留为未归并，不强配 |

---

## 3. 阈值依据（pairwise precision ≥0.80 / recall ≥0.70）

### 测量定义（冻结自 plan §d.3）

- TP = 标签同事件 且 模型归入同一事件
- FP = 标签不同事件 但 模型归并
- FN = 标签同事件 但 模型未归并
- `precision = TP/(TP+FP)`，`recall = TP/(TP+FN)`

### 阈值来源与理由

| 项 | 值 | 依据 |
|---|---|---|
| precision | ≥0.80 | v3 §3 B 完成标准；强调「不同事件不强行归并」，precision 侧重抑制假阳性（不强配） |
| recall | ≥0.70 | v3 §3 B 完成标准；允许部分弱信号遗漏，但须找回大部分同事件 |
| 样本量 | ≥20 对（≥10/≥10） | v3 §3 B 完成标准硬性下限 |
| 记录方式 | model/provider、样例版本、precision/recall | v4 §6、v3 §3，写入 `evaluation-logbook.md` |

### 失败处理

- CI 语义评估未达阈值 → 阻断合并（v4 §12 语义评估门禁）。
- prompt/model 变化 → 重跑固定评估集并记录结果。
