"""Sort Regulation Asia articles into the five beats of the daily APAC
audio update: Fraud, Financial Crime, Prudential Risk, Infrastructure,
Digital Assets.

The mapping rides on Regulation Asia's own `topics` taxonomy rather than
keyword matching. That matters: the publisher already classifies every
article by category and subcategory, so using their labels means the
segmentation is exactly as good as their editorial desk, and it does not
drift when someone writes a headline in an unusual way.

Two decisions worth knowing about:

*Each article lands in exactly one beat.* Articles routinely carry three
or four subcategories, so bucketing by every match would have ALEX and
JORDAN discussing the same enforcement action in three separate
segments. `BEAT_PRIORITY` breaks the tie, financial-crime first,
Infrastructure last — Infrastructure is the broadest bucket and makes a
better fallback than a winner.

*Nothing is silently dropped.* Articles whose topics match no beat come
back under `UNMATCHED` so the script can close with a short "also on the
radar" rather than quietly binning a story. Today that is mostly AI Risk
& Governance, Data Privacy and Sustainability & ESG — real topics that
simply are not one of the five beats.
"""

from __future__ import annotations

import re
from typing import Iterable

FRAUD = "Fraud"
FINANCIAL_CRIME = "Financial Crime"
PRUDENTIAL_RISK = "Prudential Risk"
INFRASTRUCTURE = "Infrastructure"
DIGITAL_ASSETS = "Digital Assets"
UNMATCHED = "Also on the radar"

BEATS = [FRAUD, FINANCIAL_CRIME, PRUDENTIAL_RISK, INFRASTRUCTURE, DIGITAL_ASSETS]

# Order in which a multi-topic article is claimed. Fraud outranks the
# rest of Financial Crime because a scam story filed under both should
# lead the fraud segment, not disappear into general enforcement.
BEAT_PRIORITY = [
    FRAUD,
    FINANCIAL_CRIME,
    DIGITAL_ASSETS,
    PRUDENTIAL_RISK,
    INFRASTRUCTURE,
]

# (category, subcategory) pairs owned by each beat. Subcategory None
# means "the whole category".
_BEAT_TOPICS: dict[str, list[tuple[str, str | None]]] = {
    FRAUD: [
        # Deliberately just the one subcategory. Adding
        # "AI, Technology & Data / Cybersecurity" here was tried and
        # reverted: it pulled in a SEBI cyber-resilience consultation
        # and a Hong Kong banking reform agenda, neither of which is a
        # fraud story. RA's own subcategory already ends in
        # "& Cybercrime", so their desk has decided when cyber is fraud.
        ("Financial Crime", "Fraud, Scams & Cybercrime"),
    ],
    FINANCIAL_CRIME: [
        ("Financial Crime", None),
    ],
    PRUDENTIAL_RISK: [
        ("Prudential Risk", None),
    ],
    INFRASTRUCTURE: [
        ("Markets & Infrastructure", None),
        ("AI, Technology & Data", "Cloud & Infrastructure"),
    ],
    DIGITAL_ASSETS: [
        ("Digital Assets", None),
    ],
}

# Markets the update treats as APAC. Used to rank, not to exclude — a
# US sanctions designation that bites Asian trade partners belongs in an
# APAC update even though its jurisdiction reads "United States".
_APAC_MARKETS = (
    "singapore", "hong kong", "malaysia", "indonesia", "philippines",
    "japan", "korea", "australia", "new zealand", "india", "china",
    "thailand", "vietnam", "taiwan", "pakistan", "bangladesh", "brunei",
    "cambodia", "laos", "myanmar", "nepal", "sri lanka", "mongolia",
    "macau", "maldives", "bhutan", "papua new guinea", "apac",
    "asia-pacific", "asia pacific", "southeast asia", "asean",
)
_APAC_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(m) for m in _APAC_MARKETS) + r")\b"
)


def _topic_pairs(item) -> list[tuple[str, str]]:
    """Split flattened 'Category / Subcategory' strings back into pairs."""
    pairs: list[tuple[str, str]] = []
    for raw in (getattr(item, "topics", None) or []):
        cat, _, sub = str(raw).partition(" / ")
        pairs.append((cat.strip(), sub.strip()))
    return pairs


def beat_scores(item) -> dict[str, int]:
    """How many of the article's topics each beat claims.

    Counting rather than just testing for a match is what keeps a
    secondary tag from hijacking a story: a SEBI derivatives overhaul
    carrying two Markets & Infrastructure topics and one incidental
    "Market Abuse" belongs in Infrastructure, not the financial-crime
    segment."""
    scores: dict[str, int] = {}
    for cat, sub in _topic_pairs(item):
        for beat, owned in _BEAT_TOPICS.items():
            for own_cat, own_sub in owned:
                if cat != own_cat:
                    continue
                if own_sub is None or own_sub == sub:
                    scores[beat] = scores.get(beat, 0) + 1
    return scores


def matching_beats(item) -> list[str]:
    """Every beat this article's topics touch, unordered."""
    return sorted(beat_scores(item))


def assign_beat(item) -> str:
    """The single beat this article belongs to, or UNMATCHED.

    Strongest topic match wins; BEAT_PRIORITY only breaks genuine ties."""
    scores = beat_scores(item)
    if not scores:
        return UNMATCHED
    best = max(scores.values())
    for beat in BEAT_PRIORITY:
        if scores.get(beat) == best:
            return beat
    return UNMATCHED


def is_apac(item) -> bool:
    """True when the article names an APAC market anywhere we can see.

    Checks the inferred jurisdiction first, then falls back to scanning
    title, tags and body — Regulation Asia covers APAC, but a story can
    be filed under a non-APAC regulator while being entirely about its
    effect on Asian institutions."""
    if getattr(item, "jurisdiction", ""):
        return True
    hay = " ".join([
        getattr(item, "title", "") or "",
        " ".join(getattr(item, "tags", None) or []),
        (getattr(item, "content", "") or "")[:2000],
    ]).lower()
    return bool(_APAC_PATTERN.search(hay))


def bucket(
    items: Iterable,
    *,
    apac_only: bool = False,
) -> dict[str, list]:
    """Group articles by beat, newest first within each.

    Returns a dict keyed by every beat plus UNMATCHED, so callers can
    rely on the keys existing even on a quiet day. When `apac_only` is
    set, non-APAC articles are dropped entirely; the default keeps them
    but they sort below APAC ones so the segment leads on the region.
    """
    out: dict[str, list] = {b: [] for b in BEATS}
    out[UNMATCHED] = []

    for item in items:
        apac = is_apac(item)
        if apac_only and not apac:
            continue
        out[assign_beat(item)].append(item)

    for beat in out:
        out[beat].sort(
            key=lambda i: (
                0 if is_apac(i) else 1,
                # published is an ISO date string; reverse-sort it by
                # inverting the comparison via a tuple on the negated
                # ordinal is overkill — descending string sort is enough.
                _descending(getattr(i, "published", "") or ""),
            )
        )
    return out


def _descending(iso_date: str) -> tuple:
    """Sort key that orders ISO date strings newest-first."""
    # Invert each character's ordinal so a plain ascending sort yields
    # descending dates, without needing reverse=True on a mixed key.
    return tuple(-ord(c) for c in iso_date)


def summarise(buckets: dict[str, list]) -> str:
    """One-line-per-beat count, for logs and preflight output."""
    lines = []
    for beat in BEATS + [UNMATCHED]:
        items = buckets.get(beat, [])
        apac = sum(1 for i in items if is_apac(i))
        lines.append(f"{beat:<20} {len(items):>3} ({apac} APAC)")
    return "\n".join(lines)
