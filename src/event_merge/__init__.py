"""B-module deterministic core: cross-ticker common-event merge (FR-B / NFR-B).

Public surface: schemas, the evidence registry, and the deterministic validator.
This package is deliberately a standalone package under ``src/event_merge/`` to
avoid an import collision with the upstream ``tradingagents/`` package.
"""

from __future__ import annotations

from .evidence import EvidenceRegistry
from .schemas import (
    DroppedEvidence,
    EvidenceItem,
    MergedEvent,
    MergeInput,
    MergeResult,
    MergeStatus,
    NewsRecord,
)
from .validator import validate

__all__ = [
    "DroppedEvidence",
    "EvidenceItem",
    "EvidenceRegistry",
    "MergeInput",
    "MergeResult",
    "MergeStatus",
    "MergedEvent",
    "NewsRecord",
    "validate",
]
