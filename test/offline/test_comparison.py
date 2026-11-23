"""FR-A / NFR-A / INV-A tests for same-day two-ticker comparison.

These tests are offline and deterministic: a fake graph stands in for
``TradingAgentsGraph``; no model, network, provider or real analysis runs.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from tradingagents.enhancements.comparison import (
    ComparisonInputError,
    SingleRunResult,
    _validate_inputs,
    run_comparison,
    run_one,
)

pytestmark = pytest.mark.unit

DATE = "2026-01-15"
STAMP = "20260101_000000"
C_RUN_ID_FIXTURE = "run_20260101T000000Z_example"
GENERATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TABLE_HEADER = (
    "| ticker | analysis_date | status | final_rating | summary | "
    "report_path | failure_reason |"
)
SENSITIVE_TERMS = (
    "sk-12345",
    "https://fake.com?token=secret-token",
    "ACCOUNT-SECRET",
)
SENSITIVE_EXCEPTION = " | ".join(SENSITIVE_TERMS)
GRAPH_FAILED_SAFE = "GRAPH_FAILED: Upstream analysis failed."
REPORT_SAVE_FAILED_SAFE = "REPORT_SAVE_FAILED: Upstream report save failed."


def _pm_result(ticker: str, rating: str, summary: str) -> tuple[dict, str]:
    state = {
        "company_of_interest": ticker,
        "trade_date": DATE,
        "decision_mode": "standard",
        "final_rating": rating,
        "final_trade_decision": (
            f"**Rating**: {rating}\n\n"
            f"**Executive Summary**: {summary}\n\n"
            "**Investment Thesis**: fixture thesis"
        ),
    }
    return state, rating


def _standard_review(ticker: str) -> tuple[dict, str]:
    state = {
        "company_of_interest": ticker,
        "trade_date": DATE,
        "decision_mode": "standard",
        "final_rating": "REVIEW",
        "final_trade_decision": "Review required.\n\nNo authoritative rating.",
    }
    return state, "REVIEW"


def _team_review(ticker: str, message: str) -> tuple[dict, str]:
    state = {
        "company_of_interest": ticker,
        "trade_date": DATE,
        "decision_mode": "team",
        "final_rating": "REVIEW",
        "eligibility_message": message,
        "final_trade_decision": (
            f"REVIEW\n\n{message}\n\nReason codes: market_evidence_unavailable"
        ),
    }
    return state, "REVIEW"


def _default_result(ticker: str) -> tuple[dict, str]:
    rating = "Buy" if ticker == "AAPL" else "Hold"
    return _pm_result(ticker, rating, f"{ticker} summary.")


class FakeGraph:
    """Offline stand-in for TradingAgentsGraph.

    It mirrors the upstream call shapes used by A:
    ``propagate(company_name, trade_date, asset_type="stock", portfolio=None)``
    and ``save_reports(final_state, ticker, save_path=None, html=True)``.
    """

    def __init__(
        self,
        results_root: Path,
        *,
        failures: set[str] | None = None,
        save_failures: set[str] | None = None,
        results: dict[str, tuple[dict, str]] | None = None,
    ) -> None:
        self.config = {"results_dir": str(results_root)}
        self.results_root = Path(results_root)
        self.failures = set(failures or ())
        self.save_failures = set(save_failures or ())
        self.results = dict(results or {})
        self.propagate_calls: list[tuple[str, str, str, object]] = []
        self.save_calls: list[tuple[dict, str, object, object]] = []
        self.final_states: dict[str, dict] = {}

    def propagate(
        self,
        company_name: str,
        trade_date: str,
        asset_type: str = "stock",
        portfolio=None,
    ):
        self.propagate_calls.append((company_name, trade_date, asset_type, portfolio))
        if company_name in self.failures:
            raise RuntimeError("propagate boom")
        state, signal = self.results.get(company_name, _default_result(company_name))
        self.final_states[company_name] = state
        return state, signal

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path=None,
        html: bool = True,
    ) -> Path:
        self.save_calls.append((final_state, ticker, save_path, html))
        if ticker in self.save_failures:
            raise OSError("save boom")
        folder = self.results_root / "reports" / f"{ticker}_{STAMP}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "complete_report.md"
        path.write_text(
            f"# Trading Analysis Report: {ticker}\n\n"
            f"marker:{ticker}:complete\n",
            encoding="utf-8",
        )
        return path


class CallShapeGraph(FakeGraph):
    """Records the exact positional/keyword shape of calls into upstream."""

    def __init__(self, results_root: Path, **kwargs) -> None:
        super().__init__(results_root, **kwargs)
        self.propagate_call_shape: list[tuple[tuple, dict]] = []
        self.save_call_shape: list[tuple[tuple, dict]] = []

    def propagate(self, *args, **kwargs):
        self.propagate_call_shape.append((args, kwargs))
        return super().propagate(*args, **kwargs)

    def save_reports(self, *args, **kwargs):
        self.save_call_shape.append((args, kwargs))
        return super().save_reports(*args, **kwargs)


class SensitiveFailureGraph(FakeGraph):
    """Raises exceptions whose text must never reach public artifacts."""

    def __init__(
        self,
        results_root: Path,
        *,
        propagate_failure: str | None = None,
        save_failures: set[str] | None = None,
    ) -> None:
        super().__init__(results_root)
        self.propagate_failure = propagate_failure
        self.secret_save_failures = set(save_failures or ())

    def propagate(
        self,
        company_name: str,
        trade_date: str,
        asset_type: str = "stock",
        portfolio=None,
    ):
        if company_name == self.propagate_failure:
            self.propagate_calls.append((company_name, trade_date, asset_type, portfolio))
            raise RuntimeError(SENSITIVE_EXCEPTION)
        return super().propagate(company_name, trade_date, asset_type, portfolio)

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path=None,
        html: bool = True,
    ) -> Path:
        if ticker in self.secret_save_failures:
            self.save_calls.append((final_state, ticker, save_path, html))
            raise OSError(SENSITIVE_EXCEPTION)
        return super().save_reports(final_state, ticker, save_path, html)


class AttributionGraph(FakeGraph):
    """Returns a report path that does not belong to the requested ticker."""

    def __init__(self, results_root: Path, *, kind: str) -> None:
        super().__init__(results_root)
        self.kind = kind

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path=None,
        html: bool = True,
    ) -> Path:
        self.save_calls.append((final_state, ticker, save_path, html))
        if self.kind == "msft_complete":
            folder = self.results_root / "reports" / f"MSFT_{STAMP}"
            filename = "complete_report.md"
            owner = "MSFT"
        else:
            folder = self.results_root / "reports" / f"AAPL_{STAMP}"
            filename = "notes.md"
            owner = "AAPL"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        path.write_text(
            f"# Trading Analysis Report: {owner}\n\n"
            f"marker:{owner}:complete\n",
            encoding="utf-8",
        )
        return path


class SymlinkAttributionGraph(FakeGraph):
    """Returns a report path whose resolved target belongs to another ticker."""

    def __init__(self, results_root: Path, *, kind: str) -> None:
        super().__init__(results_root)
        self.kind = kind

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path=None,
        html: bool = True,
    ) -> Path:
        if ticker != "AAPL":
            return super().save_reports(final_state, ticker, save_path, html)
        self.save_calls.append((final_state, ticker, save_path, html))
        msft_dir = self.results_root / "reports" / f"MSFT_{STAMP}"
        msft_dir.mkdir(parents=True, exist_ok=True)
        aapl_dir = self.results_root / "reports" / f"AAPL_{STAMP}"
        if self.kind == "directory":
            (msft_dir / "complete_report.md").write_text(
                "# Trading Analysis Report: MSFT\n\nmarker:MSFT:complete\n",
                encoding="utf-8",
            )
            aapl_dir.symlink_to(msft_dir, target_is_directory=True)
            return aapl_dir / "complete_report.md"
        (msft_dir / "notes.md").write_text(
            "# Trading Analysis Report: MSFT\n\nmarker:MSFT:notes\n",
            encoding="utf-8",
        )
        aapl_dir.mkdir(parents=True, exist_ok=True)
        link = aapl_dir / "complete_report.md"
        link.symlink_to(msft_dir / "notes.md")
        return link


def _assert_no_sensitive(texts: list[str]) -> None:
    for text in texts:
        for term in SENSITIVE_TERMS:
            assert term not in text


def _report_path(ticker: str) -> str:
    return f"reports/{ticker}_{STAMP}/complete_report.md"


def _manifest(results_root: Path, result) -> dict:
    return json.loads((results_root / result.manifest_path).read_text(encoding="utf-8"))


def _assert_no_artifacts(results_root: Path) -> None:
    if not results_root.exists():
        return
    assert not list(results_root.rglob("comparison.md"))
    assert not list(results_root.rglob("comparison_manifest.json"))


def _assert_no_graph_calls(graph: FakeGraph) -> None:
    assert graph.propagate_calls == []
    assert graph.save_calls == []


@pytest.mark.unit
def test_a_success_writes_both_artifacts_and_calls_upstream_in_order(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    assert result.overall_status == "SUCCESS"
    assert result.analysis_date == DATE
    assert [row.ticker for row in result.tickers] == ["AAPL", "MSFT"]
    assert [row.status for row in result.tickers] == ["SUCCESS", "SUCCESS"]
    assert result.tickers[0] == SingleRunResult(
        ticker="AAPL",
        analysis_date=DATE,
        status="SUCCESS",
        final_rating="Buy",
        summary="AAPL summary.",
        report_path=_report_path("AAPL"),
        failure_reason=None,
    )
    assert result.tickers[1] == SingleRunResult(
        ticker="MSFT",
        analysis_date=DATE,
        status="SUCCESS",
        final_rating="Hold",
        summary="MSFT summary.",
        report_path=_report_path("MSFT"),
        failure_reason=None,
    )

    assert graph.propagate_calls == [
        ("AAPL", DATE, "stock", None),
        ("MSFT", DATE, "stock", None),
    ]
    assert [call[1] for call in graph.save_calls] == ["AAPL", "MSFT"]
    assert all(call[2] is None and call[3] is True for call in graph.save_calls)

    assert (results_root / result.comparison_report_path).is_file()
    assert (results_root / result.manifest_path).is_file()
    markdown = (results_root / result.comparison_report_path).read_text(encoding="utf-8")
    assert TABLE_HEADER in markdown
    assert "| AAPL | 2026-01-15 | SUCCESS | Buy |" in markdown
    assert "| MSFT | 2026-01-15 | SUCCESS | Hold |" in markdown


@pytest.mark.unit
def test_a_review_team_mode_uses_eligibility_message_and_stays_success(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(
        results_root,
        results={
            "AAPL": _team_review("AAPL", "Market evidence unavailable."),
            "MSFT": _pm_result("MSFT", "Hold", "MSFT summary."),
        },
    )

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    row = result.tickers[0]
    assert row.status == "SUCCESS"
    assert row.final_rating == "REVIEW"
    assert row.summary == "Market evidence unavailable."
    assert row.report_path == _report_path("AAPL")
    assert row.failure_reason is None
    assert row.report_path is not None
    assert (results_root / row.report_path).is_file()


@pytest.mark.unit
def test_a_review_standard_mode_uses_first_paragraph_and_stays_success(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(
        results_root,
        results={
            "AAPL": _standard_review("AAPL"),
            "MSFT": _pm_result("MSFT", "Hold", "MSFT summary."),
        },
    )

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    row = result.tickers[0]
    assert row.status == "SUCCESS"
    assert row.final_rating == "REVIEW"
    assert row.summary == "Review required."
    assert row.report_path == _report_path("AAPL")
    assert row.failure_reason is None
    assert row.report_path is not None
    assert (results_root / row.report_path).is_file()


@pytest.mark.unit
def test_a_fail_first_ticker_preserves_second_report_and_skips_its_save(tmp_path):
    """FR-A, NFR-A, INV-A: first failure does not remove the second success."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={"AAPL"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    first, second = result.tickers
    assert first.status == "FAILED"
    assert first.final_rating is None
    assert first.summary is None
    assert first.report_path is None
    assert first.failure_reason is not None
    assert first.failure_reason.startswith("GRAPH_FAILED")

    assert second.status == "SUCCESS"
    assert second.final_rating == "Hold"
    assert second.summary == "MSFT summary."
    assert second.report_path == _report_path("MSFT")
    assert second.report_path is not None
    report = results_root / second.report_path
    assert report.is_file()
    assert "marker:MSFT:complete" in report.read_text(encoding="utf-8")

    assert [call[1] for call in graph.save_calls] == ["MSFT"]
    assert (results_root / result.comparison_report_path).is_file()
    assert (results_root / result.manifest_path).is_file()


@pytest.mark.unit
def test_a_fail_second_ticker_preserves_first_report(tmp_path):
    """FR-A, NFR-A, INV-A: second failure does not remove the first success."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={"MSFT"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    first, second = result.tickers
    assert first.status == "SUCCESS"
    assert first.final_rating == "Buy"
    assert first.report_path == _report_path("AAPL")
    assert first.report_path is not None
    report = results_root / first.report_path
    assert report.is_file()
    assert "marker:AAPL:complete" in report.read_text(encoding="utf-8")

    assert second.status == "FAILED"
    assert second.final_rating is None
    assert second.summary is None
    assert second.report_path is None
    assert second.failure_reason is not None
    assert second.failure_reason.startswith("GRAPH_FAILED")
    assert [call[1] for call in graph.save_calls] == ["AAPL"]


@pytest.mark.unit
def test_a_fail_both_tickers_still_writes_both_artifacts(tmp_path):
    """FR-A, NFR-A, INV-A: both failures still produce a complete comparison."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={"AAPL", "MSFT"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    assert result.overall_status == "FAILED"
    assert [row.status for row in result.tickers] == ["FAILED", "FAILED"]
    for row in result.tickers:
        assert row.final_rating is None
        assert row.summary is None
        assert row.report_path is None
        assert row.failure_reason is not None
        assert row.failure_reason.startswith("GRAPH_FAILED")

    assert graph.save_calls == []
    assert (results_root / result.comparison_report_path).is_file()
    assert (results_root / result.manifest_path).is_file()
    markdown = (results_root / result.comparison_report_path).read_text(encoding="utf-8")
    assert markdown.count("| null | null | null |") == 2


@pytest.mark.unit
def test_a_fail_save_failure_calls_save_reports_and_marks_only_that_row(tmp_path):
    """FR-A, NFR-A, INV-A: REPORT_SAVE_FAILED keeps the other success."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, save_failures={"AAPL"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    first, second = result.tickers
    assert first.status == "FAILED"
    assert first.final_rating is None
    assert first.summary is None
    assert first.report_path is None
    assert first.failure_reason is not None
    assert first.failure_reason.startswith("REPORT_SAVE_FAILED")

    assert second.status == "SUCCESS"
    assert second.report_path == _report_path("MSFT")
    assert second.report_path is not None
    assert (results_root / second.report_path).is_file()

    assert [call[1] for call in graph.save_calls] == ["AAPL", "MSFT"]
    assert [(call[1], call[2], call[3]) for call in graph.save_calls] == [
        ("AAPL", None, True),
        ("MSFT", None, True),
    ]


@pytest.mark.unit
def test_a_fail_missing_or_invalid_rating_does_not_call_save_reports(tmp_path):
    """FR-A, NFR-A, INV-A: invalid authoritative rating is isolated before save."""
    results_root = tmp_path / "results"
    graph = FakeGraph(
        results_root,
        results={"AAPL": _pm_result("AAPL", "Nope", "not a rating")},
    )

    row = run_one(graph, "AAPL", DATE)

    assert row.status == "FAILED"
    assert row.final_rating is None
    assert row.summary is None
    assert row.report_path is None
    assert row.failure_reason is not None
    assert row.failure_reason.startswith("MISSING_OR_INVALID_FINAL_RATING")
    assert graph.save_calls == []


@pytest.mark.unit
@pytest.mark.parametrize("failed_ticker", ["AAPL", "MSFT"])
def test_nfr_a_single_failure_retains_the_other_success_report(tmp_path, failed_ticker):
    """FR-A, NFR-A, INV-A: 100% retention in both single-failure directions."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={failed_ticker})
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    assert result.overall_status == "PARTIAL"
    successes = [row for row in result.tickers if row.status == "SUCCESS"]
    failures = [row for row in result.tickers if row.status == "FAILED"]
    assert len(successes) == 1
    assert len(failures) == 1

    success = successes[0]
    failed = failures[0]
    assert success.ticker != failed.ticker
    assert success.report_path is not None
    report = results_root / success.report_path
    assert report.is_file()
    assert f"marker:{success.ticker}:complete" in report.read_text(encoding="utf-8")

    assert failed.final_rating is None
    assert failed.summary is None
    assert failed.report_path is None
    assert failed.failure_reason is not None
    assert failed.failure_reason.startswith("GRAPH_FAILED")


@pytest.mark.unit
def test_a_fail_review_success_is_retained_when_other_fails(tmp_path):
    """FR-A, NFR-A, INV-A: REVIEW counts as success and its report is retained."""
    results_root = tmp_path / "results"
    graph = FakeGraph(
        results_root,
        failures={"MSFT"},
        results={"AAPL": _standard_review("AAPL")},
    )
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    aapl, msft = result.tickers
    assert aapl.status == "SUCCESS"
    assert aapl.final_rating == "REVIEW"
    assert aapl.summary == "Review required."
    assert aapl.report_path is not None
    assert (results_root / aapl.report_path).is_file()
    assert msft.status == "FAILED"
    assert msft.report_path is None
    assert result.overall_status == "PARTIAL"


@pytest.mark.unit
def test_a_fail_save_failure_on_second_ticker_preserves_first_report(tmp_path):
    """FR-A, NFR-A, INV-A: second save failure does not remove the first report."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, save_failures={"MSFT"})
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    first, second = result.tickers
    assert first.status == "SUCCESS"
    assert first.report_path == _report_path("AAPL")
    assert first.report_path is not None
    report = results_root / first.report_path
    assert report.is_file()
    assert "marker:AAPL:complete" in report.read_text(encoding="utf-8")

    assert second.status == "FAILED"
    assert second.final_rating is None
    assert second.summary is None
    assert second.report_path is None
    assert second.failure_reason is not None
    assert second.failure_reason.startswith("REPORT_SAVE_FAILED")
    assert [call[1] for call in graph.save_calls] == ["AAPL", "MSFT"]
    assert result.overall_status == "PARTIAL"


@pytest.mark.unit
def test_a_manifest_partial_failure_rows_and_overall_status(tmp_path):
    """FR-A, NFR-A, INV-A: manifest and Markdown agree on a failed row."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={"MSFT"})
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    manifest = _manifest(results_root, result)
    assert manifest["overall_status"] == "PARTIAL"
    assert manifest["comparison_report_path"] == result.comparison_report_path
    assert manifest["tickers"][0] == {
        "ticker": "AAPL",
        "analysis_date": DATE,
        "status": "SUCCESS",
        "final_rating": "Buy",
        "summary": "AAPL summary.",
        "report_path": _report_path("AAPL"),
        "failure_reason": None,
    }
    failed = manifest["tickers"][1]
    assert failed["ticker"] == "MSFT"
    assert failed["analysis_date"] == DATE
    assert failed["status"] == "FAILED"
    assert failed["final_rating"] is None
    assert failed["summary"] is None
    assert failed["report_path"] is None
    assert failed["failure_reason"].startswith("GRAPH_FAILED")

    markdown = (results_root / result.comparison_report_path).read_text(encoding="utf-8")
    assert "| AAPL | 2026-01-15 | SUCCESS | Buy |" in markdown
    assert "| MSFT | 2026-01-15 | FAILED | null | null | null |" in markdown


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ticker_a", "ticker_b"),
    [
        ("aapl", " AAPL "),
        ("brk.b", " BRK.B "),
    ],
)
def test_a_input_duplicate_ticker_rejected_before_any_run(tmp_path, ticker_a, ticker_b):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)

    with pytest.raises(ComparisonInputError) as excinfo:
        run_comparison(graph, ticker_a, ticker_b, DATE)

    assert excinfo.value.code == "DUPLICATE_TICKER"
    _assert_no_graph_calls(graph)
    _assert_no_artifacts(results_root)


@pytest.mark.unit
@pytest.mark.parametrize("bad_ticker", ["", "..", "A" * 33, "bad symbol!"])
def test_a_input_invalid_ticker_rejected_before_any_run(tmp_path, bad_ticker):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)

    with pytest.raises(ComparisonInputError) as excinfo:
        run_comparison(graph, bad_ticker, "MSFT", DATE)

    assert excinfo.value.code == "INVALID_TICKER"
    _assert_no_graph_calls(graph)
    _assert_no_artifacts(results_root)


@pytest.mark.unit
def test_a_input_future_date_rejected_before_any_run(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)
    future = (date.today() + timedelta(days=1)).isoformat()

    with pytest.raises(ComparisonInputError) as excinfo:
        run_comparison(graph, "AAPL", "MSFT", future)

    assert excinfo.value.code == "FUTURE_DATE"
    _assert_no_graph_calls(graph)
    _assert_no_artifacts(results_root)


@pytest.mark.unit
@pytest.mark.parametrize("bad_date", ["2026-1-1", "not-a-date", "2026-02-30", " 2026-01-15 "])
def test_a_input_noncanonical_date_rejected_before_any_run(tmp_path, bad_date):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)

    with pytest.raises(ComparisonInputError) as excinfo:
        run_comparison(graph, "AAPL", "MSFT", bad_date)

    assert excinfo.value.code == "INVALID_DATE"
    _assert_no_graph_calls(graph)
    _assert_no_artifacts(results_root)


@pytest.mark.unit
def test_a_normalize_uses_canonical_tickers_for_calls_and_report_paths(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)

    result = run_comparison(graph, " cnc.to ", " brk.b ", DATE)

    assert [row.ticker for row in result.tickers] == ["CNC.TO", "BRK.B"]
    assert [row.report_path for row in result.tickers] == [
        _report_path("CNC.TO"),
        _report_path("BRK.B"),
    ]
    assert graph.propagate_calls == [
        ("CNC.TO", DATE, "stock", None),
        ("BRK.B", DATE, "stock", None),
    ]


@pytest.mark.unit
def test_a_xtalk_success_rows_keep_their_own_rating_summary_and_report(tmp_path):
    """FR-A, NFR-A, INV-A: literal no-cross-row assertions for two successes."""
    results_root = tmp_path / "results"
    graph = FakeGraph(
        results_root,
        results={
            "AAPL": _pm_result("AAPL", "Buy", "AAPL summary."),
            "MSFT": _pm_result("MSFT", "Sell", "MSFT summary."),
        },
    )

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    assert result.tickers == (
        SingleRunResult(
            ticker="AAPL",
            analysis_date=DATE,
            status="SUCCESS",
            final_rating="Buy",
            summary="AAPL summary.",
            report_path=_report_path("AAPL"),
            failure_reason=None,
        ),
        SingleRunResult(
            ticker="MSFT",
            analysis_date=DATE,
            status="SUCCESS",
            final_rating="Sell",
            summary="MSFT summary.",
            report_path=_report_path("MSFT"),
            failure_reason=None,
        ),
    )
    aapl, msft = result.tickers
    assert aapl.final_rating != msft.final_rating
    assert aapl.summary != msft.summary
    assert aapl.report_path != msft.report_path


@pytest.mark.unit
def test_a_xtalk_partial_failure_does_not_fill_failed_row_from_success(tmp_path):
    """FR-A, NFR-A, INV-A: failed row stays null; successful row stays its own."""
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root, failures={"MSFT"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    aapl, msft = result.tickers
    assert aapl == SingleRunResult(
        ticker="AAPL",
        analysis_date=DATE,
        status="SUCCESS",
        final_rating="Buy",
        summary="AAPL summary.",
        report_path=_report_path("AAPL"),
        failure_reason=None,
    )
    assert msft.ticker == "MSFT"
    assert msft.status == "FAILED"
    assert msft.final_rating is None
    assert msft.summary is None
    assert msft.report_path is None
    assert msft.failure_reason is not None
    assert msft.failure_reason.startswith("GRAPH_FAILED")
    assert aapl.final_rating not in {None, "REVIEW"}


@pytest.mark.unit
def test_a_manifest_matches_markdown_and_is_mandatory(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)
    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    markdown_path = results_root / result.comparison_report_path
    manifest_path = results_root / result.manifest_path
    assert markdown_path.is_file()
    assert manifest_path.is_file()

    manifest = _manifest(results_root, result)
    assert manifest["schema_version"] == 1
    assert manifest["comparison_id"] == result.comparison_id
    assert manifest["analysis_date"] == DATE
    assert manifest["generated_at"] == result.generated_at
    assert manifest["overall_status"] == "SUCCESS"
    assert manifest["comparison_report_path"] == result.comparison_report_path
    assert len(manifest["tickers"]) == 2

    for manifest_row, result_row in zip(manifest["tickers"], result.tickers, strict=True):
        assert manifest_row == {
            "ticker": result_row.ticker,
            "analysis_date": result_row.analysis_date,
            "status": result_row.status,
            "final_rating": result_row.final_rating,
            "summary": result_row.summary,
            "report_path": result_row.report_path,
            "failure_reason": result_row.failure_reason,
        }

    markdown = markdown_path.read_text(encoding="utf-8")
    assert TABLE_HEADER in markdown
    assert f"| {result.tickers[0].ticker} | {DATE} | SUCCESS | Buy |" in markdown
    assert f"| {result.tickers[1].ticker} | {DATE} | SUCCESS | Hold |" in markdown


@pytest.mark.unit
def test_a_comparison_id_and_generated_at_are_fresh_and_utc(tmp_path):
    results_root = tmp_path / "results"
    graph = FakeGraph(results_root)

    first = run_comparison(graph, "AAPL", "MSFT", DATE)
    second = run_comparison(graph, "AAPL", "MSFT", DATE)

    for result in (first, second):
        assert isinstance(result.comparison_id, str)
        assert result.comparison_id
        assert result.comparison_id.startswith("cmp_")
        assert result.comparison_id != C_RUN_ID_FIXTURE

        assert isinstance(result.generated_at, str)
        assert GENERATED_AT_RE.fullmatch(result.generated_at)
        parsed = datetime.fromisoformat(result.generated_at.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)

    assert first.comparison_id != second.comparison_id


@pytest.mark.unit
def test_run_one_calls_upstream_with_exact_positional_arguments(tmp_path):
    results_root = tmp_path / "results"
    graph = CallShapeGraph(results_root)

    result = run_one(graph, "AAPL", DATE)

    assert result.status == "SUCCESS"
    assert graph.propagate_call_shape == [(("AAPL", DATE), {})]
    assert len(graph.save_call_shape) == 1
    save_args, save_kwargs = graph.save_call_shape[0]
    assert save_args == (graph.final_states["AAPL"], "AAPL")
    assert save_kwargs == {}
    assert result.report_path == _report_path("AAPL")
    assert result.report_path is not None
    assert (results_root / result.report_path).is_file()


@pytest.mark.unit
def test_a_propagate_exception_is_sanitized_in_all_artifacts(tmp_path):
    """FR-A, NFR-A, INV-A, SEC-01: raw analysis errors must not leak."""
    results_root = tmp_path / "results"
    graph = SensitiveFailureGraph(results_root, propagate_failure="AAPL")

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    failed, success = result.tickers
    assert failed.status == "FAILED"
    assert failed.failure_reason == GRAPH_FAILED_SAFE
    assert failed.final_rating is None
    assert failed.summary is None
    assert failed.report_path is None
    assert success.status == "SUCCESS"
    assert success.report_path is not None
    report = results_root / success.report_path
    assert report.is_file()
    assert "marker:MSFT:complete" in report.read_text(encoding="utf-8")
    assert [call[1] for call in graph.save_calls] == ["MSFT"]

    markdown = (results_root / result.comparison_report_path).read_text(encoding="utf-8")
    manifest = (results_root / result.manifest_path).read_text(encoding="utf-8")
    _assert_no_sensitive([failed.failure_reason, markdown, manifest])


@pytest.mark.unit
def test_a_save_exception_is_sanitized_in_all_artifacts(tmp_path):
    """FR-A, NFR-A, INV-A, SEC-01: raw save errors must not leak."""
    results_root = tmp_path / "results"
    graph = SensitiveFailureGraph(results_root, save_failures={"AAPL"})

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    failed, success = result.tickers
    assert failed.status == "FAILED"
    assert failed.failure_reason == REPORT_SAVE_FAILED_SAFE
    assert failed.final_rating is None
    assert failed.summary is None
    assert failed.report_path is None
    assert success.status == "SUCCESS"
    assert success.report_path is not None
    assert (results_root / success.report_path).is_file()
    assert [call[1] for call in graph.save_calls] == ["AAPL", "MSFT"]

    markdown = (results_root / result.comparison_report_path).read_text(encoding="utf-8")
    manifest = (results_root / result.manifest_path).read_text(encoding="utf-8")
    _assert_no_sensitive([failed.failure_reason, markdown, manifest])


@pytest.mark.unit
@pytest.mark.parametrize("case", ["wrong_ticker", "wrong_date"])
def test_a_identity_mismatch_fails_without_save(tmp_path, case):
    """FR-A, NFR-A, INV-A: final_state must belong to the requested ticker/date."""
    results_root = tmp_path / "results"
    if case == "wrong_ticker":
        state, signal = _pm_result("MSFT", "Sell", "MSFT summary.")
    else:
        state, signal = _pm_result("AAPL", "Buy", "AAPL summary.")
        state["trade_date"] = "2026-01-16"
    graph = FakeGraph(results_root, results={"AAPL": (state, signal)})

    row = run_one(graph, "AAPL", DATE)

    assert row.status == "FAILED"
    assert row.failure_reason is not None
    assert row.failure_reason.startswith("RESULT_IDENTITY_MISMATCH")
    assert row.final_rating is None
    assert row.summary is None
    assert row.report_path is None
    assert graph.save_calls == []


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["msft_complete", "notes"])
def test_a_report_attribution_mismatch_fails(tmp_path, kind):
    """FR-A, NFR-A, INV-A: report path must be the requested ticker's report."""
    results_root = tmp_path / "results"
    graph = AttributionGraph(results_root, kind=kind)

    row = run_one(graph, "AAPL", DATE)

    assert row.status == "FAILED"
    assert row.failure_reason is not None
    assert row.failure_reason.startswith("REPORT_ATTRIBUTION_FAILED")
    assert row.final_rating is None
    assert row.summary is None
    assert row.report_path is None
    assert len(graph.save_calls) == 1


@pytest.mark.unit
def test_a_multiline_executive_summary_is_fully_extracted_and_collapsed(tmp_path):
    """FR-A, NFR-A, INV-A: keep the whole summary section, then collapse it."""
    results_root = tmp_path / "results"
    state, signal = _pm_result("AAPL", "Buy", "ignored")
    state["final_trade_decision"] = (
        "**Executive Summary**: First line about entry risk.\n"
        "Second line about position sizing and risk controls.\n\n"
        "**Investment Thesis**: detailed thesis."
    )
    graph = FakeGraph(results_root, results={"AAPL": (state, signal)})

    row = run_one(graph, "AAPL", DATE)

    assert row.status == "SUCCESS"
    assert row.summary == (
        "First line about entry risk. "
        "Second line about position sizing and risk controls."
    )


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["directory", "file"])
def test_a_symlink_report_attribution_is_rejected(tmp_path, kind):
    """FR-A, NFR-A, INV-A: resolved report paths must belong to the ticker."""
    results_root = tmp_path / "results"
    graph = SymlinkAttributionGraph(results_root, kind=kind)

    result = run_comparison(graph, "AAPL", "MSFT", DATE)

    failed, success = result.tickers
    assert failed.status == "FAILED"
    assert failed.failure_reason is not None
    assert failed.failure_reason.startswith("REPORT_ATTRIBUTION_FAILED")
    assert failed.final_rating is None
    assert failed.summary is None
    assert failed.report_path is None
    assert success.status == "SUCCESS"
    assert success.report_path == _report_path("MSFT")
    assert success.report_path is not None
    assert (results_root / success.report_path).is_file()
    assert result.overall_status == "PARTIAL"


@pytest.mark.unit
def test_a_crypto_ticker_is_rejected_as_unsupported_asset_type(tmp_path):
    """FR-A, NFR-A, INV-A: A accepts stocks only; crypto is rejected up front."""
    results_root = tmp_path / "results"
    crypto_tickers = ("btcusd", "BTC-USD", "BTC-EUR", "ETH-GBP", "BTC-JPY")
    for crypto_ticker in crypto_tickers:
        for ticker_a, ticker_b in (
            (crypto_ticker, "MSFT"),
            ("MSFT", crypto_ticker),
        ):
            with pytest.raises(ComparisonInputError) as excinfo:
                _validate_inputs(ticker_a, ticker_b, DATE)
            assert excinfo.value.code == "UNSUPPORTED_ASSET_TYPE"

            graph = FakeGraph(results_root)
            with pytest.raises(ComparisonInputError) as run_excinfo:
                run_comparison(graph, ticker_a, ticker_b, DATE)
            assert run_excinfo.value.code == "UNSUPPORTED_ASSET_TYPE"
            _assert_no_graph_calls(graph)
            _assert_no_artifacts(results_root)

    assert _validate_inputs("BRK-B", "AAPL", DATE) == ("BRK-B", "AAPL", DATE)
