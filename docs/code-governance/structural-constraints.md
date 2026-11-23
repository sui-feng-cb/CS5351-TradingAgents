# Structural Constraints — B 模块

> **Purpose** (D3)：架构元素 → 模块映射、扩展现有基线的边界、模块/函数对应的 ADR 与不变量、权威接口与决策边界。

---

## 1. 架构元素 → 模块映射

| 架构元素 | 模块（`src/`） | 关键函数/类 | 对应 ADR / Invariant |
|---|---|---|---|
| Input Window | `src/event_merge/input.py` | `build_window(tickers, as_of, lookback)` | FR-B-1 |
| News Adapter | `src/event_merge/news_source.py` | `fetch_records()` | FR-B-2；复用上游（ADR-001） |
| Evidence Registry | `src/event_merge/evidence.py` | `EvidenceRegistry` | FR-B-2、NFR-B-1、INV-B-3 |
| Schema | `src/event_merge/schemas.py` | `NewsRecord`/`MergedEvent`/`MergeInput`/`MergeResult` | FR-B-4 |
| Merger | `src/event_merge/merger.py` | `merge_once()`、状态机 | FR-B-3/6、INV-B-1 |
| Validator | `src/event_merge/validator.py` | `validate(registry, model_events)` | FR-B-5/7、INV-B-2/3/5 |
| CLI | `src/cli/event_merge_cmd.py` | `merge-events --tickers ... --lookback 7` | FR-B-1（可选集成） |

## 2. 扩展现有基线的边界

| 边界 | 规则 |
|---|---|
| 上游 `tradingagents/` | **只读依赖与复用来源**；不改 `dataflows/router.py`、`vendors/*/news.py`、`config.py`、`default_config.py` 行为 |
| 上游 `tests/` | 不触碰；迁移归 D 协调（`docs/baseline.md`） |
| 新增/修改代码 | 一律放 `src/`（应用包）、`src/cli/`、`test/` |
| 测试目录 | 遵守 D8：`test/offline/`（无网络/密钥）、`test/live/`（需 API）、`test/fixtures/` |
| 范围外 | 新增新闻供应商、价格预测、热度评分、影响力排序、社交网络趋势 |

### 复用上游的具体方式（只读适配）

| 上游能力 | 复用方式 |
|---|---|
| `tradingagents/dataflows/router.py:route_to_vendor("get_news", …)` | yfinance/alpha_vantage 新闻路由 |
| `tradingagents/dataflows/vendors/yahoo/news.py:_extract_article_data` | 结构化 `{title,summary,publisher,link,pub_date}` 提取 |
| `tradingagents/dataflows/vendors/alpha_vantage/news.py:get_news` | 读 `feed` 字段 |
| `tradingagents/dataflows/date_window.py:in_window` | ≤7 天窗口过滤、时间窗口外报道剔除 |
| `tradingagents/default_config.py:news_article_limit` | 拉取上限（B 模块内再硬约束到 5） |

## 3. 权威接口与决策边界

| 权威接口 | 决策边界 | 谁说了算 |
|---|---|---|
| `validator.validate(registry, model_events)` | 证据是否合法可输出（ID 归属、ticker/date/source、≥2 ticker） | **确定性 validator（权威）** |
| `EvidenceRegistry.issued_ids` | 哪些 evidence ID 属于本次运行 | **确定性 registry（权威）** |
| `merger.merge_once()` | 事件归并建议（语义判断） | 模型（建议，非权威） |
| `status` 状态机 | merged / no_common_event / data_unavailable | 确定性代码（基于 records 与 validator 结果） |

**核心边界：模型输出是建议，validator 判定是权威；模型不能覆盖确定性边界（INV-B-5）。**

## 4. 与不变量/ADR 的绑定

| 模块 | 绑定约束 |
|---|---|
| `merger.py` | 最多一次 LLM 调用（INV-B-1、ADR-001） |
| `validator.py` | 证据合法性唯一权威（INV-B-3）、≥2 ticker（INV-B-2）、不强配（INV-B-4）、权威分层（INV-B-5） |
| `evidence.py` | ID 本次运行唯一、跨运行天然唯一（NFR-B-1/2） |
