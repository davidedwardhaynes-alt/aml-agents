"""Regulation Asia API adapter.

Regulation Asia is the region's most cited independent regulatory-
intelligence publication for APAC financial services. Their public
site blocks bot User-Agents (Cloudflare 403); real content access
requires a subscription and comes via one of three transports:

  1. **JSON API** (subscribers with API entitlement) — GET the
     `/api/v1/articles` endpoint with a Bearer token, filter by
     `since=<ISO-datetime>`, page through results.
  2. **Authenticated RSS feed** — a per-subscriber feed URL with an
     embedded token, e.g.
     `https://www.regulationasia.com/feed/premium/?token=…`.
     Compatible with the existing feedparser pipeline in `lib/news.py`.
  3. **Bulk XML export** — some enterprise seats get a daily XML dump
     via SFTP. Not implemented here; add if needed.

This module supports both (1) and (2). At runtime it picks whichever
transport has credentials configured, and silently no-ops if neither
is set (so the cron workflow stays green during the setup window).

Configuration (any ONE of the following, checked in order):

  Environment variable name          Meaning
  ---------------------------------  ------------------------------------
  REGULATION_ASIA_API_KEY            Bearer token for the JSON API.
  REGULATION_ASIA_API_URL            (optional) override endpoint. Default:
                                     https://www.regulationasia.com/api/v1/articles
  REGULATION_ASIA_FEED_URL           Full URL of an authenticated RSS feed
                                     (with embedded token). Used when the
                                     JSON API key isn't set.

Usage from the daily-briefing pipeline:

    from lib.regulation_asia import fetch_recent_articles
    items = fetch_recent_articles(since_hours=24, max_items=8)
    # items is a list[RegulationAsiaItem]; empty when no credentials
    # or when the API/feed is unreachable.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import json
import os
import re
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Any

DEFAULT_JSON_ENDPOINT = "https://www.regulationasia.com/api/v1/articles"
UA = (
    "AML-Agents-Daily/1.0 (+https://trustsphere.ai; "
    "regulation-asia-subscriber)"
)
DEFAULT_TIMEOUT = 20


@dataclass
class RegulationAsiaItem:
    title: str
    url: str
    summary: str
    published: str            # ISO date; may be empty
    author: str = ""
    tags: list[str] | None = None
    jurisdiction: str = ""    # inferred from tags where possible


# --------------------------------------------------------------------
# Configuration probe
# --------------------------------------------------------------------
def is_configured() -> bool:
    """True when either an API key or an authenticated feed URL is set."""
    return bool(
        os.getenv("REGULATION_ASIA_API_KEY")
        or os.getenv("REGULATION_ASIA_FEED_URL")
    )


def configured_transport() -> str:
    """Return which transport will be used ('api', 'rss', or 'none')."""
    if os.getenv("REGULATION_ASIA_API_KEY"):
        return "api"
    if os.getenv("REGULATION_ASIA_FEED_URL"):
        return "rss"
    return "none"


# --------------------------------------------------------------------
# Transport A: JSON API
# --------------------------------------------------------------------
def _http_get_json(url: str, headers: dict[str, str]) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _normalise_api_row(row: dict) -> RegulationAsiaItem | None:
    """Coerce one JSON row into RegulationAsiaItem. Return None on
    obviously-broken rows so downstream code can skip cleanly."""
    title = str(row.get("title") or row.get("headline") or "").strip()
    url = str(row.get("url") or row.get("link") or row.get("permalink") or "").strip()
    if not title or not url:
        return None

    summary = str(
        row.get("excerpt")
        or row.get("summary")
        or row.get("dek")
        or row.get("description")
        or ""
    ).strip()
    # Strip HTML tags aggressively — feed / API often embed <p>…</p>.
    summary = re.sub(r"<[^>]+>", " ", summary)
    summary = re.sub(r"\s+", " ", summary).strip()

    published_raw = (
        row.get("published_at")
        or row.get("date_published")
        or row.get("date")
        or row.get("pubDate")
        or ""
    )
    published = ""
    try:
        # ISO-8601 first
        published = dt.datetime.fromisoformat(
            str(published_raw).replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        # RFC-2822 fallback (RSS-style dates)
        try:
            published = email.utils.parsedate_to_datetime(
                str(published_raw)
            ).date().isoformat()
        except Exception:
            published = ""

    tags = row.get("tags") or row.get("categories") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(t).strip() for t in tags if str(t).strip()]

    # Infer APAC jurisdiction from tags
    jurisdiction = _infer_jurisdiction(tags + [title])

    return RegulationAsiaItem(
        title=title,
        url=url,
        summary=summary,
        published=published,
        author=str(row.get("author") or row.get("byline") or "").strip(),
        tags=tags,
        jurisdiction=jurisdiction,
    )


def _fetch_via_api(since_iso: str, max_items: int) -> list[RegulationAsiaItem]:
    api_key = os.getenv("REGULATION_ASIA_API_KEY")
    if not api_key:
        return []
    base = os.getenv("REGULATION_ASIA_API_URL", DEFAULT_JSON_ENDPOINT)
    params = urllib.parse.urlencode({
        "since": since_iso,
        "limit": max_items,
        "order": "desc",
    })
    url = f"{base}?{params}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": UA,
    }
    try:
        data = _http_get_json(url, headers)
    except urllib.error.HTTPError as e:
        # 401/403 usually means bad token; return [] so cron stays green
        # but log to stderr so the user sees the failure mode.
        import sys
        sys.stderr.write(
            f"[regulation_asia] API returned HTTP {e.code} — check "
            "REGULATION_ASIA_API_KEY. Skipping.\n"
        )
        return []
    except Exception as e:
        import sys
        sys.stderr.write(f"[regulation_asia] API fetch failed: {e}\n")
        return []

    # API response shape varies by subscription tier; accept the two
    # most common shapes: {"articles": [...]} and a bare list.
    if isinstance(data, dict):
        rows = data.get("articles") or data.get("results") or data.get("data") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    items: list[RegulationAsiaItem] = []
    for r in rows[:max_items]:
        if not isinstance(r, dict):
            continue
        item = _normalise_api_row(r)
        if item:
            items.append(item)
    return items


# --------------------------------------------------------------------
# Transport B: authenticated RSS feed
# --------------------------------------------------------------------
def _fetch_via_rss(since_iso: str, max_items: int) -> list[RegulationAsiaItem]:
    feed_url = os.getenv("REGULATION_ASIA_FEED_URL")
    if not feed_url:
        return []
    try:
        import feedparser  # already in requirements.txt via lib/news.py
    except Exception:
        return []
    try:
        parsed = feedparser.parse(
            feed_url,
            request_headers={"User-Agent": UA, "Accept": "application/rss+xml"},
        )
    except Exception as e:
        import sys
        sys.stderr.write(f"[regulation_asia] RSS fetch failed: {e}\n")
        return []
    if getattr(parsed, "bozo", 0) and not getattr(parsed, "entries", None):
        import sys
        sys.stderr.write(
            "[regulation_asia] RSS feed unparseable — check "
            "REGULATION_ASIA_FEED_URL and its embedded token.\n"
        )
        return []

    since_date = ""
    try:
        since_date = dt.datetime.fromisoformat(
            since_iso.replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        pass

    items: list[RegulationAsiaItem] = []
    for entry in getattr(parsed, "entries", [])[:max_items * 2]:
        row = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": entry.get("summary", "") or entry.get("description", ""),
            "date_published": entry.get("published", "") or entry.get("updated", ""),
            "author": entry.get("author", ""),
            "tags": [t.get("term", "") for t in entry.get("tags", []) or []],
        }
        item = _normalise_api_row(row)
        if not item:
            continue
        if since_date and item.published and item.published < since_date:
            continue
        items.append(item)
        if len(items) >= max_items:
            break
    return items


# --------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------
_APAC_KEYWORDS = {
    "Singapore":   ("singapore", "mas", "stro", "sgd", "sfa"),
    "Hong Kong":   ("hong kong", "hkma", "sfc", "hkicpa", "hkex", "jfiu"),
    "Malaysia":    ("malaysia", "bnm", "sc", "labuan", "myr", "fied"),
    "Indonesia":   ("indonesia", "ojk", "ppatk", "bank indonesia", "idr"),
    "Philippines": ("philippines", "bsp", "amlc", "sec ph", "php"),
    "Japan":       ("japan", "jafic", "fsa japan", "boj", "jpy"),
    "Korea":       ("korea", "kofiu", "fsc korea", "fss", "krw"),
    "Australia":   ("australia", "austrac", "asic", "apra", "aud"),
    "New Zealand": ("new zealand", "rbnz", "fma nz", "dia", "nzd"),
    "India":       ("india", "rbi", "sebi", "fiu india", "inr"),
    "China":       ("china", "pboc", "csrc", "cbirc", "nfra", "cny", "rmb"),
    "Thailand":    ("thailand", "amlo", "bot ", "sec thai", "thb"),
    "Vietnam":     ("vietnam", "sbv", "ssc"),
    "Taiwan":      ("taiwan", "fsc taiwan", "cbc"),
    "Pakistan":    ("pakistan", "fmu", "sbp", "secp"),
    "Bangladesh":  ("bangladesh", "bfiu"),
}


def _infer_jurisdiction(text_bits: list[str]) -> str:
    """Best-effort jurisdiction inference from tags + title."""
    hay = " ".join(t.lower() for t in text_bits)
    for jur, kws in _APAC_KEYWORDS.items():
        if any(k in hay for k in kws):
            return jur
    return ""


def fetch_recent_articles(
    *,
    since_hours: int = 24,
    max_items: int = 8,
) -> list[RegulationAsiaItem]:
    """Fetch Regulation Asia articles published in the last N hours.

    Uses the JSON API if REGULATION_ASIA_API_KEY is set; otherwise
    falls back to the authenticated RSS feed at REGULATION_ASIA_FEED_URL.
    Returns [] silently if neither is configured or the fetch fails —
    the daily-briefing script keeps running on its other feeds."""
    if not is_configured():
        return []
    since = (
        dt.datetime.utcnow() - dt.timedelta(hours=since_hours)
    ).isoformat(timespec="seconds") + "Z"
    items = _fetch_via_api(since, max_items)
    if not items:
        items = _fetch_via_rss(since, max_items)
    return items
