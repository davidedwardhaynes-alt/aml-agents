"""Daily podcast — generate a 3-5 minute audio briefing from the day's
news + obligations + horizon items.

Two-stage pipeline:
  1. Claude generates a conversational script (FT-quality voice, spoken
     idiom rather than written prose). Sonnet 4.6 handles this in one
     short call (~$0.08 / day at current pricing).
  2. OpenAI TTS converts the script to MP3 (gpt-4o-mini-tts, voice
     'alloy'; ~$0.05 / day at 5,400 chars).

Output: an MP3 file at data/podcasts/YYYY-MM-DD.mp3 plus a JSON sidecar
with title, summary, duration, and the generation token usage so the
cron run can be audited.

When ANTHROPIC_API_KEY or OPENAI_API_KEY is missing, the function still
runs end-to-end but writes a STUB MP3 (5 seconds of silence) and a
sidecar marked stub=true. This lets the cron workflow be enabled before
TTS is hooked up; the live app then shows 'Today's podcast (stub —
configure OPENAI_API_KEY to generate real audio)'.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import struct
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PODCAST_DIR = Path(__file__).parent.parent / "data" / "podcasts"
CLAUDE_MODEL = "claude-sonnet-4-6"
OPENAI_TTS_ENDPOINT = "https://api.openai.com/v1/audio/speech"
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
OPENAI_TTS_VOICE = "alloy"  # warm, neutral; works for SG/HK MLRO audience

PODCAST_SYSTEM_PROMPT = """You are the daily host of *AML Agents Briefing*, a 3–5 minute audio show \
for MLROs, Heads of FCC, AML supervisors, and senior compliance leaders across APAC. \
Voice: Financial Times audio briefings + Bloomberg Surveillance + The Indicator from Planet Money. \
Authoritative, conversational, specific. No marketing fluff, no hedging where facts are clear, \
no "shocking" or "groundbreaking."

Structure:
- 15-second cold-open with the single most material item of the day
- 60-90 seconds on the highest-impact news story
- 30-45 seconds on each of two further stories
- 30-second "what to watch" closing on an upcoming deadline or horizon item

Length: 600-900 words (≈ 3.5–5 minutes spoken at 175 wpm). Reference real regulatory frameworks \
(FATF Recommendations, MAS Notices, HKMA Guidelines, AMLA, AML/CTF Act, UU TPPU 2010) \
with specificity. Use first names + last initials for executives where appropriate. \
No music cues, no "[applause]" stage directions — just the host's spoken words."""


@dataclass
class PodcastResult:
    date: str
    mp3_path: Path
    sidecar_path: Path
    title: str
    duration_seconds: int
    script_chars: int
    stub: bool
    cost_estimate_usd: float


# ---------------------------------------------------------------------------
# Stub MP3 — a 5-second silent MP3 (pre-encoded as a minimal valid MP3
# stream with a single silent frame repeated). When neither Anthropic nor
# OpenAI keys are available, we write this so the audio player widget in
# the app still has a file to point at.
# ---------------------------------------------------------------------------
def _silent_mp3_bytes(seconds: int = 5) -> bytes:
    """Build a tiny valid silent MP3.

    Each frame is 4-byte MPEG-1 Layer 3 header (0xFFFB9064 → MPEG-1 L3,
    128 kbps, 44.1 kHz, mono, no padding, no CRC) plus 413 zero bytes for
    the (silent) audio payload. 26 ms / frame → ~38 frames per second.
    Used only as the last-resort fallback when both OpenAI TTS and gTTS
    are unavailable."""
    header = b"\xff\xfb\x90\x64"
    payload = b"\x00" * 413  # 417-byte total frame
    frame = header + payload
    n_frames = max(1, int(seconds * 38))
    return frame * n_frames


def _synthesize_via_gtts(script: str) -> bytes | None:
    """Free fallback TTS using Google's public translate-tts endpoint via the
    `gtts` library. No API key required, generous unofficial rate limit.
    Returns MP3 bytes or None if gTTS isn't installed or the call fails.

    gTTS chunks long text automatically and concatenates the resulting MP3
    frames into a single playable file. Quality is decent (closer to a
    Google Voice Assistant than to OpenAI's expressive 'alloy') but
    perfectly listenable for a 3-5 minute briefing."""
    if not script:
        return None
    try:
        from gtts import gTTS  # type: ignore
    except Exception:
        return None
    try:
        from io import BytesIO

        # 'en-uk' picks the British English voice — closer to FT-style
        # broadcast voice than the default US neutral. tld 'co.uk' is
        # what gTTS uses to surface the UK voice.
        tts = gTTS(text=script, lang="en", tld="co.uk", slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        data = buf.getvalue()
        # Sanity check — gTTS output must start with an MPEG/ID3 tag.
        if not data or len(data) < 1024:
            return None
        return data
    except Exception:
        return None


def _build_script(
    *,
    digest_text_summary: str,
    api_key: str | None,
) -> tuple[str, dict[str, int]]:
    """Generate the spoken script via Claude. Returns (script, usage_dict).
    On any failure or missing key, returns a stub script + zeroed usage."""
    if not api_key:
        stub = (
            "Welcome to the AML Agents Briefing. This is a stub episode — the "
            "ANTHROPIC_API_KEY secret is not configured for the daily-briefing "
            "GitHub Actions workflow. Once it is, this slot will carry a "
            "three-to-five minute conversational summary of the day's most "
            "material APAC financial-crime developments, drawn from the same "
            "news, obligations, and horizon-scanning feeds you see in the app. "
            "Goodbye for now."
        )
        return stub, {"input_tokens": 0, "output_tokens": 0}

    try:
        from anthropic import Anthropic  # local import — only needed here
    except Exception:
        return ("", {"input_tokens": 0, "output_tokens": 0})

    client = Anthropic(api_key=api_key)
    user_prompt = (
        "Write today's *AML Agents Briefing* episode based on the digest "
        "summary below. The summary lists the highest-priority items from "
        "news, obligations falling due, and horizon-scanning feeds. Keep the "
        "episode 600-900 words. Output ONLY the spoken script — no host "
        "instructions, no music cues, no episode metadata.\n\n"
        f"Digest summary for {dt.date.today().isoformat()}:\n\n"
        f"{digest_text_summary}"
    )
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=PODCAST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        return (f"[Script generation failed: {e}]", {"input_tokens": 0, "output_tokens": 0})

    text = resp.content[0].text.strip() if resp.content else ""
    return text, {
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }


def _synthesize_audio(
    script: str,
    *,
    api_key: str | None,
) -> tuple[bytes, bool, str]:
    """Synthesize audio for the script. Returns (mp3_bytes, is_stub, voice_used).

    Resolution order:
      1. OpenAI TTS (gpt-4o-mini-tts, voice 'alloy') if OPENAI_API_KEY set —
         best quality, expressive voice.
      2. gTTS (Google translate TTS via the `gtts` library) — free, no
         API key required, decent quality, en-GB voice.
      3. 5-second silent MP3 stub — last resort when neither path works.
    """
    if not script:
        return _silent_mp3_bytes(seconds=5), True, "stub"

    # 1. Preferred: OpenAI TTS
    if api_key:
        payload = json.dumps(
            {
                "model": OPENAI_TTS_MODEL,
                "input": script[:4000],  # OpenAI TTS hard cap
                "voice": OPENAI_TTS_VOICE,
                "response_format": "mp3",
            }
        ).encode()
        req = urllib.request.Request(
            OPENAI_TTS_ENDPOINT,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if resp.status == 200 and data and len(data) > 1024:
                return data, False, f"openai:{OPENAI_TTS_VOICE}"
        except Exception:
            pass  # fall through to gTTS

    # 2. Fallback: gTTS (free, no key)
    gtts_audio = _synthesize_via_gtts(script)
    if gtts_audio:
        return gtts_audio, False, "gtts:en-uk"

    # 3. Last resort: silent stub
    return _silent_mp3_bytes(seconds=5), True, "stub"


def generate_daily_podcast(
    *,
    digest_summary: str,
    today: dt.date | None = None,
    anthropic_key: str | None = None,
    openai_key: str | None = None,
) -> PodcastResult:
    """Generate today's podcast and write it under data/podcasts/."""
    today = today or dt.date.today()
    PODCAST_DIR.mkdir(parents=True, exist_ok=True)

    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
    openai_key = openai_key or os.getenv("OPENAI_API_KEY")

    script, usage = _build_script(
        digest_text_summary=digest_summary,
        api_key=anthropic_key,
    )
    audio_bytes, is_stub, voice_used = _synthesize_audio(script, api_key=openai_key)

    # Cost estimate: Anthropic at ~$3 in / $15 out per million tokens
    # (Sonnet 4.6); OpenAI TTS gpt-4o-mini-tts at $0.015 per 1k chars;
    # gTTS is free (no per-character cost).
    tts_cost = (
        (len(script) / 1000) * 0.015
        if voice_used.startswith("openai")
        else 0.0
    )
    cost = (
        (usage.get("input_tokens", 0) / 1_000_000) * 3
        + (usage.get("output_tokens", 0) / 1_000_000) * 15
        + tts_cost
    )

    mp3_path = PODCAST_DIR / f"{today.isoformat()}.mp3"
    sidecar_path = PODCAST_DIR / f"{today.isoformat()}.json"
    mp3_path.write_bytes(audio_bytes)

    title = f"AML Agents Briefing — {today.strftime('%A, %d %B %Y')}"
    duration_estimate = max(60, int(len(script.split()) / 175 * 60))

    sidecar: dict[str, Any] = {
        "date": today.isoformat(),
        "title": title,
        "duration_seconds": duration_estimate,
        "script": script,
        "script_chars": len(script),
        "stub": is_stub,
        "voice": voice_used,
        "cost_estimate_usd": round(cost, 4),
        "tokens": usage,
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2))

    return PodcastResult(
        date=today.isoformat(),
        mp3_path=mp3_path,
        sidecar_path=sidecar_path,
        title=title,
        duration_seconds=duration_estimate,
        script_chars=len(script),
        stub=is_stub,
        cost_estimate_usd=round(cost, 4),
    )


def latest_podcast() -> PodcastResult | None:
    """Return today's podcast if generated, else the most recent prior one."""
    if not PODCAST_DIR.exists():
        return None
    today = dt.date.today()
    today_path = PODCAST_DIR / f"{today.isoformat()}.json"
    if today_path.exists():
        return _load_sidecar(today_path)
    candidates = sorted(PODCAST_DIR.glob("*.json"), reverse=True)
    if candidates:
        return _load_sidecar(candidates[0])
    return None


def _load_sidecar(path: Path) -> PodcastResult:
    data = json.loads(path.read_text())
    return PodcastResult(
        date=data["date"],
        mp3_path=path.with_suffix(".mp3"),
        sidecar_path=path,
        title=data["title"],
        duration_seconds=data.get("duration_seconds", 0),
        script_chars=data.get("script_chars", 0),
        stub=data.get("stub", False),
        cost_estimate_usd=data.get("cost_estimate_usd", 0.0),
    )
