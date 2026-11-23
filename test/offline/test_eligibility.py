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
    "field, value, expected_reason",
    [
        pytest.param("market_analyst_status", "not_run", "market_analyst_not_run", id="analyst-not-run"),
        pytest.param("market_analyst_status", "failed", "market_analyst_failed", id="analyst-failed"),
        pytest.param("market_analyst_status", "unknown", "market_analyst_invalid_status", id="analyst-unknown"),
        pytest.param("market_analyst_status", None, "market_analyst_not_run", id="analyst-missing"),
        pytest.param("market_evidence_status", None, "market_evidence_missing", id="evidence-missing"),
        pytest.param("market_evidence_status", "not_run", "market_evidence_not_run", id="evidence-not-run"),
        pytest.param("market_evidence_status", "unavailable", "market_evidence_unavailable", id="evidence-unavailable"),
        pytest.param("market_evidence_status", "unknown", "market_evidence_invalid_status", id="evidence-unknown"),
        pytest.param("snapshot_date", None, "market_snapshot_date_missing", id="snapshot-missing"),
        pytest.param("snapshot_date", "2026-1-20", "market_snapshot_date_invalid", id="snapshot-noncanonical"),
        pytest.param("snapshot_date", "2026-02-30", "market_snapshot_date_invalid", id="snapshot-impossible"),
        pytest.param("snapshot_date", "2026-01-21", "market_snapshot_after_analysis", id="snapshot-future"),
        pytest.param("snapshot_date", "2026-01-09", "market_snapshot_stale", id="snapshot-stale"),
        pytest.param("analysis_date", "2026-1-20", "analysis_date_invalid", id="analysis-noncanonical"),
        pytest.param("analysis_date", "2026-02-30", "analysis_date_invalid", id="analysis-impossible"),
        pytest.param("analysis_date", "not-a-date", "analysis_date_invalid", id="analysis-malformed"),
    ],
)
def test_candidate_buy_is_rejected_for_each_independent_gate_failure(field, value, expected_reason):
    # Keep an otherwise valid date even for bad evidence status. A date alone
    # cannot establish that the snapshot was obtained successfully.
    decision = _evaluate(candidate_rating="Buy", **{field: value})

    assert decision.final_rating == RATING_REVIEW
    assert decision.eligible is False
    assert decision.reason_codes == (expected_reason,)
    assert "review" in decision.user_message.lower()


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
def test_cli_passes_team_mode_to_graph_constructor(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    import cli.main as cli_main
    import cli.run as cli_run
    from cli import selections

    for key, value in {
        "OUTPUT_LANGUAGE": "English",
        "MAX_DEBATE_ROUNDS": "1",
        "MAX_RISK_ROUNDS": "1",
        "LLM_PROVIDER": "openai",
        "QUICK_THINK_LLM": "offline",
        "DEEP_THINK_LLM": "offline",
    }.items():
        monkeypatch.setenv(f"TRADINGAGENTS_{key}", value)
    config = {
        **cli_run.DEFAULT_CONFIG,
        "results_dir": str(tmp_path), "output_language": "English",
        "llm_provider": "openai", "backend_url": None,
        "quick_think_llm": "offline", "deep_think_llm": "offline",
    }
    monkeypatch.setattr(cli_run, "DEFAULT_CONFIG", config)
    monkeypatch.setattr(selections, "DEFAULT_CONFIG", config)
    monkeypatch.setattr(selections, "load_last_run", dict)
    monkeypatch.setattr(selections, "save_last_run", lambda _selections: None)
    monkeypatch.setattr(selections, "_check_tier_providers", lambda *_args: None)
    monkeypatch.setattr(selections.updates, "enabled", lambda: False)
    constructions = []

    class GraphReached(Exception):
        """End the test before model or data setup once the graph is constructed."""

    def graph_factory(*_args, **kwargs):
        constructions.append(kwargs)
        raise GraphReached

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", graph_factory)

    flags = [
        "--ticker", "NVDA", "--date", ANALYSIS_DATE,
        "--analysts", "market", "--no-save", "--no-show",
    ]
    runner = CliRunner()
    standard = runner.invoke(cli_main.app, flags)
    assert isinstance(standard.exception, GraphReached), standard.output
    assert constructions[0].get("decision_mode", "standard") == "standard"
    constructions.clear()

    result = runner.invoke(cli_main.app, ["--decision-mode", "team", *flags])

    assert isinstance(result.exception, GraphReached), result.output
    assert [call.get("decision_mode") for call in constructions] == ["team"]


@pytest.mark.unit
def test_cli_run_prints_gate_reason_even_without_showing_full_report(monkeypatch, tmp_path):
    from contextlib import nullcontext
    from types import SimpleNamespace

    import cli.run as cli_run
    from cli.display import MessageBuffer
    from cli.models import AnalystType

    final_state = {
        "decision_mode": "team",
        "market_report": "Market report.",
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
        },
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
            # The PM produces a candidate first. It is internal until the
            # eligibility gate completes and must not reach the live display.
            yield [], {
                "decision_mode": "team",
                "risk_debate_state": {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                },
                "final_rating": "Buy",
                "final_trade_decision": "**Rating**: Buy\n\nCandidate only.",
            }
            yield [], final_state

        def record_decision(self, *_args):
            pass

        def clear_checkpoint_on_success(self, *_args):
            pass

        def end_checkpoint(self):
            pass

    buffer = MessageBuffer()
    displayed_decisions = []
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
    monkeypatch.setattr(cli_run, "update_display", lambda *_args, **_kwargs: displayed_decisions.append(
        buffer.report_sections.get("final_trade_decision") or ""
    ))
    monkeypatch.setattr(cli_run, "_offer_reports", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_run.console, "print", lambda *args, **_kwargs: printed.append(" ".join(map(str, args))))
    monkeypatch.setattr(cli_run, "Live", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(cli_run.sys, "stdin", SimpleNamespace(isatty=lambda: True))

    cli_run.run_analysis(flags={"decision_mode": "team", "save": False, "show": False})

    output = "\n".join(printed)
    assert all("Buy" not in decision for decision in displayed_decisions)
    assert "REVIEW" in displayed_decisions[-1]
    assert "REVIEW" in output
    assert "market_evidence_unavailable" in output
    assert "critical market evidence is unavailable" in output
    assert "Buy" not in output


@pytest.mark.unit
def test_cli_displays_gate_review_and_reasons_in_final_report(monkeypatch, capsys):
    from rich.console import Console

    import cli.display as display

    monkeypatch.setattr(display, "console", Console(width=120, color_system=None))
    display.display_complete_report({
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
    graph.decision_mode = "team"
    graph.memory_log = memory
    graph._log_state = lambda _trade_date, _state: None

    graph.record_decision(
        "NVDA",
        ANALYSIS_DATE,
        {
            "decision_mode": "team",
            "final_rating": RATING_REVIEW,
            "eligibility_reason_codes": ["market_evidence_unavailable"],
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
