# Permission Model — File-Level Agent Access（B 模块）

> **Purpose** (D2 / SA S58B)：按 coding agent 角色（plan / build / review）定义文件级读写权限。默认无权限，允许路径逐项加入白名单。

---

## Access Matrix

**Default policy: NO READ, NO WRITE — every path must be explicitly whitelisted.**

| Path | Plan Agent | Build Agent | Review Agent | Human Approval |
|---|---|---|---|---|
| `src/event_merge/*.py` | Read | Read/Write | Read | 否（validator/merger 关键变更需 ADR + 人工审） |
| `src/cli/event_merge_cmd.py` | Read | Read/Write | Read | 否 |
| `test/offline/*` | Read | Read/Write | Read | 否 |
| `test/fixtures/*` | Read | Read/Write | Read | 否（语义评估集冻结需团队共同审阅） |
| `docs/req/` | Read | Read | Read | 否（需求变更需人工批准） |
| `docs/architecture/**` | Read/Write（仅 adr/） | Read | Read | 是 — ADR 需人工批准 |
| `docs/code-governance/**` | Read | Read | Read | 否 |
| `docs/baseline.md` | Read | Read | Read | 否（迁移边界由 D 协调） |
| `prompts/`（运行时提示词） | Read | **No access** | Read | 是 |
| `tradingagents/`（上游） | Read | **No access** | Read | 是（任何改动须 ADR） |
| `tests/`（上游） | Read | **No access** | Read | 是 |
| `.opencode/`、`.agent/` | Read | **No access** | Read | 是（human-only） |
| **All other paths** | **No access** | **No access** | **No access** | — |

---

## Role Definitions

| Role | Permissions | Constraint |
|---|---|---|
| **Plan Agent** | 只读（除 `docs/architecture/adr/` 可写） | 不写代码；读约束、评审缺口 |
| **Build Agent** | 只在白名单路径写 | 不碰上游 `tradingagents/`、`tests/`、`prompts/`、`.opencode/` |
| **Review Agent** | 全文件只读 | 只报告，不修改任何文件 |

---

## Guarded Write（受保护写）

| Path | 保护规则 |
|---|---|
| `src/event_merge/validator.py` | 触及校验规则（ID 归属、字段匹配、≥2 ticker）的变更须 ADR 更新 + 非 B 成员人工评审 |
| `src/event_merge/merger.py` | 触及 LLM 调用次数/状态机的变更须 ADR 更新 + 人工评审 |
| `prompts/` | Build agent 无写权限；prompt 变更需人工批准并触发语义评估 |

**Rationale**：validator 是证据合法性唯一权威（INV-B-3），merger 约束单次调用（INV-B-1），变更会破坏不变量。

---

## Enforcement

| Mechanism | What It Blocks |
|---|---|
| 权限白名单（`.opencode/permissions.jsonc`） | 越权路径的读写 |
| 人工关卡 | 阶段 0/1/2/3 每阶段后人工批准，编码前计划批准 |
| CI schema/回归门禁 | 需求/架构/测试不一致的合并 |

---

## Violation Examples

| Scenario | Violation | Response |
|---|---|---|
| Build agent 修改上游 `tradingagents/dataflows/vendors/yahoo/news.py` | 写 No-access 路径 | 阻断；迁移边界由 D 协调 |
| Build agent 直接改 `prompts/` | 写 No-access 路径 | 阻断；需人工批准 + 语义评估 |
| Plan agent 提出 ADR-002 | 写 `docs/architecture/adr/` | 允许，人工批准后生效 |
| Build agent 新增 `test/offline/` 测试 | 写白名单路径 | 允许，CI 通过后合并 |

---

## Connection to Other Artifacts

| Artifact | Connection |
|---|---|
| ADR-001 | 单次 LLM + validator 权威 → 权限模型在文件级执行 |
| Invariant Register | INV-B-3/INV-B-5：Build 不碰上游、不改 validator 规则 |
| Architecture Blueprint §7 | 本文件为 Blueprint §7 的展开 |
| structural-constraints.md | 权威接口与决策边界 |
