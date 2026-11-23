"""Tests for :func:`merge_once` (FR-B-3/4/5/6, INV-B-1/4).

All tests inject a mock ``llm`` (``callable(prompt) -> str``) so no network or
real model is used. The mock returns a suggested merge; the deterministic
validator remains the authority over what is emitted.
"""

from __future__ import annotations

import json

import pytest

from event_merge.evidence import EvidenceRegistry
from event_merge.merger import merge_once
from event_merge.schemas import MergeStatus

TICKERS = ["AAPL", "MSFT", "TSLA"]
WINDOW = ("2026-11-15", "2026-11-22")


@pytest.fixture
def records():
    """Three issued records across three tickers (AAPL/MSFT share an event)."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue(
        "AAPL", "2026-11-15", "Reuters", "Apple and Microsoft partner on AI chip"
    )
    msft = registry.issue(
        "MSFT", "2026-11-16", "Bloomberg", "Microsoft and Apple announce AI chip deal"
    )
    tsla = registry.issue("TSLA", "2026-11-17", "CNBC", "Tesla delivers record vehicles")
    return [aapl, msft, tsla], aapl, msft, tsla


def _merged_json(aapl, msft, tsla) -> str:
    return json.dumps(
        {
            "events": [
                {
                    "event_id": "e1",
                    "summary": "Apple-Microsoft AI chip partnership",
                    "tickers": ["AAPL", "MSFT"],
                    "evidence_ids": [aapl.evidence_id, msft.evidence_id],
                }
            ],
            "unmerged_evidence_ids": [tsla.evidence_id],
        }
    )


@pytest.mark.offline
def test_single_llm_call(records):
    """FR-B-3 / INV-B-1: exactly one LLM call, receiving the full record set."""
    records_list, aapl, msft, tsla = records
    calls = []

    def llm(prompt):
        calls.append(prompt)
        return _merged_json(aapl, msft, tsla)

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert len(calls) == 1
    assert result.status is MergeStatus.MERGED
    prompt = calls[0]
    for record in records_list:
        assert record.evidence_id in prompt


@pytest.mark.offline
def test_legal_merge_is_accepted(records):
    """FR-B-4: a two-ticker event with valid evidence is returned verbatim."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return _merged_json(aapl, msft, tsla)

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.MERGED
    assert len(result.events) == 1
    event = result.events[0]
    assert set(event.tickers) == {"AAPL", "MSFT"}
    assert {e.evidence_id for e in event.evidence} == {aapl.evidence_id, msft.evidence_id}
    assert [r.evidence_id for r in result.unmerged] == [tsla.evidence_id]


@pytest.mark.offline
def test_llm_raises_fail_closed(records):
    """RP-B-003: an LLM exception fails closed — no verified facts emitted."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        raise RuntimeError("model unavailable")

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.NO_COMMON_EVENT
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {
        r.evidence_id for r in records_list
    }


@pytest.mark.offline
def test_json_parse_failure_degrades(records):
    """RP-B-004: unparseable output degrades conservatively, no events emitted."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return "not json at all"

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.NO_COMMON_EVENT
    assert result.events == []


@pytest.mark.offline
def test_no_records_data_unavailable():
    """FR-B-6 / RP-B-001: empty records -> data_unavailable, no LLM call."""
    calls = []

    def llm(prompt):
        calls.append(prompt)
        return "{}"

    result = merge_once([], TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.DATA_UNAVAILABLE
    assert result.events == []
    assert calls == []


@pytest.mark.offline
def test_records_but_no_events_no_common_event(records):
    """FR-B-6 / RP-B-007: records exist but no common event -> no_common_event."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return json.dumps(
            {
                "events": [],
                "unmerged_evidence_ids": [
                    aapl.evidence_id,
                    msft.evidence_id,
                    tsla.evidence_id,
                ],
            }
        )

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.NO_COMMON_EVENT
    assert result.events == []


@pytest.mark.offline
def test_forged_id_removed_by_validator(records):
    """FR-B-7 / NFR-B-2: a forged evidence ID is dropped, never verified."""
    records_list, aapl, msft, tsla = records
    forged = "ev-run123-FAKE-0"

    def llm(prompt):
        return json.dumps(
            {
                "events": [
                    {
                        "event_id": "e1",
                        "summary": "AI chip deal",
                        "tickers": ["AAPL", "MSFT"],
                        "evidence_ids": [aapl.evidence_id, msft.evidence_id, forged],
                    }
                ],
                "unmerged_evidence_ids": [],
            }
        )

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.MERGED
    event = result.events[0]
    ids = {e.evidence_id for e in event.evidence}
    assert forged not in ids
    assert ids == {aapl.evidence_id, msft.evidence_id}
    dropped = [d for d in result.dropped_invalid if d.evidence_id == forged]
    assert len(dropped) == 1
    assert dropped[0].reason == "forged_or_cross_run_id"


@pytest.mark.offline
def test_inv_b1_second_call_is_forbidden(records):
    """INV-B-1 (violation -> fails): a second LLM call raises, test fails."""
    records_list, aapl, msft, tsla = records
    calls = []

    def llm(prompt):
        calls.append(prompt)
        if len(calls) > 1:
            raise AssertionError("merge_once invoked the LLM more than once")
        return _merged_json(aapl, msft, tsla)

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.MERGED
    assert len(calls) == 1


@pytest.mark.offline
def test_inv_b4_insufficient_evidence_not_forced(records):
    """INV-B-4 (violation -> fails): a single-record event is not emitted."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        # Model tries to force a single-record "event".
        return json.dumps(
            {
                "events": [
                    {
                        "event_id": "e1",
                        "summary": "forced single-record event",
                        "evidence_ids": [aapl.evidence_id],
                    }
                ],
                "unmerged_evidence_ids": [msft.evidence_id, tsla.evidence_id],
            }
        )

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.events == []
    unmerged_ids = {r.evidence_id for r in result.unmerged}
    assert aapl.evidence_id in unmerged_ids
    assert unmerged_ids == {aapl.evidence_id, msft.evidence_id, tsla.evidence_id}
