"""Tests for :class:`EvidenceRegistry` (FR-B-2, NFR-B-1, INV-B-3).

Verifies evidence ID format, run-scoped uniqueness, and ``resolve`` behaviour.
"""

from __future__ import annotations

import pytest

from event_merge.evidence import EvidenceRegistry
from event_merge.schemas import NewsRecord


@pytest.mark.offline
def test_issue_generates_canonical_id_format():
    """FR-B-2: evidence_id == ev-{run_id}-{ticker}-{seq}."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    record = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple earnings")
    assert record.evidence_id == "ev-a1b2c3d4-AAPL-0"
    assert record.evidence_id.startswith("ev-a1b2c3d4-")
    assert record.ticker == "AAPL"


@pytest.mark.offline
def test_issue_sequence_increments_per_ticker():
    """FR-B-2: seq is 0-based and increments within the same ticker."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    first = registry.issue("AAPL", "2026-11-15", "Reuters", "t0")
    second = registry.issue("AAPL", "2026-11-15", "Reuters", "t1")
    assert first.evidence_id == "ev-a1b2c3d4-AAPL-0"
    assert second.evidence_id == "ev-a1b2c3d4-AAPL-1"


@pytest.mark.offline
def test_issue_ids_are_unique_within_run():
    """NFR-B-1: every issued ID is unique across tickers within one run."""
    registry = EvidenceRegistry()
    seen: set[str] = set()
    for ticker in ["AAPL", "MSFT", "TSLA"]:
        for _ in range(5):
            record = registry.issue(ticker, "2026-11-15", "src", "title")
            seen.add(record.evidence_id)
    assert len(seen) == 15
    assert seen == registry.issued_ids


@pytest.mark.offline
def test_resolve_returns_record_and_none_for_unknown():
    """FR-B-2 / INV-B-3: resolve maps issued IDs to records; unknown -> None."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    record = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple")
    assert registry.resolve(record.evidence_id) is record
    assert registry.resolve("ev-a1b2c3d4-AAPL-999") is None
    assert registry.resolve("ev-other-AAPL-0") is None


@pytest.mark.offline
def test_run_ids_are_distinct_across_registries():
    """NFR-B-2: two runs get different run_ids, so IDs never cross runs."""
    registry_a = EvidenceRegistry()
    registry_b = EvidenceRegistry()
    assert registry_a.run_id != registry_b.run_id
    assert registry_a.issued_ids.isdisjoint(registry_b.issued_ids)


@pytest.mark.offline
def test_register_prebuilt_record_is_resolvable():
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


@pytest.mark.offline
def test_issue_skips_collisions_after_register():
    """FR-B-2: issue() never reuses an ID already occupied by register()."""
    registry = EvidenceRegistry(run_id="a1b2c3d4")
    registry.register(
        NewsRecord(
            evidence_id="ev-a1b2c3d4-AAPL-0",
            ticker="AAPL",
            date="2026-11-15",
            source="Reuters",
            title="prebuilt",
        )
    )
    issued = registry.issue("AAPL", "2026-11-16", "Reuters", "new")
    assert issued.evidence_id == "ev-a1b2c3d4-AAPL-1"
