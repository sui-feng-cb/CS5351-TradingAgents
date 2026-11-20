# Baseline and contribution boundary

- Upstream: https://github.com/tauricresearch/tradingagents
- Baseline: `9fa1196fffbcfd9de5146d2dd2869df84ab99838` (2026-11-04).
- License: upstream Apache-2.0, preserved in root LICENSE.
- Team remote: https://github.com/sui-feng-cb/CS5351-TradingAgents
- The local repository retains upstream history; the local clone has been deepened
  from the official `upstream` remote so the historical baseline is available.
- Initialization changes are uncommitted pending human review. No migration or
  feature commit ID is claimed before one actually exists.

| Upstream path | Project path | Classification |
|---|---|---|
| `tradingagents/` | `src/tradingagents/` | Baseline moved, public imports retained |
| `cli/` | `src/cli/` | Baseline moved, entry point retained |
| `tests/conftest.py` | `test/conftest.py` | Shared upstream fixture |
| `tests/test_*.py` | `test/offline/test_*.py` | Upstream offline regression pending path review |
| DeepSeek live class in mixed test | `test/live/test_deepseek_structured.py` | Same real-API assertions, relocated |
| Upstream README | `docs/upstream/README.md` | Preserved reference, relative image links adjusted |

Three path-sensitive upstream tests require root/src path adjustments:
test_version, test_layering, test_i18n_coverage. Test assertions and acceptance
semantics must remain intact. Production Python sources are not feature changes.
The migration is not accepted until all such paths are adapted and the baseline
suite passes.

Existing parallel analysts, date guards, reports, backtests, memory, portfolio
context and rating parser remain upstream contributions. The planned comparison,
event grouping, manifest query and decision gate cannot be claimed as delivered.
See `docs/verification/initialization.md` for actual installation/test results.
