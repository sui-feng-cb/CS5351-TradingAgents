"""Tests for input window construction (FR-B-1)."""

from __future__ import annotations

import pytest

from event_merge.input import build_window


@pytest.mark.offline
def test_two_tickers_success():
    """FR-B-1: 2 tickers within a 7-day window succeed."""
    start, end = build_window(["AAPL", "MSFT"], "2026-11-22", 7)
    assert start == "2026-11-15"
    assert end == "2026-11-22"


@pytest.mark.offline
def test_three_tickers_success():
    """FR-B-1: 3 tickers succeed."""
    start, end = build_window(["AAPL", "MSFT", "TSLA"], "2026-11-22", 1)
    assert start == "2026-11-21"
    assert end == "2026-11-22"


@pytest.mark.offline
def test_one_ticker_fails():
    """FR-B-1: a single ticker is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL"], "2026-11-22", 7)


@pytest.mark.offline
def test_four_tickers_fail():
    """FR-B-1: more than 3 tickers are rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT", "TSLA", "NVDA"], "2026-11-22", 7)


@pytest.mark.offline
def test_lookback_greater_than_seven_fails():
    """FR-B-1: a look-back window longer than 7 days is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT"], "2026-11-22", 8)


@pytest.mark.offline
def test_lookback_zero_fails():
    """FR-B-1: a look-back window shorter than 1 day is rejected."""
    with pytest.raises(ValueError):
        build_window(["AAPL", "MSFT"], "2026-11-22", 0)
