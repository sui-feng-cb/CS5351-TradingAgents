"""Structured news adapter that reuses the upstream news capability (FR-B-2).

:func:`fetch_records` fetches at most five structured records per ticker and
assigns each a run-unique evidence ID via :class:`EvidenceRegistry`. The actual
vendor access is injected as a ``fetcher(ticker, start, end) -> list[dict]``
callable so offline tests never touch the network or heavy upstream deps.

The default fetcher is a *lazy* adapter over the upstream Yahoo Finance news
extractor: the ``yfinance`` and ``tradingagents`` imports happen only inside the
function body, so importing this module (and the offline test path) pulls in
nothing but the standard library.
"""

from __future__ import annotations

import datetime as _dt

from .evidence import EvidenceRegistry
from .schemas import NewsRecord

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
    fetcher=None,
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
