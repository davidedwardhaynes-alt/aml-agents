"""Render a short A/B sample of the evening show through ElevenLabs.

Purpose is to choose a voice pairing and a model by ear before
committing a daily to either. Renders the same excerpt several ways and
writes the MP3s side by side.

Two things here matter more than the voice choice:

*Model.* `eleven_v3_conversational` is tuned for dialogue;
`eleven_multilingual_v2` — what Midnight Library uses — is tuned for
audiobook narration. For a two-hander the second reads each turn as a
self-contained performance, which is a large part of why synthetic
dialogue sounds synthetic.

*Stitching.* Each turn is sent with `previous_text` and `next_text` set
to the surrounding turns. ElevenLabs uses them for prosody only — they
are not spoken — so a turn ending in a question and a turn answering it
carry the intonation across the cut instead of each starting cold.

Run:  .venv/bin/python3 scripts/render_evening_sample.py <script.txt>
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.elevenlabs_voices import api_key  # noqa: E402

API = "https://api.elevenlabs.io/v1/text-to-speech"
OUT_DIR = ROOT / "data" / "evening" / "voice-tests"

# The only British-accented options on the account that suit a news
# two-hander; the rest of the professional British voices are sleep and
# ASMR voices carried over from Midnight Library.
DANIEL = "onwK4e9ZLuTAKqWW03F9"   # Daniel — Steady Broadcaster, British male
ALICE = "Xb7hH8MSUJpSbSDYk0k2"    # Alice — Clear, Engaging Educator, British female
LILY = "pFZP5JQG7iQjIQuC4Bku"     # Lily — Velvety Actress, British female

VARIANTS = [
    ("a-daniel-alice-v3conv", DANIEL, ALICE, "eleven_v3_conversational"),
    ("b-daniel-lily-v3conv", DANIEL, LILY, "eleven_v3_conversational"),
    ("c-daniel-alice-multi2", DANIEL, ALICE, "eleven_multilingual_v2"),
]

MAX_TURNS = 12


def parse_turns(path: pathlib.Path) -> list[tuple[str, str]]:
    """Pull (speaker, text) out of a speaker-tagged script."""
    turns: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Z]+):\s*(.+)$", line)
        if m:
            turns.append((m.group(1), m.group(2).strip()))
        elif turns:
            # Continuation of the previous turn.
            speaker, text = turns[-1]
            turns[-1] = (speaker, f"{text} {line}")
    return turns


def synth(text: str, voice_id: str, model: str, key: str,
          previous_text: str = "", next_text: str = "") -> bytes:
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.45,      # lower = more expressive variation
            "similarity_boost": 0.75,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }
    # Context for prosody. Not spoken. The v3 models reject these
    # outright ("Providing previous_text or next_text is not yet
    # supported"), which is the central trade-off of this test: v3
    # conversational is trained on dialogue but renders each turn
    # cold, while multilingual v2 can carry intonation across a cut
    # but is tuned for audiobook narration.
    if not model.startswith("eleven_v3"):
        if previous_text:
            body["previous_text"] = previous_text
        if next_text:
            body["next_text"] = next_text

    req = urllib.request.Request(
        f"{API}/{voice_id}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code} for model={model}: {detail}")


def concat(parts: list[bytes], out_path: pathlib.Path) -> None:
    """Join the per-turn MP3s with a short gap between speakers."""
    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        listing = td_path / "files.txt"
        lines = []
        for i, chunk in enumerate(parts):
            p = td_path / f"{i:03d}.mp3"
            p.write_bytes(chunk)
            lines.append(f"file '{p}'")
        listing.write_text("\n".join(lines))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(out_path)],
            check=True, capture_output=True,
        )


def main() -> int:
    script_path = pathlib.Path(
        sys.argv[1] if len(sys.argv) > 1
        else ROOT / "data" / "evening" / "sample-natural-script.txt"
    )
    turns = parse_turns(script_path)[:MAX_TURNS]
    if not turns:
        raise SystemExit(f"no speaker-tagged turns found in {script_path}")

    key = api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chars = sum(len(t) for _, t in turns)
    print(f"{len(turns)} turns, {chars:,} characters per variant")
    print(f"{len(VARIANTS)} variants -> ~{chars * len(VARIANTS):,} credits\n")

    for name, alex_voice, jordan_voice, model in VARIANTS:
        print(f"{name} ({model})")
        parts: list[bytes] = []
        for i, (speaker, text) in enumerate(turns):
            voice = alex_voice if speaker == "ALEX" else jordan_voice
            audio = synth(
                text, voice, model, key,
                previous_text=turns[i - 1][1] if i else "",
                next_text=turns[i + 1][1] if i + 1 < len(turns) else "",
            )
            parts.append(audio)
            print(f"  {i+1:>2}. {speaker:<7} {len(text):>4} chars -> {len(audio):>7,} bytes")
        out = OUT_DIR / f"{name}.mp3"
        concat(parts, out)
        print(f"  -> {out}  ({out.stat().st_size:,} bytes)\n")

    print("Listen and pick one. Voice IDs are in VARIANTS at the top of this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
