"""Tests for the B-module single-module core (``tradingagents.enhancements.events``).

Covers FR-B-1 through FR-B-7, NFR-B-1/2 and the invariants INV-B-1/2/3/4/5. All
tests inject mock ``fetcher`` / ``llm`` callables so no network, upstream
dependency or real model is ever used. Every invariant has at least one
"violation -> fails" test.
"""

from __future__ import annotations

import json

import pytest

from tradingagents.enhancements.events import (
    MAX_RECORDS_PER_TICKER,
    EvidenceRegistry,
    MergeStatus,
    NewsRecord,
    build_window,
    fetch_records,
    merge_once,
    validate,
)

TICKERS = ["AAPL", "MSFT", "TSLA"]
WINDOW = ("2026-11-15", "2026-11-22")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reg():
    """A run with three issued records (AAPL, MSFT, TSLA)."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple beats estimates")
    msft = registry.issue("MSFT", "2026-11-16", "Bloomberg", "Microsoft cloud growth")
    tsla = registry.issue("TSLA", "2026-11-17", "CNBC", "Tesla deliveries")
    return registry, aapl, msft, tsla


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


def _article(i: int, ticker: str | None = None, pub_date: str = "2026-11-15") -> dict:
    return {
        "title": f"{ticker or 'T'} headline {i}",
        "summary": f"snippet body {i}",
        "publisher": "Reuters",
        "link": f"https://example.com/{i}",
        "pub_date": f"{pub_date}T09:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# build_window (FR-B-1)
# ---------------------------------------------------------------------------


def test_build_window_two_tickers_success():
    """FR-B-1: 2 tickers within a 7-day window succeed."""
    start, end = build_window(["AAPL", "MSFT"], "2026-11-22", 7)
    assert start == "2026-11-15"
    assert end == "2026-11-22"


def test_build_window_three_tickers_success():
    """FR-B-1: 3 tickers succeed."""
    start, end = build_window(["AAPL", "MSFT", "TSLA"], "2026-11-22", 1)
    assert start == "2026-11-21"
    assert end == "2026-11-22"


def test_build_window_one_ticker_fails():
    """FR-B-1: a single ticker is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL"], "2026-11-22", 7)


def test_build_window_four_tickers_fail():
    """FR-B-1: more than 3 tickers are rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT", "TSLA", "NVDA"], "2026-11-22", 7)


def test_build_window_lookback_greater_than_seven_fails():
    """FR-B-1: a look-back window longer than 7 days is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT"], "2026-11-22", 8)


def test_build_window_lookback_zero_fails():
    """FR-B-1: a look-back window shorter than 1 day is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT"], "2026-11-22", 0)


# ---------------------------------------------------------------------------
# fetch_records (FR-B-2)
# ---------------------------------------------------------------------------


def test_fetch_records_truncated_to_five_per_ticker():
    """FR-B-2: a vendor returning 20 records is truncated to <=5 per ticker."""

    def fetcher(ticker, start, end):
        return [_article(i, ticker) for i in range(20)]

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    aapl = [r for r in result if r.ticker == "AAPL"]
    msft = [r for r in result if r.ticker == "MSFT"]
    assert len(aapl) == MAX_RECORDS_PER_TICKER
    assert len(msft) == MAX_RECORDS_PER_TICKER
    assert len(result) == 2 * MAX_RECORDS_PER_TICKER


def test_fetch_records_evidence_ids_assigned_and_unique():
    """FR-B-2 / NFR-B-1: every record gets a run-unique evidence ID."""

    def fetcher(ticker, start, end):
        return [_article(i, ticker) for i in range(5)]

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    ids = [r.evidence_id for r in result]
    assert len(ids) == len(set(ids)) == 10
    for record in result:
        assert record.evidence_id.startswith("ev-")
        assert f"-{record.ticker}-" in record.evidence_id


def test_fetch_records_fields_complete():
    """FR-B-2: title/snippet/source/date/pub_date are all populated."""

    def fetcher(ticker, start, end):
        return [_article(0, ticker)]

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert len(result) == 2
    for record in result:
        assert record.title
        assert record.snippet
        assert record.source
        assert record.date
        assert record.pub_date


def test_fetch_records_empty_fetcher():
    """FR-B-6: a fetcher returning nothing yields an empty record list."""

    def fetcher(ticker, start, end):
        return []

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert result == []


def test_fetch_records_normalizes_upstream_shape():
    """FR-B-2: the upstream (summary/publisher/datetime) shape is normalised."""

    def fetcher(ticker, start, end):
        return [
            {
                "title": "headline",
                "summary": "summary text",
                "publisher": "Yahoo Finance",
                "link": "https://example.com",
                "pub_date": "2026-11-15T09:00:00+00:00",
            }
        ]

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert len(result) == 2
    for record in result:
        assert record.snippet == "summary text"
        assert record.source == "Yahoo Finance"
        assert record.date == "2026-11-15"


def test_fetch_records_filters_out_of_window_before_limit():
    """FR-B-1: future/out-of-window records are dropped before the per-ticker limit.

    Reproduces the reported bug: the first 5 records are future-dated
    (2026-11-23, outside 2026-11-15..2026-11-22) and only the 6th is in-window.
    Without window-first filtering the future records would occupy the budget
    and cut the legitimate in-window record.
    """

    def fetcher(ticker, start, end):
        records = [_article(i, ticker, pub_date="2026-11-23") for i in range(5)]
        records.append(_article(5, ticker, pub_date="2026-11-20"))
        return records

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert {r.date for r in result} == {"2026-11-20"}
    assert all(r.date != "2026-11-23" for r in result)
    assert [r.ticker for r in result] == ["AAPL", "MSFT"]


def test_fetch_records_deduplicates_identical_articles():
    """FR-B-2: identical (title, source, date) articles are collapsed."""

    def fetcher(ticker, start, end):
        return [
            _article(0, ticker, pub_date="2026-11-16"),
            _article(0, ticker, pub_date="2026-11-16"),
            _article(1, ticker, pub_date="2026-11-17"),
        ]

    result = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    aapl = [r for r in result if r.ticker == "AAPL"]
    assert len(aapl) == 2
    titles = {r.title for r in aapl}
    assert titles == {"AAPL headline 0", "AAPL headline 1"}


# ---------------------------------------------------------------------------
# EvidenceRegistry (FR-B-2 / NFR-B-1/2 / INV-B-3)
# ---------------------------------------------------------------------------


def test_registry_issue_canonical_id_format():
    """FR-B-2: evidence_id == ev-{run_id}-{ticker}-{seq}."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    record = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple earnings")
    assert record.evidence_id == "ev-a1b2c3d4-AAPL-0"
    assert record.ticker == "AAPL"


def test_registry_issue_sequence_increments_per_ticker():
    """FR-B-2: seq is 0-based and increments within the same ticker."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    first = registry.issue("AAPL", "2026-11-15", "Reuters", "t0")
    second = registry.issue("AAPL", "2026-11-15", "Reuters", "t1")
    assert first.evidence_id == "ev-a1b2c3d4-AAPL-0"
    assert second.evidence_id == "ev-a1b2c3d4-AAPL-1"


def test_registry_issue_ids_unique_within_run():
    """NFR-B-1: every issued ID is unique across tickers within one run."""
    registry = EvidenceRegistry()
    seen: set[str] = set()
    for ticker in ["AAPL", "MSFT", "TSLA"]:
        for _ in range(5):
            seen.add(registry.issue(ticker, "2026-11-15", "src", "title").evidence_id)
    assert len(seen) == 15
    assert seen == registry.issued_ids


def test_registry_resolve_known_and_unknown():
    """FR-B-2 / INV-B-3: resolve maps issued IDs to records; unknown -> None."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    record = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple")
    assert registry.resolve(record.evidence_id) is record
    assert registry.resolve("ev-a1b2c3d4-AAPL-999") is None
    assert registry.resolve("ev-other-AAPL-0") is None


def test_registry_run_ids_distinct_across_runs():
    """NFR-B-2: two runs get different run_ids, so IDs never cross runs."""
    registry_a = EvidenceRegistry()
    registry_b = EvidenceRegistry()
    assert registry_a.run_id != registry_b.run_id
    assert registry_a.issued_ids.isdisjoint(registry_b.issued_ids)


def test_registry_register_prebuilt_record():
    """FR-B-2: a pre-built NewsRecord can be registered and resolved."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    record = NewsRecord(
        evidence_id="ev-a1b2c3d4-AAPL-0",
        ticker="AAPL",
        date="2026-11-15",
        source="Reuters",
        title="title",
    )
    registry.register(record)
    assert "ev-a1b2c3d4-AAPL-0" in registry.issued_ids
    assert registry.resolve("ev-a1b2c3d4-AAPL-0") is record


# ---------------------------------------------------------------------------
# merge_once (FR-B-3/4/5/6, INV-B-1/4)
# ---------------------------------------------------------------------------


def test_merge_once_single_llm_call(records):
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


def test_merge_once_legal_merge_accepted(records):
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


def test_merge_once_llm_raises_fail_closed(records):
    """RP-B: an LLM exception fails closed as analysis_incomplete, reason preserved."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        raise RuntimeError("model unavailable")

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.ANALYSIS_INCOMPLETE
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {r.evidence_id for r in records_list}
    assert "model unavailable" in result.failure_reason


def test_merge_once_json_parse_failure_fail_closed(records):
    """RP-B: unparseable output fails closed as analysis_incomplete, reason preserved."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return "not json at all"

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.ANALYSIS_INCOMPLETE
    assert result.events == []
    assert result.failure_reason


def test_merge_once_null_event_fails_closed_as_analysis_incomplete(records):
    """RP-B: a null event entry is a malformed output -> analysis_incomplete."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return json.dumps({"events": [None]})

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.ANALYSIS_INCOMPLETE
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {r.evidence_id for r in records_list}
    assert result.failure_reason


def test_merge_once_malformed_evidence_ids_fail_closed_as_analysis_incomplete(records):
    """RP-B: a non-string evidence id is a malformed output -> analysis_incomplete."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return json.dumps({"events": [{"event_id": "e1", "summary": "x", "evidence_ids": [{}]}]})

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.ANALYSIS_INCOMPLETE
    assert result.events == []
    assert result.failure_reason


def test_merge_once_missing_event_id_and_summary_not_published(records):
    """FR-B-4: an event missing event_id/summary is never emitted with empty fields."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        return json.dumps(
            {
                "events": [{"evidence_ids": [aapl.evidence_id, msft.evidence_id]}],
                "unmerged_evidence_ids": [tsla.evidence_id],
            }
        )

    result = merge_once(records_list, TICKERS, WINDOW, llm=llm)
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {
        aapl.evidence_id,
        msft.evidence_id,
        tsla.evidence_id,
    }
    assert result.status is MergeStatus.NO_COMMON_EVENT


def test_merge_once_no_records_data_unavailable():
    """FR-B-6: empty records -> data_unavailable, no LLM call."""
    calls = []

    def llm(prompt):
        calls.append(prompt)
        return "{}"

    result = merge_once([], TICKERS, WINDOW, llm=llm)
    assert result.status is MergeStatus.DATA_UNAVAILABLE
    assert result.events == []
    assert calls == []


def test_merge_once_records_but_no_events_no_common_event(records):
    """FR-B-6: records exist but no common event -> no_common_event."""
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


def test_merge_once_forged_id_removed(records):
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


def test_inv_b1_second_call_forbidden(records):
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


def test_inv_b4_insufficient_evidence_not_forced(records):
    """INV-B-4 (violation -> fails): a single-record event is not emitted."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
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
    assert unmerged_ids == {aapl.evidence_id, msft.evidence_id, tsla.evidence_id}


# ---------------------------------------------------------------------------
# merge_once input validation (FR-B-1 boundary enforced at the entry point)
# ---------------------------------------------------------------------------


def test_merge_once_rejects_four_tickers(records):
    """FR-B-1: more than 3 tickers is rejected before any LLM call."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once(records_list, ["AAPL", "MSFT", "TSLA", "NVDA"], WINDOW, llm=llm)


def test_merge_once_rejects_window_longer_than_seven_days(records):
    """FR-B-1: a window spanning more than 7 days is rejected."""
    records_list, aapl, msft, tsla = records

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once(records_list, TICKERS, ("2026-11-01", "2026-11-22"), llm=llm)


def test_merge_once_rejects_cross_run_record(records):
    """NFR-B-2: a record whose evidence ID belongs to another run is rejected."""
    records_list, aapl, msft, tsla = records
    other = EvidenceRegistry(run_id="otherrun")
    foreign = other.issue("AAPL", "2026-11-15", "Reuters", "foreign run record")

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, msft, tsla, foreign], TICKERS, WINDOW, llm=llm)


def test_merge_once_rejects_record_ticker_not_in_input(records):
    """FR-B-1: a record whose ticker is not among the input tickers is rejected."""
    records_list, aapl, msft, tsla = records
    registry = EvidenceRegistry(run_id="run123")
    nvda = registry.issue("NVDA", "2026-11-17", "CNBC", "Nvidia record")

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, msft, tsla, nvda], TICKERS, WINDOW, llm=llm)


def test_merge_once_rejects_more_than_five_records_per_ticker(records):
    """FR-B-1: more than 5 records for one ticker is rejected."""
    records_list, aapl, msft, tsla = records
    registry = EvidenceRegistry(run_id="run123")
    extra = [registry.issue("AAPL", "2026-11-15", "Reuters", f"extra {i}") for i in range(5)]

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, msft, tsla, *extra], TICKERS, WINDOW, llm=llm)


def test_merge_once_rejects_future_dated_record():
    """FR-B-1: a future-dated record is rejected before any LLM call."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue("AAPL", "2026-11-23", "Reuters", "future Apple record")
    msft = registry.issue("MSFT", "2026-11-20", "Bloomberg", "in-window Microsoft record")

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, msft], TICKERS, WINDOW, llm=llm)


def test_merge_once_rejects_stale_record_before_window():
    """FR-B-1: a record dated before the window is rejected before any LLM call."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue("AAPL", "2026-11-01", "Reuters", "stale Apple record")
    msft = registry.issue("MSFT", "2026-11-20", "Bloomberg", "in-window Microsoft record")

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, msft], TICKERS, WINDOW, llm=llm)


def test_merge_once_rejects_missing_date_record():
    """FR-B-1: a record with no date is rejected before any LLM call."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue("AAPL", "2026-11-20", "Reuters", "dated Apple record")
    undated = NewsRecord(
        evidence_id="ev-run123-MSFT-0",
        ticker="MSFT",
        date="",
        source="Bloomberg",
        title="undated Microsoft record",
    )

    def llm(prompt):
        raise AssertionError("LLM must not be called for invalid input")

    with pytest.raises(ValueError):
        merge_once([aapl, undated], TICKERS, WINDOW, llm=llm)


# ---------------------------------------------------------------------------
# validate (FR-B-5/7, NFR-B-1/2, INV-B-2/3/5)
# ---------------------------------------------------------------------------


def test_validate_valid_grouping_accepted(reg):
    """FR-B-4/5/7: a two-ticker event with matching claims survives."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "Big tech earnings",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    assert result.status is MergeStatus.MERGED
    assert len(result.events) == 1
    event = result.events[0]
    assert set(event.tickers) == {"AAPL", "MSFT"}
    assert len(event.evidence) == 2
    assert result.dropped_invalid == []
    assert [r.evidence_id for r in result.unmerged] == [tsla.evidence_id]


def test_validate_forged_evidence_id_dropped(reg):
    """FR-B-7 / NFR-B-2: an ID not issued this run is dropped, never output."""
    registry, aapl, msft, tsla = reg
    forged = "ev-run123-XXXX-0"
    model = [
        {
            "event_id": "e1",
            "summary": "event with a forged id",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": forged, "ticker": "XXXX", "date": "2026-11-18", "source": "Fake"},
            ],
        }
    ]
    result = validate(registry, model)
    dropped = [d for d in result.dropped_invalid if d.evidence_id == forged]
    assert len(dropped) == 1
    assert dropped[0].reason == "forged_or_cross_run_id"
    out_ids = {e.evidence_id for ev in result.events for e in ev.evidence} | {
        r.evidence_id for r in result.unmerged
    }
    assert forged not in out_ids


def test_validate_mismatched_ticker_dropped(reg):
    """FR-B-7: a claim whose ticker disagrees with the record is dropped."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "ticker mismatch",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "MSFT", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    dropped = [d for d in result.dropped_invalid if d.evidence_id == aapl.evidence_id]
    assert len(dropped) == 1
    assert dropped[0].reason == "ticker_mismatch"
    assert result.events == []
    assert result.status is MergeStatus.NO_COMMON_EVENT


def test_validate_mismatched_date_dropped(reg):
    """FR-B-7: a claim whose date disagrees with the record is dropped."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "date mismatch",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2020-01-01", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    dropped = [d for d in result.dropped_invalid if d.evidence_id == aapl.evidence_id]
    assert len(dropped) == 1
    assert dropped[0].reason == "date_mismatch"
    assert result.events == []


def test_validate_mismatched_source_dropped(reg):
    """FR-B-7: a claim whose source disagrees with the record is dropped."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "source mismatch",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Bloomberg"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    dropped = [d for d in result.dropped_invalid if d.evidence_id == aapl.evidence_id]
    assert len(dropped) == 1
    assert dropped[0].reason == "source_mismatch"


def test_validate_cross_run_id_dropped():
    """NFR-B-2: an ID issued by another run is rejected as non-resolvable."""
    registry = EvidenceRegistry(run_id="runA")
    msft = registry.issue("MSFT", "2026-11-16", "Bloomberg", "m")
    other = EvidenceRegistry(run_id="runB")
    other_rec = other.issue("AAPL", "2026-11-15", "Reuters", "other run record")

    model = [
        {
            "event_id": "e1",
            "summary": "cross-run id",
            "evidence": [
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
                {"evidence_id": other_rec.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
            ],
        }
    ]
    result = validate(registry, model)
    dropped = [d for d in result.dropped_invalid if d.evidence_id == other_rec.evidence_id]
    assert len(dropped) == 1
    assert dropped[0].reason == "forged_or_cross_run_id"


def test_validate_single_ticker_event_degraded():
    """FR-B-5: an event backed by a single distinct ticker is degraded."""
    registry = EvidenceRegistry(run_id="run123")
    a0 = registry.issue("AAPL", "2026-11-15", "Reuters", "a0")
    a1 = registry.issue("AAPL", "2026-11-16", "Bloomberg", "a1")
    model = [
        {
            "event_id": "e1",
            "summary": "same ticker only",
            "evidence": [
                {"evidence_id": a0.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": a1.evidence_id, "ticker": "AAPL", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {a0.evidence_id, a1.evidence_id}
    assert result.status is MergeStatus.NO_COMMON_EVENT


def test_validate_resolution_rate_100_percent(reg):
    """NFR-B-1: every output evidence ID resolves back to a record."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "resolvable",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    for item in [e for ev in result.events for e in ev.evidence] + list(result.unmerged):
        assert registry.resolve(item.evidence_id) is not None


def test_validate_forged_and_cross_run_count_zero(reg):
    """NFR-B-2: forged / cross-run IDs never leak into verified output (== 0)."""
    registry, aapl, msft, tsla = reg
    other = EvidenceRegistry(run_id="other")
    cross = other.issue("AAPL", "2026-11-15", "Reuters", "x")
    forged = "ev-run123-FAKE-0"

    model = [
        {
            "event_id": "e1",
            "summary": "good",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        },
        {
            "event_id": "e2",
            "summary": "bad ids",
            "evidence": [
                {"evidence_id": forged, "ticker": "FAKE", "date": "2026-11-18", "source": "Fake"},
                {"evidence_id": cross.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
            ],
        },
    ]
    result = validate(registry, model)
    out_ids = {e.evidence_id for ev in result.events for e in ev.evidence} | {
        r.evidence_id for r in result.unmerged
    }
    assert forged not in out_ids
    assert cross.evidence_id not in out_ids
    forged_or_cross = [
        d for d in result.dropped_invalid if d.evidence_id in (forged, cross.evidence_id)
    ]
    assert len(forged_or_cross) == 2
    assert len(result.events) == 1


def test_inv_b2_single_ticker_event_degraded(reg):
    """INV-B-2 (violation -> fails): a single-ticker event must be degraded."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "single ticker",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "AAPL", "date": "2026-11-15", "source": "Reuters"},
            ],
        }
    ]
    result = validate(registry, model)
    assert result.events == []
    assert aapl.evidence_id in {r.evidence_id for r in result.unmerged}


def test_inv_b3_forged_and_mismatched_rejected(reg):
    """INV-B-3 (violation -> fails): forged / mismatched claims must be dropped."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "invalid claims",
            "evidence": [
                {"evidence_id": "ev-run123-NOPE-0", "ticker": "NOPE", "date": "2026-11-15", "source": "X"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    reasons = {d.reason for d in result.dropped_invalid}
    assert "forged_or_cross_run_id" in reasons
    out_ids = {e.evidence_id for ev in result.events for e in ev.evidence} | {
        r.evidence_id for r in result.unmerged
    }
    assert "ev-run123-NOPE-0" not in out_ids


def test_inv_b5_model_claims_cannot_override_authoritative_values(reg):
    """INV-B-5 (violation -> fails): final evidence uses record values, not model claims."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "bare ids",
            "evidence_ids": [aapl.evidence_id, msft.evidence_id],
        }
    ]
    result = validate(registry, model)
    event = result.events[0]
    by_id = {e.evidence_id: e for e in event.evidence}
    assert by_id[aapl.evidence_id].ticker == "AAPL"
    assert by_id[aapl.evidence_id].date == "2026-11-15"
    assert by_id[aapl.evidence_id].source == "Reuters"


def test_inv_b5_wrong_claim_rejected_not_adopted(reg):
    """INV-B-5 (violation -> fails): a wrong claim is rejected, never adopted."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "wrong ticker claim",
            "evidence": [
                {"evidence_id": aapl.evidence_id, "ticker": "TSLA", "date": "2026-11-15", "source": "Reuters"},
                {"evidence_id": msft.evidence_id, "ticker": "MSFT", "date": "2026-11-16", "source": "Bloomberg"},
            ],
        }
    ]
    result = validate(registry, model)
    assert any(d.reason == "ticker_mismatch" for d in result.dropped_invalid)
    for event in result.events:
        for item in event.evidence:
            assert item.ticker == registry.resolve(item.evidence_id).ticker


def test_validate_missing_event_id_not_published(reg):
    """FR-B-4: an event with no event_id is degraded, never emitted with empty fields."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "summary": "no event id",
            "evidence_ids": [aapl.evidence_id, msft.evidence_id],
        }
    ]
    result = validate(registry, model)
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {
        aapl.evidence_id,
        msft.evidence_id,
        tsla.evidence_id,
    }
    assert any(d.reason == "missing_event_id" for d in result.dropped_invalid)


def test_validate_missing_summary_not_published(reg):
    """FR-B-4: an event with no summary is degraded, never emitted with empty fields."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "evidence_ids": [aapl.evidence_id, msft.evidence_id],
        }
    ]
    result = validate(registry, model)
    assert result.events == []
    assert {r.evidence_id for r in result.unmerged} == {
        aapl.evidence_id,
        msft.evidence_id,
        tsla.evidence_id,
    }
    assert any(d.reason == "missing_summary" for d in result.dropped_invalid)


def test_validate_malformed_evidence_id_dropped_not_crash(reg):
    """FR-B-7: a non-string evidence id is dropped; valid ids still merge, no crash."""
    registry, aapl, msft, tsla = reg
    model = [
        {
            "event_id": "e1",
            "summary": "malformed evidence id mixed with valid ids",
            "evidence_ids": [aapl.evidence_id, msft.evidence_id, {}],
        }
    ]
    result = validate(registry, model)
    assert len(result.events) == 1
    event = result.events[0]
    assert {e.evidence_id for e in event.evidence} == {aapl.evidence_id, msft.evidence_id}
    assert any(d.reason == "malformed_evidence_id" for d in result.dropped_invalid)


def test_validate_non_dict_event_skipped_without_crash(reg):
    """RP-B: a non-object event entry is dropped observably instead of crashing."""
    registry, aapl, msft, tsla = reg
    model = [None]
    result = validate(registry, model)
    assert result.events == []
    assert any(d.reason == "malformed_event" for d in result.dropped_invalid)
