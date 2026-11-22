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

## Expected C acceptance failure (tests-first) — current Python 3.13 `.venv`

The C module `tradingagents.enhancements.manifest` and the `manifest query`
subcommand are intentionally absent.

```
$ .venv/bin/python -m pytest -q --tb=line test/offline/test_manifest.py
...
20 failed in 11.05s
```

All 20 are expected reds. Two patterns:

- CLI-driven cases reach the on-disk assertion because the real CLI path runs:
  - `test_same_day_rerun_keeps_two_distinct_records`:
    `test_manifest.py:405 assert len(manifests) == 2` → `0 == 2`.
  - `test_cli_manifest_query_subcommand_runs_and_starts_no_analysis`:
    `test_manifest.py:610 assert result.exit_code == 0` → `2`,
    output `No such command 'manifest'`.
- Remaining cases fail at the missing-module guard:

```
E   Failed: C implementation missing: tradingagents.enhancements.manifest
    (ModuleNotFoundError("No module named 'tradingagents.enhancements'")).
    Expected until the approved implementation lands.
```

Collection succeeds (20 collected); each case fails with a self-describing
message, so the rest of the suite is not blocked.

## Lint and governance — current Python 3.13 `.venv`

```
$ .venv/bin/ruff check test/offline/test_manifest.py
All checks passed!
$ .venv/bin/python scripts/check_governance.py
Registry/schema, course layout and permission synchronization passed
Basic credential-pattern scan passed (not a complete secret detector)
```

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

## Existing D test status (reported separately)

- Early environment (Python 3.14.4, no deps): `test/offline/test_eligibility.py`
  did not collect — `ModuleNotFoundError: No module named 'langchain_core'`. That
  was an environment-dependency failure, not a D acceptance result.
- Current Python 3.13 `.venv`: the D file collects and reports
  **32 failed, 3 passed in 10.00s**, i.e. the D module is also still absent and
  its remaining cases are expected reds. This is D's own tests-first state, not a
  C regression, and is noted only because it shares the checkout under test.

## Pending

- Non-C independent `Test-Plan-Approved` review of the tests-only head.
- Full `test/offline` regression, `mypy`, `pip check` and the C timing run on the
  project Python 3.13 environment (C suite, `ruff` and governance already ran on
  3.13 here).
- NFR-C ≤2 s measurement is still untested; its threshold remains pending
  approval.
- Team confirmation of A/Python run-association interface, backtest coverage and
  reused-custom-path policy before any locking assertion is added.
