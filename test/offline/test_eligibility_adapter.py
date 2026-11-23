"""Trusted snapshot and failure-path integration checks for FR-D/INV-D."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.unit
def test_typed_snapshot_metadata_uses_actual_as_of_row_and_exposes_staleness(monkeypatch):
    from tradingagents.dataflows.vendors.yahoo import snapshot
    from tradingagents.enhancements.eligibility import evaluate_eligibility

    rows = pd.DataFrame({
        "Date": pd.to_datetime(["2026-01-09", "2026-01-21"]),
        "Open": [1.0, 2.0], "High": [1.0, 2.0], "Low": [1.0, 2.0],
        "Close": [1.0, 2.0], "Volume": [10, 20],
    })
    monkeypatch.setattr(
        snapshot,
        "load_ohlcv",
        lambda *_args, **_kwargs: rows.copy(),
    )

    evidence = snapshot.read_verified_market_evidence("NVDA", "2026-01-20")
    decision = evaluate_eligibility(
        decision_mode="team",
        candidate_rating="Buy",
        market_analyst_status="completed",
        market_evidence_status=evidence.status,
        snapshot_date=evidence.snapshot_date,
        analysis_date="2026-01-20",
    )

    assert evidence.status == "valid"
    assert evidence.snapshot_date == "2026-01-09"
    assert decision.final_rating == "REVIEW"
    assert decision.reason_codes == ("market_snapshot_stale",)


@pytest.mark.unit
def test_market_analyst_execution_failure_is_recorded_for_fail_closed_gate():
    from tradingagents.graph.setup import _guarded_market_analyst_node

    class BrokenAnalystGraph:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("synthetic model failure")

    guarded = _guarded_market_analyst_node(BrokenAnalystGraph(), "market_report")
    result = guarded({"company_of_interest": "NVDA", "trade_date": "2026-01-09"})

    assert result == {"market_report": "", "market_analyst_status": "failed"}


@pytest.mark.unit
def test_stale_loader_rejection_preserves_only_typed_date_for_gate(monkeypatch):
    from tradingagents.dataflows.errors import NoMarketDataError
    from tradingagents.dataflows.vendors.yahoo import ohlcv, snapshot

    rows = pd.DataFrame({"Date": pd.to_datetime(["2026-01-09"]), "Close": [100.0]})

    def rejecting_loader(symbol, as_of_date, fill_gaps=True):
        ohlcv._assert_ohlcv_not_stale(rows, as_of_date, symbol)
        pytest.fail("the upstream loader must reject this stale frame")

    monkeypatch.setattr(snapshot, "load_ohlcv", rejecting_loader)
    evidence = snapshot.read_verified_market_evidence("NVDA", "2026-01-20")

    assert evidence.snapshot_date == "2026-01-09"
    assert not hasattr(evidence, "rows")
    with pytest.raises(NoMarketDataError):
        snapshot.build_verified_market_snapshot("NVDA", "2026-01-20")


@pytest.mark.unit
def test_report_prose_cannot_replace_missing_execution_metadata():
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    graph = object.__new__(TradingAgentsGraph)
    graph.selected_analysts = ("market",)
    result = graph._eligibility_step({
        "trade_date": "2026-01-20",
        "market_report": "The market analyst claims success. Buy.",
        "market_evidence_status": "valid",
        "snapshot_date": "2026-01-20",
        "candidate_final_rating": "Buy",
        "candidate_final_trade_decision": "Buy today.",
    })

    assert result["final_rating"] == "REVIEW"
    assert result["eligibility_reason_codes"] == ["market_analyst_not_run"]
    assert "Buy" not in result["final_trade_decision"]


@pytest.mark.unit
@pytest.mark.parametrize("close", [float("inf"), float("-inf"), float("nan"), None, "not-a-price"])
def test_typed_evidence_rejects_unusable_latest_close(monkeypatch, close):
    """FR-D/INV-D: date metadata cannot authorize missing or nonfinite critical prices."""
    from tradingagents.dataflows.errors import NoMarketDataError
    from tradingagents.dataflows.vendors.yahoo import snapshot

    rows = pd.DataFrame({"Date": [pd.Timestamp("2026-01-20")], "Close": [close]})
    monkeypatch.setattr(snapshot, "load_ohlcv", lambda *_args, **_kwargs: rows.copy())

    with pytest.raises(NoMarketDataError, match="latest close is not finite"):
        snapshot.read_verified_market_evidence("NVDA", "2026-01-20")
