# Memory / State Design — B 模块（EvidenceRegistry）

> **Purpose** (D2 / SA S57)：跨会话、中断、版本保留的状态，及其读写、所有权、保留期限、恢复与隐私规则。

---

## 状态总览：单次运行、不跨会话

B 模块的状态本质是**单次运行内的临时状态**，不跨会话、不跨运行持久化。唯一持有状态的组件是 `EvidenceRegistry`。

| State Type | What It Holds | 生命周期 |
|---|---|---|
| **EvidenceRegistry（单次运行）** | `run_id`、`set(evidence_id)`、`evidence_id → NewsRecord` 映射 | 一次 `merge-events` 运行内有效，运行结束即丢弃 |
| **（无持久化存储）** | — | B 模块不写数据库/文件缓存 |

---

## EvidenceRegistry 字段表

| Field | 内容 | 读写 | 所有权 | 保留 | 隐私 |
|---|---|---|---|---|---|
| `run_id` | `uuid4().hex[:8]`，本次运行标识 | 运行时生成，只读 | `evidence.py` | 进程内 | 无敏感数据 |
| `issued_ids` | 本次运行已分配的 evidence ID 集合 | validator 只读 | `evidence.py` | 进程内 | 无敏感数据 |
| `records` | `evidence_id → NewsRecord` 映射 | validator 只读，news_source 写入 | `evidence.py` | 进程内 | 仅公开新闻元数据（title/snippet/link/pub_date），无密钥/账户 |

### Evidence ID 生成规则（冻结自 plan §b）

- 格式：`ev-{run_id}-{ticker}-{seq}`；`run_id = uuid4().hex[:8]`，`seq` 为 ticker 内 0-based 序号。
- 本次运行内唯一；跨运行因 `run_id` 不同而天然唯一（保证 NFR-B-2 伪造/跨运行 ID 可判零）。

---

## 生命周期与恢复

| Event | State 变化 |
|---|---|
| 运行开始 | 生成 `run_id`，初始化空 registry |
| `fetch_records()` 取回记录 | 逐条分配 evidence ID，写入 `issued_ids` 与 `records` |
| `merge_once()` 调用模型 | 不写 registry（只读传入 records） |
| `validate()` 校验 | 读 `issued_ids` / `records`，不修改 |
| 运行结束 | registry 随进程结束丢弃，不落盘 |

### 恢复

| 场景 | 行为 |
|---|---|
| 运行中断/崩溃 | 无恢复机制 — 下次运行重新生成 `run_id` 与全部 evidence ID；旧 ID 天然失效（跨运行 ID = 0 保证） |
| 会话中断 | 无跨会话状态，无需恢复 |

**设计依据：** NFR-B 只要求「本次运行内」解析率 100% 与跨运行 ID = 0，因此无需持久化；丢弃 registry 恰是保证跨运行 ID 不可伪造的机制。

---

## 隐私与安全

| 约束 | 说明 |
|---|---|
| 不保存 API key / secret / 凭证 URL | 复用上游新闻能力，配置与密钥由上游处理，B 模块不复制 |
| 不保存账户隐私 | 仅新闻公开元数据 |
| 单次运行内有效 | 避免残留可被后续运行引用的旧 ID |

---

## 设计决策

| Decision | Rationale |
|---|---|
| registry 单次运行、不持久化 | 满足 NFR-B 的最小状态；持久化会引入跨运行 ID 伪造风险 |
| `run_id` 用短 UUID | 保证跨运行唯一、碰撞概率可忽略，且 ID 短小便于模型引用 |
| validator 只读 registry | 权威层不产生新状态，只做判定，保证确定性 |

---

## Connection to Other Artifacts

| Artifact | Connection |
|---|---|
| ADR-001 | 确定性 validator 权威 → 依赖 registry 作为唯一证据来源 |
| Invariant Register | INV-B-3：registry.issued_ids 是证据合法性唯一权威 |
| Trace Matrix | FR-B-2 / NFR-B-1 / NFR-B-2 行 |
| Permission Model | Build agent 写 `evidence.py`，不碰上游 |
| Runtime Policy | RP-NO-DATA：records 为空 → data_unavailable |
