"""Tests for the deterministic validator (FR-B-5/7, NFR-B-1/2, INV-B-2/3/5).

Every test below injects *suggested* model output (``model_events``) and asserts
that :func:`validate` enforces the deterministic boundary: only claims whose
``evidence_id`` is issued in the run *and* whose ticker/date/source match the
authoritative record survive; single-ticker events are degraded; forged and
cross-run IDs never appear as verified facts.
"""

from __future__ import annotations

import pytest

from event_merge.evidence import EvidenceRegistry
from event_merge.schemas import MergeStatus
from event_merge.validator import validate


@pytest.fixture
def reg():
    """A run with three issued records (AAPL, MSFT, TSLA)."""
    registry = EvidenceRegistry(run_id="run123")
    aapl = registry.issue("AAPL", "2026-11-15", "Reuters", "Apple beats estimates")
    msft = registry.issue("MSFT", "2026-11-16", "Bloomberg", "Microsoft cloud growth")
    tsla = registry.issue("TSLA", "2026-11-17", "CNBC", "Tesla deliveries")
    return registry, aapl, msft, tsla


@pytest.mark.offline
def test_valid_grouping_is_accepted(reg):
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


@pytest.mark.offline
def test_forged_evidence_id_is_dropped(reg):
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


@pytest.mark.offline
def test_mismatched_ticker_is_dropped(reg):
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


@pytest.mark.offline
def test_mismatched_date_is_dropped(reg):
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


@pytest.mark.offline
def test_mismatched_source_is_dropped(reg):
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


@pytest.mark.offline
def test_cross_run_id_is_dropped():
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


@pytest.mark.offline
def test_single_ticker_event_is_degraded():
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


@pytest.mark.offline
def test_resolution_rate_is_100_percent(reg):
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


@pytest.mark.offline
def test_forged_and_cross_run_count_is_zero_in_output(reg):
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


@pytest.mark.offline
def test_inv_b2_single_ticker_event_is_degraded(reg):
    """INV-B-2 (violation → fails): a single-ticker event must be degraded."""
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


@pytest.mark.offline
def test_inv_b3_forged_and_mismatched_evidence_is_rejected(reg):
    """INV-B-3 (violation → fails): forged / mismatched claims must be dropped."""
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


@pytest.mark.offline
def test_inv_b5_model_claims_cannot_override_authoritative_values(reg):
    """INV-B-5 (violation → fails): final evidence uses record values, not model claims."""
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


@pytest.mark.offline
def test_inv_b5_wrong_claim_is_rejected_not_adopted(reg):
    """INV-B-5 (violation → fails): a wrong claim is rejected, never adopted."""
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
