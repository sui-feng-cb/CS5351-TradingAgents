# C manifest tests-and-docs verification

Status: tests-and-docs-only baseline, pending human diff review and independent
non-C test-plan approval. No C application code, commit, push, PR or merge is
claimed. Recorded on the project Python 3.13 `.venv`.

## Environment actually used for this record

Current run (project environment, authoritative for this record):

- Python 3.13.18 in the project-local `.venv` (installed with `.tools/uv/uv
  sync --frozen --extra dev`). All project dependencies present.
- Suite run normally (with `test/conftest.py`, no `--noconftest`).

Early run (superseded, kept for history): a minimal Python 3.14.4 interpreter
without project dependencies (`langchain_core`, `yfinance`, `curl_cffi`, `ruff`,
`mypy` absent). The C suite was run there with `--noconftest` to isolate it from
unrelated import failures. Those numbers are not the target-runner result and are
retained only to show the same expected-red outcome held before `.venv` existed.

## Baseline: current checkout

- Branch `C`; baseline commit family: this branch from `main` over
  `9fa1196fffbcfd9de5146d2dd2869df84ab99838` (see `docs/baseline.md`).

## PR #5 review snapshot (separate from this round)

At PR #5 head `64f7bec` the reviewer recorded **20 expected C failures and 1532
passing tests**. That snapshot predates the additional P2 cases added since; it
is kept as the review record and is NOT this round's measurement. This round's
actual counts are in the next section.

## Expected C acceptance failure (tests-first) — this round, Python 3.13 `.venv`

Full-repository baseline (see the exact command and totals in "Full baseline"
below). The C module `tradingagents.enhancements.manifest` and the `manifest
query` subcommand are intentionally absent, so `test/offline/test_manifest.py`
is the only file with failures.

```
$ TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
29 failed, 1532 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed
```

All 29 failures are the expected C/CLI reds, in three patterns:

- Real-CLI success/failure cases reach the on-disk `run_manifest.json`
  assertion (e.g. `test_same_day_rerun_keeps_two_distinct_records`,
  `test_cli_saved_report_path_is_what_manifest_records`,
  `test_cli_run_failure_is_recorded_with_a_safe_error_code`): `0 == N` because
  no manifest was written.
- CLI query cases fail at `assert code == 0` / `assert result.exit_code == 0`
  with output `No such command 'manifest'`.
- Remaining cases fail at the missing-module guard:

```
E   Failed: C implementation missing: tradingagents.enhancements.manifest
    (ImportError("cannot import name 'manifest' from 'tradingagents.enhancements'")).
    Expected until the approved implementation lands.
```

Collection succeeds (29 collected); each case fails with a self-describing
message, so the rest of the suite is not blocked. No non-C file failed.

## Full baseline, Ruff, governance — this round

```
$ TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
29 failed, 1532 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 256.04s
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/python scripts/check_governance.py
Registry/schema, course layout and permission synchronization passed
Basic credential-pattern scan passed (not a complete secret detector)
```

The 29 failures are all `test/offline/test_manifest.py`; the skip is the optional
`langchain_aws` Bedrock dependency and the deselection is the live DeepSeek test.

## Fixture generator (deterministic)

```
$ python3.14 test/fixtures/run_manifests/gen_dataset.py --out <ds1> --count 1000
generator v2: wrote 1000 manifests to <ds1>
$ # regenerate into <ds2> with the same seed
$ diff -r <ds1> <ds2>      # no differences
```

Ticker distribution across 1000 rows (seed 20261120): AAPL 137, 0700.HK 133,
TSLA 132, MSFT 127, AMD 126, NVDA 120, AMZN 113, GOOGL 112. Regeneration is
byte-identical.

Invariant checks over the 1,000 manifests: every non-null `reports` path is
relative to the results root and resolves to a file the generator wrote, and
`finished_at` is never earlier than `started_at` (0 problems).

## Timing tool (tool only; real NFR-C conclusion deferred to CI)

```
$ PYTHONPATH=src:. python3.14 test/benchmarks/bench_manifest_query.py \
      --results-dir <ds1> --ticker AAPL
run 1: exit=1 ... match_ok=False ok=False
...
NOTE: <=2.0s per run is a PROPOSED threshold pending team approval.
```

Against the un-implemented `manifest query` command, the tool exits 1 and
reports captured startup/scan timings; in this environment it additionally hit
the missing `langchain_core` dependency of the CLI import chain. This is baseline
tooling evidence, not an NFR-C pass. The real three-process <=2 s result is
produced by CI after implementation.

The tool refuses to measure a dataset whose manifest count differs from
`--count` (default 1,000): it prints a clear error and returns exit 2.

```
$ python3.14 test/benchmarks/bench_manifest_query.py --results-dir <ds1> --count 999
ERROR: expected 999 manifests in <ds1>, found 1000. Regenerate the dataset or
pass the matching --count before timing.
```

## Existing D test status (historical, pre-main-merge — reported separately)

This note describes D's state before D's implementation was merged into `main`
and is kept only as history; it is not a current measurement of this round and
not a C result.

- Early environment (Python 3.14.4, no deps): `test/offline/test_eligibility.py`
  did not collect — `ModuleNotFoundError: No module named 'langchain_core'`. That
  was an environment-dependency failure, not a D acceptance result.
- At the time recorded, on Python 3.13 `.venv` the D file reported **32 failed,
  3 passed**, i.e. the D module was absent and its cases were expected reds.

## Pending

- Non-C independent `Test-Plan-Approved` review of the tests-only head.
- `mypy` and `pip check` on the project Python 3.13 environment (C suite,
  `ruff`, governance and the full baseline already ran on 3.13 here).
- NFR-C ≤2 s measurement is still untested; its threshold remains pending
  approval.
- Team confirmation of A/Python run-association interface, backtest coverage,
  reused-custom-path policy, the `analysis_failed` / `Analysis failed.` fixed
  values, and the CLI `matches`/`warnings` outer structure before any locking
  assertion is finalized.
