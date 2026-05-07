"""Upload today's daily podcast MP3 to SoundCloud.

Run from the GitHub Actions cron after `generate_daily_briefing.py` has
produced today's MP3 + sidecar. Skips silently if SoundCloud
credentials aren't configured (so the workflow stays green).

Usage:
  python scripts/upload_daily_podcast.py
  python scripts/upload_daily_podcast.py --date 2026-05-07
  python scripts/upload_daily_podcast.py --skip-stub  # default
  python scripts/upload_daily_podcast.py --dry-run

Required env vars (set as GitHub Actions secrets):
  SOUNDCLOUD_CLIENT_ID
  SOUNDCLOUD_CLIENT_SECRET
  SOUNDCLOUD_REFRESH_TOKEN

OR (for short-lived test runs):
  SOUNDCLOUD_ACCESS_TOKEN
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

socket.setdefaulttimeout(60)

try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

from lib.soundcloud import (  # noqa: E402
    DEFAULT_DESCRIPTION,
    SHOW_TITLE,
    is_configured,
    upload_episode,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="ISO date YYYY-MM-DD; defaults to today.",
    )
    parser.add_argument(
        "--sharing",
        choices=["public", "private"],
        default="public",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve target file + check credentials but don't upload.",
    )
    args = parser.parse_args()

    today = (
        dt.date.fromisoformat(args.date)
        if args.date
        else dt.date.today()
    )

    podcast_dir = ROOT / "data" / "podcasts"
    mp3_path = podcast_dir / f"{today.isoformat()}.mp3"
    sidecar_path = podcast_dir / f"{today.isoformat()}.json"

    if not mp3_path.exists():
        print(f"No podcast found for {today.isoformat()} — skipping.")
        return 0

    sidecar = {}
    try:
        sidecar = json.loads(sidecar_path.read_text())
    except Exception:
        pass

    if sidecar.get("stub", False):
        print(f"Today's podcast is a stub episode — skipping upload.")
        return 0

    title = sidecar.get(
        "title",
        f"{SHOW_TITLE} — {today.strftime('%A, %d %B %Y')}",
    )

    # Episode-specific description: append the lead paragraph of the
    # script so listeners landing on SoundCloud see the day's content.
    desc = DEFAULT_DESCRIPTION
    script = (sidecar.get("script") or "").strip()
    if script:
        first_para = script.split("\n", 1)[0]
        if first_para.startswith(("ALEX:", "JORDAN:")):
            first_para = first_para.split(":", 1)[1].strip()
        if len(first_para) > 600:
            first_para = first_para[:597] + "..."
        desc = f"{first_para}\n\n{DEFAULT_DESCRIPTION}"

    if not is_configured():
        print(
            "SoundCloud credentials not configured. Set SOUNDCLOUD_CLIENT_ID, "
            "SOUNDCLOUD_CLIENT_SECRET, and SOUNDCLOUD_REFRESH_TOKEN — see "
            "SOUNDCLOUD_SETUP.md. Skipping upload (cron stays green)."
        )
        return 0

    print(f"Uploading {mp3_path.name} to SoundCloud (sharing={args.sharing})...")
    print(f"  title: {title}")
    print(f"  size:  {mp3_path.stat().st_size / (1024*1024):.2f} MB")

    if args.dry_run:
        print("  [dry-run] credentials OK, would upload now.")
        return 0

    result = upload_episode(
        mp3_path=mp3_path,
        title=title,
        description=desc,
        sharing=args.sharing,
        purchase_url="https://amlagents.streamlit.app",
    )

    if result.ok:
        print(f"  ✓ uploaded — track_id={result.track_id}")
        print(f"  ✓ url:      {result.track_url}")
        # Persist the SoundCloud URL into the sidecar so the in-app
        # Subscribe panel can link to it.
        if sidecar:
            sidecar["soundcloud_url"] = result.track_url
            sidecar["soundcloud_track_id"] = result.track_id
            try:
                sidecar_path.write_text(json.dumps(sidecar, indent=2))
            except Exception:
                pass
        return 0

    print(f"  ✗ upload failed: {result.error}")
    if result.skipped_reason in ("no-credentials", "missing-file"):
        return 0  # expected non-fatal — keep cron green
    return 1


if __name__ == "__main__":
    sys.exit(main())
