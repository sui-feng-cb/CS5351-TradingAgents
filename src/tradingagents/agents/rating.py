"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (Buy, Overweight, Hold, Underweight, Sell) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision; its free-text fallback is read here)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.

``extract_rating`` returns ``None`` when no rating can be found, and every
caller turns that into ``REVIEW`` rather than a tradeable position: a decision
nobody can read is not a Hold, and a Hold recorded in its place is quoted back to
the next run as a call that was never made (#1170).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline, escape, newline
from markdown_it.tree import SyntaxTreeNode

# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: tuple[str, ...] = (
    "Buy", "Overweight", "Hold", "Underweight", "Sell",
)

# Signal emitted when the model's decision has no recognizable rating. It is not
# a tradeable position: it flags output that needs a human/re-run rather than
# silently degrading to Hold. Callers that map the signal onto the 5-tier enum
# (e.g. ``PortfolioRating(signal)``) should guard with ``is_review`` first.
RATING_REVIEW = "REVIEW"

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Matches "Rating: X" / "rating - X" / "Rating — **X**" — tolerates markdown
# bold wrappers and any dash or colon a model writes as the separator. "rating"
# must start a word, so "Operating margin: Sell-side" is not a label.
_RATING_LABEL_RE = re.compile(r"(?<![a-z])rating\b[^:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*(\w+)",
                              re.IGNORECASE)

# The decision's own rating line, in the shape the Portfolio Manager is asked to
# open with ("- **Rating**: X", "**Final Rating**: X", "## Our rating - X"): an
# optional list marker, emphasis and heading marks, and only words naming the
# decision itself before "rating". "Consensus rating: Buy" or "Trader's rating:
# Buy" is someone else's rating.
_OWN_QUALIFIER = r"(?:(?:final|our|overall|my|recommended|updated|revised|new|current)\s+)*"
_RATING_LINE_RE = re.compile(
    r"\s*(?P<item>(?:[-+*\u2022]|\d+[.)])\s+)?[\s*_#]*" + _OWN_QUALIFIER
    + r"rating[^\w:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*(?P<value>\w+)",
    re.IGNORECASE,
)

# A line presenting the scale rather than a decision ("Rating Scale: Buy, ...").
_RATING_SCALE_RE = re.compile(r"rating\s*(scale|options|legend)", re.IGNORECASE)

def extract_rating(text: str) -> str | None:
    """Extract a 5-tier rating from its label, or ``None`` if there is none.

    Reads an explicit "Rating: X" label (tolerant of markdown bold) in the
    NFKC-normalized text, so fullwidth punctuation like ``Rating：Overweight``
    matches as ASCII does: the decision's opening rating line, else its own
    rating lines or, failing those, every label, when they agree.
    """
    if not text:
        return None
    norm = unicodedata.normalize("NFKC", text)

    # The decision is asked to open with its rating, so a first line (after any
    # headings) in that shape is the call. A list item there may also be a quote
    # heading a list of other parties' ratings, so it counts with the decision's
    # other rating lines, which leave out list items; failing those, every label
    # counts. Either way they must agree: ratings that differ, with nothing
    # marking which one is the call, are no call (#1170). Lines presenting the
    # scale itself are a legend the model echoed, not a call.
    lines = [line for line in norm.splitlines() if line.strip() and not _RATING_SCALE_RE.search(line)]
    first = next((line for line in lines if not line.lstrip().startswith("#")
                  or _RATING_LINE_RE.match(line)), "")
    m = _RATING_LINE_RE.match(first)
    opening = m if m and m.group("value").lower() in _RATING_SET else None
    if opening and not opening.group("item"):
        return opening.group("value").capitalize()

    own = [opening.group("value").capitalize()] if opening else []
    labels = []
    for line in lines:
        m = _RATING_LINE_RE.match(line)
        if m and not m.group("item") and m.group("value").lower() in _RATING_SET:
            own.append(m.group("value").capitalize())
        labels += [v.capitalize() for v in _RATING_LABEL_RE.findall(line) if v.lower() in _RATING_SET]
    # Without a label there is no call to read: a rating word in the prose may be
    # one the text argues against ("not a Sell"), and reading it reports a
    # direction nobody decided.
    found = own or labels
    return found[0] if found and len(set(found)) == 1 else None


def parse_rating(text: str, default: str = RATING_REVIEW) -> str:
    """Extract a 5-tier rating, or ``REVIEW`` when the decision has none.

    For callers that need a string for every decision, such as the memory log's
    entry tag. The default is the review sentinel, never a tradeable rating.
    """
    rating = extract_rating(text)
    return rating if rating is not None else default


_TEAM_RATING_LINE_RE = re.compile(
    r"\s*(?:(?:[-+*\u2022]|\d+[.)])\s+)?[\s*_#]*" + _OWN_QUALIFIER
    + r"rating\b[\s*_]*[:\-\u2010-\u2015]\s*(?P<value>.*?)\s*",
    re.IGNORECASE,
)
_TEAM_RATING_MARKDOWN = MarkdownIt("commonmark")


def _team_rating_break(state: StateInline, silent: bool) -> bool:
    """Record source offsets for real CommonMark inline breaks (ADR-002, INV-D)."""
    offset = state.pos
    if state.src[offset] == "\n":
        matched = newline(state, silent)
    elif state.src.startswith("\\\n", offset):
        matched = escape(state, silent)
    else:
        return False
    if matched and not silent:
        state.tokens[-1].meta["rating_break_span"] = (offset, state.pos)
    return matched


_TEAM_RATING_MARKDOWN.inline.ruler.before("newline", "team_rating_break", _team_rating_break)


def _team_rating_lines(text: str) -> Iterator[str]:
    """Yield candidate fields from ordinary Markdown blocks (ADR-002, INV-D)."""
    root = SyntaxTreeNode(_TEAM_RATING_MARKDOWN.parse(text))
    for outer in root.children:
        blocks = (
            (block for item in outer.children for block in item.children)
            if outer.type in {"bullet_list", "ordered_list"}
            else (outer,)
        )
        for block in blocks:
            if block.type not in {"paragraph", "heading"}:
                continue
            inline = block.children[0].token
            start = 0
            # Keep the raw spelling and wrappers on each visible line. Source
            # newlines consumed by inline code or other markup cannot start a
            # field or turn adjacent fragments into an exact value.
            for token in inline.children or ():
                span = token.meta.get("rating_break_span")
                if span is not None:
                    stop, next_start = span
                    yield inline.content[start:stop].replace("\n", "\ufffc")
                    start = next_start
            yield inline.content[start:].replace("\n", "\ufffc")


def parse_team_rating(text: str) -> str:
    """Read exact model-owned rating fields for FR-D/ADR-002/INV-D.

    Markdown wrappers are presentation only. Values are case-sensitive and must
    occupy the entire field; consensus labels never supply a missing own rating.
    Code blocks and quotations do not supply own fields. Every own field must be
    valid and agree. Standard parse_rating is unchanged.
    """
    if not isinstance(text, str):
        return RATING_REVIEW
    own = []
    for line in _team_rating_lines(text):
        match = _TEAM_RATING_LINE_RE.fullmatch(line)
        if match is None:
            continue
        value = match.group("value")
        for wrapper in ("**", "__", "*", "_", "`"):
            if value.startswith(wrapper) and value.endswith(wrapper) and len(value) > 2 * len(wrapper):
                value = value[len(wrapper):-len(wrapper)].strip()
                break
        if value not in RATINGS_5_TIER:
            return RATING_REVIEW
        own.append(value)
    return own[0] if own and len(set(own)) == 1 else RATING_REVIEW


def run_rating(final_state: dict) -> str:
    """A finished run's rating: the Portfolio Manager's own, else read from its decision.

    The fallback serves a state without ``final_rating``, such as a run an older
    version completed and a checkpoint hands back unchanged.
    """
    return final_state.get("final_rating") or parse_rating(final_state.get("final_trade_decision", ""))


def is_review(signal: str) -> bool:
    """Whether a signal is the non-tradeable REVIEW sentinel (#1170)."""
    return signal == RATING_REVIEW
