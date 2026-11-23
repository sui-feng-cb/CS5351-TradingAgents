"""B-module deterministic core: cross-ticker common-event merge (FR-B / NFR-B / INV-B).

This module is the single authority for the B-module contract. It consolidates
what used to be six standalone files (``schemas`` / ``evidence`` / ``input`` /
``news_source`` / ``merger`` / ``validator``) into one standard-library-only
module so the offline / deterministic layer carries no third-party runtime
dependency at import time.

Contract (see ``docs/req/requirements.yaml``, owner B):

* FR-B   — group common events for 2–3 tickers, at most 7 days and 5 records
           per ticker, using actual news text and at most one grouping model
           call; publish evidence-backed groups involving at least two tickers.
* NFR-B  — every published evidence reference resolves to this run and matches
           its ticker/date/source metadata (100% valid, 0 forged / cross-run).
* INV-B  — the deterministic validator is the sole authority on evidence
           legitimacy; the model output is only a suggestion and can never
           override a deterministic boundary.

The prompt for the merge step is inlined below as :data:`_MERGE_PROMPT_TEMPLATE`
(no file read), and upstream ``tradingagents.*`` / ``yfinance`` are imported
*lazily inside function bodies* so a plain ``import`` of this module pulls in
only the standard library.
"""

from __future__ import annotations

import datetime as _dt
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "MAX_RECORDS_PER_TICKER",
    "DroppedEvidence",
    "EvidenceItem",
    "EvidenceRegistry",
    "MergeInput",
    "MergeResult",
    "MergeStatus",
    "MergedEvent",
    "NewsRecord",
    "build_window",
    "fetch_records",
    "merge_once",
    "validate",
]


# ---------------------------------------------------------------------------
# Schemas / status (FR-B-4/5/6/7)
# ---------------------------------------------------------------------------


class MergeStatus(StrEnum):
    """Final merge status of a run (FR-B-6)."""

    MERGED = "merged"
    NO_COMMON_EVENT = "no_common_event"
    DATA_UNAVAILABLE = "data_unavailable"


@dataclass(frozen=True)
class NewsRecord:
    """A single evidence-backed news record."""

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


@dataclass(frozen=True)
class EvidenceItem:
    """A verified evidence reference inside a merged event.

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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class MergeInput:
    """The full, single-batch input handed to the model."""

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


@dataclass(frozen=True)
class MergeResult:
    """The authoritative final output after deterministic validation."""

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


# ---------------------------------------------------------------------------
# Evidence registry (FR-B-2 / NFR-B-1/2, INV-B-3)
# ---------------------------------------------------------------------------


class EvidenceRegistry:
    """Issues, registers and resolves evidence IDs for one merge run.

    The sole authority on which evidence IDs belong to the current run and how
    they map back to their :class:`NewsRecord` (INV-B-3). Run-scoped and
    stateless across runs: a fresh ``run_id`` is generated per instance, so IDs
    never collide across runs (NFR-B-2).
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id if run_id is not None else uuid.uuid4().hex[:8]
        self._records: dict[str, NewsRecord] = {}
        self._issued: set[str] = set()
        self._seq: dict[str, int] = {}

    @property
    def issued_ids(self) -> set[str]:
        """Evidence IDs issued/registered during this run (authoritative set)."""
        return set(self._issued)

    def records(self) -> dict[str, NewsRecord]:
        """A snapshot of ``evidence_id -> NewsRecord`` for this run."""
        return dict(self._records)

    def issue(
        self,
        ticker: str,
        date: str,
        source: str,
        title: str,
        snippet: str = "",
        link: str = "",
        pub_date: str = "",
    ) -> NewsRecord:
        """Issue a new record with a run-unique ``ev-{run_id}-{ticker}-{seq}`` ID.

        The sequence is per-ticker and 0-based. If an ID would collide (e.g.
        after :meth:`register` injected a record), the sequence is advanced until
        unique, guaranteeing ``issued_ids`` uniqueness within the run.
        """
        seq = self._seq.get(ticker, 0)
        while True:
            evidence_id = f"ev-{self.run_id}-{ticker}-{seq}"
            if evidence_id not in self._records:
                break
            seq += 1
        self._seq[ticker] = seq + 1

        record = NewsRecord(
            evidence_id=evidence_id,
            ticker=ticker,
            date=date,
            source=source,
            title=title,
            snippet=snippet,
            link=link,
            pub_date=pub_date,
        )
        self._records[evidence_id] = record
        self._issued.add(evidence_id)
        return record

    def register(self, record: NewsRecord) -> NewsRecord:
        """Register a pre-built record (used by fixtures/tests)."""
        self._records[record.evidence_id] = record
        self._issued.add(record.evidence_id)
        return record

    def resolve(self, evidence_id: str) -> NewsRecord | None:
        """Return the authoritative record for ``evidence_id``, or ``None``."""
        return self._records.get(evidence_id)


# ---------------------------------------------------------------------------
# Input window construction (FR-B-1)
# ---------------------------------------------------------------------------


def _parse_date(value: _dt.date | _dt.datetime | str) -> _dt.date:
    """Coerce ``as_of`` to a ``datetime.date`` (accepts date/datetime/ISO string)."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        return _dt.date.fromisoformat(value)
    raise TypeError(
        f"as_of must be a date/datetime or 'YYYY-MM-DD' string, got {type(value).__name__}"
    )


def build_window(
    tickers: list[str] | tuple[str, ...],
    as_of: _dt.date | _dt.datetime | str,
    lookback_days: int,
) -> tuple[str, str]:
    """Validate inputs and return the ``(window_start, window_end)`` pair.

    Constraints (FR-B-1):
      - ``2 <= len(tickers) <= 3``
      - ``1 <= lookback_days <= 7``

    ``window_end`` is ``as_of``; ``window_start`` is ``as_of - lookback_days``.
    """
    if not isinstance(tickers, (list, tuple)):
        raise TypeError(f"tickers must be a list or tuple, got {type(tickers).__name__}")

    if not (2 <= len(tickers) <= 3):
        raise ValueError(f"expected 2 or 3 tickers, got {len(tickers)}")

    if isinstance(lookback_days, bool) or not isinstance(lookback_days, int):
        raise ValueError(f"lookback_days must be an integer, got {type(lookback_days).__name__}")

    if not (1 <= lookback_days <= 7):
        raise ValueError(f"lookback_days must be between 1 and 7, got {lookback_days}")

    as_of_dt = _parse_date(as_of)
    window_start = as_of_dt - _dt.timedelta(days=lookback_days)
    return window_start.strftime("%Y-%m-%d"), as_of_dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# News adapter (FR-B-2)
# ---------------------------------------------------------------------------

MAX_RECORDS_PER_TICKER = 5


def _coerce_publication(value) -> tuple[str, str]:
    """Return ``(date, pub_date)`` from a date/datetime/ISO-string/None value.

    ``date`` is ``YYYY-MM-DD``; ``pub_date`` is the full ISO string when known.
    """
    if value is None:
        return "", ""
    if isinstance(value, _dt.datetime):
        return value.strftime("%Y-%m-%d"), value.isoformat()
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d"), value.isoformat()
    if isinstance(value, str):
        return value[:10], value
    text = str(value)
    return text[:10], text


def _normalize_article(raw: dict) -> dict:
    """Map a raw article dict to the canonical ``{title,snippet,source,date,pub_date,link}``.

    Accepts both the upstream ``_extract_article_data`` shape (``summary`` /
    ``publisher`` / datetime ``pub_date``) and already-canonical dicts.
    """
    title = str(raw.get("title") or "").strip()
    snippet = str(raw.get("snippet") or raw.get("summary") or "").strip()
    source = str(raw.get("source") or raw.get("publisher") or "").strip()
    link = str(raw.get("link") or "").strip()
    pub = raw.get("pub_date", raw.get("date"))
    date_str, pub_date_str = _coerce_publication(pub)
    return {
        "title": title,
        "snippet": snippet,
        "source": source,
        "date": date_str,
        "pub_date": pub_date_str,
        "link": link,
    }


def _default_fetcher(ticker: str, start: str, end: str) -> list[dict]:
    """Lazy structured adapter over the upstream Yahoo Finance news extractor.

    Returns the upstream ``_extract_article_data`` dicts (``title`` / ``summary``
    / ``publisher`` / ``link`` / ``pub_date``) that fall inside ``[start, end]``;
    :func:`fetch_records` normalises them. All heavy imports are function-local.
    """
    import yfinance as yf

    from tradingagents.dataflows.config import get_config
    from tradingagents.dataflows.date_window import in_window
    from tradingagents.dataflows.symbols import normalize_symbol
    from tradingagents.dataflows.vendors.yahoo.common import yf_retry
    from tradingagents.dataflows.vendors.yahoo.news import _extract_article_data

    limit = get_config()["news_article_limit"]
    canonical = normalize_symbol(ticker)
    feed = yf_retry(lambda: yf.Ticker(canonical).get_news(count=limit)) or []
    articles = [_extract_article_data(a) for a in feed]

    start_dt = _dt.datetime.strptime(start, "%Y-%m-%d")
    end_dt = _dt.datetime.strptime(end, "%Y-%m-%d")
    return [a for a in articles if in_window(a["pub_date"], start_dt, end_dt)]


def fetch_records(
    tickers: list[str] | tuple[str, ...],
    window_start: str,
    window_end: str,
    *,
    fetcher: Callable[[str, str, str], list[dict]] | None = None,
) -> list[NewsRecord]:
    """Fetch at most ``MAX_RECORDS_PER_TICKER`` records per ticker.

    Each record gets a run-unique evidence ID from a fresh :class:`EvidenceRegistry`
    and complete ``title`` / ``snippet`` / ``source`` / ``date`` / ``pub_date``
    fields. Records are returned in ticker order, then fetch order.
    """
    if fetcher is None:
        fetcher = _default_fetcher

    registry = EvidenceRegistry()
    for ticker in tickers:
        raw_records = fetcher(ticker, window_start, window_end) or []
        for raw in raw_records[:MAX_RECORDS_PER_TICKER]:
            data = _normalize_article(raw)
            registry.issue(
                ticker=ticker,
                date=data["date"],
                source=data["source"],
                title=data["title"],
                snippet=data["snippet"],
                link=data["link"],
                pub_date=data["pub_date"],
            )
    return list(registry.records().values())


# ---------------------------------------------------------------------------
# Merge prompt (inlined; no file read)
# ---------------------------------------------------------------------------

_INPUT_PLACEHOLDER = "{{INPUT_JSON}}"

_MERGE_PROMPT_TEMPLATE = """# Event Merge Prompt (v1)

You are a cross-ticker financial news event-merge analyst. Your job is to group
news records that describe the **same real-world event** and to leave everything
else unmerged.

## Role

Deterministic, evidence-only analyst. You never invent facts, never fabricate
evidence IDs, and never force a grouping that the records do not support.

## Task

Given a single batch of records (one batch, one answer), decide which records
refer to the same underlying event across **different tickers**, and emit a
single JSON object. You must answer in one pass; you will not be called again.

## Output JSON schema

Respond with **only** a JSON object of this shape (no markdown fences, no prose):

```json
{
  "events": [
    {
      "event_id": "string, short unique id e.g. e1",
      "summary": "string, one short sentence describing the shared event",
      "tickers": ["TICKER_A", "TICKER_B"],
      "evidence_ids": ["ev-<run_id>-<ticker>-<seq>", "ev-<run_id>-<ticker>-<seq>"]
    }
  ],
  "unmerged_evidence_ids": ["ev-<run_id>-<ticker>-<seq>"]
}
```

Rules that must hold:

1. Every event must be supported by records from **at least two distinct
   tickers**. A single-ticker event is invalid and must not be emitted.
2. `evidence_ids` in an event must be exactly the evidence IDs of the records
   that support that event. Use the `evidence_id` field from the input records
   verbatim; do not invent, renumber, or copy IDs from other runs.
3. Records that do not clearly belong to any cross-ticker event go into
   `unmerged_evidence_ids`. Do not force them into an event.
4. Do **not** merge two records merely because they share generic words
   (e.g. "earnings", "AI", "chip", "stock rises"). Two records belong to the
   same event only if they describe the same specific occurrence (same
   announcement, deal, product launch, regulation, incident, etc.) across
   different tickers.
5. Same-ticker duplicate reports of one story are not, by themselves, a
   cross-ticker event; a grouping still needs a second distinct ticker.
6. If no cross-ticker common event exists, return `{"events": [], "unmerged_evidence_ids": [<all ids>]}`.

## Input

The input is the JSON object below. `records` contains all records for this run.

{{INPUT_JSON}}
"""


# ---------------------------------------------------------------------------
# Merge entry point (FR-B-3/6, INV-B-1)
# ---------------------------------------------------------------------------


def _run_id_from_records(records: list[NewsRecord]) -> str | None:
    """Recover the run id embedded in the evidence IDs (``ev-{run_id}-...``)."""
    for record in records:
        evidence_id = record.evidence_id
        if evidence_id.startswith("ev-"):
            rest = evidence_id[3:]
            dash = rest.find("-")
            if dash > 0:
                return rest[:dash]
    return None


def _build_prompt(
    records: list[NewsRecord],
    tickers: list[str] | tuple[str, ...],
    window: tuple[str, str],
    run_id: str,
) -> str:
    payload = {
        "run_id": run_id,
        "tickers": list(tickers),
        "window_start": window[0],
        "window_end": window[1],
        "records": [record.to_dict() for record in records],
    }
    input_json = json.dumps(payload, ensure_ascii=False, indent=2)
    if _INPUT_PLACEHOLDER in _MERGE_PROMPT_TEMPLATE:
        return _MERGE_PROMPT_TEMPLATE.replace(_INPUT_PLACEHOLDER, input_json)
    return _MERGE_PROMPT_TEMPLATE + "\n\n## Input\n```json\n" + input_json + "\n```\n"


def _parse_model_output(raw: str) -> list[dict]:
    """Parse the model's JSON string into a list of suggested events."""
    if not isinstance(raw, str):
        raise ValueError("LLM output must be a JSON string")
    data = json.loads(raw)
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("events", [])
    else:
        raise ValueError("LLM output must be a JSON array or an object with 'events'")
    if not isinstance(events, list):
        raise ValueError("'events' must be a list")
    return events


def _fail_closed(registry: EvidenceRegistry, records: list[NewsRecord]) -> MergeResult:
    """Fail-closed result: no events, every record left unmerged."""
    return MergeResult(
        status=MergeStatus.NO_COMMON_EVENT,
        run_id=registry.run_id,
        events=[],
        unmerged=list(records),
        dropped_invalid=[],
    )


def _default_llm() -> Callable[[str], str]:
    """Lazy placeholder LLM — not wired to a network client.

    Raises a clear error if invoked without an injected ``llm`` callable, so an
    offline run fails loudly instead of silently emitting unverified facts.
    """

    def _invoke(prompt: str) -> str:
        raise RuntimeError(
            "Default LLM is a placeholder and is not wired to a network client; "
            "inject a `llm` callable (see merge_once) or wire the upstream "
            "TradingAgents LLM client before a live run."
        )

    return _invoke


def merge_once(
    records: list[NewsRecord],
    tickers: list[str] | tuple[str, ...],
    window: tuple[str, str],
    *,
    llm: Callable[[str], str] | None = None,
) -> MergeResult:
    """Merge ``records`` into cross-ticker events with exactly one LLM call.

    The entire record set is handed to ``llm`` in a single batch and invoked
    exactly once (INV-B-1). The model's output is only a suggestion: it is
    parsed into ``model_events`` and passed through the deterministic
    :func:`validate`, which is the sole authority on what may be emitted as a
    verified fact (INV-B-3 / INV-B-5).

    Failure behaviour:
      - no records                          -> ``data_unavailable`` (no LLM call)
      - ``llm`` raises / output unparseable -> fail-closed, no verified facts
      - records but no common event         -> ``no_common_event``

    Args:
        records: the full, single-batch set of :class:`NewsRecord`.
        tickers: the input ticker list (same order as the run).
        window: ``(window_start, window_end)`` from :func:`build_window`.
        llm: injectable ``callable(prompt) -> str``; defaults to the lazy
            placeholder (not wired to a network client).

    Returns:
        The authoritative :class:`MergeResult` after deterministic validation.
    """
    registry = EvidenceRegistry(run_id=_run_id_from_records(records))
    for record in records:
        registry.register(record)

    if not registry.issued_ids:
        return MergeResult(
            status=MergeStatus.DATA_UNAVAILABLE,
            run_id=registry.run_id,
            events=[],
            unmerged=[],
            dropped_invalid=[],
        )

    if llm is None:
        llm = _default_llm()

    prompt = _build_prompt(list(records), tickers, window, registry.run_id)

    try:
        raw = llm(prompt)
    except Exception:
        return _fail_closed(registry, list(records))

    try:
        model_events = _parse_model_output(raw)
    except Exception:
        return _fail_closed(registry, list(records))

    return validate(registry, model_events)


# ---------------------------------------------------------------------------
# Deterministic validator (FR-B-7 / NFR-B-1/2, INV-B-2/3/5)
# ---------------------------------------------------------------------------

_FORGED = "forged_or_cross_run_id"
_TICKER_MISMATCH = "ticker_mismatch"
_DATE_MISMATCH = "date_mismatch"
_SOURCE_MISMATCH = "source_mismatch"


def _extract_claims(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a model event into a list of evidence-claim dicts.

    Accepts either ``evidence`` (a list of dicts or plain IDs) or the compact
    ``evidence_ids`` form.
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


def _make_drop(claim: dict[str, Any], reason: str) -> DroppedEvidence:
    return DroppedEvidence(
        evidence_id=claim.get("evidence_id"),
        ticker=claim.get("ticker"),
        date=claim.get("date"),
        source=claim.get("source"),
        reason=reason,
    )


def validate(
    registry: EvidenceRegistry,
    model_events: list[dict[str, Any]],
) -> MergeResult:
    """Validate model-suggested events and return the authoritative result.

    Rules applied to each claimed evidence item, in order (FR-B-7 / INV-B-3):

    1. ``evidence_id`` must be in ``registry.issued_ids`` — otherwise the claim is
       forged or belongs to another run and is dropped (NFR-B-2).
    2. If the model claims ``ticker`` / ``date`` / ``source``, each must equal the
       authoritative record value — otherwise the claim is dropped.

    After filtering, every surviving event must still carry at least two distinct
    tickers; otherwise the whole event is degraded to ``unmerged`` (FR-B-5 /
    INV-B-2). Records not attached to any surviving event become ``unmerged``.
    """
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
                dropped_invalid.append(_make_drop(claim, _FORGED))
                continue

            if "ticker" in claim and claim["ticker"] != record.ticker:
                dropped_invalid.append(_make_drop(claim, _TICKER_MISMATCH))
                continue

            if "date" in claim and claim["date"] != record.date:
                dropped_invalid.append(_make_drop(claim, _DATE_MISMATCH))
                continue

            if "source" in claim and claim["source"] != record.source:
                dropped_invalid.append(_make_drop(claim, _SOURCE_MISMATCH))
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
