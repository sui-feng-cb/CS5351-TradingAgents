"""Live (real-model) pairwise semantic evaluation gate for NFR-B-3.

Companion to ``test/offline/test_semantic_eval.py``, which mocks the model and
only verifies the metric/gate logic. This file calls a **real** LLM once per
labeled pair (24 calls total) from the frozen evaluation set
``test/fixtures/semantic_eval.json`` and measures pairwise precision / recall.

Definitions are frozen in ``docs/architecture/evaluation-table.md`` §3:

    TP = labeled same_event AND model answers "same"
    FP = labeled different_event BUT model answers "same"
    FN = labeled same_event BUT model answers "different"

    precision = TP / (TP + FP)   (threshold >= 0.80)
    recall    = TP / (TP + FN)   (threshold >= 0.70)

If the gate fails, the test (or ``__main__``) exits non-zero, so this file also
doubles as the CI live semantic-evaluation step.

environment and network access. It is never run by the default offline CI.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SEMANTIC_EVAL_PATH = FIXTURES_DIR / "semantic_eval.json"

PRECISION_THRESHOLD = 0.80
RECALL_THRESHOLD = 0.70

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"

_VERDICT_RE = re.compile(r"\b(same|different)\b", re.IGNORECASE)


@dataclass
class Record:
    """A NewsRecord-shaped record inside the evaluation set."""

    evidence_id: str
    ticker: str
    date: str
    source: str
    title: str
    snippet: str = ""
    link: str = ""
    pub_date: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Record:
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
class Pair:
    """One labeled pair of records plus the human ``same_event`` judgment."""

    pair_id: str
    same_event: bool
    records: list[Record]

    @property
    def record_a(self) -> Record:
        return self.records[0]

    @property
    def record_b(self) -> Record:
        return self.records[1]

    @property
    def label(self) -> str:
        return "same" if self.same_event else "different"


@dataclass
class PairResult:
    """One pair's model verdict and any call failure."""

    pair_id: str
    label: str
    verdict: str
    error: str = ""

    @property
    def failed(self) -> bool:
        return bool(self.error)

    @property
    def is_true_positive(self) -> bool:
        return self.label == "same" and self.verdict == "same"

    @property
    def is_false_positive(self) -> bool:
        return self.label == "different" and self.verdict == "same"

    @property
    def is_false_negative(self) -> bool:
        return self.label == "same" and self.verdict == "different"


@dataclass
class LiveMetrics:
    precision: float
    recall: float
    tp: int
    fp: int
    fn: int
    attempted: int
    failed: int


def load_pairs(path: Path = SEMANTIC_EVAL_PATH) -> list[Pair]:
    """Load the ``pairs`` field of the frozen evaluation set."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Pair(
            pair_id=item["pair_id"],
            same_event=bool(item["same_event"]),
            records=[Record.from_dict(r) for r in item["records"]],
        )
        for item in data["pairs"]
    ]


def _build_prompt(pair: Pair) -> str:
    a, b = pair.record_a, pair.record_b
    return (
        "You are a news-event deduplication judge. Decide whether the two news "
        "records below describe the SAME underlying real-world event.\n\n"
        "Rules:\n"
        '- Answer "same" only if both records refer to one specific, concrete '
        "real-world event (the same announcement, decision, deal, disaster, "
        "ruling, recall, etc.), even if reported by different outlets or tied "
        "to different tickers.\n"
        '- Answer "different" if they are separate events, even when they share '
        "generic words, an industry, or similar wording (e.g. two unrelated "
        '"earnings beats", "dividend increases", "FDA approvals", "recalls", or '
        '"stock splits").\n'
        '- Do NOT merge two records merely because they share a broad category '
        "or industry.\n"
        '- Reply with exactly one word: "same" or "different".\n\n'
        f"Record A:\n- ticker: {a.ticker}\n- date: {a.date}\n- source: {a.source}\n"
        f"- title: {a.title}\n- snippet: {a.snippet}\n\n"
        f"Record B:\n- ticker: {b.ticker}\n- date: {b.date}\n- source: {b.source}\n"
        f"- title: {b.title}\n- snippet: {b.snippet}\n"
    )


def _parse_verdict(raw: str | None) -> str:
    """Extract ``same`` / ``different`` from the model answer, ignoring casing
    and surrounding characters. Returns ``""`` when no verdict is recognizable."""
    if not raw:
        return ""
    matches = _VERDICT_RE.findall(raw)
    lowered = [m.lower() for m in matches]
    if "different" in lowered:
        return "different"
    if "same" in lowered:
        return "same"
    return ""


def _call_model(client: OpenAI, model: str, prompt: str) -> str:
    """One real model call; returns the raw assistant text."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def run_live_eval(pairs: list[Pair]) -> tuple[list[PairResult], LiveMetrics]:
    """Call the real model once per pair and compute pairwise metrics.

    A pair whose call fails is recorded (reason preserved) and skipped; metrics
    are computed over the successfully judged subset only.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set; the live semantic-evaluation gate "
            "requires a real model call."
        )
    base_url = os.environ.get("EVAL_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("EVAL_MODEL", DEFAULT_MODEL)
    client = OpenAI(base_url=base_url, api_key=api_key)

    print(f"live semantic eval: model={model} base_url={base_url} pairs={len(pairs)}")

    results: list[PairResult] = []
    for pair in pairs:
        a, b = pair.record_a, pair.record_b
        try:
            raw = _call_model(client, model, _build_prompt(pair))
            verdict = _parse_verdict(raw)
            if not verdict:
                raise ValueError(f"unrecognized model answer: {raw!r}")
            result = PairResult(pair_id=pair.pair_id, label=pair.label, verdict=verdict)
        except Exception as exc:  # noqa: BLE001 - record and continue, never swallow
            result = PairResult(
                pair_id=pair.pair_id,
                label=pair.label,
                verdict="",
                error=f"{type(exc).__name__}: {exc}",
            )
            print(
                f"[{pair.pair_id}] FAILED {a.ticker}/{b.ticker} "
                f"label={pair.label} -> {result.error}"
            )
        results.append(result)
        if not result.failed:
            print(
                f"[{pair.pair_id}] label={result.label:<9} verdict={result.verdict:<9} "
                f"{a.ticker}({a.title}) vs {b.ticker}({b.title})"
            )

    tp = sum(1 for r in results if r.is_true_positive)
    fp = sum(1 for r in results if r.is_false_positive)
    fn = sum(1 for r in results if r.is_false_negative)
    attempted = len(results) - sum(1 for r in results if r.failed)
    failed = len(results) - attempted

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    metrics = LiveMetrics(
        precision=precision,
        recall=recall,
        tp=tp,
        fp=fp,
        fn=fn,
        attempted=attempted,
        failed=failed,
    )

    print(
        f"live semantic eval: TP={tp} FP={fp} FN={fn} "
        f"attempted={attempted} failed={failed} "
        f"precision={precision:.4f} recall={recall:.4f}"
    )
    return results, metrics


def _assert_gate(metrics: LiveMetrics) -> None:
    if metrics.precision < PRECISION_THRESHOLD:
        raise AssertionError(
            f"pairwise precision {metrics.precision:.4f} < {PRECISION_THRESHOLD}"
        )
    if metrics.recall < RECALL_THRESHOLD:
        raise AssertionError(
            f"pairwise recall {metrics.recall:.4f} < {RECALL_THRESHOLD}"
        )


def test_live_semantic_eval_gate():
    """NFR-B-3: real-model pairwise precision >= 0.80 and recall >= 0.70."""
    pairs = load_pairs()
    _, metrics = run_live_eval(pairs)
    _assert_gate(metrics)


if __name__ == "__main__":
    pairs = load_pairs()
    _, metrics = run_live_eval(pairs)
    try:
        _assert_gate(metrics)
    except AssertionError as exc:
        print(f"live semantic eval gate FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    print("live semantic eval gate: OK")
    raise SystemExit(0)
