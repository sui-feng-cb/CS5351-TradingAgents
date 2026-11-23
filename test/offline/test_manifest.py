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
# Monitoring helpers: prove a read-only query opens nothing outside and writes
# nothing inside the results root. Wrapping the common Python open/write entry
# points catches same-byte rewrites that a before/after diff alone would miss.
# --------------------------------------------------------------------------- #

def _norm(path) -> Path:
    return Path(path).resolve()


class _OpenSpy:
    """Record every open/read attempt aimed at one watched target path."""

    def __init__(self, target: Path):
        self.target = _norm(target)
        self.hits: list[str] = []

    def check(self, path, how: str) -> None:
        try:
            resolved = _norm(path)
        except (TypeError, ValueError):
            return
        if resolved == self.target:
            self.hits.append(f"{how}: {resolved}")

    def install(self, monkeypatch) -> None:
        import builtins
        import io
        import os

        spy = self
        real_builtin_open = builtins.open
        real_io_open = io.open
        real_os_open = os.open
        real_read_text = Path.read_text
        real_read_bytes = Path.read_bytes
        real_path_open = Path.open

        def spy_builtin_open(file, *a, **k):
            spy.check(file, "builtins.open")
            return real_builtin_open(file, *a, **k)

        def spy_io_open(file, *a, **k):
            spy.check(file, "io.open")
            return real_io_open(file, *a, **k)

        def spy_os_open(path, *a, **k):
            spy.check(path, "os.open")
            return real_os_open(path, *a, **k)

        def spy_read_text(self, *a, **k):
            spy.check(self, "Path.read_text")
            return real_read_text(self, *a, **k)

        def spy_read_bytes(self, *a, **k):
            spy.check(self, "Path.read_bytes")
            return real_read_bytes(self, *a, **k)

        def spy_path_open(self, *a, **k):
            spy.check(self, "Path.open")
            return real_path_open(self, *a, **k)

        monkeypatch.setattr(builtins, "open", spy_builtin_open)
        monkeypatch.setattr(io, "open", spy_io_open)
        monkeypatch.setattr(os, "open", spy_os_open)
        monkeypatch.setattr(Path, "read_text", spy_read_text)
        monkeypatch.setattr(Path, "read_bytes", spy_read_bytes)
        monkeypatch.setattr(Path, "open", spy_path_open)


class _WriteSpy:
    """Record every mutation attempt whose target is inside a watched root.

    Covers create/append/overwrite (including a same-byte rewrite), delete,
    rename and replace. Only *attempts*, not byte changes, are recorded.
    """

    def __init__(self, root: Path):
        self.root = _norm(root)
        self.hits: list[str] = []

    def _inside(self, path) -> bool:
        try:
            resolved = _norm(path)
        except (TypeError, ValueError):
            return False
        return resolved == self.root or self.root in resolved.parents

    def record(self, path, how: str) -> None:
        if self._inside(path):
            self.hits.append(f"{how}: {_norm(path)}")

    def install(self, monkeypatch) -> None:
        import builtins
        import io
        import os
        import shutil

        spy = self
        real_builtin_open = builtins.open
        real_io_open = io.open
        real_os_open = os.open
        real_write_text = Path.write_text
        real_write_bytes = Path.write_bytes
        real_path_open = Path.open
        real_replace = os.replace
        real_rename = os.rename
        real_remove = os.remove
        real_unlink = os.unlink

        def spy_builtin_open(file, mode="r", *a, **k):
            if any(ch in mode for ch in "wax+"):
                spy.record(file, f"builtins.open[{mode}]")
            return real_builtin_open(file, mode, *a, **k)

        def spy_io_open(file, mode="r", *a, **k):
            if any(ch in mode for ch in "wax+"):
                spy.record(file, f"io.open[{mode}]")
            return real_io_open(file, mode, *a, **k)

        def spy_os_open(path, flags, *a, **k):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                spy.record(path, f"os.open[{flags}]")
            return real_os_open(path, flags, *a, **k)

        def spy_write_text(self, *a, **k):
            spy.record(self, "Path.write_text")
            return real_write_text(self, *a, **k)

        def spy_write_bytes(self, *a, **k):
            spy.record(self, "Path.write_bytes")
            return real_write_bytes(self, *a, **k)

        def spy_path_open(self, mode="r", *a, **k):
            if any(ch in mode for ch in "wax+"):
                spy.record(self, f"Path.open[{mode}]")
            return real_path_open(self, mode, *a, **k)

        def spy_replace(src, dst, *a, **k):
            spy.record(src, "os.replace[src]")
            spy.record(dst, "os.replace[dst]")
            return real_replace(src, dst, *a, **k)

        def spy_rename(src, dst, *a, **k):
            spy.record(src, "os.rename[src]")
            spy.record(dst, "os.rename[dst]")
            return real_rename(src, dst, *a, **k)

        def spy_remove(path, *a, **k):
            spy.record(path, "os.remove")
            return real_remove(path, *a, **k)

        def spy_unlink(path, *a, **k):
            spy.record(path, "os.unlink")
            return real_unlink(path, *a, **k)

        monkeypatch.setattr(builtins, "open", spy_builtin_open)
        monkeypatch.setattr(io, "open", spy_io_open)
        monkeypatch.setattr(os, "open", spy_os_open)
        monkeypatch.setattr(Path, "write_text", spy_write_text)
        monkeypatch.setattr(Path, "write_bytes", spy_write_bytes)
        monkeypatch.setattr(Path, "open", spy_path_open)
        monkeypatch.setattr(os, "replace", spy_replace)
        monkeypatch.setattr(os, "rename", spy_rename)
        monkeypatch.setattr(os, "remove", spy_remove)
        monkeypatch.setattr(os, "unlink", spy_unlink)
        for name in ("copy", "copy2", "copyfile", "copytree", "move"):
            real = getattr(shutil, name)

            def make(real=real, name=name):
                def spy_shutil(*a, **k):
                    if a:
                        spy.record(a[0], f"shutil.{name}[src]")
                    if len(a) > 1:
                        spy.record(a[1], f"shutil.{name}[dst]")
                    return real(*a, **k)
                return spy_shutil

            monkeypatch.setattr(shutil, name, make())


def _snapshot(root: Path):
    """Directory entries and every file's bytes under ``root``, for a diff."""

    root = Path(root)
    entries = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    blobs = {}
    for p in root.rglob("*"):
        if p.is_file():
            blobs[str(p.relative_to(root))] = p.read_bytes()
    return {"entries": entries, "blobs": blobs}


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
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda d: d.__setitem__("status", "done"), id="invalid-status"),
        pytest.param(lambda d: d.__setitem__("extra_top_level", 1), id="extra-field"),
        pytest.param(lambda d: d.pop("ticker"), id="missing-required-field"),
        pytest.param(lambda d: d.__setitem__("run_id", "not-a-uuid"), id="invalid-uuid"),
        pytest.param(lambda d: d.__setitem__("trade_date", "2026-13-40"), id="invalid-date"),
        pytest.param(lambda d: d.__setitem__("started_at", "2026-11-20T14:00:00"),
                     id="naive-timestamp"),
        pytest.param(lambda d: d.__setitem__("reports", "reports/complete_report.md"),
                     id="wrong-reports-structure"),
        pytest.param(lambda d: d.__setitem__("error", "boom"), id="wrong-error-structure"),
    ],
)
def test_one_schema_error_is_rejected_at_validation(mutate):
    module = _manifest_module()
    # Start from the valid sample and introduce exactly one error.
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    mutate(data)

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


class _SavingSuccessGraph(_SuccessGraph):
    """A successful graph whose ``save_reports`` writes a non-default-named file.

    Mirrors the CLI save path: ``run_analysis`` calls ``save_reports`` with the
    default path, but this stub writes ``custom_report.md`` underneath it and
    returns that exact file, so the test can prove the manifest records the path
    ``save_reports`` actually produced rather than the default name.
    """

    def __init__(self):
        super().__init__()
        self.saved_path: Path | None = None

    def default_report_path(self, ticker):
        return Path(self.config_results_dir) / "reports" / f"{ticker}_default"

    def save_reports(self, final_state, ticker, save_path=None, html=True):
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        target = save_path / "custom_report.md"
        target.write_text("custom report\n", encoding="utf-8")
        self.saved_path = target
        return target


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


def _run_saving_cli(tmp_path, monkeypatch, *, results_dir, ticker="NVDA",
                    analysis_date="2026-01-10"):
    """Drive the real ``cli.run.run_analysis`` to success with saving enabled.

    Answers the save question with the flags (``save=True, show=False,
    html=False``) so ``_offer_reports`` calls ``save_reports`` with the default
    path; the stub writes a custom-named file and returns it. Returns
    ``(results_dir, saved_path)``.
    """

    import cli.run as cli_run
    from cli.models import AnalystType

    graph = _SavingSuccessGraph()
    graph.config_results_dir = str(results_dir)
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

    def _no_prompt(*a, **k):
        raise AssertionError("saving/once flags were supplied, so run_analysis must not prompt")

    monkeypatch.setattr(cli_run.typer, "prompt", _no_prompt)

    cli_run.run_analysis(flags={"save": True, "show": False, "html": False})
    return results_dir, graph.saved_path


@pytest.mark.unit
def test_cli_run_failure_is_recorded_with_a_safe_error_code(tmp_path, monkeypatch):
    # A distinctive original exception message that must NOT reach the manifest.
    crash_message = "simulated mid-run crash SECRET-INTERNAL-DETAIL"
    results_dir = _run_failing_cli(tmp_path, monkeypatch, crash_message=crash_message)

    manifests = list(results_dir.rglob("run_manifest.json"))
    assert len(manifests) == 1
    written = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert written["status"] == "failed"
    # Candidate contract values (pending human confirmation; see the test plan).
    assert written["error"]["code"] == "analysis_failed"
    assert written["error"]["message"] == "Analysis failed."
    # The raw exception text and any traceback must never be persisted.
    serialized = manifests[0].read_text(encoding="utf-8")
    assert "simulated mid-run crash" not in serialized
    assert "SECRET-INTERNAL-DETAIL" not in serialized
    assert "Traceback" not in serialized
    assert "RuntimeError" not in serialized


@pytest.mark.unit
def test_cli_saved_report_path_is_what_manifest_records(tmp_path, monkeypatch):
    results_dir, saved_path = _run_saving_cli(
        tmp_path, monkeypatch, results_dir=tmp_path / "results",
        ticker="NVDA", analysis_date="2026-01-10")

    # The stub wrote and returned a non-default-named report.
    assert saved_path is not None and saved_path.exists()
    assert saved_path.name == "custom_report.md"
    assert saved_path.name != "complete_report.md"

    manifests = list(results_dir.rglob("run_manifest.json"))
    assert len(manifests) == 1
    written = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert written["status"] == "succeeded"
    # The manifest records the path save_reports returned, relative to the root.
    recorded = written["reports"]["complete_report_md"]
    assert recorded is not None
    resolved = (results_dir / recorded).resolve()
    assert resolved == saved_path.resolve()
    assert not Path(recorded).is_absolute()


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
def test_report_path_escaping_results_root_warns_and_is_not_followed(tmp_path, monkeypatch):
    # A real file outside the results root, reached from the results root via a
    # traversal ref. Create it and prove the resolution up front, before the
    # missing-module guard, so this precheck runs even while the red test fails.
    results_root = tmp_path / "results"
    results_root.mkdir(parents=True)
    outside_file = tmp_path / "outside_secret.md"
    outside_file.write_text("do not follow\n", encoding="utf-8")
    report_ref = "../outside_secret.md"
    assert (results_root / report_ref).resolve() == outside_file.resolve()
    assert outside_file.exists()

    module = _manifest_module()
    good = results_root / "AAPL" / "2026-11-20"
    _write_manifest(module, good, ticker="AAPL")
    # Write the escaping manifest directly with the stdlib so the C writer cannot
    # sanitise the traversal ref before the query sees it.
    bad = results_root / "MSFT" / "2026-11-20"
    bad.mkdir(parents=True)
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data.update(ticker="MSFT", run_id="88888888-8888-4888-8888-888888888888",
                reports={"complete_report_md": report_ref,
                         "complete_report_html": None})
    (bad / "run_manifest.json").write_text(json.dumps(data), encoding="utf-8")

    spy = _OpenSpy(outside_file)
    with monkeypatch.context() as m:
        spy.install(m)
        outcome = _query(module, results_root)

    assert spy.hits == [], f"query opened the out-of-root file: {spy.hits}"
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

    before = _snapshot(tmp_path)
    write_spy = _WriteSpy(tmp_path)
    with monkeypatch.context() as m:
        write_spy.install(m)
        result = CliRunner().invoke(
            cli_main.app,
            ["manifest", "query", "--results-dir", str(tmp_path), "--ticker", "AAPL", "--json"],
        )

    # Snapshot after the monitoring context exits, so a real write during the
    # query is what the byte diff reflects, not the spies' own bookkeeping.
    after = _snapshot(tmp_path)
    assert write_spy.hits == [], f"query wrote inside the results root: {write_spy.hits}"
    assert after == before, "query changed entries or bytes under the results root"
    assert result.exit_code == 0, result.output
    assert "AAPL" in result.output
    assert "AAPL/2026-11-20/reports/complete_report.md" in result.output


def _seed_strlib_manifest(results_root: Path, ticker: str, trade_date: str):
    """Write a valid manifest directly with the stdlib (no C writer) under a run dir.

    Each seeded record gets its own run id so distinct combos never collide.
    """

    run_dir = results_root / ticker / trade_date
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    (run_dir / "reports" / "complete_report.md").write_text("report body\n", encoding="utf-8")
    data = json.loads(SUCCESS.read_text(encoding="utf-8"))
    data.update(
        run_id=str(uuid.uuid4()),
        ticker=ticker,
        trade_date=trade_date,
        as_of=trade_date,
        reports={"complete_report_md": f"{ticker}/{trade_date}/reports/complete_report.md",
                 "complete_report_html": None},
    )
    (run_dir / "run_manifest.json").write_text(json.dumps(data), encoding="utf-8")


def _invoke_query(cli_main, args):
    """Invoke the real ``manifest query`` subcommand and parse its JSON stdout.

    Returns ``(exit_code, payload, raw_output)``. ``payload`` is parsed from
    ``result.stdout`` (the machine channel); ``raw_output`` is ``result.output``
    kept for diagnostics. ``payload`` is ``None`` when stdout is not JSON.
    """

    from typer.testing import CliRunner

    result = CliRunner().invoke(cli_main.app, ["manifest", "query", *args, "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = None
    return result.exit_code, payload, result.output


@pytest.mark.unit
def test_cli_manifest_query_filters_by_ticker_date_and_reports_bad_json(tmp_path, monkeypatch):
    # Three ticker/date combos so each filter selects a distinct set, plus one
    # corrupt record that must warn without hiding the valid matches.
    _seed_strlib_manifest(tmp_path, "AAPL", "2026-11-20")
    _seed_strlib_manifest(tmp_path, "MSFT", "2026-11-20")
    _seed_strlib_manifest(tmp_path, "AAPL", "2026-11-19")
    broken = tmp_path / "NVDA" / "2026-11-20"
    broken.mkdir(parents=True)
    (broken / "run_manifest.json").write_text("{ not json", encoding="utf-8")

    import cli.main as cli_main

    # A query starts nothing: building a graph or touching a vendor fails hard.
    def _boom(*args, **kwargs):
        raise AssertionError("manifest query must not start an analysis or a data vendor")

    monkeypatch.setattr(cli_main, "run_analysis", _boom, raising=False)
    monkeypatch.setattr(cli_main, "run_backtest", _boom, raising=False)

    def pairs(payload):
        # Candidate outer shape: {"matches": [{"ticker":..,"trade_date":..}], "warnings": [...]}.
        return sorted((m["ticker"], m["trade_date"]) for m in payload["matches"])

    code, payload, out = _invoke_query(
        cli_main, ["--results-dir", str(tmp_path), "--ticker", "AAPL"])
    assert code == 0, out
    assert "warnings" in payload  # candidate outer structure
    assert pairs(payload) == [("AAPL", "2026-11-19"), ("AAPL", "2026-11-20")]

    # A normal date query returns valid records and still reports the corrupt one.
    code, payload, out = _invoke_query(
        cli_main, ["--results-dir", str(tmp_path), "--date", "2026-11-20"])
    assert code == 0, out
    assert pairs(payload) == [("AAPL", "2026-11-20"), ("MSFT", "2026-11-20")]
    assert payload["warnings"], "corrupt record should warn while valid matches return"

    code, payload, out = _invoke_query(
        cli_main, ["--results-dir", str(tmp_path), "--ticker", "AAPL", "--date", "2026-11-19"])
    assert code == 0, out
    assert pairs(payload) == [("AAPL", "2026-11-19")]

    # No match: only the empty result is asserted here.
    code, payload, out = _invoke_query(
        cli_main, ["--results-dir", str(tmp_path), "--ticker", "ZZZZ"])
    assert code == 0, out
    assert pairs(payload) == []
