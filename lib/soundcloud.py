"""SoundCloud uploader — pushes the daily podcast MP3 to a SoundCloud
account via the SoundCloud REST API.

SoundCloud's developer API is OAuth2-based. Two flows are supported:

  1. **client_credentials** (server-to-server, app-only) — works for
     uploading tracks to the app's own profile when the app has been
     enrolled in SoundCloud's API programme.

  2. **refresh_token** (long-lived) — the GitHub Actions cron is given
     a refresh token; on each run it exchanges it for a short-lived
     access_token and uploads the day's MP3.

Setup steps for the user (documented in SOUNDCLOUD_SETUP.md):

  a. Register an app at https://developers.soundcloud.com (note:
     SoundCloud has periodically restricted new app registration; if
     access is denied use the Zapier fallback path described in the
     setup doc).
  b. Set redirect_uri to a localhost URL (e.g. http://localhost:8888).
  c. Run scripts/soundcloud_get_refresh_token.py (interactive) which
     guides through the OAuth2 authorisation-code exchange and prints
     a refresh_token.
  d. Add three secrets to GitHub Actions:
       SOUNDCLOUD_CLIENT_ID, SOUNDCLOUD_CLIENT_SECRET,
       SOUNDCLOUD_REFRESH_TOKEN.
  e. The daily-briefing cron auto-uploads each new MP3 to the
     account's profile.

Each upload is tagged 'podcast' + the show's keyword set + a track
description that links back to amlagents.streamlit.app for full
detail.
"""

from __future__ import annotations

import datetime as dt
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

SOUNDCLOUD_TOKEN_ENDPOINT = "https://api.soundcloud.com/oauth2/token"
SOUNDCLOUD_TRACK_ENDPOINT = "https://api.soundcloud.com/tracks"
SOUNDCLOUD_ME_ENDPOINT = "https://api.soundcloud.com/me"

SHOW_TITLE = "AML Agents Briefing"
SHOW_TAG_LIST = (
    "AML compliance financial-crime APAC daily briefing podcast "
    "MLRO MAS HKMA BNM AUSTRAC JAFIC KoFIU AMLC PPATK FATF"
)
DEFAULT_DESCRIPTION = (
    "Daily two-host AML and financial-crime briefing for compliance "
    "leaders across Asia-Pacific. Hosts Alex and Jordan cover the "
    "morning's most material regulator notices, enforcement actions, "
    "obligations falling due, and horizon-scanning items, with concrete "
    "action items for your working day. Produced by TrustSphere "
    "Partners. Full detail at amlagents.streamlit.app."
)


@dataclass
class UploadResult:
    ok: bool
    track_id: int | None
    track_url: str | None
    error: str | None
    skipped_reason: str | None = None


def _refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> tuple[str, str | None]:
    """Exchange a refresh_token for a short-lived access_token. Returns
    (access_token, new_refresh_token_if_rotated). SoundCloud rotates
    refresh tokens on every refresh in some flows — caller should
    persist the new value if returned."""
    body = (
        f"grant_type=refresh_token"
        f"&client_id={urllib.parse.quote(client_id)}"
        f"&client_secret={urllib.parse.quote(client_secret)}"
        f"&refresh_token={urllib.parse.quote(refresh_token)}"
    )
    req = urllib.request.Request(
        SOUNDCLOUD_TOKEN_ENDPOINT,
        data=body.encode(),
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["access_token"], data.get("refresh_token")


def _multipart_track_upload(
    *,
    access_token: str,
    mp3_path: Path,
    title: str,
    description: str,
    tag_list: str,
    sharing: str,
    purchase_url: str | None,
) -> dict:
    """POST a track to /tracks with multipart/form-data. SoundCloud
    expects the audio in `track[asset_data]` and metadata in
    `track[title]` etc."""
    boundary = f"----amlagents{uuid.uuid4().hex}"

    fields = {
        "track[title]": title,
        "track[description]": description,
        "track[sharing]": sharing,             # "public" or "private"
        "track[downloadable]": "false",
        "track[tag_list]": tag_list,
        "track[license]": "all-rights-reserved",
        "track[genre]": "Business",
    }
    if purchase_url:
        fields["track[purchase_url]"] = purchase_url

    parts: list[bytes] = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        )
        parts.append(v.encode("utf-8"))
        parts.append(b"\r\n")

    # Audio file
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        b'Content-Disposition: form-data; '
        b'name="track[asset_data]"; filename="'
        + mp3_path.name.encode("utf-8")
        + b'"\r\n'
    )
    mime = mimetypes.guess_type(mp3_path.name)[0] or "audio/mpeg"
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
    parts.append(mp3_path.read_bytes())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(parts)

    req = urllib.request.Request(
        SOUNDCLOUD_TRACK_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_episode(
    *,
    mp3_path: Path,
    title: str,
    description: str,
    sharing: str = "public",
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
    access_token: str | None = None,
    purchase_url: str | None = None,
    tag_list: str = SHOW_TAG_LIST,
) -> UploadResult:
    """Upload one episode to SoundCloud. Returns UploadResult.

    Either supply (client_id + client_secret + refresh_token) for the
    refresh-token flow, OR supply access_token directly (e.g. for a
    short-lived test). When SOUNDCLOUD_* env vars are set they're used
    as defaults."""
    client_id = client_id or os.getenv("SOUNDCLOUD_CLIENT_ID")
    client_secret = client_secret or os.getenv("SOUNDCLOUD_CLIENT_SECRET")
    refresh_token = refresh_token or os.getenv("SOUNDCLOUD_REFRESH_TOKEN")
    access_token = access_token or os.getenv("SOUNDCLOUD_ACCESS_TOKEN")

    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
        return UploadResult(
            ok=False, track_id=None, track_url=None,
            error=f"MP3 not found or empty: {mp3_path}",
            skipped_reason="missing-file",
        )

    if not access_token:
        if not (client_id and client_secret and refresh_token):
            return UploadResult(
                ok=False, track_id=None, track_url=None,
                error=(
                    "SoundCloud credentials not configured. Set "
                    "SOUNDCLOUD_CLIENT_ID + SOUNDCLOUD_CLIENT_SECRET + "
                    "SOUNDCLOUD_REFRESH_TOKEN as GitHub Actions secrets, "
                    "or use the Zapier / manual upload paths described "
                    "in SOUNDCLOUD_SETUP.md."
                ),
                skipped_reason="no-credentials",
            )
        try:
            access_token, _new_refresh = _refresh_access_token(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            )
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                err_body = ""
            return UploadResult(
                ok=False, track_id=None, track_url=None,
                error=f"OAuth refresh failed (HTTP {e.code}): {err_body}",
            )
        except Exception as e:
            return UploadResult(
                ok=False, track_id=None, track_url=None,
                error=f"OAuth refresh failed: {type(e).__name__}: {e}",
            )

    try:
        result = _multipart_track_upload(
            access_token=access_token,
            mp3_path=mp3_path,
            title=title,
            description=description,
            tag_list=tag_list,
            sharing=sharing,
            purchase_url=purchase_url,
        )
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = ""
        return UploadResult(
            ok=False, track_id=None, track_url=None,
            error=f"Upload failed (HTTP {e.code}): {err_body}",
        )
    except Exception as e:
        return UploadResult(
            ok=False, track_id=None, track_url=None,
            error=f"Upload failed: {type(e).__name__}: {e}",
        )

    return UploadResult(
        ok=True,
        track_id=result.get("id"),
        track_url=result.get("permalink_url") or result.get("uri"),
        error=None,
    )


def is_configured() -> bool:
    """True if env-vars are set sufficient for an automated upload."""
    return bool(
        os.getenv("SOUNDCLOUD_ACCESS_TOKEN")
        or (
            os.getenv("SOUNDCLOUD_CLIENT_ID")
            and os.getenv("SOUNDCLOUD_CLIENT_SECRET")
            and os.getenv("SOUNDCLOUD_REFRESH_TOKEN")
        )
    )
