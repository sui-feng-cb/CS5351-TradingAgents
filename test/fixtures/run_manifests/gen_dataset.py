"""Deterministic, versioned generator of synthetic run manifests (NFR-C).

Requirement: NFR-C (query 1,000 synthetic manifests within the approved CI
timing budget). The generated data is synthetic; it is not probe of upstream
models or vendors and makes no network call.

Usage:
    python test/fixtures/run_manifests/gen_dataset.py --out DIR --count 1000

The seed and generator version are fixed so a dataset can be regenerated
byte-for-byte and a measurement can be attributed to it. Each manifest is a
valid ``run_manifest.json`` per the C v1 contract, placed at
``<out>/<ticker>/<trade_date>-<index>/run_manifest.json`` so the local-scan
query walks the same layout a real results root has. Every ``reports`` path is
relative to the results root (``<out>``) and points at a file this generator
actually writes; ``finished_at`` is never earlier than ``started_at``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

GENERATOR_VERSION = 2
DEFAULT_SEED = 20261120

_TICKERS = ("AAPL", "MSFT", "NVDA", "0700.HK", "TSLA", "AMD", "GOOGL", "AMZN")
_ANALYSTS = ("market", "news", "fundamentals", "social")
_PROVIDERS = ("openai", "deepseek", "google", "anthropic")
_VENDORS = ("yfinance", "alpha_vantage", "local", "unavailable")


def _draw(seed: int, index: int, salt: str) -> int:
    """A deterministic 64-bit draw for ``(seed, index, salt)``.

    Independent of the process and of ``random``'s implementation, so a dataset
    regenerates byte-for-byte on any interpreter. Mixing the index into every
    draw keeps fields from collapsing onto one value across rows.
    """

    digest = hashlib.sha256(f"{seed}:{index}:{salt}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _run_rel_dir(ticker: str, trade_date: str, index: int) -> str:
    """The run's directory relative to the results root, as POSIX segments."""

    return f"{ticker}/{trade_date}-{index:04d}"


def _manifest(seed: int, index: int, base_date: str) -> dict:
    ticker = _TICKERS[_draw(seed, index, "ticker") % len(_TICKERS)]
    provider = _PROVIDERS[_draw(seed, index, "deep") % len(_PROVIDERS)]
    quick = _PROVIDERS[_draw(seed, index, "quick") % len(_PROVIDERS)]
    day = int(base_date[-2:]) + (index % 28)
    trade_date = f"{base_date[:8]}{min(day, 28):02d}"
    failed = _draw(seed, index, "failed") % 7 == 0
    run_id = str(uuid.UUID(int=_draw(seed, index, "run_id")))

    # A fixed start, with a finish that is always 30 minutes later, so
    # finished_at is never earlier than started_at regardless of the index.
    started = datetime.strptime(trade_date, "%Y-%m-%d").replace(
        hour=12, minute=index % 60, second=0)
    finished = started + timedelta(minutes=30)

    # Report paths are relative to the results root and name files this
    # generator writes under the run directory.
    run_rel = _run_rel_dir(ticker, trade_date, index)
    return {
        "schema_version": 1,
        "run_id": run_id,
        "ticker": ticker,
        "asset_type": "stock",
        "trade_date": trade_date,
        "as_of": trade_date,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_version": "0.7.1",
        "analysts": list(_ANALYSTS),
        "models": {
            "deep": {"provider": provider, "model": f"{provider}-deep"},
            "quick": {"provider": quick, "model": f"{quick}-quick"},
        },
        "configured_data_vendors": {
            "core_stock_apis": _VENDORS[_draw(seed, index, "vendor_core") % len(_VENDORS)],
            "news_data": _VENDORS[_draw(seed, index, "vendor_news") % len(_VENDORS)],
        },
        "status": "failed" if failed else "succeeded",
        "reports": {
            "complete_report_md": None if failed else f"{run_rel}/reports/complete_report.md",
            "complete_report_html": None if failed else f"{run_rel}/reports/complete_report.html",
        },
        "error": {"code": "no_data", "message": "synthetic failure"} if failed else None,
        "unknown_fields": [],
    }


def generate(out_dir: Path, count: int, seed: int = DEFAULT_SEED) -> list[Path]:
    """Write ``count`` manifests under ``out_dir``; return the written paths."""
    written: list[Path] = []
    for index in range(count):
        data = _manifest(seed, index, "2026-11-01")
        run_dir = out_dir / _run_rel_dir(data["ticker"], data["trade_date"], index)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "run_manifest.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        if data["status"] == "succeeded":
            reports = run_dir / "reports"
            reports.mkdir(exist_ok=True)
            (reports / "complete_report.md").write_text("synthetic\n", encoding="utf-8")
            (reports / "complete_report.html").write_text(
                "<html><body>synthetic</body></html>\n", encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="results root to populate")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    written = generate(args.out, args.count, args.seed)
    print(f"generator v{GENERATOR_VERSION}: wrote {len(written)} manifests to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
