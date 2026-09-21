"""List the ElevenLabs voices and credit balance on David's account.

Read-only. The key is read the same way the Midnight Library nightly
render reads it — from its own credentials.env, in place — and is never
printed, logged or copied anywhere. Only voice metadata and the credit
balance come out.

Run:  .venv/bin/python3 scripts/elevenlabs_voices.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

CREDENTIALS = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Claude Folder/"
    "Midnight Library/credentials.env"
)
API = "https://api.elevenlabs.io/v1"


def api_key() -> str:
    """Read the key from Midnight Library's credentials.env.

    Same one-line KEY=value shape that batch_produce.py parses. An
    ELEVENLABS_API_KEY environment variable wins if set, so this works
    in a context where the iCloud file is unreadable."""
    env = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if env:
        return env
    with open(CREDENTIALS, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit(f"no key found in {CREDENTIALS}")


def get(path: str, key: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"xi-api-key": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Never echo the key, even in an error path.
        raise SystemExit(f"ElevenLabs {path} returned HTTP {e.code}: {e.reason}")


def main() -> int:
    key = api_key()

    sub = get("/user/subscription", key)
    used = sub.get("character_count", 0)
    limit = sub.get("character_limit", 0)
    print(f"Tier     : {sub.get('tier')}")
    print(f"Credits  : {used:,} used of {limit:,}  ({limit - used:,} left)")
    print(f"Resets   : {sub.get('next_character_count_reset_unix')}")
    print()

    voices = get("/voices", key).get("voices", [])
    print(f"{len(voices)} voices on the account\n")
    for v in voices:
        labels = v.get("labels") or {}
        desc = ", ".join(
            f"{k}={labels[k]}" for k in ("accent", "gender", "age", "description")
            if labels.get(k)
        )
        print(f"  {v.get('name','?'):<28} {v.get('voice_id','')}")
        print(f"    category={v.get('category','?')}  {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
