import logging
from collections import Counter
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_aggressive_debator,
    create_bear_researcher,
    create_bull_researcher,
    create_conservative_debator,
    create_fundamentals_analyst,
    create_market_analyst,
    create_neutral_debator,
    create_news_analyst,
    create_portfolio_manager,
    create_research_manager,
    create_sentiment_analyst,
    create_trader,
)
from tradingagents.agents.analysts.turn import WRAP_UP
from tradingagents.agents.state import AgentState

from .analyst_execution import build_analyst_execution_plan
from .conditional_logic import ConditionalLogic

logger = logging.getLogger(__name__)

# Every target a shared conditional router can return. Each edge driven by the
# router maps all of them, so a fall-through return (e.g. under prompt/i18n/
# refactor drift in the speaker labels) can never hit a missing path_map entry
# and crash LangGraph mid-run (#1088).
DEBATE_PATH_MAP = {
    "Bull Researcher": "Bull Researcher",
    "Bear Researcher": "Bear Researcher",
    "Research Manager": "Research Manager",
}
RISK_ANALYSIS_PATH_MAP = {
    "Aggressive Analyst": "Aggressive Analyst",
    "Conservative Analyst": "Conservative Analyst",
    "Neutral Analyst": "Neutral Analyst",
    "Portfolio Manager": "Portfolio Manager",
}


def _tools_or_done(state) -> str:
    """Route an analyst's turn: run its tool calls, or finish with its report."""
    return "tools" if state["messages"][-1].tool_calls else END


def _analyst_graph(spec, agent, max_tool_rounds: int):
    """One analyst as a graph of its own: the model and its tools, on a private message history.

    It returns only its report, so analysts running side by side never write the
    same key, and its tool calls never reach the other analysts' messages. After
    ``max_tool_rounds`` rounds of tool calls it is told to write its report, and
    that turn ends it whatever it answers, so a model that keeps calling tools
    cannot run the graph into its recursion limit (#1420).
    """
    output = TypedDict(f"{spec.key.capitalize()}Report", {spec.report_key: str})
    graph = StateGraph(AgentState, output_schema=output)
    graph.add_node("agent", agent)
    graph.add_edge(START, "agent")
    if not spec.tools:
        graph.add_edge("agent", END)
        return graph.compile()

    def calls(messages):
        return [call["name"] for m in messages for call in (getattr(m, "tool_calls", None) or [])]

    def rounds(messages) -> int:
        return sum(1 for m in messages if getattr(m, "tool_calls", None))

    def more_or_wrap_up(state) -> str:
        return "wrap_up" if rounds(state["messages"]) >= max_tool_rounds else "agent"

    def wrap_up(state):
        repeated = ", ".join(f"{name} x{n}" for name, n in Counter(calls(state["messages"])).most_common())
        logger.warning("%s used its %d tool rounds (%s); asking for its report",
                       spec.agent_node, max_tool_rounds, repeated)
        return agent({**state, "messages": [*state["messages"], HumanMessage(WRAP_UP)]})

    graph.add_node("tools", ToolNode(list(spec.tools)))
    graph.add_node("wrap_up", wrap_up)
    graph.add_conditional_edges("agent", _tools_or_done, ["tools", END])
    graph.add_conditional_edges("tools", more_or_wrap_up, ["agent", "wrap_up"])
    graph.add_edge("wrap_up", END)
    return graph.compile()


def _guarded_market_analyst_node(analyst_graph, report_key: str):
    """Return an FR-D wrapper that records analyst failure without a candidate call."""

    def guarded_market_analyst(state, config=None):
        try:
            result = analyst_graph.invoke(state, config=config)
        except Exception as exc:
            logger.warning(
                "Market analyst failed for %s on %s: %s",
                state.get("company_of_interest"), state.get("trade_date"), type(exc).__name__,
            )
            return {report_key: "", "market_analyst_status": "failed"}
        report = result.get(report_key) or ""
        return {
            report_key: report,
            "market_analyst_status": "completed" if report.strip() else "failed",
        }

    return guarded_market_analyst


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        conditional_logic: ConditionalLogic,
        max_tool_rounds: int,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.conditional_logic = conditional_logic
        self.max_tool_rounds = max_tool_rounds

    def setup_graph(
        self,
        selected_analysts=("market", "social", "news", "fundamentals"),
        memory_node=None,
        decision_mode: str = "standard",
        market_evidence_node=None,
        eligibility_node=None,
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Sentiment analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
            memory_node: Node that settles past decisions and returns the run's
                ``past_context``. It runs alongside the analysts.
            decision_mode: ``team`` adds typed evidence acquisition and the FR-D
                eligibility boundary; ``standard`` keeps the existing graph path.
            market_evidence_node: Deterministic typed market-data adapter for team mode.
            eligibility_node: Deterministic post-Portfolio-Manager gate for team mode.
        """
        if decision_mode not in {"standard", "team"}:
            raise ValueError("decision_mode must be 'standard' or 'team'")
        if decision_mode == "team" and (market_evidence_node is None or eligibility_node is None):
            raise ValueError("team mode requires market evidence and eligibility nodes")

        plan = build_analyst_execution_plan(selected_analysts)

        analyst_factories = {
            "market": lambda: create_market_analyst(self.quick_thinking_llm),
            "social": lambda: create_sentiment_analyst(self.quick_thinking_llm),
            "news": lambda: create_news_analyst(self.quick_thinking_llm),
            "fundamentals": lambda: create_fundamentals_analyst(self.quick_thinking_llm),
        }

        bull_researcher_node = create_bull_researcher(self.quick_thinking_llm)
        bear_researcher_node = create_bear_researcher(self.quick_thinking_llm)
        research_manager_node = create_research_manager(self.deep_thinking_llm)
        trader_node = create_trader(self.quick_thinking_llm)

        aggressive_analyst = create_aggressive_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        conservative_analyst = create_conservative_debator(self.quick_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        for spec in plan.specs:
            analyst_graph = _analyst_graph(
                spec, analyst_factories[spec.key](), self.max_tool_rounds
            )
            if decision_mode == "team" and spec.key == "market":
                workflow.add_node(
                    spec.agent_node,
                    _guarded_market_analyst_node(analyst_graph, spec.report_key),
                )
            else:
                workflow.add_node(spec.agent_node, analyst_graph)

        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Conservative Analyst", conservative_analyst)
        if decision_mode == "team":
            def candidate_portfolio_manager(state):
                """Keep the unqualified PM result internal until the FR-D gate."""
                result = portfolio_manager_node(state)
                return {
                    "risk_debate_state": result["risk_debate_state"],
                    "candidate_final_trade_decision": result["final_trade_decision"],
                    "candidate_final_rating": result["final_rating"],
                }

            workflow.add_node("Portfolio Manager", candidate_portfolio_manager)
            workflow.add_node("Eligibility Gate", eligibility_node)
        else:
            workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # The analysts work at the same time; the research debate starts once
        # every one of them has filed its report. The memory log settles past
        # decisions alongside them: only the Portfolio Manager reads its lessons.
        first_steps = [spec.agent_node for spec in plan.specs]
        if memory_node is not None:
            workflow.add_node("Memory Log", memory_node)
            first_steps.append("Memory Log")
        if decision_mode == "team":
            workflow.add_node("Market Evidence", market_evidence_node)
            first_steps.append("Market Evidence")
        for node in first_steps:
            workflow.add_edge(START, node)
        workflow.add_edge(first_steps, "Bull Researcher")

        # Both research-debate edges share the complete DEBATE_PATH_MAP (#1088).
        for debate_node in ("Bull Researcher", "Bear Researcher"):
            workflow.add_conditional_edges(
                debate_node,
                self.conditional_logic.should_continue_debate,
                DEBATE_PATH_MAP,
            )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        # All three risk edges share the complete RISK_ANALYSIS_PATH_MAP (#1088).
        for risk_node in ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"):
            workflow.add_conditional_edges(
                risk_node,
                self.conditional_logic.should_continue_risk_analysis,
                RISK_ANALYSIS_PATH_MAP,
            )

        if decision_mode == "team":
            workflow.add_edge("Portfolio Manager", "Eligibility Gate")
            workflow.add_edge("Eligibility Gate", END)
        else:
            workflow.add_edge("Portfolio Manager", END)

        return workflow
