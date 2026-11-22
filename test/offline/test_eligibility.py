"""FR-D/NFR-D acceptance tests for the deterministic team-mode rating gate.

Test expectations are literal contract values, independent of the gate
implementation. The application module is intentionally absent in this
tests-first revision; a non-D reviewer must approve this contract before it is
implemented.
"""

from __future__ import annotations

import pytest

from tradingagents.agents.rating import RATING_REVIEW, RATINGS_5_TIER

ANALYSIS_DATE = "2026-01-20"


def _evaluate(**overrides):
    from tradingagents.enhancements.eligibility import evaluate_eligibility

    values = {
        "decision_mode": "team",
        "candidate_rating": "Buy",
        "market_analyst_status": "completed",
        "market_evidence_status": "valid",
        "snapshot_date": ANALYSIS_DATE,
        "analysis_date": ANALYSIS_DATE,
    }
    values.update(overrides)
    return evaluate_eligibility(**values)


@pytest.mark.unit
@pytest.mark.parametrize("rating", ["Buy", "Overweight", "Hold", "Underweight", "Sell"])
def test_each_allowed_rating_passes_with_verified_market_evidence(rating):
    decision = _evaluate(candidate_rating=rating)

    assert decision.final_rating == rating
    assert decision.eligible is True
    assert decision.reason_codes == ()
    assert decision.user_message == ""


@pytest.mark.unit
def test_snapshot_exactly_ten_calendar_days_old_passes_existing_freshness_bound():
    decision = _evaluate(snapshot_date="2026-01-10")

    assert decision.final_rating == "Buy"
    assert decision.eligible is True
    assert decision.reason_codes == ()


@pytest.mark.unit
@pytest.mark.parametrize(
    "analyst_status, expected_reason",
    [
        ("not_run", "market_analyst_not_run"),
        ("failed", "market_analyst_failed"),
        ("unknown", "market_analyst_invalid_status"),
        (None, "market_analyst_not_run"),
    ],
)
def test_market_analyst_must_have_a_known_successful_execution(analyst_status, expected_reason):
    decision = _evaluate(market_analyst_status=analyst_status)

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == (expected_reason,)
    assert "review" in decision.user_message.lower()


@pytest.mark.unit
@pytest.mark.parametrize(
    "evidence_status, expected_reason",
    [
        (None, "market_evidence_missing"),
        ("not_run", "market_evidence_not_run"),
        ("unavailable", "market_evidence_unavailable"),
        ("unknown", "market_evidence_invalid_status"),
    ],
)
def test_missing_or_unusable_market_evidence_forces_review(evidence_status, expected_reason):
    decision = _evaluate(market_evidence_status=evidence_status, snapshot_date=None)

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == (expected_reason,)


@pytest.mark.unit
@pytest.mark.parametrize(
    "snapshot_date, expected_reason",
    [
        (None, "market_snapshot_date_missing"),
        ("2026-1-20", "market_snapshot_date_invalid"),
        ("2026-02-30", "market_snapshot_date_invalid"),
        ("2026-01-21", "market_snapshot_after_analysis"),
        ("2026-01-09", "market_snapshot_stale"),
    ],
)
def test_invalid_or_future_market_snapshot_dates_force_review(snapshot_date, expected_reason):
    decision = _evaluate(snapshot_date=snapshot_date)

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == (expected_reason,)


@pytest.mark.unit
@pytest.mark.parametrize("analysis_date", ["2026-1-20", "2026-02-30", "not-a-date"])
def test_invalid_analysis_date_fails_closed(analysis_date):
    decision = _evaluate(analysis_date=analysis_date)

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == ("analysis_date_invalid",)


@pytest.mark.unit
@pytest.mark.parametrize("rating", [None, "REVIEW", "buy", "Buy today", "Long"])
def test_only_exact_five_tier_values_are_eligible(rating):
    decision = _evaluate(candidate_rating=rating)

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == ("invalid_rating",)


@pytest.mark.unit
def test_gate_reports_multiple_causes_in_contract_order_and_ignores_candidate_buy():
    decision = _evaluate(
        candidate_rating="Buy",
        market_analyst_status="not_run",
        market_evidence_status="unavailable",
    )

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == (
        "market_analyst_not_run",
        "market_evidence_unavailable",
    )
    assert "market analyst" in decision.user_message.lower()
    assert "market evidence" in decision.user_message.lower()


@pytest.mark.unit
def test_ineligible_report_shows_authoritative_review_and_reason_in_both_formats(tmp_path):
    from tradingagents.reporting import write_report_tree

    state = {
        "trade_date": ANALYSIS_DATE,
        "market_report": "Market analyst report.",
        "final_trade_decision": (
            "REVIEW (market_evidence_unavailable): critical market evidence is unavailable."
        ),
        "final_rating": RATING_REVIEW,
        "eligibility_reason_codes": ["market_evidence_unavailable"],
        "eligibility_message": "Review required: critical market evidence is unavailable.",
    }
    write_report_tree(state, "NVDA", tmp_path, html=True)

    markdown = (tmp_path / "complete_report.md").read_text(encoding="utf-8")
    html = (tmp_path / "complete_report.html").read_text(encoding="utf-8")
    for output in (markdown, html):
        assert "REVIEW" in output
        assert "market_evidence_unavailable" in output
        assert "critical market evidence is unavailable" in output
        assert "Buy" not in output


@pytest.mark.unit
def test_cli_exposes_team_decision_mode_without_changing_its_default(monkeypatch):
    from typer.testing import CliRunner

    import cli.main as cli_main

    calls = []
    monkeypatch.setattr(cli_main, "run_analysis", lambda **kwargs: calls.append(kwargs))
    runner = CliRunner()

    default = runner.invoke(cli_main.app, [])
    team = runner.invoke(cli_main.app, ["--decision-mode", "team"])
    invalid = runner.invoke(cli_main.app, ["--decision-mode", "unsupported"])

    assert default.exit_code == 0, default.output
    assert team.exit_code == 0, team.output
    assert invalid.exit_code != 0
    assert calls[0]["flags"]["decision_mode"] == "standard"
    assert calls[1]["flags"]["decision_mode"] == "team"
    assert len(calls) == 2


@pytest.mark.unit
def test_cli_run_prints_gate_reason_even_without_showing_full_report(monkeypatch, tmp_path):
    from types import SimpleNamespace

    import cli.run as cli_run
    from cli.models import AnalystType

    final_state = {
        "market_report": "Market report.",
        "final_trade_decision": (
            "REVIEW (market_evidence_unavailable): critical market evidence is unavailable."
        ),
        "final_rating": RATING_REVIEW,
        "eligibility_reason_codes": ["market_evidence_unavailable"],
        "eligibility_message": "Review required: critical market evidence is unavailable.",
    }

    class _Graph:
        propagator = SimpleNamespace(get_graph_args=lambda **_kwargs: {})

        def create_run_state(self, *_args):
            return {"messages": []}

        def begin_checkpoint(self, *_args):
            return None

        def checkpoint_input(self, state):
            return state

        def stream_run(self, *_args, **_kwargs):
            yield [], final_state

        def record_decision(self, *_args):
            pass

        def clear_checkpoint_on_success(self, *_args):
            pass

        def end_checkpoint(self):
            pass

    class _Buffer:
        def __init__(self):
            self.messages = []
            self.tool_calls = []
            self.report_sections = {}
            self.selected_analysts = []
            self.agent_status = {}
            self._processed_message_ids = set()

        def init_for_analysis(self, analysts):
            self.selected_analysts = list(analysts)
            self.agent_status = {"Market Analyst": "pending"}

        def add_message(self, kind, content):
            self.messages.append(("12:00:00", kind, content))

        def add_tool_call(self, name, args):
            self.tool_calls.append((name, args))

        def update_report_section(self, name, content):
            if name in self.report_sections:
                self.report_sections[name] = content

        def update_agent_status(self, name, status):
            self.agent_status[name] = status

    buffer = _Buffer()
    printed = []
    monkeypatch.setattr(cli_run, "message_buffer", buffer)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda _flags: {
        "ticker": "NVDA", "analysis_date": ANALYSIS_DATE,
        "analysts": [AnalystType.MARKET], "asset_type": "stock",
    })
    monkeypatch.setattr(cli_run, "_build_run_config", lambda *_args: {
        "data_cache_dir": str(tmp_path / "cache"), "results_dir": str(tmp_path / "results"),
    })
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *_args, **_kwargs: _Graph())
    monkeypatch.setattr(cli_run, "create_layout", lambda: object())
    monkeypatch.setattr(cli_run, "update_display", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_run, "_offer_reports", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_run.console, "print", lambda *args, **_kwargs: printed.append(" ".join(map(str, args))))
    monkeypatch.setattr(cli_run, "Live", type("L", (), {
        "__init__": lambda self, *_args, **_kwargs: None,
        "__enter__": lambda self: self,
        "__exit__": lambda self, *_args: False,
    }))
    monkeypatch.setattr(cli_run.sys, "stdin", SimpleNamespace(isatty=lambda: True))

    cli_run.run_analysis(flags={"decision_mode": "team"})

    output = "\n".join(printed)
    assert "REVIEW" in output
    assert "market_evidence_unavailable" in output
    assert "critical market evidence is unavailable" in output
    assert "Buy" not in output


@pytest.mark.unit
def test_cli_displays_gate_review_and_reasons_in_final_report(capsys):
    from cli.display import display_complete_report

    display_complete_report({
        "final_trade_decision": (
            "REVIEW (market_evidence_unavailable): critical market evidence is unavailable."
        ),
        "final_rating": RATING_REVIEW,
        "eligibility_reason_codes": ["market_evidence_unavailable"],
        "eligibility_message": "Review required: critical market evidence is unavailable.",
    })

    output = capsys.readouterr().out
    assert "REVIEW" in output
    assert "market_evidence_unavailable" in output
    assert "critical market evidence is unavailable" in output
    assert "Buy" not in output


@pytest.mark.unit
def test_review_decision_is_not_added_to_pending_settlement_or_reflection(tmp_path):
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.memory import TradingMemoryLog

    memory = TradingMemoryLog({"memory_log_path": str(tmp_path / "memory.md")})
    graph = object.__new__(TradingAgentsGraph)
    graph.memory_log = memory
    graph._log_state = lambda _trade_date, _state: None

    graph.record_decision(
        "NVDA",
        ANALYSIS_DATE,
        {
            "final_rating": RATING_REVIEW,
            "final_trade_decision": (
                "REVIEW (market_evidence_unavailable): critical market evidence is unavailable."
            ),
        },
    )

    assert memory.get_pending_entries() == []


@pytest.mark.unit
def test_rating_allowlist_in_the_test_matches_the_project_five_tier_contract():
    # Keep the fixture's explicit expected values independent while also
    # detecting accidental vocabulary drift in the shared upstream parser.
    assert RATINGS_5_TIER == ("Buy", "Overweight", "Hold", "Underweight", "Sell")
