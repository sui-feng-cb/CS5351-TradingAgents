# MCP Tool Manifest — B 模块

> **Purpose** (D3)：可用工具及各角色的调用权限；记录项目实际采用的工具/MCP 配置。

---

## 1. 可用工具清单

| 工具 | 用途 | 说明 |
|---|---|---|
| OpenCode coding agent（本仓库） | 规划、编码、评审 | 由 `AGENTS.md` 入口驱动，分阶段人工关卡 |
| `pytest` | 测试 | `test/offline/` 默认 CI；`test/live/` 需 API |
| LLM provider（上游配置复用） | 事件归并 | 仅 `merger.merge_once()` 单次调用，不新增供应商 |
| 上游新闻数据能力 | 新闻抓取 | `route_to_vendor("get_news", …)` 复用，不修改 |
| CI（`.github/workflows/ci.yml`） | 门禁 | schema/静态分析/offline/语义评估/回归 |

## 2. 角色 → 工具/权限

| 角色 | 可调用工具 | 禁止 |
|---|---|---|
| Plan Agent | 读文档、探索代码（只读）、写 ADR | 写代码、改上游 |
| Build Agent | 写 `src/`、`test/` 白名单；运行 pytest 自验证 | 调真实模型做语义评估（用 mock/fixtures）；改上游、prompts、.opencode |
| Review Agent | 读全部文件、运行测试 | 修改任何文件 |
| Human | 批准计划/关卡/ADR、冻结语义评估集 | — |

## 3. 运行时工具/MCP 配置

| 项 | 配置 |
|---|---|
| LLM 调用 | 复用上游 `config.get_config()` 的模型/provider 配置；B 模块不新增密钥/供应商 |
| 语义评估模型 | 与归并模型一致，记录 model/provider + 样例版本（写入 `evaluation-logbook.md`） |
| 测试标记 | 需建立 `offline`/`live` pytest 标记（D8，阶段 3 接入 CI） |

## 4. 未采用/禁用

| 工具 | 状态 | 理由 |
|---|---|---|
| 新增新闻供应商 | 禁用 | v3 §3 范围外 |
| 逐条/双 LLM 归并 | 禁用 | 违反 INV-B-1 单次调用 |
