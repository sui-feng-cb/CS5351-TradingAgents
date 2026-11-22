"""FR-D/NFR-D/INV-D: exact model-owned free-text rating, independent of quotations."""

import pytest


@pytest.mark.unit
@pytest.mark.parametrize("rating", ["Buy", "Overweight", "Hold", "Underweight", "Sell"])
@pytest.mark.parametrize("template", ["Rating: {}", "- **Rating**: **{}**", "## Final Rating: {}"])
def test_team_accepts_exact_own_rating_with_markdown_and_unrelated_consensus(rating, template):
    from tradingagents.agents.rating import parse_team_rating

    assert parse_team_rating(template.format(rating) + "\n\nConsensus rating: Buy") == rating


@pytest.mark.unit
@pytest.mark.parametrize("own_text", [
    "Rating: Strong Buy", "Rating: Buy today", "Rating: buy", "Rating: BUY",
    "Rating: Buy / Sell", "Rating: REVIEW", "Rating:", "", "No own rating.",
    "Rating: Hold\nRating: Buy", "Rating: Strong Buy\nRating: Buy",
    "> Rating: Buy", "Rating Scale: Buy / Overweight / Hold / Underweight / Sell",
])
def test_team_rejects_invalid_missing_or_conflicting_own_rating_even_with_consensus(own_text):
    from tradingagents.agents.rating import parse_team_rating

    assert parse_team_rating(own_text + "\n\nConsensus rating: Buy") == "REVIEW"
