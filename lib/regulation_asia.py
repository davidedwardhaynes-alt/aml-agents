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

DEFAULT_JSON_ENDPOINT = "https://api.regulationasia.com/api/articles"

# Regulation Asia issues the key into their own .env, which we read in
# place rather than copying: one copy of the secret, their file unedited,
# and nothing sensitive in a file that syncs to iCloud. Matches how
# regasia-drafter and regasia-daily source the same key.
RA_ENV_FILE = (
    "~/Library/Mobile Documents/com~apple~CloudDocs/script/.env"
)
RA_ENV_KEY_NAME = "API_KEY"

# The API caps `limit` at 100 and has no `since` parameter — it returns
# newest-first and we window by date on our side.
API_MAX_LIMIT = 100

# Article bodies run ~5,300 chars on average and up to ~23,000. The cap
# exists so one long article can't dominate a prompt, but it belongs to
# the *caller's* budget, not to the fetch: the 5-minute podcast prompt
# trims to 900 chars of its own accord, while the long-form briefing
# wants everything. Defaulting high and letting a caller clamp is the
# right way round — the old 4,000 default silently discarded 37% of a
# typical day's source material before anyone could ask for it.
CONTENT_CHAR_CAP = int(os.getenv("REGULATION_ASIA_CONTENT_CAP", "24000"))
UA = (
    "AML-Agents-Daily/1.0 (+https://trustsphere.ai; "
    "regulation-asia-subscriber)"
)
DEFAULT_TIMEOUT = 20


@dataclass
class RegulationAsiaItem:
    title: str
    url: str
    summary: str              # short teaser (~1-2 sentences, from `excerpt`)
    published: str            # ISO date; may be empty
    author: str = ""
    tags: list[str] | None = None
    jurisdiction: str = ""    # inferred from tags where possible
    content: str = ""         # FULL article body — populated by the API's
                              # `content` field. Podcast prompt uses this
                              # for richer context beyond the summary.
    topics: list[str] | None = None
                              # Flattened category/subcategory strings from
                              # the API's structured `topics` list —
                              # e.g. ["Financial Crime / KYC & CDD",
                              # "AI, Technology & Data / Cybersecurity"].


# --------------------------------------------------------------------
# Configuration probe
# --------------------------------------------------------------------
def _resolve_api_key() -> str:
    """Return the Regulation Asia API key, preferring an explicit env
    var and falling back to RA's own .env file.

    The env var wins so CI and one-off runs can override without
    touching the file. The file fallback is what makes the cron work
    unattended on David's Mac, where the key only ever lives in RA's
    .env."""
    for var in ("REGULATION_ASIA_API_KEY", "RA_API_KEY"):
        val = (os.getenv(var) or "").strip()
        if val:
            return val

    path = os.path.expanduser(
        os.getenv("REGULATION_ASIA_ENV_FILE", RA_ENV_FILE)
    )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                if name.strip() == RA_ENV_KEY_NAME:
                    return value.strip().strip("'\"")
    except OSError:
        # Missing or unreadable (macOS sandboxing can block iCloud reads
        # from a cron context) — caller falls through to another
        # transport rather than raising.
        pass
    return ""


def is_configured() -> bool:
    """True when any transport is configured (API key, authenticated
    feed URL, or a local sample JSON path for offline testing)."""
    return bool(
        _resolve_api_key()
        or os.getenv("REGULATION_ASIA_FEED_URL")
        or os.getenv("REGULATION_ASIA_SAMPLE_PATH")
    )


def configured_transport() -> str:
    """Return which transport will be used ('api', 'rss', 'sample',
    or 'none'). The 'sample' transport reads from a local JSON file
    pointed at by REGULATION_ASIA_SAMPLE_PATH — useful for CI + demos
    when you don't want to hit the paid API on every cron run."""
    if _resolve_api_key():
        return "api"
    if os.getenv("REGULATION_ASIA_FEED_URL"):
        return "rss"
    if os.getenv("REGULATION_ASIA_SAMPLE_PATH"):
        return "sample"
    return "none"


def _fetch_via_sample(since_iso: str, max_items: int) -> list[RegulationAsiaItem]:
    """Load articles from a local JSON file. The file should match the
    Regulation Asia v1 API response shape: `{"articles": [...], "total": N}`
    OR be a bare list of article dicts. Ignored silently if the path
    isn't set or the file is unreadable."""
    path = os.getenv("REGULATION_ASIA_SAMPLE_PATH")
    if not path:
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        import sys
        sys.stderr.write(f"[regulation_asia] sample file unreadable: {e}\n")
        return []

    rows: list[dict] = []
    if isinstance(data, dict):
        rows = data.get("articles") or data.get("results") or data.get("data") or []
    elif isinstance(data, list):
        rows = data

    since_date = ""
    try:
        since_date = dt.datetime.fromisoformat(
            since_iso.replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        pass

    items: list[RegulationAsiaItem] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        item = _normalise_api_row(r)
        if not item:
            continue
        # Filter to items on/after since_date; if either date is empty
        # keep the item (fail-open — sample files may be small).
        if since_date and item.published and item.published < since_date:
            continue
        items.append(item)
        if len(items) >= max_items:
            break
    return items


# --------------------------------------------------------------------
# Transport A: JSON API
# --------------------------------------------------------------------
def _http_get_json(url: str, headers: dict[str, str]) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _flatten_topics(raw_topics: Any) -> list[str]:
    """Regulation Asia's `topics` field is a list of dicts:
        [{"category": "Financial Crime",
          "subcategory": ["KYC & CDD", "Sanctions"]}, ...]
    Flatten to human-readable strings for downstream use:
        ["Financial Crime / KYC & CDD",
         "Financial Crime / Sanctions",
         ...]
    Falls back gracefully on any unexpected shape."""
    out: list[str] = []
    if not raw_topics:
        return out
    if isinstance(raw_topics, str):
        return [raw_topics]
    for t in raw_topics:
        if isinstance(t, str):
            out.append(t)
            continue
        if not isinstance(t, dict):
            continue
        cat = str(t.get("category") or "").strip()
        subs = t.get("subcategory") or t.get("subcategories") or []
        if isinstance(subs, str):
            subs = [subs]
        subs = [str(s).strip() for s in subs if str(s).strip()]
        if cat and subs:
            for s in subs:
                out.append(f"{cat} / {s}")
        elif cat:
            out.append(cat)
    return out


def _normalise_api_row(row: dict) -> RegulationAsiaItem | None:
    """Coerce one JSON row into RegulationAsiaItem. Return None on
    obviously-broken rows so downstream code can skip cleanly.

    Handles the actual Regulation Asia v1 API schema:
      {title, url, excerpt, content, published_at,
       topics: [{category, subcategory: [...]}], tags: [...]}
    plus more permissive aliases for RSS-derived rows."""
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

    # Full article body — Regulation Asia's `content` field averages
    # ~5,300 chars, up to ~23,000. Kept whole by default; see
    # CONTENT_CHAR_CAP for why the trimming decision sits with callers.
    content = str(row.get("content") or row.get("body") or "").strip()
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"\s+", " ", content).strip()
    if CONTENT_CHAR_CAP and len(content) > CONTENT_CHAR_CAP:
        content = content[: CONTENT_CHAR_CAP - 3] + "..."

    published_raw = (
        row.get("published_at")
        or row.get("date_published")
        or row.get("date")
        or row.get("pubDate")
        or ""
    )
    published = ""
    try:
        # ISO-8601 first — the Regulation Asia API returns millisecond-
        # precision timestamps like "2026-08-25T03:10:18.481000Z".
        # fromisoformat() on 3.9 can't handle 'Z'; also stumbles on the
        # 6-digit microseconds — normalise both explicitly.
        s = str(published_raw).strip().replace("Z", "+00:00")
        # Split off fractional seconds beyond the ISO 3.9-parseable form
        m = re.match(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(.*)$",
            s,
        )
        if m:
            s = m.group(1) + m.group(3)
        published = dt.datetime.fromisoformat(s).date().isoformat()
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

    topics = _flatten_topics(row.get("topics"))

    # Infer APAC jurisdiction from tags + topics + title
    jurisdiction = _infer_jurisdiction(tags + topics + [title])

    return RegulationAsiaItem(
        title=title,
        url=url,
        summary=summary,
        published=published,
        author=str(row.get("author") or row.get("byline") or "").strip(),
        tags=tags,
        jurisdiction=jurisdiction,
        content=content,
        topics=topics,
    )


def _fetch_via_api(since_iso: str, max_items: int) -> list[RegulationAsiaItem]:
    api_key = _resolve_api_key()
    if not api_key:
        return []
    base = os.getenv("REGULATION_ASIA_API_URL", DEFAULT_JSON_ENDPOINT)

    # The API takes `limit` only — no `since`, no `order`. It returns
    # newest-first, so ask for a window wide enough that the since_iso
    # cut below still has candidates left after filtering. Publishing
    # runs 25-50 articles/day, so a 24h ask of 6 items off an unfiltered
    # newest-first feed would be fine, but a 7-day ask would silently
    # truncate — hence pulling the full page and trimming locally.
    limit = min(API_MAX_LIMIT, max(max_items, 100))
    params = urllib.parse.urlencode({"limit": limit})
    url = f"{base}?{params}"
    headers = {
        "X-API-Key": api_key,
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

    # Window by date on our side, since the API has no `since`. Rows
    # carry a full timestamp but _normalise_api_row reduces it to a
    # date, so the comparison is date-to-date. Undated rows are dropped
    # rather than kept: this feed mixes promotional and evergreen pages
    # in with the news, and an undated item can't honestly be called
    # part of "the last N hours".
    cutoff_date = since_iso[:10]
    items: list[RegulationAsiaItem] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        item = _normalise_api_row(r)
        if not item or not item.published:
            continue
        if item.published < cutoff_date:
            continue
        items.append(item)
        if len(items) >= max_items:
            break
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


_KEYWORD_PATTERNS = {
    jur: re.compile(
        r"\b(?:" + "|".join(re.escape(k.strip()) for k in kws) + r")\b"
    )
    for jur, kws in _APAC_KEYWORDS.items()
}


def _infer_jurisdiction(text_bits: list[str]) -> str:
    """Best-effort jurisdiction inference from tags + topics + title.

    Two rules earn their keep here. Matching is word-bounded, because
    several of the keywords are two- and three-letter regulator
    acronyms that otherwise match inside ordinary words — Malaysia's
    "sc" hit "Scaled-Back", New Zealand's "dia" hit "India". And the
    winner is the jurisdiction with the *most* hits rather than the
    first one in dict order, so a genuine cluster ("India", "SEBI",
    "INR") beats a single incidental acronym."""
    hay = " ".join(t.lower() for t in text_bits)
    best, best_score = "", 0
    for jur, pattern in _KEYWORD_PATTERNS.items():
        score = len(pattern.findall(hay))
        if score > best_score:
            best, best_score = jur, score
    return best


def fetch_recent_articles(
    *,
    since_hours: int = 24,
    max_items: int = 8,
) -> list[RegulationAsiaItem]:
    """Fetch Regulation Asia articles published in the last N hours.

    Uses the JSON API when a key is resolvable (env var, or RA's own
    .env file); otherwise falls back to the authenticated RSS feed at
    REGULATION_ASIA_FEED_URL.
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
    if not items:
        items = _fetch_via_sample(since, max_items)
    return items
