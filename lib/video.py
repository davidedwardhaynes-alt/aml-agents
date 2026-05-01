"""Daily video — turn the podcast script + audio into a captioned slideshow MP4.

Pipeline:
  1. Render N PNG slides (Apple-style: dark text on a #F5F5F7 canvas with
     hairline cards). Each slide carries a single headline plus the
     supporting summary, branded with the AML Agents wordmark.
  2. Render a separate "intro" and "outro" slide with the same look.
  3. Compose into MP4 using FFmpeg: slides as the visual track, the
     podcast MP3 as the audio track. Each slide displays for
     `duration / n_slides` seconds.
  4. Optionally upload to YouTube via youtube-dl-equivalent or the
     YouTube Data API v3 — left as a separate `scripts/upload_youtube.py`
     stub to be filled in once OAuth credentials are configured.

This module only produces an MP4 file at data/videos/YYYY-MM-DD.mp4 plus
a JSON sidecar. When FFmpeg is unavailable on the host (e.g. ad-hoc local
dev without `brew install ffmpeg`), the sidecar still gets written so the
app's video player widget can render a graceful 'video pending — install
FFmpeg in the cron container' fallback.

Pillow (PIL) is used for slide rendering. Pillow is in the base
requirements.txt because it's already a transitive dep of Streamlit.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

VIDEO_DIR = Path(__file__).parent.parent / "data" / "videos"

# Slide canvas — 1920×1080 (16:9). Aligns with YouTube + LinkedIn standards.
W, H = 1920, 1080
BG_COLOR = (245, 245, 247)  # Apple #F5F5F7
CARD_COLOR = (255, 255, 255)
HAIRLINE = (213, 213, 218)
TEXT_PRIMARY = (29, 29, 31)
TEXT_SECONDARY = (110, 110, 115)
ACCENT = (0, 113, 227)


@dataclass
class VideoResult:
    date: str
    mp4_path: Path
    sidecar_path: Path
    title: str
    duration_seconds: int
    n_slides: int
    stub: bool


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _font(size: int) -> "Any":
    """Pick a font that exists on macOS (dev) and Ubuntu (CI)."""
    try:
        from PIL import ImageFont
    except Exception:
        return None
    candidates = [
        "/System/Library/Fonts/SF-Pro-Display-Bold.otf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_card(draw, x, y, w, h, fill=CARD_COLOR, border=HAIRLINE, radius=24):
    """Rounded-rect 'card' to mirror the Apple aesthetic in the app."""
    try:
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=radius,
            fill=fill,
            outline=border,
            width=2,
        )
    except Exception:
        # Older Pillow without rounded_rectangle support
        draw.rectangle((x, y, x + w, y + h), fill=fill, outline=border, width=2)


def _render_intro_slide(today: dt.date, out_path: Path) -> None:
    from PIL import Image, ImageDraw  # local import; PIL ships with Streamlit
    img = Image.new("RGB", (W, H), BG_COLOR)
    d = ImageDraw.Draw(img)
    _draw_card(d, 100, 120, W - 200, H - 240, radius=32)

    f_label = _font(40)
    f_h1 = _font(120)
    f_h2 = _font(56)
    f_meta = _font(32)

    d.text((180, 220), "AML AGENTS · DAILY BRIEFING", font=f_label, fill=ACCENT)
    d.text((180, 320), today.strftime("%A"), font=f_h2, fill=TEXT_SECONDARY)
    d.text((180, 410), today.strftime("%d %B %Y"), font=f_h1, fill=TEXT_PRIMARY)
    d.text(
        (180, H - 220),
        "News  ·  Obligations  ·  Horizon scanning",
        font=f_meta,
        fill=TEXT_SECONDARY,
    )
    img.save(out_path, "PNG")


def _render_content_slide(
    *,
    section: str,
    headline: str,
    summary: str,
    out_path: Path,
) -> None:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG_COLOR)
    d = ImageDraw.Draw(img)
    _draw_card(d, 100, 120, W - 200, H - 240, radius=32)

    f_label = _font(36)
    f_head = _font(76)
    f_body = _font(38)

    d.text((180, 200), section.upper(), font=f_label, fill=ACCENT)

    # Wrap headline manually — width-limited to ~22 chars at this font size.
    wrapped_head = textwrap.fill(headline, width=42)
    d.text((180, 290), wrapped_head, font=f_head, fill=TEXT_PRIMARY, spacing=12)

    wrapped_body = textwrap.fill(summary, width=68)
    d.text((180, 600), wrapped_body, font=f_body, fill=TEXT_SECONDARY, spacing=10)

    d.text((180, H - 180), "amlagents.streamlit.app", font=_font(28), fill=TEXT_SECONDARY)
    img.save(out_path, "PNG")


def _render_outro_slide(out_path: Path) -> None:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG_COLOR)
    d = ImageDraw.Draw(img)
    _draw_card(d, 100, 120, W - 200, H - 240, radius=32)
    d.text((180, 380), "Subscribe to the daily briefing", font=_font(72), fill=TEXT_PRIMARY)
    d.text((180, 500), "amlagents.streamlit.app", font=_font(56), fill=ACCENT)
    d.text(
        (180, 620),
        "TrustSphere Partners  ·  AML Agents",
        font=_font(36),
        fill=TEXT_SECONDARY,
    )
    img.save(out_path, "PNG")


def _compose_video(
    *,
    slide_paths: list[Path],
    audio_path: Path | None,
    out_path: Path,
    duration_total_s: int,
) -> bool:
    """FFmpeg compose: each slide displays for duration_total_s/n seconds,
    with the MP3 (if any) as the audio track. Returns True on success."""
    if not _have_ffmpeg() or not slide_paths:
        return False

    n = len(slide_paths)
    per_slide = max(2.0, duration_total_s / n)

    # Build a concat list file pointing at the slides.
    concat_file = out_path.with_suffix(".concat.txt")
    lines = []
    for p in slide_paths:
        lines.append(f"file '{p.absolute()}'")
        lines.append(f"duration {per_slide}")
    # FFmpeg concat-demuxer quirk: last file needs to be repeated without duration.
    lines.append(f"file '{slide_paths[-1].absolute()}'")
    concat_file.write_text("\n".join(lines))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", "scale=1920:1080,format=yuv420p",
        "-r", "30",
    ]
    if audio_path and audio_path.exists():
        cmd += ["-i", str(audio_path), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "22", str(out_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        ok = True
    except Exception:
        ok = False
    finally:
        try:
            concat_file.unlink()
        except Exception:
            pass
    return ok


def generate_daily_video(
    *,
    today: dt.date | None = None,
    headlines: list[tuple[str, str, str]] | None = None,
    audio_path: Path | None = None,
    duration_seconds: int = 240,
) -> VideoResult:
    """Generate today's video. `headlines` is a list of (section, headline,
    summary) tuples. If omitted, a stub list is used so the cron run still
    produces an MP4 placeholder.

    `audio_path` should be the daily-podcast MP3 (so the video and the
    podcast share the same voice track)."""
    today = today or dt.date.today()
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    if headlines is None:
        headlines = [
            (
                "Today's brief",
                "AML Agents Daily Briefing",
                "Configure ANTHROPIC_API_KEY, OPENAI_API_KEY and the daily-"
                "briefing GitHub Actions workflow to populate this slot.",
            )
        ]

    work = VIDEO_DIR / f"{today.isoformat()}_slides"
    work.mkdir(exist_ok=True)
    slide_paths: list[Path] = []

    try:
        intro = work / "00_intro.png"
        _render_intro_slide(today, intro)
        slide_paths.append(intro)
        for i, (section, headline, summary) in enumerate(headlines, 1):
            slide = work / f"{i:02d}_content.png"
            _render_content_slide(
                section=section,
                headline=headline,
                summary=summary,
                out_path=slide,
            )
            slide_paths.append(slide)
        outro = work / "99_outro.png"
        _render_outro_slide(outro)
        slide_paths.append(outro)
    except Exception:
        # PIL unavailable / font issue / disk issue: produce no slides; we
        # will still write a sidecar so the cron run reports cleanly.
        slide_paths = []

    mp4_path = VIDEO_DIR / f"{today.isoformat()}.mp4"
    sidecar_path = VIDEO_DIR / f"{today.isoformat()}.json"
    composed = _compose_video(
        slide_paths=slide_paths,
        audio_path=audio_path,
        out_path=mp4_path,
        duration_total_s=duration_seconds,
    )
    if not composed:
        # Write an empty placeholder so the player widget can show a
        # 'video pending' state without 404ing.
        if not mp4_path.exists():
            mp4_path.write_bytes(b"")

    title = f"AML Agents Briefing — {today.strftime('%A, %d %B %Y')}"
    sidecar = {
        "date": today.isoformat(),
        "title": title,
        "duration_seconds": duration_seconds,
        "n_slides": len(slide_paths),
        "stub": not composed,
        "audio_used": str(audio_path) if audio_path else None,
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2))

    return VideoResult(
        date=today.isoformat(),
        mp4_path=mp4_path,
        sidecar_path=sidecar_path,
        title=title,
        duration_seconds=duration_seconds,
        n_slides=len(slide_paths),
        stub=not composed,
    )


def latest_video() -> VideoResult | None:
    if not VIDEO_DIR.exists():
        return None
    today = dt.date.today()
    today_path = VIDEO_DIR / f"{today.isoformat()}.json"
    if today_path.exists():
        return _load_sidecar(today_path)
    candidates = sorted(VIDEO_DIR.glob("*.json"), reverse=True)
    if candidates:
        return _load_sidecar(candidates[0])
    return None


def _load_sidecar(path: Path) -> VideoResult:
    data = json.loads(path.read_text())
    return VideoResult(
        date=data["date"],
        mp4_path=path.with_suffix(".mp4"),
        sidecar_path=path,
        title=data["title"],
        duration_seconds=data.get("duration_seconds", 0),
        n_slides=data.get("n_slides", 0),
        stub=data.get("stub", False),
    )
