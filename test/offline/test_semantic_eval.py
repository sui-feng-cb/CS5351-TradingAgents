"""Pairwise semantic-evaluation metrics and threshold gate (NFR-B-3).

Reads the frozen, human-labeled evaluation set ``test/fixtures/semantic_eval.json``
(v1) and measures the pairwise precision / recall of a *grouping* produced by a
model. Definitions are frozen in ``docs/architecture/evaluation-table.md`` §3:

    TP = labeled same_event  AND  both records grouped into the same event
    FP = labeled different_event  BUT  both records grouped together
    FN = labeled same_event  BUT  records not grouped together

    precision = TP / (TP + FP)   (threshold >= 0.80)
    recall    = TP / (TP + FN)   (threshold >= 0.70)

This is an **offline** gate: it never calls a real model or network. It verifies
the metric computation and the threshold-gate logic using two mock models:

  * ``merge_by_label``  — the "perfect" model: groups each same_event pair into
    its own event and leaves every different_event pair unmerged. Expected
    precision == 1.0 and recall == 1.0 (gate passes).
  * ``merge_all`` / ``merge_none`` — "wrong" models that merge everything or
    nothing, expected to fall below threshold and trigger the gate.

Running this file directly (``python3 test/offline/test_semantic_eval.py``) prints
the measured precision/recall and exits non-zero if the gate blocks, so it doubles
as the CI semantic-evaluation gate step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SEMANTIC_EVAL_PATH = FIXTURES_DIR / "semantic_eval.json"
MOCK_OUTPUTS_PATH = FIXTURES_DIR / "mock_model_outputs.json"

PRECISION_THRESHOLD = 0.80
RECALL_THRESHOLD = 0.70


@dataclass
class EvalRecord:
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
    def from_dict(cls, data: dict) -> EvalRecord:
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
class EvalPair:
    """One labeled pair of records plus the human ``same_event`` judgment."""

    pair_id: str
    same_event: bool
    records: list[EvalRecord] = field(default_factory=list)

    @property
    def record_a(self) -> EvalRecord:
        return self.records[0]

    @property
    def record_b(self) -> EvalRecord:
        return self.records[1]


@dataclass
class PairwiseMetrics:
    precision: float
    recall: float
    tp: int
    fp: int
    fn: int


class SemanticGateError(Exception):
    """Raised when pairwise precision / recall falls below the threshold."""


def load_eval_pairs(path: Path = SEMANTIC_EVAL_PATH) -> list[EvalPair]:
    """Load the frozen semantic evaluation set into :class:`EvalPair` objects."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalPair(
            pair_id=item["pair_id"],
            same_event=bool(item["same_event"]),
            records=[EvalRecord.from_dict(r) for r in item["records"]],
        )
        for item in data["pairs"]
    ]


def compute_pairwise_metrics(
    pairs: list[EvalPair],
    grouping: dict[str, str],
) -> PairwiseMetrics:
    """Compute pairwise precision / recall for a model grouping.

    ``grouping`` maps ``evidence_id -> event_id``. Records absent from the map are
    treated as unmerged. Two records are "grouped" iff both are present and share
    the same ``event_id``.
    """
    tp = fp = fn = 0
    for pair in pairs:
        a = pair.record_a.evidence_id
        b = pair.record_b.evidence_id
        grouped = a in grouping and b in grouping and grouping[a] == grouping[b]
        if pair.same_event and grouped:
            tp += 1
        elif not pair.same_event and grouped:
            fp += 1
        elif pair.same_event and not grouped:
            fn += 1
        # different_event and not grouped -> true negative (not counted)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return PairwiseMetrics(precision=precision, recall=recall, tp=tp, fp=fp, fn=fn)


def evaluate_gate(
    metrics: PairwiseMetrics,
    precision_threshold: float = PRECISION_THRESHOLD,
    recall_threshold: float = RECALL_THRESHOLD,
) -> bool:
    """Return ``True`` when both thresholds are met, else raise :class:`SemanticGateError`."""
    if metrics.precision < precision_threshold:
        raise SemanticGateError(
            f"pairwise precision {metrics.precision:.4f} < {precision_threshold}"
        )
    if metrics.recall < recall_threshold:
        raise SemanticGateError(
            f"pairwise recall {metrics.recall:.4f} < {recall_threshold}"
        )
    return True


def merge_by_label(pairs: list[EvalPair]) -> dict[str, str]:
    """Perfect mock model: group each same_event pair; leave different_event pairs unmerged."""
    grouping: dict[str, str] = {}
    for pair in pairs:
        if pair.same_event:
            grouping[pair.record_a.evidence_id] = pair.pair_id
            grouping[pair.record_b.evidence_id] = pair.pair_id
    return grouping


def merge_all(pairs: list[EvalPair]) -> dict[str, str]:
    """Wrong mock model: force every record into a single event."""
    grouping: dict[str, str] = {}
    for pair in pairs:
        grouping[pair.record_a.evidence_id] = "single_event"
        grouping[pair.record_b.evidence_id] = "single_event"
    return grouping


def merge_none(pairs: list[EvalPair]) -> dict[str, str]:
    """Wrong mock model: merge nothing (every record unmerged)."""
    return {}


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

@pytest.mark.offline
def test_fixture_has_minimum_pairs_and_version():
    """NFR-B-3: the eval set is v1 with >=20 pairs (>=10 same / >=10 different)."""
    data = json.loads(SEMANTIC_EVAL_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "v1"
    pairs = load_eval_pairs()
    assert len(pairs) >= 20
    same = [p for p in pairs if p.same_event]
    different = [p for p in pairs if not p.same_event]
    assert len(same) >= 10
    assert len(different) >= 10


@pytest.mark.offline
def test_every_pair_has_two_cross_ticker_records():
    """NFR-B-3: each pair is a cross-ticker pair with two complete records."""
    pairs = load_eval_pairs()
    for pair in pairs:
        assert len(pair.records) == 2
        assert pair.record_a.ticker != pair.record_b.ticker
        for record in pair.records:
            assert record.evidence_id
            assert record.ticker
            assert record.date
            assert record.source
            assert record.title


@pytest.mark.offline
def test_distractor_types_are_present():
    """NFR-B-3: the four required distractor classes are present."""
    data = json.loads(SEMANTIC_EVAL_PATH.read_text(encoding="utf-8"))
    distractors = data.get("distractors", {})
    assert set(distractors) == {
        "same_ticker_duplicate",
        "out_of_window",
        "no_data",
        "insufficient_evidence",
    }
    assert distractors["same_ticker_duplicate"]["records"][0]["ticker"] == \
        distractors["same_ticker_duplicate"]["records"][1]["ticker"]
    assert distractors["no_data"]["records"] == []
    assert len(distractors["insufficient_evidence"]["records"]) == 1


@pytest.mark.offline
def test_perfect_model_precision_recall_are_one():
    """NFR-B-3: the label-driven perfect model yields precision == recall == 1.0."""
    pairs = load_eval_pairs()
    metrics = compute_pairwise_metrics(pairs, merge_by_label(pairs))
    assert metrics.tp == sum(1 for p in pairs if p.same_event)
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert evaluate_gate(metrics) is True


@pytest.mark.offline
def test_wrong_model_merge_all_blocks_on_precision():
    """NFR-B-3: a model that merges everything falls below the precision threshold."""
    pairs = load_eval_pairs()
    metrics = compute_pairwise_metrics(pairs, merge_all(pairs))
    assert metrics.precision < PRECISION_THRESHOLD
    with pytest.raises(SemanticGateError):
        evaluate_gate(metrics)


@pytest.mark.offline
def test_wrong_model_merge_none_blocks_on_recall():
    """NFR-B-3: a model that merges nothing falls below the recall threshold."""
    pairs = load_eval_pairs()
    metrics = compute_pairwise_metrics(pairs, merge_none(pairs))
    assert metrics.recall < RECALL_THRESHOLD
    with pytest.raises(SemanticGateError):
        evaluate_gate(metrics)


@pytest.mark.offline
def test_mock_model_outputs_fixture_is_well_formed():
    """The mock model-outputs fixture covers the required categories."""
    data = json.loads(MOCK_OUTPUTS_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "v1"
    cases = data["cases"]
    assert {"legal_grouping", "single_ticker", "no_events", "forged_id", "cross_run_id"} \
        <= set(cases)
    assert cases["no_events"]["events"] == []
    assert len(cases["legal_grouping"]["events"][0]["tickers"]) >= 2
    assert len(cases["single_ticker"]["events"][0]["tickers"]) == 1


# --------------------------------------------------------------------------- #
# Standalone CI gate: python3 test/offline/test_semantic_eval.py
# --------------------------------------------------------------------------- #

def _run_gate() -> int:
    pairs = load_eval_pairs()

    perfect = compute_pairwise_metrics(pairs, merge_by_label(pairs))
    print(
        "perfect mock model: "
        f"TP={perfect.tp} FP={perfect.fp} FN={perfect.fn} "
        f"precision={perfect.precision:.4f} recall={perfect.recall:.4f}"
    )
    evaluate_gate(perfect)

    wrong_all = compute_pairwise_metrics(pairs, merge_all(pairs))
    print(
        "wrong mock model (merge all): "
        f"TP={wrong_all.tp} FP={wrong_all.fp} FN={wrong_all.fn} "
        f"precision={wrong_all.precision:.4f} recall={wrong_all.recall:.4f}"
    )
    try:
        evaluate_gate(wrong_all)
        print("ERROR: wrong model unexpectedly passed the gate")
        return 1
    except SemanticGateError as exc:
        print(f"gate correctly blocked wrong model: {exc}")

    wrong_none = compute_pairwise_metrics(pairs, merge_none(pairs))
    print(
        "wrong mock model (merge none): "
        f"TP={wrong_none.tp} FP={wrong_none.fp} FN={wrong_none.fn} "
        f"precision={wrong_none.precision:.4f} recall={wrong_none.recall:.4f}"
    )
    try:
        evaluate_gate(wrong_none)
        print("ERROR: wrong model unexpectedly passed the gate")
        return 1
    except SemanticGateError as exc:
        print(f"gate correctly blocked wrong model: {exc}")

    print("semantic eval gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_gate())
