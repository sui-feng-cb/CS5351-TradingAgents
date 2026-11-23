# C manifest and query test plan

Status: implemented locally on this branch (FR-C/NFR-C). The C module,
`manifest query` CLI and CLI run-recording are in place and the C suite is green
at 47 cases; an independent review of the implementation PR is still pending. The
tests and documentation at `677e9f3` passed independent review earlier; the PR #5
20/29 expected-failure counts are kept below as history. Owner: C. Acceptance
reviewer: a team member other than C. Three implementation-contract items still
require team confirmation (CLI JSON structure; failed-run error code and message;
NFR-C runner and timing method) — see below.

## Trace and scope

- Requirements: FR-C, NFR-C (`docs/req/requirements.yaml:55-78`).
- Contracts/architecture: `docs/architecture/interface-contracts.md` (C section),
  `docs/architecture/run-manifest-v1.schema.json`,
  `docs/architecture/trace-matrix.md`, `docs/architecture/adr/001-layout-and-extension-boundaries.md`.
- Offline acceptance suite: `test/offline/test_manifest.py` (47 cases). Fixtures:
  `test/fixtures/run_manifests/`. Manual timing tool: `test/benchmarks/bench_manifest_query.py`.
- Review status: the tests and documentation at `677e9f3` passed independent
  review; the implementation PR awaits an independent non-C review. Three
  implementation-contract items remain for team confirmation (CLI JSON
  structure, failed-run error code and message, NFR-C runner and timing
  method); the historical baselines (20 and 29 expected-red) are retained
  further down, along with the separate integration questions.
- No model API, market API, account input or credential is used. Every test runs
  offline; the query test additionally proves neither analysis nor vendor starts.

## C public interface (implemented)

`tradingagents.enhancements.manifest` provides:
`ManifestRecord.from_dict`, `validate_manifest`, `write_manifest`,
`query_manifests`, and a `QueryOutcome` carrying `matches` and `warnings`. The
CLI run-recording hooks use the helpers `new_run_id`, `utc_now_iso`,
`attempt_manifest_path` and `build_record`. Storage is one `run_manifest.json`
per attempt directory (`<results_root>/<ticker>/<YYYY-MM-DD>/runs/<uuid>/`) plus
a read-only local scan. The machine-readable schema is
`docs/architecture/run-manifest-v1.schema.json`.

The CLI `manifest query --json` stdout outer structure is **implemented but its
shape still needs team confirmation**: a JSON object with top-level `matches`
(each entry carrying at least `ticker` and `trade_date`/date) and `warnings` (a
list of human-readable warning strings). Each match also carries its report
paths. The CLI filter test parses this shape from stdout; if the team picks a
different outer structure, that test and the CLI must be revised together.

### Frozen v1 contract items (asserted by tests)

- Field whitelist: `schema_version`, `run_id`, `ticker`, `asset_type`,
  `trade_date`, `as_of`, `started_at`, `finished_at`, `code_version`, `analysts`,
  `models`, `configured_data_vendors`, `status`, `reports`, `error`,
  `unknown_fields`. No extra top-level keys.
- `status` is exactly `running | succeeded | failed`; any other value is rejected
  at validation.
- `run_id` is a UUID string (one per execution attempt). Same-day reruns append
  new records; existing records are never overwritten.
- Timestamps are UTC-aware ISO-8601 (`Z`); `trade_date`/`as_of` stay plain
  `YYYY-MM-DD`.
- `models` validates per-tier provider/model; `configured_data_vendors` is an
  explicit "configured" map (source config, not per-request provenance).
- Errors record a fixed error `code` plus safe text, never a traceback blob and
  never a secret value. The candidate fixed values for a failed CLI analysis run
  are `error.code == "analysis_failed"` and `error.message ==
  "Analysis failed."`; these specific strings are **pending human confirmation**.
- `reports` is a required top-level object; its `complete_report_md` and
  `complete_report_html` subkeys are optional and may be `null`; each present
  path is relative to the results root, and unknown report keys are rejected. A
  skipped save is `null` and query succeeds. A declared-but-missing report warns
  and the record is still returned.
- Query tolerates a single bad JSON record, unknown `schema_version`, and missing
  declared reports: each warns and the rest are returned unchanged; no report is
  modified or deleted.
- Unsafe report paths (escaping the results root) warn and are not followed.
- No secret material (API keys, tokens, passwords, credentials) appears in any
  serialized manifest.

### Review-pending items (team confirmation before implementation)

These three are the implementation-contract items flagged by the `677e9f3`
review. The tests currently encode candidate values; the team must confirm or
adjust them before product implementation:

1. **CLI JSON structure.** The `manifest query --json` stdout outer shape
   (top-level `matches` with `ticker`/date fields, plus `warnings`) is a
   candidate contract. The CLI filter test parses this shape from stdout.
2. **Failed-run error code and message.** The candidate fixed values are
   `error.code == "analysis_failed"` and `error.message == "Analysis failed."`;
   these specific strings need confirmation.
3. **NFR-C runner and timing method.** The fixed CI runner (Python 3.13), the
   three independent CLI-process measurement (including startup, scan,
   validation and output capture), and the ≤2.0 s per-run threshold are
   proposed and require confirmation.

### Integration questions (documented, NOT locked by executable assertions)

These depend on decisions still open. They are listed here so the tests do not
prematurely freeze the public API:

1. A/Python run-association interface. How FR-A (which calls `propagate` then
   `save_reports` per ticker) links its per-ticker runs to manifests. The tests
   do not assert a cross-module signature.
2. Backtest coverage. `run_backtest` writes to `results_dir/backtest/<run_id>`
   with its own memory log and no `save_reports` tree; whether/how backtest cells
   emit manifests is undecided.
3. Reused custom save path policy. `write_report_tree` removes stale owned files
   when a directory is reused; whether a reused save path updates or appends the
   run record is undecided. Tests use distinct run directories.

## Acceptance case map (`test/offline/test_manifest.py`)

| Requirement | Test | Independent expectation |
|---|---|---|
| FR-C schema | `test_fixed_sample_validates_against_v1_schema[success/failed]` | Exact field set; status in enum; UUID length 36 |
| FR-C failed shape | `test_failed_sample_carries_an_error_code_and_null_reports` | `error.code == "no_data"`; reports null |
| FR-C validation | `test_one_schema_error_is_rejected_at_validation[...]` (parametrized: invalid-status, extra-field, missing-required-field, invalid-uuid, invalid-date, naive-timestamp, wrong-reports-structure, wrong-error-structure) | From a valid sample, each single injected error raises `ValueError` |
| FR-C write success | `test_successful_run_writes_dated_manifest` | Manifest on disk; status succeeded; finished_at set |
| FR-C write failure | `test_failed_run_still_writes_manifest_with_error` | Manifest on disk for failed run |
| FR-C CLI error | `test_cli_run_failure_is_recorded_with_a_safe_error_code` | On-disk `error.code == "analysis_failed"`, `error.message == "Analysis failed."`; raw exception text, `Traceback` and `RuntimeError` never persisted (candidate fixed values pending human confirmation) |
| FR-C null path | `test_skipped_save_records_null_report_path_and_query_succeeds` | Null report; query ok; no warnings |
| FR-C missing report | `test_declared_but_missing_report_warns_and_query_continues` | Warning; record still returned |
| FR-C rerun | `test_same_day_rerun_keeps_two_distinct_records` | Two real CLI successes, same ticker/date/results root, save off; two on-disk succeeded manifests with distinct run ids and null report paths |
| FR-C filters | `test_unfiltered_query_returns_all_runs`, `..._ticker_filter...`, `..._date_filter...`, `..._combined...` | Correct subset |
| FR-C CLI filters | `test_cli_manifest_query_filters_by_ticker_date_and_reports_bad_json` | Real Typer subcommand over three ticker/date combos; `--ticker`, `--date`, combined and no-match each select the exact (ticker, date) set parsed from stdout JSON; one corrupt record warns and valid matches still return |
| FR-C no match | `test_no_match_returns_empty_without_error` | Empty, no error |
| FR-C bad JSON | `test_bad_json_is_skipped_and_other_records_still_return` | Good returned; one warning |
| FR-C unknown version | `test_unknown_schema_version_is_skipped_with_warning` | Future version (stdlib-written record) skipped + warning; valid record still returned |
| SEC-01 | `test_manifest_never_records_secret_values` | Real CLI failure with two distinct fake credentials (mock config + injected exception); on-disk manifest written, neither credential present |
| FR-C unsafe path | `test_report_path_escaping_results_root_warns_and_is_not_followed` | Real out-of-root temp file; traversal record warns, valid record still returned, escaping path not followed |
| FR-C CLI + no analysis | `test_cli_manifest_query_subcommand_runs_and_starts_no_analysis` | Stdlib-placed fixed manifest + report; real Typer subcommand exit 0 with the matched report relative path; patched `run_analysis`/`run_backtest` never called |
| FR-C saved report path | `test_cli_saved_report_path_is_what_manifest_records` | Real `run_analysis` with saving on; stub `save_reports` writes and returns a non-default-named file; on-disk manifest's `reports.complete_report_md`, resolved from the results root, equals that file and is not absolute |
| FR-C save failure | `test_cli_report_save_failure_is_distinct_and_hides_exception` | Analysis succeeds and `save_reports` raises: `status == "succeeded"`, report paths null, `error == {"code": "report_save_failed", "message": "Report save failed."}`; exception marker/`OSError`/`Traceback` never persisted; show still runs |
| FR-C skipped-save control | `test_cli_skipped_save_control_has_null_error` | A deliberately skipped save keeps `status == "succeeded"` and `error is None` (distinct from a save failure) |
| FR-C save failure in query | `test_cli_report_save_failure_is_visible_in_query_json` | Real `manifest query --json` over a save-failure manifest keeps the match and surfaces a fixed `report save failed` warning; a skipped-save manifest raises no such warning; output has no exception text |

Each case references its requirement ID via this table; assertions use literal
contract values, not production helpers, so a bug cannot mirror itself.

## Baseline evidence (tests-first)

Recorded on the current checkout. The C module is absent, so every case is an
expected acceptance failure; see `docs/verification/c-manifest.md` for the raw
outputs and the distinction between the early Python 3.14 environment and the
current project Python 3.13 `.venv`.

- Project interpreter (current): Python 3.13.18 `.venv`.
  - Collection succeeds: 29 tests collected.
  - Execution: all expected reds for the unimplemented C module and query
    subcommand — the real-CLI cases (`same-day rerun`, `saved report path`,
    `CLI failure`) reach the on-disk `run_manifest.json` assertion; the CLI query
    cases fail at `No such command 'manifest'`; the rest fail at the
    missing-module guard.
  - `ruff check test/offline/test_manifest.py`: pass.
  - `scripts/check_governance.py`: pass.
- Early environment (superseded): Python 3.14.4 without project dependencies;
  same 20 expected reds, run with `--noconftest`.
- Generator writes 1,000 deterministic manifests (regeneration byte-identical).
- Timing tool targets `python -m cli.main manifest query ...`; against the
  un-implemented command it exits 1 with captured startup/scan timing (baseline),
  not an NFR-C pass. The real ≤2 s NFR-C measurement is still untested and its
  runner/timing method and threshold await team confirmation (see NFR-C item 3).

## NFR-C performance plan (tool only; real conclusion deferred to CI)

- Dataset: `gen_dataset.py` v2, fixed seed `20261120`, 1,000 manifests. Report
  paths are relative to the results root and each non-null path names a file the
  generator writes; `finished_at` is never earlier than `started_at`.
- The timing tool refuses to measure unless the dataset holds exactly `--count`
  manifests (default 1,000), returning a clear error otherwise.
- Measurement: three *independent* CLI processes (`subprocess`), each timing
  includes interpreter/CLI startup, scan, validation and output capture.
- Runner: fixed CI runner, Python 3.13.
- Per run: verify exit code 0 and reported match count equals the expected
  ticker count (computed independently from the dataset). Record all three
  elapsed times; print slowest.
- Proposed threshold: each run <= 2.0 s, **pending team approval**
  (`requirements.yaml:71-78`). This document and the tool do not assert it.
- The implementation-phase CI run produces the real NFR-C result and its raw
  output is recorded in `docs/verification/c-manifest.md`.
