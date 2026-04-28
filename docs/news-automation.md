# News auto-generation — cron / launchd setup

The `scripts/generate_articles.py` script pulls latest items from configured RSS feeds and uses Claude to write 250-400-word FT/Regulation-Asia-voice articles. Designed for unattended operation throughout the day.

## How it works

1. Loads existing generated articles from `data/generated_articles.yaml`
2. Pulls from **127 RSS feeds** (70 horizon + 57 news, including 21 APAC regulators: India RBI/SEBI, Thailand BOT/SEC, Philippines BSP/AMLC, Indonesia BI/OJK, Japan FSA/BOJ, Korea FSC/BoK, Taiwan FSC, China CSRC/PBoC, Pakistan FMU, NZ RBNZ/FMA), filters items < 14 days old, drops already-processed URLs. Best-effort URLs — many APAC regulator endpoints don't expose RSS, but the script handles failures gracefully.
3. Picks N items per run (default 1; configurable via `--max`)
4. For each, prompts Claude with the source title + summary + URL
5. Auto-classifies jurisdiction (from RSS feed origin or keyword match) and topic (from keyword scoring)
6. Saves to YAML, appended to feed
7. **Caps at 30 articles/day** to bound API spend

The Streamlit app reads `data/generated_articles.yaml` and merges generated articles with curated NEWS_ITEMS and live RSS pulls.

## Cost (Claude Sonnet 4.6)

- ~5,000 input tokens × $3/M = $0.015 per article in
- ~600 output tokens × $15/M = $0.009 per article out
- **~$0.024/article × 30 = ~$0.72/day, ~$22/month**

## Recommended cron schedule (every 30 min, max 1 per run)

This produces up to 48 runs/day; the 30/day cap stops generation once reached.

```bash
crontab -e
```

Add:
```
*/30 * * * * cd ~/dev/amlagents && .venv/bin/python scripts/generate_articles.py >> /tmp/amlagents-news.log 2>&1
```

Verify cron is running:
```bash
crontab -l
tail -f /tmp/amlagents-news.log
```

## Alternative: macOS launchd

Better for laptops that sleep — launchd will run on next wake. Create `~/Library/LaunchAgents/ai.amlagents.news.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.amlagents.news</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/davidandgaellegmail.com/dev/amlagents/.venv/bin/python</string>
        <string>/Users/davidandgaellegmail.com/dev/amlagents/scripts/generate_articles.py</string>
    </array>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>StandardOutPath</key>
    <string>/tmp/amlagents-news.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/amlagents-news.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/davidandgaellegmail.com/dev/amlagents</string>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/ai.amlagents.news.plist
```

Unload (to stop):
```bash
launchctl unload ~/Library/LaunchAgents/ai.amlagents.news.plist
```

## Manual run for testing

```bash
cd ~/dev/amlagents
source .venv/bin/activate

# Dry-run (shows what would be generated, doesn't call Claude)
python scripts/generate_articles.py --dry-run --max 5

# Real run, 1 article
python scripts/generate_articles.py

# Real run, up to 5 articles
python scripts/generate_articles.py --max 5
```

## Tuning

- **Daily cap**: edit `MAX_PER_DAY` in `scripts/generate_articles.py` (default 30)
- **Article age cutoff**: `MAX_AGE_DAYS` (default 14 — older RSS items are skipped)
- **Model**: `MODEL` (default `claude-sonnet-4-6`; switch to `claude-opus-4-7` for higher quality at ~5x cost)
- **Output length**: `MAX_TOKENS` (default 1200 → ~400 words article + headroom)

## Resetting

If you want to clear all generated articles and start fresh:

```bash
rm data/generated_articles.yaml
```

Next cron run will start populating again.

## What you'll see in the app

After the first cron run, the Jurisdictional news tab will show generated articles mixed in with curated and live items, sorted by date. Each generated article has the same UI structure as curated ones (intro + Read more for the full article + source link). Generated articles can be filtered by jurisdiction and topic the same way.
