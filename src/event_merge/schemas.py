"""Data schemas for the B-module cross-ticker event merge (FR-B / NFR-B).

This module is the single source of truth for the record/event/result shapes
used across the deterministic core. It intentionally depends only on the
standard library (``dataclasses`` / ``enum`` / ``typing``) so the offline /
deterministic layer carries no third-party runtime dependency.

Schema contract frozen in ``_refs/plan-B-approved.md`` §b and
``docs/architecture/architecture-blueprint.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MergeStatus(StrEnum):
    """Final merge status of a run (FR-B-6)."""

    MERGED = "merged"
    NO_COMMON_EVENT = "no_common_event"
    DATA_UNAVAILABLE = "data_unavailable"


@dataclass
class NewsRecord:
    """A single evidence-backed news record (plan §b.1)."""

    evidence_id: str
    ticker: str
    date: str
    source: str
    title: str
    snippet: str = ""
    link: str = ""
    pub_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "ticker": self.ticker,
            "date": self.date,
            "source": self.source,
            "title": self.title,
            "snippet": self.snippet,
            "link": self.link,
            "pub_date": self.pub_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsRecord:
        return cls(
            evidence_id=data["evidence_id"],
            ticker=data["ticker"],
            date=data["date"],
            source=data["source"],
            title=data["title"],
            snippet=data.get("snippet", ""),
            link=data.get("link", ""),
            pub_date=data.get("pub_date", ""),
        )


@dataclass
class EvidenceItem:
    """A verified evidence reference inside a merged event (plan §b.4).

    Values are always taken from the authoritative :class:`NewsRecord`, never
    from the model's suggestions (INV-B-3 / INV-B-5).
    """

    evidence_id: str
    ticker: str
    source: str
    date: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "ticker": self.ticker,
            "source": self.source,
            "date": self.date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceItem:
        return cls(
            evidence_id=data["evidence_id"],
            ticker=data["ticker"],
            source=data["source"],
            date=data["date"],
        )


@dataclass
class MergedEvent:
    """A cross-ticker common event with at least two supporting tickers (FR-B-4/5)."""

    event_id: str
    summary: str
    tickers: list[str]
    evidence: list[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "summary": self.summary,
            "tickers": list(self.tickers),
            "evidence": [item.to_dict() for item in self.evidence],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergedEvent:
        return cls(
            event_id=data["event_id"],
            summary=data["summary"],
            tickers=list(data.get("tickers", [])),
            evidence=[EvidenceItem.from_dict(item) for item in data.get("evidence", [])],
        )


@dataclass
class DroppedEvidence:
    """An evidence claim rejected by the deterministic validator (FR-B-7).

    ``ticker`` / ``date`` / ``source`` are the model's *claimed* values (may be
    ``None`` when the model supplied none); ``reason`` records why it failed.
    """

    evidence_id: str
    ticker: str | None
    date: str | None
    source: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "ticker": self.ticker,
            "date": self.date,
            "source": self.source,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DroppedEvidence:
        return cls(
            evidence_id=data["evidence_id"],
            ticker=data.get("ticker"),
            date=data.get("date"),
            source=data.get("source"),
            reason=data["reason"],
        )


@dataclass
class MergeInput:
    """The full, single-batch input handed to the model (plan §b.2)."""

    run_id: str
    tickers: list[str]
    window_start: str
    window_end: str
    records: list[NewsRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tickers": list(self.tickers),
            "window_start": self.window_start,
            "window_end": self.window_end,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeInput:
        return cls(
            run_id=data["run_id"],
            tickers=list(data["tickers"]),
            window_start=data["window_start"],
            window_end=data["window_end"],
            records=[NewsRecord.from_dict(record) for record in data.get("records", [])],
        )


@dataclass
class MergeResult:
    """The authoritative final output after deterministic validation (plan §b.4)."""

    status: MergeStatus
    run_id: str
    events: list[MergedEvent] = field(default_factory=list)
    unmerged: list[NewsRecord] = field(default_factory=list)
    dropped_invalid: list[DroppedEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "run_id": self.run_id,
            "events": [event.to_dict() for event in self.events],
            "unmerged": [record.to_dict() for record in self.unmerged],
            "dropped_invalid": [item.to_dict() for item in self.dropped_invalid],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeResult:
        return cls(
            status=MergeStatus(data["status"]),
            run_id=data["run_id"],
            events=[MergedEvent.from_dict(event) for event in data.get("events", [])],
            unmerged=[NewsRecord.from_dict(record) for record in data.get("unmerged", [])],
            dropped_invalid=[
                DroppedEvidence.from_dict(item) for item in data.get("dropped_invalid", [])
            ],
        )
