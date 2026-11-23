"""Single-call cross-ticker merge entry point + status state machine (FR-B-3/6).

:func:`merge_once` hands the *entire* record set to the model in one batch and
invokes ``llm`` exactly once (INV-B-1). The model's output is only a suggestion:
it is parsed into ``model_events`` and passed through the deterministic
:func:`event_merge.validator.validate`, which is the sole authority on what may
be emitted as a verified fact (INV-B-3 / INV-B-5).

Failure behaviour follows ``docs/architecture/runtime-policy-catalog.md``:
  - no records                          -> ``data_unavailable`` (no LLM call)
  - ``llm`` raises / output unparseable -> fail-closed, no verified facts
  - records but no common event         -> ``no_common_event``
"""

from __future__ import annotations

import json
from pathlib import Path

from .evidence import EvidenceRegistry
from .schemas import MergeResult, MergeStatus, NewsRecord
from .validator import validate

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_PROMPT_FILE = _PROMPTS_DIR / "event_merge_v1.md"

_INPUT_PLACEHOLDER = "{{INPUT_JSON}}"


def _load_prompt() -> str:
    return _PROMPT_FILE.read_text(encoding="utf-8")


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


def _build_prompt(records: list[NewsRecord], tickers, window, run_id: str) -> str:
    template = _load_prompt()
    payload = {
        "run_id": run_id,
        "tickers": list(tickers),
        "window_start": window[0],
        "window_end": window[1],
        "records": [record.to_dict() for record in records],
    }
    input_json = json.dumps(payload, ensure_ascii=False, indent=2)
    if _INPUT_PLACEHOLDER in template:
        return template.replace(_INPUT_PLACEHOLDER, input_json)
    return template + "\n\n## Input\n```json\n" + input_json + "\n```\n"


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
    """Fail-closed result: no events, every record left unmerged (RP-B-003/004)."""
    return MergeResult(
        status=MergeStatus.NO_COMMON_EVENT,
        run_id=registry.run_id,
        events=[],
        unmerged=list(records),
        dropped_invalid=[],
    )


def _default_llm():
    """Lazy, stage-2 structural placeholder for the upstream LLM client."""

    def _invoke(prompt: str) -> str:
        # Function-local import keeps heavy LLM SDKs off the offline import path.
        from tradingagents.llm_clients.factory import create_llm_client  # noqa: F401

        raise RuntimeError(
            "Default LLM is a stage-2 structural placeholder and is not wired to "
            "a network client; inject a `llm` callable (see merge_once) or wire "
            "the upstream create_llm_client in a later stage."
        )

    return _invoke


def merge_once(
    records: list[NewsRecord],
    tickers,
    window,
    *,
    llm=None,
) -> MergeResult:
    """Merge ``records`` into cross-ticker events with exactly one LLM call.

    Args:
        records: the full, single-batch set of :class:`NewsRecord`.
        tickers: the input ticker list (same order as the run).
        window: ``(window_start, window_end)`` from :func:`build_window`.
        llm: injectable ``callable(prompt) -> str``; defaults to the lazy
            upstream placeholder (not wired in stage 2).

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
