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
    """Return (free-form text summary for Claude, headline triples for video)."""
    headlines: list[tuple[str, str, str]] = []
    text_parts: list[str] = []

    # Top news (up to 4)
    news, _ = news_items_for(
        jurisdiction="All jurisdictions",
        topic="All topics",
        include_live=False,
    )
    text_parts.append("=== TOP NEWS ===")
    for it in news[:4]:
        text_parts.append(
            f"- [{it.date} | {it.jurisdiction} | {it.topic}] {it.title}\n"
            f"  {(it.summary or '')[:280]}"
        )
        headlines.append(("News", it.title, (it.summary or "")[:240]))

    # Imminent obligations (next 60 days, top 3 by date)
    cutoff = (today + dt.timedelta(days=60)).isoformat()
    obs = [
        o for o in load_obligations()
        if o.due_date and o.due_date <= cutoff and o.status != "Closed"
    ]
    obs.sort(key=lambda o: (o.due_date, o.jurisdiction))
    text_parts.append("\n=== OBLIGATIONS DUE (next 60d) ===")
    for o in obs[:3]:
        text_parts.append(
            f"- [{o.due_date} | {o.jurisdiction}] {o.title} — {o.description}"
        )
        headlines.append(("Obligation due", o.title, o.description or ""))

    # Top horizon items
    horizon, _ = all_items_for_jurisdiction(jurisdiction=None, include_live=False)
    text_parts.append("\n=== HORIZON SCANNING ===")
    for it in horizon[:3]:
        text_parts.append(
            f"- [{it.date} | {it.jurisdiction} | {it.impact}] {it.title}\n"
            f"  {(it.summary or '')[:240]}"
        )
        headlines.append(("Horizon", it.title, (it.summary or "")[:240]))

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
