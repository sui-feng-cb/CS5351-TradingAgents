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


@pytest.mark.unit
@pytest.mark.parametrize("text, expected", [
    pytest.param("    Rating: Buy", "REVIEW", id="indented-code"),
    pytest.param("\tRating: Buy", "REVIEW", id="tab-indented-code"),
    pytest.param("~~~text\n```\nRating: Buy\n~~~", "REVIEW", id="mixed-fence"),
    pytest.param("````text\n```\nRating: Buy\n````", "REVIEW", id="short-closer"),
    pytest.param("~~~\n~~~text\nRating: Buy\n~~~", "REVIEW", id="closer-with-text"),
    pytest.param("```\nRating: Buy\n```", "REVIEW", id="ordinary-fence"),
    pytest.param("- Example:\n\n      Rating: Buy", "REVIEW", id="list-indented-code"),
    pytest.param("`Example\nRating: Buy\nEnd`", "REVIEW", id="multiline-code-span"),
    pytest.param(
        "Rating: Strong Buy\n`example\ncontinued`\n\nRating: Buy",
        "REVIEW",
        id="visible-invalid-rating-before-multiline-code-span",
    ),
    pytest.param(
        "**Rating**: `Hold`  \n`example\nRating: Buy\ncontinued`",
        "Hold",
        id="visible-valid-rating-with-space-hardbreak",
    ),
    pytest.param(
        "Rating: Hold\\\n`example\nRating: Buy\ncontinued`",
        "Hold",
        id="visible-valid-rating-with-backslash-hardbreak",
    ),
    pytest.param("Rating: `Buy\n`", "REVIEW", id="multiline-code-cannot-supply-value"),
    pytest.param(
        "Rating: Strong Buy\n<!-- example\ncontinued -->\n\nRating: Buy",
        "REVIEW",
        id="inline-comment-cannot-hide-invalid-rating",
    ),
    pytest.param("<!--\nRating: Buy\n-->", "REVIEW", id="html-comment"),
    pytest.param("~~~text\n```\nRating: Buy\n~~~~\n\n- **Rating**: **Hold**", "Hold", id="real-rating-after-longer-closer"),
    pytest.param("    Rating: Buy\n\n## Final Rating: Hold", "Hold", id="real-rating-after-indented-code"),
])
def test_team_only_uses_rating_fields_outside_markdown_code(text, expected):
    """FR-D/INV-D: a Markdown example is not the PM's own rating."""
    from tradingagents.agents.rating import parse_team_rating

    assert parse_team_rating(text) == expected
