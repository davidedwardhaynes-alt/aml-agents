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

PODCAST_SYSTEM_PROMPT = """You are the writer for AML Agents Briefing, a 4 to 6 minute \
two-host conversation podcast for MLROs, heads of financial crime compliance, AML \
supervisors, and senior compliance leaders across the Asia-Pacific region. Voice is \
closest to NPR's *The Indicator from Planet Money*, *FT News Briefing*, and *Bloomberg \
Surveillance Daybreak Asia*. Authoritative, conversational, specific. No marketing fluff. \
No hedging where facts are clear. No words like "shocking" or "groundbreaking."

TWO HOSTS — the script is a dialogue between two co-hosts:

ALEX is the lead host. Voice: UK male, broadcast-style, authoritative. Drives the \
agenda. Introduces each story. Frames the regulatory significance.

JORDAN is the practitioner co-host. Voice: UK female, warm, sharp. Translates \
regulatory developments into operational implications for the listener. Asks Alex \
follow-up questions to draw out detail. Provides the action items.

FORMAT — the script MUST use these EXACT speaker tags, one per turn, on a new line:

ALEX: [Alex's spoken line]
JORDAN: [Jordan's spoken line]

Use the speaker tags ONLY at the start of a turn. Do not write "ALEX says" or "JORDAN \
asks" inside narration. The tag is the dialogue prefix; everything after the colon is \
literal spoken text. Each turn is one or more sentences. Aim for natural exchange — \
short rejoinders ("Right, and...", "That's the key point.", "So what should listeners \
do?") interleaved with longer explanatory turns.

CRITICAL — this script is read aloud by a text-to-speech engine, so:
- Write only what should be spoken. Do not include any markdown, bullet points, \
numbered lists, headings, or formatting characters of any kind.
- Do not use em-dashes (—), en-dashes (–), or hyphen-dashes (---). Use commas, \
semicolons, or simply rephrase. The TTS engine reads these out loud as the word "dash."
- Do not use section dividers like ---, ***, ===, or any decorative separators.
- Do not use parentheses or square brackets for asides. Build asides into the sentence \
flow, the way a podcast host would speak them.
- Do not use bullet points or numbered lists when introducing items. Say "the first item is, \
the second is, and the third is" naturally.
- Use contractions where natural (it's, we're, that's, won't) — they sound human.
- Spell out abbreviations on first reference, then use the abbreviation.
- For currency amounts, write them as a speaker would say them: "three point seven million \
Singapore dollars" not "S$3.7m"; "eighteen million Hong Kong dollars" not "HK$18m".
- For statute references, prefer the spoken form: "Section 84 of the AML/CTF Act" not "s.84 \
AML/CTF Act"; "Article 23 of Indonesia's Law Number 8 of 2010" not "UU TPPU 2010 Art. 23".
- Use spoken transitions between segments. Natural phrases like "moving on", "elsewhere in \
the region", "shifting our focus", "on a related note", "what to watch", or "before we close."
- End with a sign-off line in the host's natural voice.

PAUSE CONTROL — the TTS engine pauses on every period and on every line break, \
so write to control where the listener experiences silence:
- Prefer shorter declarative sentences. Aim for 12 to 22 words per sentence. \
A 30-word sentence with two commas will pause awkwardly mid-thought.
- Do not break lines mid-paragraph. One logical thought is one paragraph, with \
sentence-final periods doing the pacing. Use a blank line only between major \
segment changes.
- Avoid abbreviations with internal periods (such as a.m., U.S., U.K.). Write \
"morning", "United States", "United Kingdom" or use the unspaced abbreviation.
- Avoid ellipses (...) entirely. Use a comma or finish the sentence.
- For numbers in a series, separate them with explicit conjunctions: "the four \
exchanges Upbit, Bithumb, Coinone, and Korbit" rather than relying on commas alone.
- For statute or notice numbers, use connecting prepositions: "Notice 626" not \
"Notice six twenty six". Multi-digit codes are fine spoken naturally.
- Read each sentence aloud in your head before writing the next. If it sounds \
choppy, rewrite it.

Flow (deliver as a dialogue alternating ALEX and JORDAN turns, no headings):
1. ALEX opens with the welcome and frames the day. He says this is an audio overview of \
today's most material APAC AML and financial-crime developments, and directs the listener \
to amlagents dot streamlit dot app for the underlying detail, full obligation register, \
news sources, and horizon scanning. JORDAN comes in with a short reaction ("Big day, \
Alex.") and previews the agenda. The whole opening should fit inside the first 30 seconds.
2. ALEX introduces the highest-impact news story. JORDAN asks at least one follow-up \
question, then summarises the operational implication for listeners. Total 90-120 seconds \
across 6-10 alternating turns.
3. ALEX transitions to the second story; JORDAN drives the action item. Total 45-60 \
seconds across 4-6 alternating turns.
4. JORDAN introduces the third story (so the agenda alternates lead); ALEX adds the \
read-across. Total 45-60 seconds across 4-6 alternating turns.
5. ALEX moves to forward-looking what-to-watch. JORDAN closes each segment with one \
or two concrete next steps for the listener's coming week. 45-60 seconds.
6. JORDAN signs off with the prompt to visit amlagents dot streamlit dot app for full \
detail. ALEX adds the final word. Natural, friendly sign-off.

ACTION ITEMS — this is a working briefing, not a news bulletin. The listener is an \
MLRO, head of FCC, fraud lead, or AML supervisor with a busy morning. Every story \
segment must give them at least one concrete action, suggestion, or next step they can \
take today. JORDAN typically delivers the action items, prompted by a transition cue \
from ALEX such as "So what should listeners do?" or "What's the read-across?". Be \
specific:
- Reference the role being addressed where it sharpens the action: "If you're the \
MLRO at a virtual bank...", "For heads of fraud at an EMI...", "For AML/CTF compliance \
officers running tranche-two readiness..."
- Suggest a specific artefact or process: "convene your transaction-monitoring team \
this week to review", "before Friday's risk committee, pull the last six months of...", \
"add this to your next thematic-review scope", "raise this with your group head of \
financial crime before Monday."
- For deadlines, tell them what to file or check: "verify your STR governance pack is \
ready for the December audit committee", "confirm your KYT vendor integration covers \
both inbound and outbound flows."
- For enforcement actions, draw the lesson: "the read-across for your bank is...", \
"what regulators in your jurisdiction will look for next is..."
- For the closing what-to-watch segment, JORDAN names two or three concrete next steps \
listeners should take in the coming week.

Length: 900 to 1300 words total across both speakers (about 5 to 7 minutes spoken at \
175 words per minute). MUST be at least 900 words. The dialogue-format and action-items \
requirements add roughly 200 to 300 words over a single-host format. \
Reference real regulatory frameworks (FATF Recommendations, MAS Notices, HKMA Guidelines, \
the AMLA, the AML/CTF Act, Indonesia's Law Number 8 of 2010) with specificity. Use first \
names and last initials for executives where appropriate.

Output only the spoken script. No host instructions. No music cues. No stage directions. \
No metadata. Pure spoken prose, ready for the microphone."""


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
def _scrub_for_tts(text: str) -> str:
    """Strip TTS-hostile characters and normalise punctuation so the
    synthesised voice flows naturally.

    Things gTTS reads literally that we want to remove:
      - section dividers like '---', '***', '===' (read as "dash dash dash")
      - em-dashes '—' and en-dashes '–' (read as "dash")
      - markdown headers '#', '##', '###'
      - bullet markers '-', '*', '•' at start of line
      - parentheses around asides (read with awkward pauses)
      - asterisks for emphasis (read as "asterisk")
      - inline code backticks
      - URL fragments
      - multiple consecutive blank lines

    Things we normalise so the voice flows better:
      - em/en-dash mid-sentence -> ", " (natural pause without saying 'dash')
      - line-leading numerals like '1.' / '1)' -> nothing (dropped — the
        sentence prefix carries the order naturally)
      - smart quotes -> straight quotes
    """
    import re

    if not text:
        return text

    out = text

    # Smart quotes → straight quotes (TTS handles them but normalise anyway)
    out = (
        out.replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
    )

    # Section dividers on their own line (must run BEFORE em-dash replacement)
    out = re.sub(r"^[ \t]*[-—–=*_]{3,}[ \t]*$", "", out, flags=re.MULTILINE)

    # Em-dashes and en-dashes mid-sentence → comma + space.
    # Handle both surrounded-by-spaces and tight-bound forms.
    out = re.sub(r"\s*[—–]\s*", ", ", out)

    # Line-leading bullet markers — skip lines starting with a SPEAKER:
    # tag (we preserve those for the dialogue parser).
    out = re.sub(
        r"^(?![A-Z]+:)[ \t]*[-*•][ \t]+",
        "",
        out,
        flags=re.MULTILINE,
    )

    # Markdown headers
    out = re.sub(r"^#+[ \t]*", "", out, flags=re.MULTILINE)

    # Numbered list prefixes "1." / "1)" — skip lines starting with
    # SPEAKER: tag.
    out = re.sub(
        r"^(?![A-Z]+:)\s*\d+[.)][ \t]+",
        "",
        out,
        flags=re.MULTILINE,
    )

    # Strip asterisks used for emphasis (gTTS reads "asterisk")
    out = re.sub(r"\*+", "", out)

    # Strip inline code backticks
    out = out.replace("`", "")

    # Drop bracketed asides — content kept, brackets removed
    out = re.sub(r"\(([^)]{1,80})\)", r", \1,", out)
    out = re.sub(r"\[([^\]]{1,80})\]", r"\1", out)

    # Collapse multiple blank lines so paragraph breaks are short pauses
    out = re.sub(r"\n{3,}", "\n\n", out)

    # Clean up leftover double spaces and orphan commas from the dash
    # replacement (e.g. ", , " or " , ")
    out = re.sub(r" *, *,(?: *,)*", ", ", out)
    out = re.sub(r"  +", " ", out)
    # Strip trailing comma on a sentence that originally ended with em-dash
    out = re.sub(r", *(?=[.\n])", "", out)

    return out.strip()


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


# Edge Neural voices — paired so they sound complementary in dialogue.
EDGE_VOICE_ALEX = "en-GB-RyanNeural"   # UK male, lead host
EDGE_VOICE_JORDAN = "en-GB-SoniaNeural"  # UK female, co-host

# Map speaker tag → voice name. Extra aliases for robustness if Claude
# slips into HOST/HOST-1 etc.
SPEAKER_VOICES = {
    "ALEX": EDGE_VOICE_ALEX,
    "HOST": EDGE_VOICE_ALEX,
    "HOST 1": EDGE_VOICE_ALEX,
    "HOST1": EDGE_VOICE_ALEX,
    "A": EDGE_VOICE_ALEX,
    "JORDAN": EDGE_VOICE_JORDAN,
    "CO-HOST": EDGE_VOICE_JORDAN,
    "HOST 2": EDGE_VOICE_JORDAN,
    "HOST2": EDGE_VOICE_JORDAN,
    "J": EDGE_VOICE_JORDAN,
    "B": EDGE_VOICE_JORDAN,
}


def _split_dialogue_turns(script: str) -> list[tuple[str, str]]:
    """Parse a multi-speaker script into [(voice, text), ...].

    Returns an empty list when the script doesn't contain any recognised
    speaker tags — caller falls back to single-voice synthesis."""
    import re

    if not script:
        return []

    pattern = re.compile(
        r"^[ \t]*([A-Z][A-Z0-9 \-_]{0,15}):[ \t]*",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(script))
    if not matches:
        return []

    turns: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        tag = m.group(1).upper().strip()
        voice = SPEAKER_VOICES.get(tag)
        if not voice:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(script)
        text = script[start:end].strip()
        if text:
            turns.append((voice, text))
    return turns


async def _edge_tts_synthesize_one(text: str, voice: str) -> bytes:
    """Render a single utterance via edge-tts. Returns raw MP3 bytes."""
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text=text, voice=voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def _synthesize_via_edge_tts(script: str) -> bytes | None:
    """Free natural-sounding TTS using Microsoft Edge's Azure Cognitive
    Services neural voices, via the `edge-tts` library. No API key
    required; same endpoint that powers Edge browser's read-aloud.

    DIALOGUE MODE: when the script contains recognised speaker tags
    (ALEX:, JORDAN:, HOST:, etc.), each turn is synthesised with its
    own voice and the resulting MP3 streams are concatenated. The MP3
    container format permits raw stream concat — every player handles
    the result correctly.

    SOLO MODE: when no speaker tags are present, the entire script is
    rendered in en-GB-RyanNeural.

    Returns MP3 bytes or None on failure."""
    if not script:
        return None
    try:
        import asyncio
        import edge_tts  # noqa: F401 — import-presence check only
    except Exception:
        return None

    turns = _split_dialogue_turns(script)

    async def _run_dialogue() -> bytes:
        parts: list[bytes] = []
        for voice, text in turns:
            audio = await _edge_tts_synthesize_one(text, voice)
            if audio:
                parts.append(audio)
        return b"".join(parts)

    async def _run_solo() -> bytes:
        return await _edge_tts_synthesize_one(script, EDGE_VOICE_ALEX)

    coro = _run_dialogue() if turns else _run_solo()

    try:
        try:
            data = asyncio.run(coro)
        except RuntimeError:
            # If we're inside an event loop (e.g. Streamlit script-run
            # context), spin up a fresh loop.
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(coro)
            finally:
                loop.close()
        if not data or len(data) < 1024:
            return None
        return data
    except Exception:
        return None


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

    Resolution order (best → worst):
      1. OpenAI TTS (gpt-4o-mini-tts, voice 'alloy') if OPENAI_API_KEY
         set — most expressive voice. ~$0.05 / 5min episode.
      2. Microsoft Edge Neural TTS (en-GB-RyanNeural via edge-tts) —
         FREE; closest to FT-broadcast / Bloomberg Surveillance cadence.
         Best free option for a daily briefing.
      3. gTTS (Google Translate TTS via the `gtts` library) — FREE,
         workable but more robotic.
      4. 5-second silent MP3 stub — last resort when none of the above
         succeed (e.g. network outage in the cron container).
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
            pass  # fall through to edge-tts

    # 2. Free natural-voice fallback: Microsoft Edge Neural TTS
    edge_audio = _synthesize_via_edge_tts(script)
    if edge_audio:
        # Distinguish dialogue (2 voices) from solo so the player badge
        # can label correctly.
        was_dialogue = bool(_split_dialogue_turns(script))
        voice_tag = (
            "edge:dialogue:Ryan+Sonia"
            if was_dialogue
            else "edge:en-GB-RyanNeural"
        )
        return edge_audio, False, voice_tag

    # 3. Free robotic-voice fallback: gTTS
    gtts_audio = _synthesize_via_gtts(script)
    if gtts_audio:
        return gtts_audio, False, "gtts:en-uk"

    # 4. Last resort: silent stub
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
    # Scrub the script for TTS — strip section dividers, em-dashes, markdown,
    # asterisks, ellipses and other characters that gTTS reads literally or
    # that produce awkward pauses. The transcript shown in the app uses the
    # ORIGINAL `script`; only `script_for_tts` is sent to the synthesizer.
    script_for_tts = _scrub_for_tts(script)
    audio_bytes, is_stub, voice_used = _synthesize_audio(
        script_for_tts, api_key=openai_key
    )

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
