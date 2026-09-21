"""Daily briefing generator — produces today's podcast MP3 and video MP4
from the same digest content used by the email channel. Runs from a
GitHub Actions cron at ~22:30 UTC (just before the 23:00 UTC email send
that hits SGT/HKT 07:00) so the email can reference the freshly
generated audio + video.

Pipeline:
  1. Build a "digest summary" string covering today's news + obligations
     + horizon items (uses lib.digest sections).
  2. lib.podcast.generate_daily_podcast(...) — writes data/podcasts/<date>.mp3
  3. lib.video.generate_daily_video(...) — writes data/videos/<date>.mp4
     using the podcast MP3 as its audio track.
  4. Print a one-line summary so the GitHub Actions log is easy to scan.

Costs (today's pricing, ~5,400-char script):
  Anthropic Claude Sonnet 4.6 — script generation:    ~$0.08
  OpenAI gpt-4o-mini-tts — audio synthesis:           ~$0.05
  FFmpeg compose:                                     $0
  Total per day:                                      ~$0.13
"""

from __future__ import annotations

import datetime as dt
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

socket.setdefaulttimeout(60)

# Load .env so local runs pick up ANTHROPIC_API_KEY / OPENAI_API_KEY without
# needing them exported. In GitHub Actions the keys come from the secret
# context already, so load_dotenv() is a no-op when no .env exists.
try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

from lib.digest import build_digest  # noqa: E402
from lib.podcast_feed import build_feed, feed_summary  # noqa: E402
from lib.horizon import all_items_for_jurisdiction  # noqa: E402
from lib.news import items_for as news_items_for  # noqa: E402
from lib.obligations import load_obligations  # noqa: E402
from lib.podcast import generate_daily_podcast  # noqa: E402
from lib.subscriptions import Subscription  # noqa: E402
from lib.video import generate_daily_video  # noqa: E402


def _compose_summary(today: dt.date) -> tuple[str, list[tuple[str, str, str]]]:
    """Return (free-form text summary for Claude, headline triples for video).

    SOURCE PRIMACY (per user feedback 2026-05-07: "some content is not
    accurate or current, please validate the source material — start
    using the Regulation Asia API or other trusted regulatory sources"):

    Regulation Asia's subscription API is the PRIMARY factual source
    when configured. Local seed data becomes fallback / background
    context only. This ensures every episode is anchored on verified,
    dated regulatory coverage from a credible publisher.

    FRESHNESS POLICY (same user feedback, plus "podcasts reference 2024
    obligations — this is too old"): items older than 90 days are
    filtered out unless they're High/Critical priority overdue
    obligations that are STILL actionable this week. The prompt also
    tells Claude to speak in the present and forward-looking voice —
    no 'last year', no 'a previous cycle'."""
    headlines: list[tuple[str, str, str]] = []
    text_parts: list[str] = []

    # =============================================================
    # PRIMARY SOURCE — Regulation Asia (credible publisher, dated)
    # =============================================================
    ra_items = []
    ra_transport = "none"
    try:
        from lib.regulation_asia import (
            fetch_recent_articles,
            configured_transport,
        )
        ra_transport = configured_transport()
        # Widen the window to 120 hours (5 days) so the podcast has
        # enough material even on quiet news days. RA publishes 50-60
        # articles per day so this typically returns dozens of items.
        ra_items = fetch_recent_articles(since_hours=120, max_items=40)
    except Exception as e:
        import sys as _sys
        _sys.stderr.write(f"[regulation_asia] adapter failed: {e}\n")

    if ra_items:
        text_parts.append(
            f"=== REGULATION ASIA — PRIMARY SOURCE (last 5 days, transport={ra_transport}) ==="
        )
        text_parts.append(
            "The podcast must anchor on these dated regulatory-intelligence "
            "items. Prefer them for the lead story and supporting segments; "
            "cite them with 'Regulation Asia' attribution where natural."
        )
        # Cap at the top 8 for the digest so we stay inside a workable
        # token budget for the model, but keep more headlines for the
        # video slides.
        for it in ra_items[:8]:
            jur = it.jurisdiction or "APAC"
            topics = ", ".join((it.topics or [])[:3])
            topic_line = f"  Topics: {topics}\n" if topics else ""
            context_snippet = ""
            if it.content:
                ctx = it.content[:900]
                context_snippet = f"  Context: {ctx}\n"
            text_parts.append(
                f"- [{it.published} | {jur}] {it.title}\n"
                f"  {(it.summary or '')[:280]}\n"
                f"{topic_line}"
                f"{context_snippet}"
                f"  Source: Regulation Asia — {it.url}"
            )
        for it in ra_items[:6]:
            headlines.append(
                ("Regulation Asia", it.title, (it.summary or "")[:240])
            )
    else:
        # RA is unavailable — signal fallback mode explicitly so the
        # cron log makes it obvious why the episode is thinner.
        text_parts.append(
            f"[REGULATION ASIA UNAVAILABLE — transport={ra_transport}. "
            f"Falling back to seed news only. Configure REGULATION_ASIA_API_KEY "
            f"in GitHub Actions secrets to restore the primary source.]"
        )

    # =============================================================
    # FALLBACK — seed news (background context only when RA is present,
    # primary source when RA is absent)
    # =============================================================
    news, _ = news_items_for(
        jurisdiction="All jurisdictions",
        topic="All topics",
        include_live=False,
    )
    # Freshness cap — 90 days
    fresh_floor = (today - dt.timedelta(days=90)).isoformat()
    fresh_news = [it for it in news if not it.date or it.date >= fresh_floor]
    label = "SEED NEWS (background context)" if ra_items else "TOP NEWS"
    text_parts.append(f"\n=== {label} — last 90 days ===")
    for it in fresh_news[:4]:
        text_parts.append(
            f"- [{it.date} | {it.jurisdiction} | {it.topic}] {it.title}\n"
            f"  {(it.summary or '')[:280]}"
        )
        if not ra_items:
            headlines.append(("News", it.title, (it.summary or "")[:240]))

    # =============================================================
    # Obligations — active + still-actionable overdue only
    # =============================================================
    soon_cutoff = (today + dt.timedelta(days=90)).isoformat()
    legacy_floor = (today - dt.timedelta(days=180)).isoformat()

    all_obs = load_obligations()
    upcoming = [
        o for o in all_obs
        if o.due_date and fresh_floor <= o.due_date <= soon_cutoff
        and o.status != "Closed"
    ]
    upcoming.sort(key=lambda o: (o.due_date, o.jurisdiction))
    overdue_actionable = [
        o for o in all_obs
        if o.due_date
        and legacy_floor <= o.due_date < today.isoformat()
        and o.status != "Closed"
        and getattr(o, "priority", "Standard") in ("Critical", "High")
    ]
    overdue_actionable.sort(key=lambda o: o.due_date, reverse=True)

    text_parts.append("\n=== ACTIVE OBLIGATIONS (next 90 days) ===")
    if upcoming:
        for o in upcoming[:3]:
            text_parts.append(
                f"- [{o.due_date} | {o.jurisdiction} | "
                f"{getattr(o, 'priority', 'Standard')}] {o.title} — {o.description}"
            )
            headlines.append(("Obligation due", o.title, o.description or ""))
    else:
        text_parts.append("- (no items due in the window)")

    if overdue_actionable:
        text_parts.append(
            "\n=== STILL-ACTIONABLE OVERDUE (last 6 months, Critical/High only) ==="
        )
        for o in overdue_actionable[:2]:
            text_parts.append(
                f"- [{o.due_date} | {o.jurisdiction} | "
                f"{getattr(o, 'priority', 'Standard')}] {o.title} — {o.description}"
            )
            headlines.append(("Overdue", o.title, o.description or ""))

    # =============================================================
    # Horizon — filtered to fresh items only
    # =============================================================
    horizon, _ = all_items_for_jurisdiction(jurisdiction=None, include_live=False)
    fresh_horizon = [
        it for it in horizon if not it.date or it.date >= fresh_floor
    ]
    text_parts.append("\n=== HORIZON SCANNING (last 90 days) ===")
    for it in fresh_horizon[:3]:
        text_parts.append(
            f"- [{it.date} | {it.jurisdiction} | {it.impact}] {it.title}\n"
            f"  {(it.summary or '')[:240]}"
        )
        headlines.append(("Horizon", it.title, (it.summary or "")[:240]))

    # =============================================================
    # Freshness + attribution directive to the host
    # =============================================================
    text_parts.append(
        f"\n=== DIRECTIVE FOR THE HOST ===\n"
        f"Today is {today.isoformat()}. Speak in the present tense and "
        f"forward-looking voice. Do NOT dwell on stale 2024-cycle items "
        f"unless they are explicitly listed under 'STILL-ACTIONABLE "
        f"OVERDUE'. Avoid phrases like 'last year', 'a previous cycle', "
        f"or 'back in 2024'. Anchor each story on the Regulation Asia "
        f"items above where possible; when you reference an RA article, "
        f"a natural attribution like 'as Regulation Asia reported earlier "
        f"this week' or 'per Regulation Asia's coverage' lets the "
        f"listener trace the source. Never fabricate a story or a "
        f"detail that isn't in the digest above."
    )

    # Credible-source citation context — for the jurisdictions touched
    # by today's news + obligations + horizon items, list the top
    # authoritative regulator URLs from lib/regulator_sources.py. The
    # podcast prompt uses these so ALEX and JORDAN can cite specific
    # regulators ("MAS just published a Notice 626 amendment on their
    # website...") rather than hand-waving generalities.
    try:
        from lib.regulator_sources import sources_for
        touched: dict[str, None] = {}
        for it in list(news[:4]) + list(horizon[:3]):
            jur_label = str(getattr(it, "jurisdiction", "")).strip()
            # Strip any bracketed suffix like " (STRO)" for lookup
            jur = jur_label.split(" (")[0].strip()
            if jur:
                touched[jur] = None
        for o in obs[:3]:
            jur = str(o.jurisdiction).split(" (")[0].strip()
            if jur:
                touched[jur] = None

        if touched:
            text_parts.append("\n=== CREDIBLE SOURCES (cite these when discussing today's stories) ===")
            for jur in list(touched)[:6]:  # cap to 6 jurisdictions for prompt length
                sources = sources_for(jur)
                if not sources:
                    continue
                text_parts.append(f"[{jur}]")
                for name, url in sources[:5]:  # top 5 per jurisdiction
                    text_parts.append(f"  - {name}: {url}")
    except Exception:
        # Non-fatal if the catalogue module isn't importable; podcast
        # still generates from news + obligations + horizon alone.
        pass

    return "\n".join(text_parts), headlines


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Daily briefing generator — podcast MP3 + video MP4"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override today's date (ISO YYYY-MM-DD). Useful for backfill.",
    )
    parser.add_argument(
        "--podcast-only",
        action="store_true",
        help="Skip the video generation step.",
    )
    parser.add_argument(
        "--video-only",
        action="store_true",
        help="Skip the podcast generation step.",
    )
    args = parser.parse_args()

    today = (
        dt.date.fromisoformat(args.date)
        if args.date
        else dt.date.today()
    )

    summary_text, headlines = _compose_summary(today)
    print(f"Generating daily briefing for {today.isoformat()} …")
    print(f"  digest summary chars: {len(summary_text):,}")
    print(f"  headlines: {len(headlines)}")

    podcast = None
    if not args.video_only:
        podcast = generate_daily_podcast(
            digest_summary=summary_text,
            today=today,
            anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_key=os.getenv("OPENAI_API_KEY"),
        )
        print(
            f"  ✓ podcast: {podcast.mp3_path.name} "
            f"({podcast.script_chars:,} chars, "
            f"~{podcast.duration_seconds}s, "
            f"stub={podcast.stub}, ${podcast.cost_estimate_usd:.3f})"
        )

    if not args.podcast_only:
        audio_path = podcast.mp3_path if podcast and not podcast.stub else None
        video = generate_daily_video(
            today=today,
            headlines=headlines,
            audio_path=audio_path,
            duration_seconds=podcast.duration_seconds if podcast else 240,
        )
        print(
            f"  ✓ video:   {video.mp4_path.name} "
            f"({video.n_slides} slides, "
            f"~{video.duration_seconds}s, "
            f"stub={video.stub})"
        )

    # ----------------------------------------------------------------
    # Rebuild the podcast RSS feed (data/podcasts/feed.xml). The cron
    # commits this alongside the new MP3 so trustsphere.ai's Wix
    # Podcast Player widget picks up the new episode automatically.
    # Stub episodes are excluded from the published feed.
    # ----------------------------------------------------------------
    feed_path = build_feed()
    summary = feed_summary()
    print(
        f"  ✓ RSS:     {feed_path.name} "
        f"({summary['items']} episodes, latest {summary['latest']}, "
        f"feed: {summary['url']})"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
