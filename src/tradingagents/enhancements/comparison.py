"""FR-A / NFR-A / INV-A same-day two-ticker comparison contract.

This module owns A's orchestration layer. It does not reimplement upstream
analysis, providers, prompts, graph nodes or rating parsing.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from tradingagents.dataflows.date_window import get_current_date
from tradingagents.dataflows.symbols import normalize_symbol, safe_ticker_component

__all__ = [
    "ComparisonInputError",
    "ComparisonResult",
    "SingleRunResult",
    "run_comparison",
    "run_one",
]

_ALLOWED_RATINGS = frozenset(
    {"Buy", "Overweight", "Hold", "Underweight", "Sell", "REVIEW"}
)
_SUMMARY_FALLBACK = "Summary unavailable from upstream final state."
_SAFE_FAILURE_MESSAGES = {
    "GRAPH_FAILED": "Upstream analysis failed.",
    "REPORT_SAVE_FAILED": "Upstream report save failed.",
    "RESULT_IDENTITY_MISMATCH": "Result does not match the requested ticker or date.",
    "REPORT_ATTRIBUTION_FAILED": "Report path does not belong to the requested ticker.",
    "MISSING_OR_INVALID_FINAL_RATING": "No valid final rating was returned.",
    "INTERNAL_ERROR": "Comparison processing failed.",
}
_NON_STOCK_SUFFIXES = ("-USD", "-USDT", "-USDC", "-BTC", "-ETH")
_KNOWN_CRYPTO_BASES = frozenset(
    {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "LTC", "BCH", "DOT", "AVAX", "LINK"}
)
_CRYPTO_QUOTES = frozenset(
    {
        "USD", "USDT", "USDC",
        "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "CNH", "HKD",
        "SGD", "NZD", "KRW", "INR", "BRL", "RUB", "MXN", "ZAR", "TRY",
        "SEK", "NOK", "DKK", "PLN",
    }
)


class _GraphLike(Protocol):
    config: Mapping[str, object]

    def propagate(
        self,
        company_name: str,
        trade_date: str,
        asset_type: str = "stock",
        portfolio: object = None,
    ) -> tuple[dict, str]: ...

    def save_reports(
        self,
        final_state: dict,
        ticker: str,
        save_path: object = None,
        html: bool = True,
    ) -> Path: ...


@dataclass(frozen=True, slots=True)
class SingleRunResult:
    """One ticker's result inside a same-day comparison."""

    ticker: str
    analysis_date: str
    status: Literal["SUCCESS", "FAILED"]
    final_rating: str | None
    summary: str | None
    report_path: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """The two per-ticker results plus the two comparison artifacts."""

    comparison_id: str
    analysis_date: str
    generated_at: str
    overall_status: Literal["SUCCESS", "PARTIAL", "FAILED"]
    tickers: tuple[SingleRunResult, SingleRunResult]
    comparison_report_path: str
    manifest_path: str


class ComparisonInputError(ValueError):
    """Request-level input error raised before any graph run or artifact write."""

    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        self.code = code
        self.message = message
        self.field = field
        super().__init__(f"{code}: {message}")


class _ReportAttributionError(ValueError):
    """The resolved report path does not belong to the requested ticker."""


def _canonical_ticker(raw: object, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ComparisonInputError(
            "INVALID_TICKER", "ticker must be a non-empty string", field
        )
    try:
        canonical = normalize_symbol(raw)
        return safe_ticker_component(canonical)
    except (TypeError, ValueError) as exc:
        raise ComparisonInputError("INVALID_TICKER", str(exc), field) from exc


# Equivalent to _validate_trade_date at commit ecc2ff4
# (src/tradingagents/graph/trading_graph.py:32-43). If upstream date validation
# changes, update this check in the same change.
def _validate_analysis_date(value: object) -> str:
    if not isinstance(value, str):
        raise ComparisonInputError(
            "INVALID_DATE", "analysis_date must be a string", "analysis_date"
        )
    try:
        canonical = datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        canonical = False
    if not canonical:
        raise ComparisonInputError(
            "INVALID_DATE",
            f"analysis_date must be canonical YYYY-MM-DD, got {value!r}",
            "analysis_date",
        )
    if value > get_current_date():
        raise ComparisonInputError(
            "FUTURE_DATE",
            f"analysis_date cannot be in the future: {value}",
            "analysis_date",
        )
    return value


def _is_stock_symbol(symbol: str) -> bool:
    if symbol.endswith(("=X", "=F")) or symbol.startswith("^"):
        return False
    if symbol.endswith(_NON_STOCK_SUFFIXES):
        return False
    base, separator, quote = symbol.partition("-")
    return not (
        separator
        and base in _KNOWN_CRYPTO_BASES
        and quote in _CRYPTO_QUOTES
    )


def _validate_inputs(
    ticker_a: object, ticker_b: object, analysis_date: object
) -> tuple[str, str, str]:
    canonical_a = _canonical_ticker(ticker_a, "ticker_a")
    canonical_b = _canonical_ticker(ticker_b, "ticker_b")
    for symbol, field in ((canonical_a, "ticker_a"), (canonical_b, "ticker_b")):
        if not _is_stock_symbol(symbol):
            raise ComparisonInputError(
                "UNSUPPORTED_ASSET_TYPE",
                f"A supports stocks only; unsupported symbol: {symbol}",
                field,
            )
    if canonical_a == canonical_b:
        raise ComparisonInputError(
            "DUPLICATE_TICKER",
            f"tickers resolve to the same canonical symbol: {canonical_a}",
            "ticker_b",
        )
    canonical_date = _validate_analysis_date(analysis_date)
    return canonical_a, canonical_b, canonical_date


def _failure_reason(code: str) -> str:
    message = _SAFE_FAILURE_MESSAGES.get(code, "Comparison failed.")
    return f"{code}: {message}"


def _failed(
    ticker: str,
    analysis_date: str,
    code: str,
) -> SingleRunResult:
    return SingleRunResult(
        ticker=ticker,
        analysis_date=analysis_date,
        status="FAILED",
        final_rating=None,
        summary=None,
        report_path=None,
        failure_reason=_failure_reason(code),
    )


def _authoritative_rating(final_state: dict, signal: object) -> str | None:
    state_rating = final_state.get("final_rating")
    if isinstance(state_rating, str) and state_rating in _ALLOWED_RATINGS:
        return state_rating
    if isinstance(signal, str) and signal in _ALLOWED_RATINGS:
        return signal
    return None


def _normalize_summary(summary: str) -> str:
    collapsed = " ".join(summary.split())
    return collapsed[:500] if collapsed else _SUMMARY_FALLBACK


def _executive_summary(text: str) -> str | None:
    marker = "**Executive Summary**:"
    collected: list[str] = []
    collecting = False
    for line in text.splitlines():
        stripped = line.strip()
        if not collecting:
            if stripped.startswith(marker):
                collecting = True
                remainder = stripped[len(marker):].strip()
                if remainder:
                    collected.append(remainder)
            continue
        if stripped.startswith("**") and "**:" in stripped:
            break
        collected.append(line)
    summary = " ".join(" ".join(collected).split())
    return summary or None


def _first_paragraph(text: str) -> str | None:
    for block in re.split(r"\n\s*\n", text.strip()):
        collapsed = " ".join(block.split())
        if collapsed:
            return collapsed
    return None


def _summary_for(final_state: dict, rating: str) -> str:
    text = str(final_state.get("final_trade_decision") or "")
    mode = final_state.get("decision_mode", "standard")
    if rating == "REVIEW" and mode == "team":
        message = final_state.get("eligibility_message")
        if isinstance(message, str) and message.strip():
            return _normalize_summary(message)
    if rating != "REVIEW":
        summary = _executive_summary(text)
        if summary:
            return _normalize_summary(summary)
    paragraph = _first_paragraph(text)
    if paragraph:
        return _normalize_summary(paragraph)
    return _SUMMARY_FALLBACK


def _relative_report_path(saved: object, results_root: object, ticker: str) -> str:
    saved_path = Path(saved)
    root = Path(str(results_root))
    if saved_path.is_symlink() or saved_path.parent.is_symlink():
        raise _ReportAttributionError(f"report path uses a symlink: {saved_path}")
    resolved_saved = saved_path.resolve(strict=True)
    resolved_root = root.resolve(strict=True)
    try:
        relative = resolved_saved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"report path escapes results_dir: {saved_path}") from exc
    if not resolved_saved.is_file():
        raise ValueError(f"complete_report.md not found: {saved_path}")
    expected_dir = re.compile(
        rf"^{re.escape(safe_ticker_component(ticker))}_\d{{8}}_\d{{6}}$"
    )
    parts = relative.parts
    if (
        len(parts) != 3
        or parts[0] != "reports"
        or parts[2] != "complete_report.md"
        or not expected_dir.fullmatch(parts[1])
    ):
        raise _ReportAttributionError(
            f"report path does not belong to {ticker}: {relative.as_posix()}"
        )
    return relative.as_posix()


def run_one(
    graph: _GraphLike,
    ticker: str,
    analysis_date: str,
) -> SingleRunResult:
    """Run one validated ticker and isolate its failure from the other ticker."""
    try:
        final_state, signal = graph.propagate(ticker, analysis_date)
    except Exception:
        return _failed(ticker, analysis_date, "GRAPH_FAILED")

    if not isinstance(final_state, dict):
        return _failed(ticker, analysis_date, "INTERNAL_ERROR")
    if (
        final_state.get("company_of_interest") != ticker
        or final_state.get("trade_date") != analysis_date
    ):
        return _failed(ticker, analysis_date, "RESULT_IDENTITY_MISMATCH")

    try:
        rating = _authoritative_rating(final_state, signal)
        if rating is None:
            return _failed(
                ticker,
                analysis_date,
                "MISSING_OR_INVALID_FINAL_RATING",
            )
        summary = _summary_for(final_state, rating)
    except Exception:
        return _failed(ticker, analysis_date, "INTERNAL_ERROR")

    try:
        saved = graph.save_reports(final_state, ticker)
    except Exception:
        return _failed(ticker, analysis_date, "REPORT_SAVE_FAILED")

    try:
        report_path = _relative_report_path(
            saved, graph.config["results_dir"], ticker
        )
    except _ReportAttributionError:
        return _failed(ticker, analysis_date, "REPORT_ATTRIBUTION_FAILED")
    except Exception:
        return _failed(ticker, analysis_date, "REPORT_SAVE_FAILED")

    return SingleRunResult(
        ticker=ticker,
        analysis_date=analysis_date,
        status="SUCCESS",
        final_rating=rating,
        summary=summary,
        report_path=report_path,
        failure_reason=None,
    )


_TABLE_HEADER = (
    "| ticker | analysis_date | status | final_rating | summary | "
    "report_path | failure_reason |"
)


def _overall_status(
    tickers: tuple[SingleRunResult, SingleRunResult],
) -> Literal["SUCCESS", "PARTIAL", "FAILED"]:
    successes = sum(row.status == "SUCCESS" for row in tickers)
    if successes == 2:
        return "SUCCESS"
    if successes == 1:
        return "PARTIAL"
    return "FAILED"


def _md_cell(value: object) -> str:
    if value is None:
        return "null"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _row_payload(row: SingleRunResult) -> dict[str, object]:
    return {
        "ticker": row.ticker,
        "analysis_date": row.analysis_date,
        "status": row.status,
        "final_rating": row.final_rating,
        "summary": row.summary,
        "report_path": row.report_path,
        "failure_reason": row.failure_reason,
    }


def _render_markdown(
    comparison_id: str,
    generated_at: str,
    overall_status: str,
    analysis_date: str,
    tickers: tuple[SingleRunResult, SingleRunResult],
) -> str:
    first, second = tickers
    lines = [
        f"# Same-day comparison: {first.ticker} vs {second.ticker} ({analysis_date})",
        "",
        f"- Comparison ID: `{comparison_id}`",
        f"- Generated at: {generated_at}",
        f"- Overall status: {overall_status}",
        "",
        _TABLE_HEADER,
        "|---|---|---|---|---|---|---|",
    ]
    for row in tickers:
        cells = [
            row.ticker,
            row.analysis_date,
            row.status,
            row.final_rating,
            row.summary,
            row.report_path,
            row.failure_reason,
        ]
        lines.append("| " + " | ".join(_md_cell(cell) for cell in cells) + " |")
    return "\n".join(lines) + "\n"


def _manifest_payload(
    comparison_id: str,
    analysis_date: str,
    generated_at: str,
    overall_status: str,
    tickers: tuple[SingleRunResult, SingleRunResult],
    comparison_report_path: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "comparison_id": comparison_id,
        "analysis_date": analysis_date,
        "generated_at": generated_at,
        "overall_status": overall_status,
        "tickers": [_row_payload(row) for row in tickers],
        "comparison_report_path": comparison_report_path,
    }


def run_comparison(
    graph: _GraphLike,
    ticker_a: str,
    ticker_b: str,
    analysis_date: str,
) -> ComparisonResult:
    """Run two validated tickers sequentially and write both comparison artifacts."""
    canonical_a, canonical_b, canonical_date = _validate_inputs(
        ticker_a, ticker_b, analysis_date
    )
    first = run_one(graph, canonical_a, canonical_date)
    second = run_one(graph, canonical_b, canonical_date)
    tickers = (first, second)

    comparison_id = f"cmp_{uuid.uuid4().hex}"
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    overall_status = _overall_status(tickers)
    results_root = Path(str(graph.config["results_dir"]))
    comparison_report_path = f"comparisons/{comparison_id}/comparison.md"
    manifest_path = f"comparisons/{comparison_id}/comparison_manifest.json"

    markdown = _render_markdown(
        comparison_id,
        generated_at,
        overall_status,
        canonical_date,
        tickers,
    )
    manifest = _manifest_payload(
        comparison_id,
        canonical_date,
        generated_at,
        overall_status,
        tickers,
        comparison_report_path,
    )

    folder = results_root / "comparisons" / comparison_id
    folder.mkdir(parents=True, exist_ok=True)
    (results_root / comparison_report_path).write_text(markdown, encoding="utf-8")
    (results_root / manifest_path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return ComparisonResult(
        comparison_id=comparison_id,
        analysis_date=canonical_date,
        generated_at=generated_at,
        overall_status=overall_status,
        tickers=tickers,
        comparison_report_path=comparison_report_path,
        manifest_path=manifest_path,
    )
