"""The whole graph, end to end, with scripted models and no network.

Every tool-using analyst calls each of its tools once through the vendor router,
the debates and managers run, and the decision is parsed and logged. This pins
the wiring: a restructure that drops a node, a tool or an edge fails here.
"""

from __future__ import annotations

import copy
import json
import time

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field

from tradingagents.agents import context, schemas
from tradingagents.agents.analysts import sentiment_analyst
from tradingagents.dataflows import router
from tradingagents.dataflows.vendors.yahoo import market as yahoo_market, snapshot
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph import trading_graph

TRADE_DATE = "2026-01-09"

# Enough for every free-text reader: the PM's labelled rating and the trader's
# closing proposal line.
TEXT = "Report.\n\n**Rating**: Overweight\n\nFINAL TRANSACTION PROPOSAL: **BUY**"

STRUCTURED = {
    schemas.ResearchPlan: schemas.ResearchPlan(
        recommendation=schemas.PortfolioRating.OVERWEIGHT, rationale="r", strategic_actions="a"),
    schemas.TraderProposal: schemas.TraderProposal(action=schemas.TraderAction.BUY, reasoning="r"),
    # The thesis quotes another party's rating; the decision is still the PM's own.
    schemas.PortfolioDecision: schemas.PortfolioDecision(
        rating=schemas.PortfolioRating.OVERWEIGHT, executive_summary="s",
        investment_thesis="Street consensus rating: Buy (28 of 35 analysts)."),
    schemas.SentimentReport: schemas.SentimentReport(
        overall_band=schemas.SentimentBand.NEUTRAL, overall_score=5.0, confidence="low", narrative="n"),
}

ARGS = {"symbol": "NVDA", "ticker": "NVDA", "curr_date": TRADE_DATE, "start_date": "2026-01-02",
        "end_date": TRADE_DATE, "indicator": "rsi", "topic": "Fed rate cut", "freq": "quarterly"}


class ScriptedModel(BaseChatModel):
    """Calls every bound tool once, then answers with TEXT."""

    structured: bool = False
    tools: tuple = ()
    calls: list = Field(default_factory=list)   # shared across bound copies
    threads: set = Field(default_factory=set)   # threads that served a tool-bound call
    fail_at: int | None = None                  # raise on this call, once

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"tools": tuple(tools)})

    def with_structured_output(self, schema, **kwargs):
        if not self.structured:
            raise NotImplementedError
        return RunnableLambda(lambda _: self._count() or STRUCTURED[schema])

    def _count(self) -> None:
        self.calls.append(1)
        if len(self.calls) == self.fail_at:
            raise RuntimeError("provider unavailable")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self._count()
        if self.tools:
            import threading
            import time
            self.threads.add(threading.current_thread().name)
            time.sleep(0.05)   # long enough for concurrent analysts to overlap
        if self.tools and not isinstance(messages[-1], ToolMessage):
            calls = [{"name": t.name, "id": f"call_{i}",
                      "args": {k: v for k, v in ARGS.items()
                               if k in t.tool_call_schema.model_json_schema()["properties"]}}
                     for i, t in enumerate(self.tools)]
            message = AIMessage(content="", tool_calls=calls)
        else:
            message = AIMessage(content=TEXT)
        return ChatResult(generations=[ChatGeneration(message=message)])


class _Client:
    def __init__(self, model):
        self.model = model

    def get_llm(self):
        return self.model


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Every vendor answers offline; returns the set of router methods called."""
    called: set[str] = set()
    for method, vendors in router.VENDOR_METHODS.items():
        for vendor in vendors:
            monkeypatch.setitem(vendors, vendor,
                                lambda *a, _m=method, **k: called.add(_m) or f"{_m} data")
    prices = pd.DataFrame({
        "Date": pd.bdate_range(end=TRADE_DATE, periods=60),
        "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5, "Volume": 1_000_000,
    })
    monkeypatch.setattr(snapshot, "load_ohlcv",
                        lambda *a, **k: called.add("ohlcv") or prices.copy())
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages", lambda *a, **k: "no posts")
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts", lambda *a, **k: "no posts")
    monkeypatch.setattr(yahoo_market.yf, "Ticker", lambda s: type("T", (), {"info": {"longName": "NVIDIA"}})())
    context._identity.cache_clear()
    return called


def _graph(tmp_path, monkeypatch, model, debug=False, **config):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    decision_mode = config.pop("decision_mode", None)
    selected_analysts = config.pop(
        "selected_analysts", ("market", "social", "news", "fundamentals")
    )
    cfg.update(results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
               memory_log_path=str(tmp_path / "log.md"), **config)
    monkeypatch.setattr(trading_graph, "create_tier_client", lambda config, tier, **k: _Client(model))
    graph_kwargs = {"config": cfg, "debug": debug}
    if decision_mode is not None:
        graph_kwargs["decision_mode"] = decision_mode
    return trading_graph.TradingAgentsGraph(selected_analysts, **graph_kwargs)


@pytest.mark.unit
@pytest.mark.parametrize("structured", [False, True], ids=["free-text", "structured"])
def test_a_full_run_reaches_a_logged_decision(tmp_path, monkeypatch, offline, structured):
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=structured))

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == "Overweight"
    for key in ("market_report", "sentiment_report", "news_report", "fundamentals_report",
                "investment_plan", "trader_investment_plan", "final_trade_decision"):
        assert state[key].strip(), key
    tool_methods = {"get_stock_data", "get_indicators", "get_news", "get_global_news",
                    "get_macro_indicators", "get_prediction_markets", "get_fundamentals",
                    "get_balance_sheet", "get_cashflow", "get_income_statement",
                    "get_insider_transactions", "ohlcv"}
    assert offline == tool_methods
    assert [e["rating"] for e in graph.memory_log.load_entries()] == ["Overweight"]


@pytest.mark.unit
def test_team_mode_graph_accepts_valid_market_evidence_and_allowed_rating(
    tmp_path, monkeypatch, offline,
):
    load_prices = snapshot.load_ohlcv
    monkeypatch.setattr(snapshot, "load_ohlcv", lambda *args, **kwargs: load_prices(*args, **kwargs).iloc[:-1])
    graph = _graph(
        tmp_path, monkeypatch, ScriptedModel(structured=True), decision_mode="team"
    )

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == "Overweight"
    assert "ohlcv" in offline
    assert state["market_analyst_status"] == "completed"
    assert state["market_evidence_status"] == "valid"
    assert state["snapshot_date"] == "2026-01-08"
    assert state["eligibility_reason_codes"] == []


@pytest.fixture
def model_buy(monkeypatch):
    candidate_text = "PM candidate only: Buy based on the analyst narrative."
    monkeypatch.setitem(
        STRUCTURED,
        schemas.PortfolioDecision,
        schemas.PortfolioDecision(
            rating=schemas.PortfolioRating.BUY,
            executive_summary="Candidate Buy",
            investment_thesis=candidate_text,
        ),
    )
    return candidate_text


@pytest.mark.unit
def test_team_mode_gate_rejects_model_buy_when_verified_market_data_is_unavailable(
    tmp_path, monkeypatch, offline, model_buy,
):
    from tradingagents.dataflows.errors import VendorUnavailableError

    def unavailable(*_args, **_kwargs):
        raise VendorUnavailableError("synthetic offline failure")

    monkeypatch.setattr(snapshot, "load_ohlcv", unavailable)
    graph = _graph(
        tmp_path, monkeypatch, ScriptedModel(structured=True), decision_mode="team"
    )

    state, signal = graph.propagate("NVDA", TRADE_DATE)
    report = graph.save_reports(state, "NVDA", tmp_path / "report", html=True)
    state_log = next((tmp_path / "results" / "NVDA" / "TradingAgentsStrategy_logs").glob("*.json"))
    logged = json.loads(state_log.read_text(encoding="utf-8"))
    markdown = report.read_text(encoding="utf-8")
    html = (tmp_path / "report" / "complete_report.html").read_text(encoding="utf-8")

    assert signal == state["final_rating"] == "REVIEW"
    assert "market_evidence_unavailable" in state["eligibility_reason_codes"]
    assert "Buy" not in state["final_trade_decision"]
    assert model_buy not in state["final_trade_decision"]
    assert logged["final_rating"] == "REVIEW"
    assert "market_evidence_unavailable" in logged["eligibility_reason_codes"]
    for output in (markdown, html):
        assert "REVIEW" in output
        assert "market_evidence_unavailable" in output
        assert "Buy" not in output
    assert graph.memory_log.get_pending_entries() == []


@pytest.mark.unit
def test_team_mode_stream_never_publishes_buy_before_gate_replaces_it_with_review(
    tmp_path, monkeypatch, offline, model_buy,
):
    from tradingagents.dataflows.errors import VendorUnavailableError

    def unavailable(*_args, **_kwargs):
        raise VendorUnavailableError("synthetic offline failure")

    monkeypatch.setattr(snapshot, "load_ohlcv", unavailable)
    graph = _graph(
        tmp_path, monkeypatch, ScriptedModel(structured=True), decision_mode="team"
    )

    initial = graph.create_run_state("NVDA", TRADE_DATE)
    decisions = []
    for messages, state in graph.stream_run(
        graph.checkpoint_input(initial), **graph.propagator.get_graph_args()
    ):
        assert all(model_buy not in str(message.content) for message in messages)
        if state:
            assert not state.get("trader_investment_plan")
            assert "candidate_final_rating" not in state
            assert "candidate_final_trade_decision" not in state
        if state and (state.get("final_rating") or state.get("final_trade_decision")):
            assert state["final_rating"] == "REVIEW"
            assert "REVIEW" in state["final_trade_decision"]
            assert "Buy" not in state["final_trade_decision"]
            assert "market_evidence_unavailable" in state["eligibility_reason_codes"]
            decisions.append(state["final_rating"])

    assert decisions


@pytest.mark.unit
@pytest.mark.parametrize("close, expected", [
    pytest.param(float("inf"), "REVIEW", id="positive-inf"),
    pytest.param(float("-inf"), "REVIEW", id="negative-inf"),
    pytest.param(100.5, "Buy", id="finite-control"),
])
def test_team_gate_validates_close_through_real_loader(
    tmp_path, monkeypatch, offline, model_buy, close, expected,
):
    """FR-D/NFR-D/INV-D: actual loader rows with invalid prices cannot authorize Buy."""
    from tradingagents.dataflows.vendors.yahoo import ohlcv

    class VendorTicker:
        info = {"longName": "NVIDIA"}

        def history(self, **_kwargs):
            return pd.DataFrame({
                "Open": [100.0, 100.0], "High": [101.0, 101.0], "Low": [99.0, 99.0],
                "Close": [100.5, close], "Volume": [1000, 1000],
            }, index=pd.DatetimeIndex(["2026-01-08", TRADE_DATE], name="Date"))

    monkeypatch.setattr(ohlcv.yf, "Ticker", lambda _symbol: VendorTicker())
    monkeypatch.setattr(snapshot, "load_ohlcv", ohlcv.load_ohlcv)
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True), decision_mode="team")

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == expected
    if expected == "REVIEW":
        assert state["market_evidence_status"] == "unavailable"
        assert "market_evidence_unavailable" in state["eligibility_reason_codes"]
        assert "Buy" not in state["final_trade_decision"]
        assert graph.memory_log.get_pending_entries() == []
    else:
        assert state["market_evidence_status"] == "valid"
        assert state["snapshot_date"] == TRADE_DATE
        assert state["eligibility_reason_codes"] == []
        assert [entry["rating"] for entry in graph.memory_log.get_pending_entries()] == ["Buy"]


@pytest.mark.unit
@pytest.mark.parametrize("own_rating", ["Rating: Strong Buy", "No own rating was supplied."])
@pytest.mark.parametrize("mode, expected", [("team", "REVIEW"), ("standard", "Buy")])
def test_free_text_own_rating_cannot_be_replaced_by_consensus(
    tmp_path, monkeypatch, offline, own_rating, mode, expected,
):
    """FR-D/NFR-D/BASE-01: team fails closed; standard retains heuristic parsing."""
    monkeypatch.setitem(globals(), "TEXT", f"{own_rating}\n\nConsensus rating: Buy")
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(), decision_mode=mode)

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == expected
    if mode == "team":
        assert state["market_evidence_status"] == "valid"
        assert state["eligibility_reason_codes"] == ["invalid_rating"]
        assert "Buy" not in state["final_trade_decision"]
        assert graph.memory_log.get_pending_entries() == []
    else:
        assert [entry["rating"] for entry in graph.memory_log.get_pending_entries()] == ["Buy"]


@pytest.mark.unit
@pytest.mark.parametrize("pm_text, expected", [
    pytest.param("Example only:\n\n    Rating: Buy", "REVIEW", id="indented-code"),
    pytest.param("Example only:\n\n~~~text\n```\nRating: Buy\n~~~", "REVIEW", id="mixed-fence"),
    pytest.param("Example only:\n\n```text\nRating: Buy\n```", "REVIEW", id="ordinary-fence"),
    pytest.param(
        "Rating: Strong Buy\n`example\ncontinued`\n\nRating: Buy",
        "REVIEW",
        id="invalid-own-rating-before-multiline-code-and-later-buy",
    ),
    pytest.param(
        "Rating: Hold\n`example\ncontinued`",
        "Hold",
        id="valid-own-rating-with-multiline-code-in-paragraph",
    ),
    pytest.param("~~~text\n```\nRating: Buy\n~~~~\n\n**Rating**: Hold", "Hold", id="real-rating"),
])
def test_team_graph_distinguishes_markdown_examples_from_own_rating(
    tmp_path, monkeypatch, offline, pm_text, expected,
):
    """FR-D/NFR-D/INV-D: code examples cannot publish or settle as a PM decision."""
    monkeypatch.setitem(globals(), "TEXT", pm_text)
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(), decision_mode="team")

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert state["market_evidence_status"] == "valid"
    assert signal == state["final_rating"] == expected
    pending = graph.memory_log.get_pending_entries()
    if expected == "REVIEW":
        assert state["eligibility_reason_codes"] == ["invalid_rating"]
        assert "Rating: Buy" not in state["final_trade_decision"]
        assert pending == []
    else:
        assert state["eligibility_reason_codes"] == []
        assert [entry["rating"] for entry in pending] == ["Hold"]


@pytest.mark.unit
def test_team_stream_releases_trader_proposal_only_after_positive_qualification(
    tmp_path, monkeypatch, offline,
):
    """FR-D/INV-D: withholding must still release an eligible proposal after the gate."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True), decision_mode="team")
    published = []
    for _messages, state in graph.stream_run(
        graph.create_run_state("NVDA", TRADE_DATE), **graph.propagator.get_graph_args()
    ):
        if state and state.get("trader_investment_plan"):
            assert state["eligibility_checked"] is True
            assert state["eligibility_status"] == "eligible"
            assert state["final_rating"] == "Overweight"
            published.append(state["trader_investment_plan"])
    assert published


@pytest.mark.unit
@pytest.mark.parametrize("policy_suffix", ["", "|eligibility=v2", "|eligibility=v3"], ids=["v1", "v2", "v3"])
def test_team_run_does_not_resume_a_pre_fix_portfolio_candidate(tmp_path, monkeypatch, offline, policy_suffix):
    """NFR-D/INV-D: recovery cannot skip the corrected evidence and rating checks."""
    from tradingagents.dataflows.errors import VendorUnavailableError
    from tradingagents.graph.checkpointer import get_checkpointer, thread_id

    standard = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True), checkpoint_enabled=True)
    # Earlier signatures could persist a candidate without the current checks.
    legacy_signature = standard._run_signature("stock") + "|decision_mode=team" + policy_suffix
    graph = _graph(
        tmp_path, monkeypatch, ScriptedModel(structured=True), checkpoint_enabled=True, decision_mode="team",
    )
    legacy_config = {"configurable": {"thread_id": thread_id("NVDA", TRADE_DATE, legacy_signature)}}
    with get_checkpointer(graph.config["data_cache_dir"], "NVDA") as saver:
        old_graph = graph.workflow.compile(checkpointer=saver)
        old_graph.update_state(legacy_config, {
            **graph.create_run_state("NVDA", TRADE_DATE),
            "market_analyst_status": "completed",
            "market_evidence_status": "valid",
            "snapshot_date": TRADE_DATE,
            "investment_plan": "Earlier research plan.",
            "trader_investment_plan": "**Action**: Buy",
            "candidate_final_rating": "Buy",
            "candidate_final_trade_decision": "Rating: Buy",
        }, as_node="Portfolio Manager")
        assert old_graph.get_state(legacy_config).next == ("Eligibility Gate",)

    def unavailable(*_args, **_kwargs):
        raise VendorUnavailableError("synthetic offline failure")

    monkeypatch.setattr(snapshot, "load_ohlcv", unavailable)
    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == "REVIEW"
    assert state["eligibility_reason_codes"] == ["market_evidence_unavailable"]
    assert graph.memory_log.get_pending_entries() == []


@pytest.mark.unit
def test_team_mode_with_no_market_analyst_fails_closed_as_review(tmp_path, monkeypatch, offline, model_buy):
    graph = _graph(
        tmp_path,
        monkeypatch,
        ScriptedModel(structured=True),
        decision_mode="team",
        selected_analysts=("news",),
    )

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == state["final_rating"] == "REVIEW"
    assert "market_analyst_not_run" in state["eligibility_reason_codes"]
    assert "Buy" not in state["final_trade_decision"]
    assert model_buy not in state["final_trade_decision"]
    assert graph.memory_log.get_pending_entries() == []


@pytest.mark.unit
def test_an_interrupted_run_resumes_from_its_checkpoint(tmp_path, monkeypatch, offline):
    model = ScriptedModel(fail_at=12)            # past the analysts, before the decision
    graph = _graph(tmp_path, monkeypatch, model, checkpoint_enabled=True)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        graph.propagate("NVDA", TRADE_DATE)
    calls_before = len(model.calls)

    _, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == "Overweight"
    resumed_calls = len(model.calls) - calls_before
    full_run = ScriptedModel()
    _graph(tmp_path / "fresh", monkeypatch, full_run).propagate("NVDA", TRADE_DATE)
    # The resumed run makes only the calls the interrupted one had not completed.
    assert resumed_calls == len(full_run.calls) - (model.fail_at - 1)


@pytest.mark.unit
def test_a_graph_reused_across_runs_keeps_no_run_state(tmp_path, monkeypatch, offline):
    """A backtest reuses one graph over its whole grid; holding every run's full
    state would grow without bound."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel())
    for trade_date in ("2026-01-08", TRADE_DATE):
        graph.propagate("NVDA", trade_date)

    held = [v for v in vars(graph).values() if isinstance(v, dict) and TRADE_DATE in v]
    assert held == []
    assert len(list(tmp_path.glob("results/NVDA/TradingAgentsStrategy_logs/*.json"))) == 2


@pytest.mark.unit
def test_the_analysts_run_at_the_same_time(tmp_path, monkeypatch, offline):
    model = ScriptedModel()
    graph = _graph(tmp_path, monkeypatch, model)

    assert not [n for n in graph.graph.get_graph().nodes if n.startswith("Msg Clear")]
    graph.propagate("NVDA", TRADE_DATE)

    assert len(model.threads) > 1


@pytest.mark.unit
def test_a_debug_run_prints_the_analysts_work_and_reaches_the_same_decision(tmp_path, monkeypatch, offline, capsys):
    """Debug mode streams the analysts' own graphs, so their tool calls still print."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(), debug=True)

    state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert signal == "Overweight"
    assert state["market_report"].strip() and state["fundamentals_report"].strip()
    printed = capsys.readouterr().out
    assert "get_stock_data" in printed and "get_balance_sheet" in printed


@pytest.mark.unit
def test_each_report_streams_as_soon_as_its_analyst_files_it(tmp_path, monkeypatch, offline):
    """The main state takes the analysts' reports only when the slowest one is
    done; the CLI shows each report, and stops each clock, as it lands."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel())
    reports = ("market_report", "sentiment_report", "news_report", "fundamentals_report")

    first = next(state for _, state in graph.stream_run(graph.create_run_state("NVDA", TRADE_DATE),
                                                        **graph.propagator.get_graph_args())
                 if state and any(state.get(k) for k in reports))

    assert sum(bool(first.get(k)) for k in reports) == 1


@pytest.mark.unit
def test_a_streamed_run_reads_its_own_graph_config(tmp_path, monkeypatch, offline):
    """The CLI streams the run; a process-wide config set elsewhere must not reach
    its tools, and the graph's config must not reach the caller between steps."""
    from tradingagents.dataflows.config import get_config, set_config

    graph = _graph(tmp_path, monkeypatch, ScriptedModel(), output_language="French")
    set_config({"output_language": "German"})
    seen = []
    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance",
                        lambda *a, **k: seen.append(get_config()["output_language"]) or "prices")

    between = [get_config()["output_language"]
               for _ in graph.stream_run(graph.create_run_state("NVDA", TRADE_DATE), **graph.propagator.get_graph_args())]

    assert seen and set(seen) == {"French"}
    assert set(between) == {"German"}


class LoopingModel(ScriptedModel):
    """Calls a tool on every turn it is offered one (#1420)."""

    tool_turns: list = Field(default_factory=list)    # shared across bound copies
    last_turns: list = Field(default_factory=list)    # histories of the turns offered no tools

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if not self.tools:
            self.last_turns.append(messages)
            return super()._generate(messages, stop, run_manager, **kwargs)
        self.tool_turns.append(1)
        tool = self.tools[0]
        call = {"name": tool.name, "id": f"call_{len(self.tool_turns)}",
                "args": {k: v for k, v in ARGS.items()
                         if k in tool.tool_call_schema.model_json_schema()["properties"]}}
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[call]))])


@pytest.mark.unit
def test_an_analyst_that_keeps_calling_tools_writes_its_report_at_the_limit(tmp_path, monkeypatch, offline):
    """A model that does not stop calling tools must not end the run (#1420)."""
    model = LoopingModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model, max_tool_rounds=3)

    final_state, rating = graph.propagate("NVDA", TRADE_DATE)

    assert len(model.tool_turns) == 3 * 3   # three tool-using analysts, three rounds each
    for key in ("market_report", "news_report", "fundamentals_report"):
        assert final_state[key] == TEXT
    assert rating == "Overweight"


@pytest.mark.unit
def test_the_last_turn_is_offered_no_tools_and_reads_its_tool_results_as_text(tmp_path, monkeypatch, offline):
    """Offered tools, a model may call one whatever it is told; a history holding
    tool calls may be refused by a provider when no tools are bound."""
    model = LoopingModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model, max_tool_rounds=2)

    graph.propagate("NVDA", TRADE_DATE)

    wrap_ups = [h for h in model.last_turns if isinstance(h[-1], HumanMessage) and "tool round" in h[-1].content]
    assert len(wrap_ups) == 3
    for history in wrap_ups:
        assert not any(isinstance(m, ToolMessage) or getattr(m, "tool_calls", None) for m in history)
        assert any("returned]" in str(m.content) for m in history)
        assert "tool rounds are spent" in history[0].content   # the system prompt lists no tools


@pytest.mark.unit
def test_a_tool_limit_the_recursion_limit_cannot_hold_is_refused(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="max_tool_rounds"):
        _graph(tmp_path, monkeypatch, ScriptedModel(), max_tool_rounds=60, max_recur_limit=100)


class TimedModel(ScriptedModel):
    """ScriptedModel that records each call's graph step, prompt and timing."""

    seen: list = Field(default_factory=list)    # shared across bound copies

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        step = (run_manager.metadata or {}).get("langgraph_node") if run_manager else None
        started = time.monotonic()
        if step in {"Market Analyst", "agent"} or step == "Memory Log":
            time.sleep(0.2)                     # long enough to see what overlaps
        result = super()._generate(messages, stop, run_manager, **kwargs)
        prompt = "\n".join(str(m.content) for m in messages)
        self.seen.append((step, prompt, started, time.monotonic()))
        return result


@pytest.mark.unit
def test_past_decisions_settle_alongside_the_analysts(tmp_path, monkeypatch, offline):
    from tradingagents.memory import settlement

    model = TimedModel()
    graph = _graph(tmp_path, monkeypatch, model)
    graph.memory_log.store_decision("NVDA", "2025-12-31", "Rating: Buy\n\nBuy NVDA.")
    closes = pd.Series([100.0 + i for i in range(10)], index=pd.bdate_range("2026-01-02", periods=10))
    monkeypatch.setattr(settlement, "get_closes", lambda *a, **k: closes)

    graph.propagate("NVDA", TRADE_DATE)

    reflections = [c for c in model.seen if c[0] == "Memory Log"]
    assert len(reflections) == 1                # settled once, inside the run
    analyst_turns = [c for c in model.seen if c[0] == "agent"]
    assert reflections[0][2] < max(c[3] for c in analyst_turns), "settled before the analysts, not alongside"
    settled = next(e for e in graph.memory_log.load_entries() if e["date"] == "2025-12-31")
    assert not settled["pending"]
    lessons = graph.memory_log.get_past_context("NVDA", as_of=TRADE_DATE)
    assert lessons
    pm_prompt = next(c[1] for c in model.seen if c[0] == "Portfolio Manager")
    assert lessons in pm_prompt


@pytest.mark.unit
def test_a_settlement_failure_is_noted_and_the_run_goes_on(tmp_path, monkeypatch, offline):
    """The analysts have spent their tokens by the time the join waits on settlement."""
    from tradingagents.reporting import write_report_tree

    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))

    def locked():
        raise OSError("memory log is locked")

    monkeypatch.setattr(graph, "settle_all_pending", locked)
    final_state, rating = graph.propagate("NVDA", TRADE_DATE)

    assert rating == "Overweight"
    assert "could not be settled" in final_state["memory_note"]
    report = write_report_tree(final_state, "NVDA", tmp_path / "report").read_text()
    assert "Memory log: Past decisions could not be settled" in report


@pytest.mark.unit
def test_the_run_settles_other_tickers_due_decisions_too(tmp_path, monkeypatch, offline):
    """A ticker a scheduler stopped analysing still gets its decisions settled (#1445)."""
    from tradingagents.memory import settlement

    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    graph.memory_log.store_decision("MSFT", "2026-01-02", "Rating: Buy\n\nBuy MSFT.")
    closes = pd.Series([100.0 + i for i in range(10)], index=pd.bdate_range("2026-01-02", periods=10))
    monkeypatch.setattr(settlement, "get_closes", lambda *a, **k: closes)

    graph.propagate("NVDA", TRADE_DATE)

    msft = next(e for e in graph.memory_log.load_entries() if e["ticker"] == "MSFT")
    assert not msft["pending"]


@pytest.mark.unit
def test_the_memory_step_reads_lessons_as_of_the_trade_date_and_settles_once(tmp_path, monkeypatch, offline):
    """A past-dated run reads only lessons known by its date (#1251); a resumed run
    that re-runs the step settles nothing twice."""
    from tradingagents.memory import settlement

    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    graph.memory_log.store_decision("NVDA", "2025-12-31", "Rating: Buy\n\nBuy NVDA.")
    closes = pd.Series([100.0 + i for i in range(10)], index=pd.bdate_range("2026-01-02", periods=10))
    monkeypatch.setattr(settlement, "get_closes", lambda *a, **k: closes)
    asked = []
    real = graph.memory_log.get_past_context
    monkeypatch.setattr(graph.memory_log, "get_past_context",
                        lambda ticker, as_of=None, **k: asked.append(as_of) or real(ticker, as_of=as_of, **k))
    state = {"company_of_interest": "NVDA", "trade_date": "2026-01-20"}

    graph._memory_step(state)
    log_after_first = (tmp_path / "log.md").read_text()
    graph._memory_step(state)

    assert asked == ["2026-01-20", "2026-01-20"]
    assert (tmp_path / "log.md").read_text() == log_after_first
