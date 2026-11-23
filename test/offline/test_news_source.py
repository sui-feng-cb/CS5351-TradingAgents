"""Tests for the structured news adapter (FR-B-2).

Every test injects a ``fetcher`` so no network or upstream dependency is touched.
"""

from __future__ import annotations

import pytest

from event_merge.news_source import MAX_RECORDS_PER_TICKER, fetch_records


def _article(i: int, ticker: str | None = None) -> dict:
    return {
        "title": f"{ticker or 'T'} headline {i}",
        "summary": f"snippet body {i}",
        "publisher": "Reuters",
        "link": f"https://example.com/{i}",
        "pub_date": f"2026-11-1{i % 10}T09:00:00+00:00",
    }


@pytest.mark.offline
def test_over_20_records_truncated_to_five_per_ticker():
    """FR-B-2: a vendor returning 20 records is truncated to <=5 per ticker."""

    def fetcher(ticker, start, end):
        return [_article(i, ticker) for i in range(20)]

    records = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    aapl = [r for r in records if r.ticker == "AAPL"]
    msft = [r for r in records if r.ticker == "MSFT"]
    assert len(aapl) == MAX_RECORDS_PER_TICKER
    assert len(msft) == MAX_RECORDS_PER_TICKER
    assert len(records) == 2 * MAX_RECORDS_PER_TICKER


@pytest.mark.offline
def test_evidence_ids_assigned_and_unique():
    """FR-B-2 / NFR-B-1: every record gets a run-unique evidence ID."""

    def fetcher(ticker, start, end):
        return [_article(i, ticker) for i in range(5)]

    records = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    ids = [r.evidence_id for r in records]
    assert len(ids) == len(set(ids)) == 10
    for record in records:
        assert record.evidence_id.startswith("ev-")
        assert f"-{record.ticker}-" in record.evidence_id


@pytest.mark.offline
def test_fields_are_complete():
    """FR-B-2: title/snippet/source/date/pub_date are all populated."""

    def fetcher(ticker, start, end):
        return [_article(0, ticker)]

    records = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert len(records) == 2
    for record in records:
        assert record.title
        assert record.snippet
        assert record.source
        assert record.date
        assert record.pub_date


@pytest.mark.offline
def test_empty_fetcher_returns_no_records():
    """FR-B-6: a fetcher returning nothing yields an empty record list."""

    def fetcher(ticker, start, end):
        return []

    records = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert records == []


@pytest.mark.offline
def test_normalizes_upstream_article_shape():
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

    records = fetch_records(["AAPL", "MSFT"], "2026-11-15", "2026-11-22", fetcher=fetcher)
    assert len(records) == 2
    for record in records:
        assert record.snippet == "summary text"
        assert record.source == "Yahoo Finance"
        assert record.date == "2026-11-15"
