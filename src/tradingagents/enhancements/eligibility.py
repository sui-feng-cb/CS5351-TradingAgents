"""Deterministic team-mode decision qualification (FR-D, NFR-D, ADR-002, INV-D)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from tradingagents.agents.rating import RATING_REVIEW, RATINGS_5_TIER
from tradingagents.dataflows.vendors.yahoo.ohlcv import MAX_OHLCV_STALE_DAYS


@dataclass(frozen=True)
class EligibilityDecision:
    """The immutable authoritative outcome of the FR-D qualification check."""

    final_rating: str
    eligible: bool
    reason_codes: tuple[str, ...]
    user_message: str


_REASON_TEXT = {
    "market_analyst_not_run": "the market analyst did not run",
    "market_analyst_failed": "the market analyst failed",
    "market_analyst_invalid_status": "the market analyst status is invalid",
    "market_evidence_missing": "critical market evidence is missing",
    "market_evidence_not_run": "critical market evidence was not acquired",
    "market_evidence_unavailable": "critical market evidence is unavailable",
    "market_evidence_invalid_status": "the market evidence status is invalid",
    "market_snapshot_date_missing": "the market snapshot date is missing",
    "market_snapshot_date_invalid": "the market snapshot date is invalid",
    "market_snapshot_after_analysis": "the market snapshot is after the analysis date",
    "market_snapshot_stale": "the market snapshot is stale",
    "analysis_date_invalid": "the analysis date is invalid",
    "invalid_rating": "the candidate rating is not one of the five allowed values",
}


def _canonical_date(value: object) -> date | None:
    """Parse only canonical ISO calendar dates; malformed metadata fails closed."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def evaluate_eligibility(
    *,
    decision_mode: str,
    candidate_rating: str | None,
    market_analyst_status: str | None,
    market_evidence_status: str | None,
    snapshot_date: str | None,
    analysis_date: str | None,
) -> EligibilityDecision:
    """Qualify a team-mode candidate using only typed status/date metadata.

    Reason order and exact rating values implement FR-D and INV-D. The existing
    OHLCV freshness constant supplies the inclusive calendar-day bound (ADR-002).
    """
    if decision_mode != "team":
        raise ValueError("evaluate_eligibility is only valid for decision_mode='team'")

    reasons: list[str] = []

    if market_analyst_status in (None, "not_run"):
        reasons.append("market_analyst_not_run")
    elif market_analyst_status == "failed":
        reasons.append("market_analyst_failed")
    elif market_analyst_status != "completed":
        reasons.append("market_analyst_invalid_status")

    if market_evidence_status is None:
        reasons.append("market_evidence_missing")
    elif market_evidence_status == "not_run":
        reasons.append("market_evidence_not_run")
    elif market_evidence_status == "unavailable":
        reasons.append("market_evidence_unavailable")
    elif market_evidence_status != "valid":
        reasons.append("market_evidence_invalid_status")

    parsed_analysis_date = _canonical_date(analysis_date)
    if market_evidence_status == "valid":
        if snapshot_date is None:
            reasons.append("market_snapshot_date_missing")
        else:
            parsed_snapshot_date = _canonical_date(snapshot_date)
            if parsed_snapshot_date is None:
                reasons.append("market_snapshot_date_invalid")
            elif parsed_analysis_date is not None:
                if parsed_snapshot_date > parsed_analysis_date:
                    reasons.append("market_snapshot_after_analysis")
                elif (parsed_analysis_date - parsed_snapshot_date).days > MAX_OHLCV_STALE_DAYS:
                    reasons.append("market_snapshot_stale")

    if parsed_analysis_date is None:
        reasons.append("analysis_date_invalid")

    if candidate_rating not in RATINGS_5_TIER:
        reasons.append("invalid_rating")

    if not reasons:
        return EligibilityDecision(
            final_rating=candidate_rating,
            eligible=True,
            reason_codes=(),
            user_message="",
        )

    descriptions = "; ".join(_REASON_TEXT[code] for code in reasons)
    return EligibilityDecision(
        final_rating=RATING_REVIEW,
        eligible=False,
        reason_codes=tuple(reasons),
        user_message=f"Review required: {descriptions}.",
    )
