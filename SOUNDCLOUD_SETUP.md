# SoundCloud auto-upload setup

Daily podcast MP3s upload to your SoundCloud profile automatically each
morning, right after the GitHub Actions cron generates them. One-time
setup — five steps, ~10 minutes.

## Step 1 — Register a SoundCloud app (if you don't have one)

1. Go to <https://developers.soundcloud.com>
2. Sign in with the SoundCloud account you want the podcast uploaded to
3. Click **Register a new app** and fill in:
   - **App name**: `AML Agents Daily Briefing`
   - **Website**: `https://amlagents.streamlit.app`
   - **Redirect URI**: `http://localhost:8888/callback`
   - **Description**: brief description of the show
4. Save. SoundCloud may take a day or two to approve new app registrations
   — they have rate-limited new applications since 2014.

After approval you'll see:
- **Client ID** (~30 chars)
- **Client Secret** (~30 chars)

> **If SoundCloud rejects the app registration:** fall back to either
> Zapier (RSS-to-SoundCloud zap, ~$20/mo) or manual upload (drag-drop
> the MP3 from `https://amlagents.streamlit.app` News tab → "🎙 Today's
> briefing" expander).

## Step 2 — Mint the refresh token (one-time)

On your local machine, in the repo root:

```bash
.venv/bin/python scripts/soundcloud_get_refresh_token.py \
    --client-id YOUR_CLIENT_ID \
    --client-secret YOUR_CLIENT_SECRET
```

This will:
1. Open SoundCloud's authorisation page in your browser
2. You sign in (if not already) and click **Connect**
3. SoundCloud redirects to `http://localhost:8888/callback`
4. The script catches the redirect, exchanges the code, and prints:

```
SOUNDCLOUD_CLIENT_ID       = ...
SOUNDCLOUD_CLIENT_SECRET   = ...
SOUNDCLOUD_REFRESH_TOKEN   = ...
```

The refresh token is **long-lived** — this is a one-time exchange. After
this, the cron uses the refresh token to mint short-lived access
tokens forever.

## Step 3 — Add the three secrets to GitHub Actions

Go to: <https://github.com/davidedwardhaynes-alt/aml-agents/settings/secrets/actions>

Click **New repository secret** for each of:

| Name | Value |
|---|---|
| `SOUNDCLOUD_CLIENT_ID` | from your app dashboard |
| `SOUNDCLOUD_CLIENT_SECRET` | from your app dashboard |
| `SOUNDCLOUD_REFRESH_TOKEN` | from Step 2 output |

## Step 4 — Trigger a test upload

In GitHub Actions, run the **Daily briefing — generate podcast + video**
workflow manually:

1. Go to <https://github.com/davidedwardhaynes-alt/aml-agents/actions/workflows/daily-briefing.yml>
2. Click **Run workflow** → **Run workflow**

Watch the workflow log. The "Upload today's podcast to SoundCloud" step
should print:

```
Uploading 2026-05-XX.mp3 to SoundCloud (sharing=public)...
  title: AML Agents Briefing — Friday, 09 May 2026
  size:  2.34 MB
  ✓ uploaded — track_id=1234567890
  ✓ url:      https://soundcloud.com/your-handle/aml-agents-briefing-...
```

## Step 5 — Confirm on SoundCloud

The new track appears on your SoundCloud profile. The track URL also
gets stored in `data/podcasts/<date>.json` and the in-app Subscribe
panel shows a 🎧 SoundCloud link directly.

## Daily run

Every morning at 22:30 UTC the cron:
1. Generates today's dialogue podcast MP3 (~$0.03)
2. Rebuilds the RSS feed
3. **Uploads to SoundCloud** (free)
4. Commits everything back to `main`

Any podcast app subscribing to the RSS feed (Apple Podcasts, Spotify,
Pocket Casts, Overcast, Wix Podcast Player) ALSO picks up the new
episode.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "no-credentials" in the workflow log | One of the three secrets isn't set or has a typo. Re-paste them at the GitHub secrets page. |
| HTTP 401 from `/oauth2/token` | The refresh token was rotated or revoked. Re-run Step 2. |
| HTTP 403 from `/tracks` | The app is not approved for the `non-expiring` scope. Check your SoundCloud app status, or request the scope. |
| Track uploaded but invisible | Check the **track sharing** field — it defaults to `public`. If you set it to `private`, only you can see it on SoundCloud. |
| Duplicate uploads | The script doesn't dedupe by title. If a re-run uploads twice, delete one manually on SoundCloud — or add `--skip-if-exists` (TODO). |

## Optional: customise

- **Track description**: edit `lib/soundcloud.py` → `DEFAULT_DESCRIPTION`
- **Tags / keywords**: edit `lib/soundcloud.py` → `SHOW_TAG_LIST`
- **Public vs private**: edit `scripts/upload_daily_podcast.py` default
  `sharing` flag, or set per-run via cron input
- **Genre**: edit `lib/soundcloud.py` `_multipart_track_upload()` →
  `track[genre]` (currently `Business`)

The track description per-episode auto-includes the day's lead paragraph
from the dialogue script, so each SoundCloud track has unique content
that makes it discoverable.
