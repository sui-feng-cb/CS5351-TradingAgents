# C manifest verification

Status: implementation-complete locally on branch `c-manifest-implementation`; the
C module, the `manifest query` CLI command and the CLI run-recording hooks are
implemented. An independent review of the implementation PR is still pending;
remaining plan decisions and formal NFR-C acceptance are pending too. Recorded on
the project Python 3.13 `.venv`.

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

- Branch `c-manifest-implementation`; baseline commit family: this branch from `main` over
  `9fa1196fffbcfd9de5146d2dd2869df84ab99838` (see `docs/baseline.md`).

## PR #5 review snapshot (separate from this round)

At PR #5 head `64f7bec` the reviewer recorded **20 expected C failures and 1532
passing tests**. That snapshot predates the additional P2 cases added since; it
is kept as the review record and is NOT this round's measurement. This round's
actual counts are in the next section.

## Current implementation — full local regression (this round, Python 3.13 `.venv`)

The C module, `manifest query` CLI and CLI run-recording are implemented, so the
whole offline suite is green. The PR #5 tests-first baseline above is retained as
history; it is superseded by this result.

```
$ TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
1579 passed, 1 skipped, 1 deselected, 24 warnings, 100 subtests passed in 52.64s
```

- Skip: optional `langchain_aws` Bedrock dependency. Deselect: live DeepSeek.
- `test/offline/test_manifest.py`: 47 cases, all passing (schema/validation,
  write, CLI run recording, query, filters, bad-record tolerance, secrets,
  unsafe paths, result-root boundary scan, CLI startup regression).
- Schema `docs/architecture/run-manifest-v1.schema.json` (Draft 2020-12) mirrors
  `validate_manifest`: both fixed samples validate; an empty `reports: {}` is
  accepted; an unknown report key and an unknown top-level field are rejected.
  The two report subkeys are optional/nullable. A declared-but-missing report
  warns and keeps its record; the reused-custom-report-directory policy remains
  to be confirmed; the implementation PR still needs an independent non-C review.

## Repo-wide checks — this round

```
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/python scripts/check_governance.py
Registry/schema, course layout and permission synchronization passed
Basic credential-pattern scan passed (not a complete secret detector)
$ .venv/bin/python -m mypy scripts/check_governance.py
Success: no issues found in 1 source file
$ .tools/uv/uv pip check --python .venv/bin/python
Checked 102 packages in 541ms
All installed packages are compatible
```

(`.venv` has no bundled `pip`; dependency consistency is checked with
`uv pip check`, matching the initialization record.)

## CLI startup optimization (this round)

The `manifest query` command no longer imports the analysis graph, backtest,
model SDKs or vendor routing at start-up: those imports were deferred into the
commands that use them, a lightweight `cli.console` Console was shared, and the
`login`/`logout` plan is built from a light literal (still `chatgpt` only). The
patchable entry points `cli.main.run_analysis` / `run_backtest` / `summarize`
remain as thin lazy wrappers. Modules imported at start-up dropped from 2651 to
302. A separate-process regression test asserts the query starts with none of
those heavy modules loaded.

## Fixture generator (deterministic)

Recorded in the earlier Python 3.14 environment; the generator is interpreter
independent and the current `.venv` v2 rebuild is byte-identical.

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

## Timing tool — NFR-C local baseline (this round; formal acceptance pending)

Dataset: 1,000 manifests regenerated with the v2 generator (`gen_dataset.py`,
seed 20261120) into a fresh WSL temp dir (the earlier `/tmp` dataset had been
cleaned). Generation ran separately and is excluded from the timings.

```
$ .venv/bin/python test/benchmarks/bench_manifest_query.py \
      --results-dir <fresh v2 dir> --count 1000 --ticker AAPL
run 1: exit=0 elapsed=1.889s expected_matches=137 match_ok=True ok=True
run 2: exit=0 elapsed=1.837s expected_matches=137 match_ok=True ok=True
run 3: exit=0 elapsed=1.808s expected_matches=137 match_ok=True ok=True
slowest=1.889s proposed_budget=2.0s within_proposed=True all_runs_ok=True
```

- Three independent CLI processes: **1.889 / 1.837 / 1.808 s**, each matching
  **137** AAPL records; the script validates the count per run.
- These are a **local WSL baseline**, not formal NFR-C acceptance. The fixed CI
  runner, the three-process method and the ≤2.0 s threshold still require team
  confirmation; formal acceptance is deferred to CI.

The tool refuses to measure a dataset whose manifest count differs from
`--count` (default 1,000): it prints a clear error and returns exit 2.

```
$ .venv/bin/python test/benchmarks/bench_manifest_query.py --results-dir <ds> --count 999
ERROR: expected 999 manifests in <ds>, found 1000. Regenerate the dataset or
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

- Independent non-C review of the implementation PR remains outstanding. (The
  PR #5 review record above — `64f7bec`, 20 expected failures — is kept as
  history.)
- Non-C independent `Test-Plan-Approved` review of any remaining locking
  decisions.
- NFR-C: the local WSL baseline is inside the proposed 2 s budget, but formal
  acceptance depends on the team confirming the fixed CI runner, the
  three-process method and the ≤2.0 s threshold, then a CI run.
- Team confirmation of the A/Python run-association interface, backtest coverage,
  reused-custom-path policy, the `analysis_failed` / `Analysis failed.` fixed
  values, and the CLI `matches`/`warnings` outer structure.

## Merge with origin/main (0a48402) — this round

Merged origin/main (0a48402) into `c-manifest-implementation` (HEAD 6362ddb) and
resolved three documentation conflicts (ai-use-log, interface-contracts,
requirements). The earlier section recorded **1579 passed** as the pre-merge C
baseline; it is kept as history. Post-merge actual results:

```
$ TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
1665 passed, 1 skipped, 2 deselected, 24 warnings, 100 subtests passed in 76.80s
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/python scripts/check_governance.py
Registry/schema, course layout and permission synchronization passed
Basic credential-pattern scan passed (not a complete secret detector)
$ git diff --check
(clean)
```

The C module, `manifest query` and run-recording remain green; the C suite is
unchanged at 47 cases. The implementation PR's independent review and formal
NFR-C acceptance (fixed CI runner, three-process method, ≤2.0 s threshold) are
still pending; the reused-custom-report-directory policy is still to confirm.

## PR #9 review fix — report-save failure (this round)

Reviewer feedback: a report-save failure after a successful analysis was
indistinguishable from a deliberately skipped save (both recorded `error: null`,
null report paths). Fix keeps the v1 field structure and the existing query
`warnings`.

Original failing assertion (before the fix):

```
test/offline/test_manifest.py:815
assert written["error"] == {"code": "report_save_failed", "message": "Report save failed."}
E   AssertionError: assert None == {'code': 'report_save_failed', 'message': 'Report save failed.'}
```

After the fix (all green):

- `status` records the analysis result; on a save failure it stays `succeeded`,
  report paths are `null`, and `error` is
  `{"code": "report_save_failed", "message": "Report save failed."}`. A skipped
  save keeps `error: null`; a normal save records the actual relative paths.
- `_offer_reports` returns the save outcome (with a `save_failed` flag) while
  still returning `None` for a skipped save, so existing callers/stubs are
  unchanged. The console uses fixed text; the raw exception is never stored.
- `manifest query` recognises `report_save_failed` and adds a fixed warning while
  keeping the matching record; the CLI `--json` `matches`/`warnings` shape is
  unchanged.

Targeted red-to-green:

```
$ .venv/bin/python -m pytest -q test/offline/test_manifest.py \
    -k "report_save_failure or skipped_save_control or save_then_show or saved_report_path"
5 passed
$ .venv/bin/python -m pytest -q test/offline/test_manifest.py \
    test/offline/test_cli_headless.py test/offline/test_eligibility.py
116 passed
```

Full local regression and gates (this round, Python 3.13 `.venv`):

```
$ TZ=America/New_York .venv/bin/python -m pytest -q --tb=line --disable-warnings
1678 passed, 1 skipped, 2 deselected, 24 warnings, 100 subtests passed in 130.31s
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/python scripts/check_governance.py
(passed)
$ git diff --check
(clean)
```

The C suite is unchanged in count semantics; the earlier 1579 (pre-merge) and
1665 (post-merge, before this fix) runs are kept above as history. Formal NFR-C
acceptance and the implementation PR's independent review remain pending.
