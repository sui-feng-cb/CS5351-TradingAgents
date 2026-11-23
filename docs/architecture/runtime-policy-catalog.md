# Runtime Policy Catalog — B 模块

> **Purpose** (D2 / SA S61)：降级与失败路径的触发条件与运行时动作。

---

## 输入与数据层

### RP-B-001: 无可用新闻记录

| Field | Value |
|---|---|
| **Trigger** | `fetch_records()` 对全部 ticker 返回 0 条记录（上游无数据/网络不可用/窗口内无新闻） |
| **System action** | 设置 `status=data_unavailable`，附带「数据不可用/无记录」说明；不调用 LLM |
| **Evidence** | 最终输出 `status` 字段 |
| **Decision** | 数据不可用/无记录 |
| **Escalation** | 上游新闻供应商可用性告警 |
| **Requirement** | FR-B-6 |

### RP-B-002: 窗口外记录剔除

| Field | Value |
|---|---|
| **Trigger** | 记录 `pub_date` 不在 `[window_start, window_end]` 内 |
| **System action** | 复用 `date_window.in_window` 过滤，窗口外记录不进入归并 |
| **Evidence** | 该记录不出现在 records/输入 |
| **Decision** | 剔除，继续 |
| **Escalation** | 无 |
| **Requirement** | FR-B-1（≤7 天窗口）；v3 §3 时间窗口外报道为负向样例 |

---

## 归并与校验层

### RP-B-003: LLM 调用失败

| Field | Value |
|---|---|
| **Trigger** | `merge_once()` 的模型调用抛异常/超时 |
| **System action** | 不重试归并（避免违反 INV-B-1 单次调用）；状态置为可诊断的失败态，返回错误；不产出任何已验证事件 |
| **Evidence** | 错误信息 + 状态 |
| **Decision** | 失败，不输出事件 |
| **Escalation** | 连续失败触发 provider/密钥排查 |
| **Requirement** | FR-B-3、INV-B-1 |

### RP-B-004: 模型输出非结构化/解析失败

| Field | Value |
|---|---|
| **Trigger** | 模型输出无法解析为 `{events[], unmerged_evidence_ids[]}` schema |
| **System action** | 不把无法解析的输出当作事件；保守降级为 `no_common_event`（有记录但未确认共同事件），或标记错误 |
| **Evidence** | 解析错误记录 |
| **Decision** | 保守降级，不强行输出 |
| **Escalation** | 频繁解析失败触发 prompt 复核 |
| **Requirement** | FR-B-4、INV-B-5 |

### RP-B-005: validator 校验失败（伪造 ID / 错配 ticker/date/source）

| Field | Value |
|---|---|
| **Trigger** | 证据项 `evidence_id ∉ issued_ids` 或 ticker/date/source 与 record 不符 |
| **System action** | 该证据从事件移除并记入 `dropped_invalid`；事件只保留合法证据 |
| **Evidence** | `dropped_invalid[]` |
| **Decision** | 剔除非法证据 |
| **Escalation** | 伪造/跨运行 ID > 0 即触发 INV-B-3 复核 |
| **Requirement** | FR-B-7、NFR-B-1、NFR-B-2、INV-B-3 |

### RP-B-006: 单一 ticker 事件

| Field | Value |
|---|---|
| **Trigger** | validator 二次检查发现事件去重 ticker 数 <2 |
| **System action** | 整事件降级为未归并，证据回 `unmerged` |
| **Evidence** | `unmerged[]` + 降级原因 |
| **Decision** | 不作为已验证事件输出 |
| **Escalation** | 频繁出现触发 prompt 复核 |
| **Requirement** | FR-B-5、INV-B-2 |

### RP-B-007: 有记录但无跨 ticker 共同事件

| Field | Value |
|---|---|
| **Trigger** | 记录非空，但模型未给出任何跨 ticker 事件 |
| **System action** | 设置 `status=no_common_event` |
| **Evidence** | 最终输出 `status` 字段 |
| **Decision** | 报告「没有发现共同事件」 |
| **Escalation** | 无 |
| **Requirement** | FR-B-6 |

---

## Summary Matrix

| Policy | Trigger | Result | Blocks Pipeline? | Escalates? |
|---|---|---|---|---|
| RP-B-001 | 无记录 | data_unavailable | 是（不调 LLM） | 供应商告警 |
| RP-B-002 | 窗口外记录 | 剔除 | 否 | 无 |
| RP-B-003 | LLM 调用失败 | 失败态，不输出 | 是 | provider/密钥 |
| RP-B-004 | 输出解析失败 | 保守降级 | 是 | prompt 复核 |
| RP-B-005 | validator 校验失败 | 证据剔除 | 否（局部） | 伪造>0 即复核 |
| RP-B-006 | 单一 ticker 事件 | 降级未归并 | 否（局部） | prompt 复核 |
| RP-B-007 | 无共同事件 | no_common_event | 是 | 无 |
