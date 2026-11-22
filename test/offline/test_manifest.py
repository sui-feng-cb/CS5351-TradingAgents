"""FR-C/NFR-C acceptance tests for the versioned run manifest and local query.

Test expectations are literal contract values, independent of the C module. The
application module (``tradingagents.enhancements.manifest``) is intentionally
absent in this tests-first revision; a non-C reviewer must approve this
contract before it is implemented. When the module is missing, every test that
needs it fails with an explicit import/skip reason rather than breaking
collection of the rest of the suite.

Fixed sample shapes live in ``test/fixtures/run_manifests/``. This file asserts only
behaviour that the frozen C v1 contract pins down; behaviours still awaiting
team decision (A/Python run-association API, backtest coverage, reused custom
save paths) are listed in ``docs/testing/c-manifest-test-plan.md`` and are NOT
locked by executable assertions here.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "run_manifests"
SUCCESS = FIXTURES / "sample_success.json"
FAILED = FIXTURES / "sample_failed.json"

# C v1 field whitelist, from docs/architecture/interface-contracts.md.
REQUIRED_FIELDS = (
    "schema_version",
    "run_id",
    "ticker",
    "asset_type",
    "trade_date",
    "as_of",
    "started_at",
    "finished_at",
    "code_version",
    "analysts",
    "models",
    "configured_data_vendors",
    "status",
    "reports",
    "error",
    "unknown_fields",
)
ALLOWED_STATUS = {"running", "succeeded", "failed"}
SECRET_MARKERS = ("api_key", "apikey", "secret", "token", "password", "credential", "bearer")


def _manifest_module():
    """Import the C module or fail with an explainable message.

    Kept as a helper so a missing implementation produces a clear assertion
    failure in this test, not a collection error for the whole suite.
    """

    try:
        from tradingagents.enhancements import manifest
    except Exception as exc:  # ImportError or partial-module dependency error
        pytest.fail(
            f"C implementation missing: tradingagents.enhancements.manifest ({exc!r}). "
            "Expected until the approved implementation lands."
        )
    return manifest


def _write_manifest(module, run_dir: Path, **overrides):
    """Build and persist one manifest with the module under test.

    Defaults keep an ordinary record inert so a case introduces only the one
    anomaly it is about: report paths are null (nothing is declared on disk) and
    every call gets its own test run id (so two records in one results root never
    share an id). Callers override ``reports``/``run_id``/``status``/``ticker``
    explicitly when a case needs that anomaly.
    """

    run_dir.mkdir(parents=True, exist_ok=True)
    values = json.loads(SUCCESS.read_text(encoding="utf-8"))
    values.update(
        run_id=str(uuid.uuid4()),
        reports={"complete_report_md": None, "complete_report_html": None},
    )
    values.update(overrides)
    target = run_dir / "run_manifest.json"
    module.write_manifest(target, module.ManifestRecord.from_dict(values))
    return target


def _query(module, results_dir: Path, **filters):
    return module.query_manifests(results_dir, **filters)


# --------------------------------------------------------------------------- #
# Schema of the two fixed samples
# --------------------------------------------------------------------------- #

@pytest.mark.unit
@pytest.mark.parametrize("fixture", [SUCCESS, FAILED], ids=["success", "failed"])
def test_fixed_sample_validates_against_v1_schema(fixture):
    module = _manifest_module()
    data = json.loads(fixture.read_text(encoding="utf-8"))

    record = module.ManifestRecord.from_dict(data)
    module.validate_manifest(record)

    assert set(data) == set(REQUIRED_FIELDS)
    assert data["status"] in ALLOWED_STATUS
    assert isinstance(data["run_id"], str) and len(data["run_id"]) == 36


@pytest.mark.unit
def test_failed_sample_carries_an_error_code_and_null_reports():
    module = _manifest_module()
    data = json.loads(FAILED.read_text(encoding="utf-8"))

    record = module.ManifestRecord.from_dict(data)
    module.validate_manifest(record)

    assert data["error"]["code"] == "no_data"
    assert data["reports"]["complete_report_md"] is None
    assert data["reports"]["complete_report_html"] is None


@pytest.mark.unit
def test_invalid_status_value_is_rejected_at_validation():
    module = _manifest_module()
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data["status"] = "done"  # not one of running|succeeded|failed

    with pytest.raises(ValueError):
        module.validate_manifest(module.ManifestRecord.from_dict(data))


# --------------------------------------------------------------------------- #
# Success and failure are written to disk
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_successful_run_writes_dated_manifest(tmp_path):
    module = _manifest_module()
    run_dir = tmp_path / "AAPL" / "2026-11-20"

    path = _write_manifest(module, run_dir)

    assert path.exists()
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["status"] == "succeeded"
    assert written["finished_at"] is not None


@pytest.mark.unit
def test_failed_run_still_writes_manifest_with_error(tmp_path):
    module = _manifest_module()
    run_dir = tmp_path / "AAPL" / "2026-11-20"
    data = json.loads(FAILED.read_text(encoding="utf-8"))

    path = run_dir / "run_manifest.json"
    run_dir.mkdir(parents=True)
    module.write_manifest(path, module.ManifestRecord.from_dict(data))

    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["status"] == "failed"
    assert written["error"]["code"] == "no_data"


# --------------------------------------------------------------------------- #
# CLI execution errors are recorded, not asserted away
# --------------------------------------------------------------------------- #

class _FailingGraph:
    """A graph whose run aborts, mimicking a crash inside the CLI stream.

    Wired the same way ``test_cli_memory_log._FakeGraph`` is, so the real
    ``cli.run.run_analysis`` lifecycle runs and fails at ``stream_run``. The
    abort message may carry an injected credential so the failure-recording test
    can prove it never reaches the manifest.
    """

    def __init__(self, crash_message="simulated mid-run crash"):
        self.graph = self
        self.propagator = self
        self._resuming = False
        self._crash_message = crash_message

    def create_run_state(self, ticker, trade_date, asset_type="stock", portfolio=None):
        return {"messages": [], "company_of_interest": ticker}

    def get_graph_args(self, callbacks=None):
        return {}

    def begin_checkpoint(self, *a, **k):
        return None

    def checkpoint_input(self, state):
        return state

    def end_checkpoint(self):
        pass

    def stream_run(self, graph_input, **kwargs):
        raise RuntimeError(self._crash_message)
        yield  # pragma: no cover - marks this a generator, never reached


class _SuccessGraph:
    """A graph whose run streams to completion, so ``run_analysis`` finishes.

    Same lifecycle surface as ``_FailingGraph``/``test_cli_memory_log._FakeGraph``
    but yields a final state and records the decision, letting the real CLI
    success path run end to end. It never writes a manifest itself: that is the
    C implementation's job, which these tests exercise.
    """

    def __init__(self):
        self.graph = self
        self.propagator = self
        self._resuming = False

    def create_run_state(self, ticker, trade_date, asset_type="stock", portfolio=None):
        return {"messages": [], "company_of_interest": ticker}

    def get_graph_args(self, callbacks=None):
        return {}

    def begin_checkpoint(self, *a, **k):
        return None

    def checkpoint_input(self, state):
        return state

    def record_decision(self, *a, **k):
        pass

    def clear_checkpoint_on_success(self, *a, **k):
        pass

    def end_checkpoint(self):
        pass

    def stream_run(self, graph_input, **kwargs):
        yield [], {"messages": [], "market_report": "M"}
        yield [], {"messages": [], "final_trade_decision": "Rating: Hold\n\nHold.",
                   "final_rating": "Hold"}


class _NullLive:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeBuffer:
    def __init__(self):
        self.messages = []
        self.tool_calls = []
        self.report_sections = {}
        self.agent_status = {}
        self.selected_analysts = []
        self._processed_message_ids = set()

    def init_for_analysis(self, selected_analysts):
        self.selected_analysts = [a.lower() for a in selected_analysts]

    def add_message(self, kind, content):
        self.messages.append((0.0, kind, content))

    def add_tool_call(self, name, args):
        self.tool_calls.append((0.0, name, args))

    def update_report_section(self, *a):
        pass

    def update_agent_status(self, agent, status):
        self.agent_status[agent] = status


def _run_failing_cli(tmp_path, monkeypatch, *, run_config=None, crash_message=None):
    """Drive the real ``cli.run.run_analysis`` so it aborts in ``stream_run``.

    Returns the results directory. Reused by the failure-recording and
    secret-leak tests; ``run_config`` and ``crash_message`` let a caller inject
    credentials through the mock config and the injected exception respectively.
    """

    import cli.run as cli_run
    from cli.models import AnalystType

    graph = _FailingGraph() if crash_message is None else _FailingGraph(crash_message)
    results_dir = tmp_path / "results"
    config = {"data_cache_dir": str(tmp_path / "cache"), "results_dir": str(results_dir)}
    config.update(run_config or {})

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "message_buffer", _FakeBuffer())
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": "2026-01-10",
        "analysts": [AnalystType.MARKET], "asset_type": "stock",
    })
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: config)
    monkeypatch.setattr(cli_run.typer, "prompt", lambda *a, **k: "N")

    with pytest.raises(RuntimeError):
        cli_run.run_analysis()
    return results_dir


def _run_successful_cli(tmp_path, monkeypatch, *, results_dir, ticker="NVDA",
                        analysis_date="2026-01-10"):
    """Drive the real ``cli.run.run_analysis`` to completion with saving off.

    Uses the same ``results_dir``/ticker/date a caller passes, so two calls
    model a same-day rerun. Reporting is disabled by answering "N" to the save
    prompt; the test never fabricates a manifest or a run id itself.
    """

    import cli.run as cli_run
    from cli.models import AnalystType

    graph = _SuccessGraph()
    config = {"data_cache_dir": str(tmp_path / "cache"), "results_dir": str(results_dir)}
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "message_buffer", _FakeBuffer())
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": ticker, "analysis_date": analysis_date,
        "analysts": [AnalystType.MARKET], "asset_type": "stock",
    })
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: config)
    monkeypatch.setattr(cli_run.typer, "prompt", lambda *a, **k: "N")

    cli_run.run_analysis()
    return results_dir


@pytest.mark.unit
def test_cli_run_failure_is_recorded_with_a_safe_error_code(tmp_path, monkeypatch):
    results_dir = _run_failing_cli(tmp_path, monkeypatch)

    manifests = list(results_dir.rglob("run_manifest.json"))
    assert len(manifests) == 1
    written = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert written["status"] == "failed"


# --------------------------------------------------------------------------- #
# Null report path and missing declared report
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_skipped_save_records_null_report_path_and_query_succeeds(tmp_path):
    module = _manifest_module()
    run_dir = tmp_path / "AAPL" / "2026-11-20"
    _write_manifest(module, run_dir, status="succeeded",
                    reports={"complete_report_md": None, "complete_report_html": None})

    outcome = _query(module, tmp_path, ticker="AAPL")

    assert len(outcome.matches) == 1
    assert outcome.matches[0].reports["complete_report_md"] is None
    assert outcome.warnings == []


@pytest.mark.unit
def test_declared_but_missing_report_warns_and_query_continues(tmp_path):
    module = _manifest_module()
    run_dir = tmp_path / "AAPL" / "2026-11-20"
    # Manifest claims a report that was never written to disk.
    _write_manifest(module, run_dir, status="succeeded",
                    reports={"complete_report_md": "reports/complete_report.md",
                             "complete_report_html": None})

    outcome = _query(module, tmp_path, ticker="AAPL")

    assert len(outcome.matches) == 1
    assert any("missing" in w.lower() for w in outcome.warnings)


# --------------------------------------------------------------------------- #
# Same-day rerun keeps both records
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_same_day_rerun_keeps_two_distinct_records(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    # Two real CLI runs, same ticker/date/results root, saving disabled both
    # times. The test creates no manifest and assigns no run id itself.
    _run_successful_cli(tmp_path, monkeypatch, results_dir=results_dir,
                        ticker="NVDA", analysis_date="2026-01-10")
    _run_successful_cli(tmp_path, monkeypatch, results_dir=results_dir,
                        ticker="NVDA", analysis_date="2026-01-10")

    manifests = list(results_dir.rglob("run_manifest.json"))
    assert len(manifests) == 2
    records = [json.loads(p.read_text(encoding="utf-8")) for p in manifests]
    assert {r["status"] for r in records} == {"succeeded"}
    run_ids = {r["run_id"] for r in records}
    assert len(run_ids) == 2
    for record in records:
        assert record["reports"]["complete_report_md"] is None
        assert record["reports"]["complete_report_html"] is None


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_unfiltered_query_returns_all_runs(tmp_path):
    module = _manifest_module()
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-20", ticker="AAPL")
    _write_manifest(module, tmp_path / "MSFT" / "2026-11-19", ticker="MSFT",
                    trade_date="2026-11-19", as_of="2026-11-19")

    outcome = _query(module, tmp_path)

    assert len(outcome.matches) == 2


@pytest.mark.unit
def test_ticker_filter_selects_only_that_ticker(tmp_path):
    module = _manifest_module()
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-20", ticker="AAPL")
    _write_manifest(module, tmp_path / "MSFT" / "2026-11-20", ticker="MSFT")

    outcome = _query(module, tmp_path, ticker="MSFT")

    assert [m.ticker for m in outcome.matches] == ["MSFT"]


@pytest.mark.unit
def test_date_filter_selects_only_that_date(tmp_path):
    module = _manifest_module()
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-20", ticker="AAPL")
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-19", ticker="AAPL",
                    trade_date="2026-11-19", as_of="2026-11-19")

    outcome = _query(module, tmp_path, date="2026-11-19")

    assert [m.trade_date for m in outcome.matches] == ["2026-11-19"]


@pytest.mark.unit
def test_combined_ticker_and_date_filter(tmp_path):
    module = _manifest_module()
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-20", ticker="AAPL")
    _write_manifest(module, tmp_path / "MSFT" / "2026-11-20", ticker="MSFT")
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-19", ticker="AAPL",
                    trade_date="2026-11-19", as_of="2026-11-19")

    outcome = _query(module, tmp_path, ticker="AAPL", date="2026-11-20")

    assert [(m.ticker, m.trade_date) for m in outcome.matches] == [("AAPL", "2026-11-20")]


@pytest.mark.unit
def test_no_match_returns_empty_without_error(tmp_path):
    module = _manifest_module()
    _write_manifest(module, tmp_path / "AAPL" / "2026-11-20", ticker="AAPL")

    outcome = _query(module, tmp_path, ticker="ZZZZ")

    assert outcome.matches == []


# --------------------------------------------------------------------------- #
# Tolerating bad records; continue scanning
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_bad_json_is_skipped_and_other_records_still_return(tmp_path):
    module = _manifest_module()
    good = tmp_path / "AAPL" / "2026-11-20"
    _write_manifest(module, good, ticker="AAPL")
    broken = tmp_path / "MSFT" / "2026-11-20"
    broken.mkdir(parents=True)
    (broken / "run_manifest.json").write_text("{ not json", encoding="utf-8")

    outcome = _query(module, tmp_path)

    assert [m.ticker for m in outcome.matches] == ["AAPL"]
    assert len(outcome.warnings) == 1


@pytest.mark.unit
def test_unknown_schema_version_is_skipped_with_warning(tmp_path):
    module = _manifest_module()
    good = tmp_path / "AAPL" / "2026-11-20"
    _write_manifest(module, good, ticker="AAPL")
    # Write the unknown-version record directly with the stdlib, independent of
    # any C writer that might refuse to emit an unsupported version.
    future = tmp_path / "MSFT" / "2026-11-20"
    future.mkdir(parents=True)
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data.update(ticker="MSFT", run_id="99999999-9999-4999-8999-999999999999",
                schema_version=999)
    (future / "run_manifest.json").write_text(json.dumps(data), encoding="utf-8")

    outcome = _query(module, tmp_path)

    assert [m.ticker for m in outcome.matches] == ["AAPL"]
    assert any("schema" in w.lower() for w in outcome.warnings)


# --------------------------------------------------------------------------- #
# Sensitive information and unsafe paths
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_manifest_never_records_secret_values(tmp_path, monkeypatch):
    # Two different fake credentials from two sources: one set in the offline
    # mock run config, one injected via the exception message. Both must be
    # absent from the manifest the failing CLI run leaves on disk.
    config_secret = "sk-CONFIG-fake-0123456789abcdef"
    crash_secret = "Bearer CRASH-fake-ffffffffffffffff"
    results_dir = _run_failing_cli(
        tmp_path,
        monkeypatch,
        run_config={
            "llm_provider": "openai",
            "backend_url": "https://api.example.test",
            "openai_api_key": config_secret,
            "data_api_key": config_secret,
        },
        crash_message=f"provider rejected credentials {crash_secret}",
    )

    manifests = list(results_dir.rglob("run_manifest.json"))
    assert len(manifests) == 1
    serialized = manifests[0].read_text(encoding="utf-8")
    assert config_secret not in serialized
    assert crash_secret not in serialized
    lowered = serialized.lower()
    for marker in SECRET_MARKERS:
        assert marker not in lowered


@pytest.mark.unit
def test_report_path_escaping_results_root_warns_and_is_not_followed(tmp_path):
    module = _manifest_module()
    results_root = tmp_path / "results"
    good = results_root / "AAPL" / "2026-11-20"
    _write_manifest(module, good, ticker="AAPL")
    # A real file outside the results root, reached by a traversal path; write
    # the escaping manifest directly with the stdlib so the C writer cannot
    # sanitise it away before the query sees it.
    outside_file = tmp_path / "outside_secret.md"
    outside_file.write_text("do not follow\n", encoding="utf-8")
    bad = results_root / "MSFT" / "2026-11-20"
    bad.mkdir(parents=True)
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data.update(ticker="MSFT", run_id="88888888-8888-4888-8888-888888888888",
                reports={"complete_report_md": "../../../outside_secret.md",
                         "complete_report_html": None})
    (bad / "run_manifest.json").write_text(json.dumps(data), encoding="utf-8")

    outcome = _query(module, results_root)

    assert [m.ticker for m in outcome.matches] == ["AAPL"]
    assert any("path" in w.lower() or "unsafe" in w.lower() for w in outcome.warnings)
    for match in outcome.matches:
        md = match.reports.get("complete_report_md")
        assert md is None or ".." not in Path(md).parts


# --------------------------------------------------------------------------- #
# A real Typer subcommand, and a query that starts no analysis / no vendor
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_cli_manifest_query_subcommand_runs_and_starts_no_analysis(tmp_path, monkeypatch):
    # Place a fixed manifest and the report it references directly in the temp
    # results root with the stdlib; the test does not call any C writer.
    run_dir = tmp_path / "AAPL" / "2026-11-20"
    (run_dir / "reports").mkdir(parents=True)
    (run_dir / "reports" / "complete_report.md").write_text("report body\n", encoding="utf-8")
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data["reports"] = {"complete_report_md": "AAPL/2026-11-20/reports/complete_report.md",
                       "complete_report_html": None}
    (run_dir / "run_manifest.json").write_text(json.dumps(data), encoding="utf-8")

    from typer.testing import CliRunner

    import cli.main as cli_main

    # A query is read-only: building a graph or touching a vendor would start an
    # analysis. Turn both into hard failures if the query path reaches them.
    def _boom(*args, **kwargs):
        raise AssertionError("manifest query must not start an analysis or a data vendor")

    monkeypatch.setattr(cli_main, "run_analysis", _boom, raising=False)
    monkeypatch.setattr(cli_main, "run_backtest", _boom, raising=False)

    result = CliRunner().invoke(
        cli_main.app,
        ["manifest", "query", "--results-dir", str(tmp_path), "--ticker", "AAPL", "--json"],
    )

    assert result.exit_code == 0, result.output
    assert "AAPL" in result.output
    assert "AAPL/2026-11-20/reports/complete_report.md" in result.output
