"""Deterministic evidence validator — the authority for FR-B-7 / NFR-B-1/2.

The model's merge output is only a *suggestion*. :func:`validate` filters every
claimed evidence item against :class:`EvidenceRegistry` and is the single
source of truth for what may be emitted as a verified fact (INV-B-3 / INV-B-5).

Rules applied to each claimed evidence item, in order:

1. ``evidence_id`` must be in ``registry.issued_ids`` — otherwise the claim is
   forged or belongs to another run and is dropped (NFR-B-2).
2. If the model claims ``ticker`` / ``date`` / ``source``, each must equal the
   authoritative record value — otherwise the claim is dropped (FR-B-7).

After filtering, every surviving event must still carry at least two distinct
tickers; otherwise the whole event is degraded to ``unmerged`` (FR-B-5 /
INV-B-2). Records not attached to any surviving event become ``unmerged``.
"""

from __future__ import annotations

from typing import Any

from .evidence import EvidenceRegistry
from .schemas import DroppedEvidence, EvidenceItem, MergedEvent, MergeResult, MergeStatus

_FORGED = "forged_or_cross_run_id"
_TICKER_MISMATCH = "ticker_mismatch"
_DATE_MISMATCH = "date_mismatch"
_SOURCE_MISMATCH = "source_mismatch"


def _extract_claims(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a model event into a list of evidence-claim dicts.

    Accepts either ``evidence`` (a list of dicts or plain IDs) or the compact
    ``evidence_ids`` form from plan §b.3.
    """
    evidence = event.get("evidence")
    if evidence is not None:
        claims: list[dict[str, Any]] = []
        for item in evidence:
            if isinstance(item, str):
                claims.append({"evidence_id": item})
            else:
                claims.append(dict(item))
        return claims
    ids = event.get("evidence_ids", [])
    return [{"evidence_id": evidence_id} for evidence_id in ids]


def validate(registry: EvidenceRegistry, model_events: list[dict[str, Any]]) -> MergeResult:
    """Validate model-suggested events and return the authoritative result."""
    events: list[MergedEvent] = []
    dropped_invalid: list[DroppedEvidence] = []
    surviving_ids: set[str] = set()

    for event in model_events:
        event_id = event.get("event_id", "")
        summary = event.get("summary", "")

        valid_items: list[EvidenceItem] = []
        for claim in _extract_claims(event):
            evidence_id = claim.get("evidence_id")
            record = registry.resolve(evidence_id)

            if record is None:
                dropped_invalid.append(
                    DroppedEvidence(
                        evidence_id=evidence_id,
                        ticker=claim.get("ticker"),
                        date=claim.get("date"),
                        source=claim.get("source"),
                        reason=_FORGED,
                    )
                )
                continue

            if "ticker" in claim and claim["ticker"] != record.ticker:
                dropped_invalid.append(
                    DroppedEvidence(
                        evidence_id=evidence_id,
                        ticker=claim.get("ticker"),
                        date=claim.get("date"),
                        source=claim.get("source"),
                        reason=_TICKER_MISMATCH,
                    )
                )
                continue

            if "date" in claim and claim["date"] != record.date:
                dropped_invalid.append(
                    DroppedEvidence(
                        evidence_id=evidence_id,
                        ticker=claim.get("ticker"),
                        date=claim.get("date"),
                        source=claim.get("source"),
                        reason=_DATE_MISMATCH,
                    )
                )
                continue

            if "source" in claim and claim["source"] != record.source:
                dropped_invalid.append(
                    DroppedEvidence(
                        evidence_id=evidence_id,
                        ticker=claim.get("ticker"),
                        date=claim.get("date"),
                        source=claim.get("source"),
                        reason=_SOURCE_MISMATCH,
                    )
                )
                continue

            valid_items.append(
                EvidenceItem(
                    evidence_id=record.evidence_id,
                    ticker=record.ticker,
                    source=record.source,
                    date=record.date,
                )
            )

        distinct_tickers = {item.ticker for item in valid_items}
        if len(distinct_tickers) < 2:
            # Whole event degraded to unmerged (INV-B-2 / FR-B-5).
            continue

        events.append(
            MergedEvent(
                event_id=event_id,
                summary=summary,
                tickers=sorted(distinct_tickers),
                evidence=valid_items,
            )
        )
        for item in valid_items:
            surviving_ids.add(item.evidence_id)

    unmerged = [
        record
        for evidence_id, record in registry.records().items()
        if evidence_id not in surviving_ids
    ]

    if not registry.issued_ids:
        status = MergeStatus.DATA_UNAVAILABLE
    elif not events:
        status = MergeStatus.NO_COMMON_EVENT
    else:
        status = MergeStatus.MERGED

    return MergeResult(
        status=status,
        run_id=registry.run_id,
        events=events,
        unmerged=unmerged,
        dropped_invalid=dropped_invalid,
    )
