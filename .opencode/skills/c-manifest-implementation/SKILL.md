---
name: c-manifest-implementation
description: Use when implementing or verifying FR-C/NFR-C run manifests and the read-only `manifest query` CLI in CS5351-TradingAgents.
---

# C manifest implementation (FR-C / NFR-C)

Reusable notes for the C module (`src/tradingagents/enhancements/manifest.py`),
the `manifest query` CLI and the CLI run-recording hooks. Contracts live in
`docs/architecture/interface-contracts.md` and
`docs/architecture/run-manifest-v1.schema.json`; evidence in
`docs/verification/c-manifest.md`.

## Shape

- One `run_manifest.json` per execution attempt at
  `<results_root>/<ticker>/<YYYY-MM-DD>/runs/<uuid>/` (fresh UUID per attempt, so
  same-day reruns keep separate records).
- 16 top-level fields, `additionalProperties: false`; nullable:
  `finished_at`(running), `code_version`, `models`, `error`. `reports` is a
  required object whose `complete_report_md`/`complete_report_html` subkeys are
  optional and nullable; present values are **paths relative to the results
  root**. `status` in `running|succeeded|failed`. `schema_version` must be int 1.
- Errors are a fixed `code` + safe text; never a traceback or secret.

## Invariants that live in code, not the schema

- Path containment is checked at runtime: query resolves each manifest/report
  path (symlinks included) and skips out-of-root ones with a warning; a write
  refuses a target that resolves outside the results root before creating
  directories.
- Missing-manifest warnings only for recognizable run dirs
  (`<ticker>/<date>/runs/<uuid>/`), skipping unreadable branches, symlinked dirs
  and impossible calendar dates.
- Query is read-only; tolerates bad JSON / unknown schema / non-UTF-8 per file
  and continues. A declared-but-missing report warns but keeps the record.
- Vendor metadata on write is filtered to known categories/tools/provider
  identifiers (keeps ordered chains like `sec_edgar,yfinance`, drops credential
  URLs and unknown keys).

## Verification commands (project Python 3.13 `.venv`)

```
.venv/bin/python -m pytest -q test/offline/test_manifest.py          # C suite (47)
TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
.venv/bin/ruff check .
.venv/bin/python scripts/check_governance.py
.venv/bin/python -m mypy scripts/check_governance.py
.tools/uv/uv pip check --python .venv/bin/python
```

Schema check (dev dependency `jsonschema`, Draft 2020-12):

```
.venv/bin/python - <<'PY'
import json
from jsonschema import Draft202012Validator
s=json.load(open('docs/architecture/run-manifest-v1.schema.json'))
Draft202012Validator.check_schema(s); v=Draft202012Validator(s)
for n in ('sample_success.json','sample_failed.json'):
    data=json.load(open(f'test/fixtures/run_manifests/{n}'))
    v.validate(data)  # raises if the sample violates the schema
print('samples OK')
PY
```

## Performance diagnosis (NFR-C)

The 2 s budget is dominated by CLI start-up imports, not the scan. To diagnose:

1. Generate data with the v2 generator:
   `test/fixtures/run_manifests/gen_dataset.py --out DIR --count 1000`.
2. In-process scan time (isolates the real query):
   time `query_manifests(DIR, ticker="AAPL")` with `perf_counter` after import —
   typically ~0.15 s for 1,000 manifests.
3. Separate-process CLI wall time, empty vs full dir: if both are similar, the
   cost is import/startup. `.venv/bin/python -X importtime -m cli.main manifest
   query ...` names the heavy import chain.
4. Fix pattern that worked: defer analysis/backtest/model/vendor imports into the
   command bodies, share a lightweight `cli.console` Console, keep patchable
   thin wrappers for `cli.main.run_analysis`/`run_backtest`/`summarize`. Start-up
   imports dropped 2651 → 302 modules; CLI query fell from ~20 s to ~1.8 s.

Run the timing tool:
`.venv/bin/python test/benchmarks/bench_manifest_query.py --results-dir DIR --count 1000 --ticker AAPL`
— it checks each run's match count and flags the proposed ≤2 s threshold (local
baseline only; formal CI acceptance pending team confirmation).

## Status to preserve

- FR-C/NFR-C are implemented **locally** (47 C cases); the implementation PR
  still needs an independent non-C review.
- PR #5's 20/29 expected-failure counts are historical, superseded by the green
  suite.
- Reused-custom-report-directory policy, the `analysis_failed`/`Analysis failed.`
  literals, the CLI `matches`/`warnings` outer shape and the NFR-C CI runner +
  threshold remain to be team-confirmed.
