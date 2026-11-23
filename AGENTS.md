# CS5351 小组项目 — B 模块（FR-B / NFR-B）编码代理入口

> 本文件是 coding agent 的统一入口。agent 进入项目后先读本文件，再读 `Prompt.md`，提出计划并**在生成代码前停止等待人工批准**。

## 1. 构建目标

在锁定 commit `9fa1196fffbcfd9de5146d2dd2869df84ab99838` 的 TradingAgents 上游基线上，实现 B 模块：

- **FR-B 跨标的共同事件归并**：输入 2–3 个 ticker + ≤7 天回看窗口，复用上游已有新闻数据能力（每 ticker 最多 5 条），以**一次** LLM 调用把记录归并为「跨标的共同事件」，并用确定性 validator 校验证据。
- **NFR-B 证据可追溯性**：输出 evidence ID 解析率 100%，伪造/跨运行 ID 数为 0。

确定性代码是权威，模型输出是建议；模型输出不能覆盖确定性边界。

## 2. 读取顺序（生成任何代码前必须全部读完）

1. 本文件（`AGENTS.md`）
2. `Prompt.md`（启动提示词）
3. `_refs/CS5351小组项目要求v4.md` —— 重点 §4 FR-B、§5 NFR-B、§7 目录结构、§9 D1–D9、§12 CI 门禁
4. `_refs/CS5351小组项目A-D模块的最低任务与验收标准v3.md` —— 重点 §3 B
5. `_refs/docs_example/docs/AGENTS.md`、`_refs/docs_example/docs/architecture/README.md`、`_refs/docs_example/docs/architecture/adr/README.md` —— 文档**内容/结构/书写时机**范本
6. 上游代码中与「新闻数据」相关的模块（用于复用，不修改其行为）

## 3. 代码基线

- 上游已克隆到本仓库根目录，保持原布局与历史；上游代码作为只读依赖与复用来源。
- 团队新增或实质修改的代码一律放 `src/`（应用包）、`src/cli/`、`test/`，并遵守 D8 的 `test/offline/`（无网络/密钥）、`test/live/`（需 API）、`test/fixtures/` 划分。
- **范围外**：新增新闻供应商、价格预测、热度评分、影响力排序、社交网络趋势分析。

## 4. 文档目录结构（固定路径，不得自创）

```text
docs/
├── baseline.md
├── req/
│   ├── requirements.yaml
│   └── req-schema.json
├── architecture/
│   ├── architecture-blueprint.md
│   ├── adr/001-<decision>.md
│   ├── invariants.md
│   ├── trace-matrix.md
│   ├── memory-design.md
│   ├── permission-model.md
│   ├── runtime-policy-catalog.md
│   ├── evaluation-table.md
│   ├── evaluation-logbook.md   # 可选
│   ├── risk-list.md            # 可选
│   └── option-ledger.md        # 可选
├── code-governance/
│   ├── structural-constraints.md
│   ├── verification-constraints.md
│   └── mcp-tool-manifest.md
├── ai-use-log.yaml
├── review-memo.md
├── debt-register.md
└── bug-diary.md
```

根目录 `architecture-blueprint.md` 只放指向 `docs/architecture/architecture-blueprint.md` 的 Markdown 链接。

## 5. 文档内容、结构与书写时机

| 文档 | 内容要点 | 书写时机 |
|---|---|---|
| `docs/req/requirements.yaml` | 机器可读 PRD/注册表。每条含 ID、类型、需求陈述、可机器检查的 fit criterion、MoSCoW、来源与取舍、Owner/验收人。类型覆盖功能/不变量/质量属性/性能/成本/治理/安全。 | 编码前登记 FR-B、NFR-B；需求变化时更新 |
| `docs/req/req-schema.json` | 注册表的 JSON Schema，供 CI 校验 | 编码前，与注册表同步 |
| `docs/architecture/architecture-blueprint.md` | 范围、驱动因素、系统与组件边界、建议性/权威性决策分界、agent 工作流、权限、验证、可观测性、变更政策 | 编码前 |
| `docs/architecture/adr/001-<decision>.md` | 一决策一文件：设计问题、比较过的方案、选择理由、后果、重新考虑条件；记录 AI 上下文分层、Token 预算、关键约束重新注入政策 | 做架构决策时 |
| `docs/architecture/invariants.md` | 每条不变量：陈述、来源需求、执行组件、验证方法、违反后的兜底动作 | 编码前，零容忍 |
| `docs/architecture/trace-matrix.md` | 需求 → 执行组件 → 测试/证据 → 监控 | **持续**随实现与验证更新 |
| `docs/architecture/memory-design.md` | 跨会话/中断/版本保留的状态、读写、所有权、保留期、恢复、隐私 | 编码前 |
| `docs/architecture/permission-model.md` | 按 agent 角色规定文件级读写权限，默认无权限，白名单逐项加 | 编码前 |
| `docs/architecture/runtime-policy-catalog.md` | 降级/失败路径触发条件与运行时动作 | 编码前 |
| `docs/architecture/evaluation-table.md` | 候选架构比较、评价依据、设计取舍 | 架构评估时 |
| `docs/code-governance/structural-constraints.md` | 架构元素→模块映射、扩展现有基线的边界、权威接口与决策边界 | 编码前，随结构变化更新 |
| `docs/code-governance/verification-constraints.md` | 每个验收标准至少一个测试、每个不变量至少一个违反即失败的测试 | 编码前 |
| `docs/code-governance/mcp-tool-manifest.md` | 可用工具及各角色调用权限、实际采用的工具/MCP 配置 | 编码前，随工具变化更新 |
| `docs/ai-use-log.yaml` | 每个 PR 记录 agent、需求、会话引用、人工监督、变更、验证结果 | 每个 PR 持续更新 |
| `docs/review-memo.md` | 每个 PR 的需求/架构/代码/测试/运行元数据/安全/效率评审，结论 APPROVE/CHANGES REQUIRED/REJECT | 每个 PR 持续更新 |
| `docs/debt-register.md` | 提示词腐化、虚构/隐藏依赖、难改代码、agent 膨胀、评估债、护栏债、认知债 | 发现技术债时持续更新 |
| `docs/bug-diary.md` | 显著缺陷的症状、复现、分类、根因、修复、暴露的不变量缺口 | 修复缺陷时持续更新 |

## 6. FR-B / NFR-B 规格摘要

完整要求以 `_refs/CS5351小组项目A-D模块的最低任务与验收标准v3.md` §3 为准。要点：

### 输入与范围
- 输入 2–3 个 ticker，回看窗口 ≤7 天。
- 每个 ticker 用上游新闻数据能力取 ≤5 条记录；每条分配本次运行唯一 evidence ID，保留 ticker、日期、来源、模型可读标题/内容片段。
- 将本次全部限定记录作为**一组**交给模型做事件归并，**最多一次** LLM 调用；不得逐条新闻分别调用模型。

### 输出与失败行为
- 每个归并事件输出：简短摘要、涉及的 ticker、支持的 evidence ID/来源/日期。
- 一个事件至少有两个 ticker 的记录支持；证据不足的记录留作未归并，不得强行配组。
- 无可用新闻 → 标记「数据不可用/无记录」；有新闻但未发现跨 ticker 共同事件 → 才报告「没有发现共同事件」。
- 确定性 validator 检查 evidence ID 是否属于本次输入、ticker/date 是否与该记录相符；失败则该条不得作为已验证事实输出。

### 完成标准（最低）
- 固定人工标注离线评估样例覆盖：同一事件、不同事件、同标的重复报道、时间窗口外报道、无数据、证据不足。
- 模型输出符合结构化 schema；同事件有来源支持；不同事件不得因共享泛化词而强行归并。
- 离线测试 mock 模型输出，覆盖：合法分组、伪造 evidence ID、错配 ticker/date、单一 ticker 事件、无记录状态。
- 固定语义评估集 ≥20 对（≥10 同事件 / ≥10 不同事件）；pairwise precision ≥0.80、recall ≥0.70。记录模型/provider、样例版本、precision/recall；CI 未达阈值即阻断。
- **NFR-B**：输出 evidence ID 解析率 100%，伪造/跨运行 ID = 0，由确定性 validator 测试验证。

## 7. 权威边界与不变量

- 确定性 validator 是证据合法性的唯一权威；校验失败的证据不得输出为已验证事实。
- 每次归并最多一次 LLM 调用。
- 一个事件至少关联两个 ticker 的记录。
- 证据不足的记录保留为未归并，不强行配对。
- 模型输出不能覆盖确定性代码的判定。

## 8. 验证要求

- 每个验收标准至少对应一个测试；每个不变量至少一个「违反即失败」的测试；测试须引用需求或不变量 ID。
- offline 测试默认 CI 运行，不调用真实模型/API（用 mock/fixtures）。
- 语义评估用固定评估集，记录模型/provider、样例版本、precision/recall。
- 生成代码前先提出计划（需求追踪、接口契约、范围、测试策略、执行步骤）并**停止等待人工批准**；后续构建与自验证分阶段经人工关卡。
