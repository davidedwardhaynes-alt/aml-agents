"""Podcast RSS feed generator.

Walks data/podcasts/ for all sidecar JSONs, builds an Apple Podcasts /
Spotify-compatible RSS 2.0 feed with iTunes namespace tags, and writes
it to data/podcasts/feed.xml.

Once the feed.xml is committed and pushed, it's reachable at:
  https://raw.githubusercontent.com/davidedwardhaynes-alt/aml-agents/main/data/podcasts/feed.xml

Wix's Podcast Player widget — and any other podcast platform (Apple
Podcasts, Spotify for Podcasters, Pocket Casts, Overcast) — can ingest
this URL directly. Each new daily MP3 the cron commits is automatically
picked up because the feed is regenerated and committed alongside the
audio file.

For Wix specifically:
  - In the trustsphere.ai editor, add the "Spotify Player" or "Custom
    RSS Podcast" widget under the Podcast tab and paste the feed URL.
  - The widget then renders the episode list with an inline player.
"""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
PODCAST_DIR = ROOT / "data" / "podcasts"
FEED_PATH = PODCAST_DIR / "feed.xml"

# Public-facing URLs. The MP3s are served straight from GitHub raw, which
# is fine for a free demo at this volume; switch to S3/Cloudflare R2 with
# a cache CDN once daily downloads exceed ~10k.
GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/davidedwardhaynes-alt/"
    "aml-agents/main/data/podcasts"
)
PODCAST_PAGE_URL = "https://amlagents.streamlit.app"
COVER_ART_URL = (
    "https://raw.githubusercontent.com/davidedwardhaynes-alt/"
    "aml-agents/main/data/podcasts/cover.jpg"
)

PODCAST_TITLE = "AML Agents Briefing"
PODCAST_AUTHOR = "TrustSphere Partners"
PODCAST_OWNER_NAME = "David Edward Haynes"
PODCAST_OWNER_EMAIL = "david@trustsphere.partners"
PODCAST_DESCRIPTION = (
    "A 4 to 6 minute daily two-host audio briefing for MLROs, heads of "
    "financial-crime compliance, AML supervisors, and senior compliance "
    "leaders across the Asia-Pacific region. Each morning Alex and Jordan "
    "cover the most material APAC AML and financial-crime developments — "
    "regulator notices, enforcement actions, supervisory thematic findings, "
    "obligations falling due, and horizon-scanning items — with concrete "
    "action items for the listener's working day. Produced by TrustSphere "
    "Partners. Full detail at amlagents.streamlit.app."
)
PODCAST_LANGUAGE = "en-gb"
PODCAST_CATEGORY_PRIMARY = "Business"
PODCAST_CATEGORY_SECONDARY = "Government"
PODCAST_KEYWORDS = (
    "AML, anti-money laundering, financial crime, compliance, MLRO, "
    "FATF, MAS, HKMA, BNM, JAFIC, KoFIU, AUSTRAC, FIU NZ, AMLC, PPATK, "
    "APAC, Singapore, Hong Kong, Malaysia, Australia, Japan, Korea, "
    "Indonesia, Philippines, New Zealand, fraud, sanctions"
)


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _rfc2822(d: dt.date) -> str:
    """Convert an ISO date to an RFC 2822 datetime at 07:00 SGT (the show's
    nominal release slot). RSS requires RFC 2822 / RFC 822 format."""
    publish = dt.datetime(d.year, d.month, d.day, 7, 0, 0)
    # Mon, 07 May 2026 07:00:00 +0800
    return publish.strftime("%a, %d %b %Y %H:%M:%S +0800")


def _episode_item(sidecar_path: Path) -> str | None:
    """Render one <item> from a sidecar JSON. Skips silent/stub episodes
    (so the published feed never includes a 5-second silent placeholder)."""
    try:
        meta = json.loads(sidecar_path.read_text())
    except Exception:
        return None
    if meta.get("stub", False):
        return None
    date_iso = meta.get("date")
    if not date_iso:
        return None
    try:
        date = dt.date.fromisoformat(date_iso)
    except Exception:
        return None
    mp3_path = sidecar_path.with_suffix(".mp3")
    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
        return None

    title = meta.get("title") or f"AML Agents Briefing — {date_iso}"
    duration_s = int(meta.get("duration_seconds", 0))
    h, rem = divmod(duration_s, 3600)
    m, s = divmod(rem, 60)
    duration = f"{h:02d}:{m:02d}:{s:02d}"
    file_size = mp3_path.stat().st_size
    mp3_url = f"{GITHUB_RAW_BASE}/{date_iso}.mp3"

    # Episode summary — pull the script's first paragraph, strip speaker tags.
    script = (meta.get("script") or "").strip()
    summary = script.split("\n", 1)[0] if script else title
    if summary.startswith("ALEX:") or summary.startswith("JORDAN:"):
        summary = summary.split(":", 1)[1].strip()
    if len(summary) > 300:
        summary = summary[:297] + "..."

    return f"""    <item>
      <title>{_esc(title)}</title>
      <description>{_esc(summary)}</description>
      <itunes:summary>{_esc(summary)}</itunes:summary>
      <itunes:subtitle>Daily APAC AML and financial-crime briefing</itunes:subtitle>
      <itunes:author>{_esc(PODCAST_AUTHOR)}</itunes:author>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
      <pubDate>{_rfc2822(date)}</pubDate>
      <guid isPermaLink="false">aml-agents-briefing-{date_iso}</guid>
      <enclosure url="{_esc(mp3_url)}" length="{file_size}" type="audio/mpeg"/>
      <link>{_esc(PODCAST_PAGE_URL)}</link>
    </item>"""


def build_feed() -> Path:
    """Walk data/podcasts/, render an Apple-Podcasts-compatible RSS 2.0
    feed, write it to data/podcasts/feed.xml, return the path."""
    PODCAST_DIR.mkdir(parents=True, exist_ok=True)

    sidecars = sorted(PODCAST_DIR.glob("*.json"), reverse=True)
    items: list[str] = []
    for sc in sidecars:
        if sc.name == "feed.xml":
            continue
        item_xml = _episode_item(sc)
        if item_xml:
            items.append(item_xml)

    last_build = dt.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{_esc(PODCAST_TITLE)}</title>
    <link>{_esc(PODCAST_PAGE_URL)}</link>
    <atom:link href="{_esc(GITHUB_RAW_BASE)}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{_esc(PODCAST_DESCRIPTION)}</description>
    <language>{PODCAST_LANGUAGE}</language>
    <copyright>© {dt.date.today().year} {_esc(PODCAST_AUTHOR)}</copyright>
    <lastBuildDate>{last_build}</lastBuildDate>
    <generator>AML Agents (lib/podcast_feed.py)</generator>
    <itunes:author>{_esc(PODCAST_AUTHOR)}</itunes:author>
    <itunes:summary>{_esc(PODCAST_DESCRIPTION)}</itunes:summary>
    <itunes:subtitle>Daily APAC AML and financial-crime briefing</itunes:subtitle>
    <itunes:owner>
      <itunes:name>{_esc(PODCAST_OWNER_NAME)}</itunes:name>
      <itunes:email>{_esc(PODCAST_OWNER_EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:image href="{_esc(COVER_ART_URL)}"/>
    <itunes:category text="{PODCAST_CATEGORY_PRIMARY}">
      <itunes:category text="Management"/>
    </itunes:category>
    <itunes:category text="{PODCAST_CATEGORY_SECONDARY}"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:keywords>{_esc(PODCAST_KEYWORDS)}</itunes:keywords>
{chr(10).join(items)}
  </channel>
</rss>
"""

    FEED_PATH.write_text(feed, encoding="utf-8")
    return FEED_PATH


def feed_summary() -> dict[str, Any]:
    """Quick stats for the feed (item count + latest date) — handy for
    cron logs and the in-app 'Subscribe' panel."""
    if not FEED_PATH.exists():
        return {"items": 0, "latest": None, "url": None}
    sidecars = sorted(PODCAST_DIR.glob("*.json"), reverse=True)
    n = 0
    latest = None
    for sc in sidecars:
        if sc.name == "feed.xml":
            continue
        try:
            meta = json.loads(sc.read_text())
            if meta.get("stub", False):
                continue
            n += 1
            if latest is None:
                latest = meta.get("date")
        except Exception:
            continue
    return {
        "items": n,
        "latest": latest,
        "url": f"{GITHUB_RAW_BASE}/feed.xml",
    }
