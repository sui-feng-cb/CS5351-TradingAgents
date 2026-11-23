"""Input window construction for the B-module merge (FR-B-1).

:func:`build_window` validates the ticker count (2–3) and the look-back window
(1–7 days) and returns the inclusive ``(window_start, window_end)`` pair as
``YYYY-MM-DD`` strings. This module is deterministic and standard-library only,
so it is safe to import on the offline test path.
"""

from __future__ import annotations

import datetime as _dt


def _parse_date(value: _dt.date | _dt.datetime | str) -> _dt.date:
    """Coerce ``as_of`` to a ``datetime.date`` (accepts date/datetime/ISO string)."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        return _dt.date.fromisoformat(value)
    raise TypeError(f"as_of must be a date/datetime or 'YYYY-MM-DD' string, got {type(value).__name__}")


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
