# Baseline — 上游基线与归属

> **Purpose** (v4 §7)：登记上游 URL、锁定 commit、路径映射、迁移边界与归属说明。

---

## 1. 上游来源

| 项 | 值 |
|---|---|
| 上游仓库 URL | `https://github.com/TauricResearch/TradingAgents`（v4 §2 记作 `https://github.com/tauricresearch/tradingagents`，同一仓库大小写差异） |
| 远程命名 | `origin`（团队仓库）；官方上游 `upstream`（按 v4 §8 建立） |
| 锁定 commit | `9fa1196fffbcfd9de5146d2dd2869df84ab99838` |
| commit 主题 | `announce Trading-R1 official release` |
| 锁定日期 | 2026-11-04（v4 §2 记录） |
| 许可证 | 保留上游 LICENSE（Apache-2.0，见根目录 `LICENSE`） |

## 2. 基线状态

- 当前仓库 HEAD 位于锁定 commit `9fa1196`，保留上游原布局与历史。
- 上游代码仍在根目录 `tradingagents/`、`cli/`、`tests/`；`src/`、`test/` 尚不存在（迁移由 D 协调，见 §4）。

## 3. 路径映射（上游 → 团队）

| 上游路径 | 团队路径 | 规则 |
|---|---|---|
| `tradingagents/` | `src/tradingagents/`（迁移后） | 迁移由 D 协调；B 模块新增代码暂放 `src/event_merge/`，import 上游 `tradingagents` 包 |
| `cli/` | `src/cli/`（迁移后） | B 模块 CLI 放 `src/cli/event_merge_cmd.py` |
| `tests/` | `test/`（迁移后，按 D8 归 offline/live/fixtures） | B 模块测试放 `test/offline/`、`test/fixtures/` |

## 4. 迁移边界

| 边界 | 说明 |
|---|---|
| 迁移责任人 | 成员 D（v4 §3） |
| 迁移方式 | 以独立迁移提交将应用包与 CLI 移至 `src/`，上游 `tests/` 按 D8 归入 `test/` |
| B 模块在此边界上的约束 | B 模块新增/修改代码一律放 `src/`、`test/`，**不触碰**上游 `tradingagents/`、`tests/`、`config` 行为 |
| 提交边界标注 | 迁移提交与增强提交边界在本文件 + Git 历史标出 |

## 5. 归属说明

| 内容 | 归属 |
|---|---|
| 上游 `tradingagents/`、`cli/`、`tests/` 全部现有代码 | 上游 TauricResearch，只读依赖与复用来源 |
| B 模块新增（`src/event_merge/`、`src/cli/event_merge_cmd.py`、`test/offline/`、`test/fixtures/`） | 团队成员 B |
| 复用上游新闻能力（router/vendors/date_window/default_config） | 只读复用，不改行为（见 `structural-constraints.md`） |
| 文档（`docs/**`） | 团队共同维护，B 模块文档由成员 B 撰写 |

## 6. 验证证据（待阶段迁移后补）

- [ ] 基线测试在锁定 commit 运行通过的记录（迁移前留证）
- [ ] 迁移后包安装、CLI 启动、离线回归、live 收集、缓存/报告路径验证记录
