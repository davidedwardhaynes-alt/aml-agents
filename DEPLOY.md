# Deployment guide

Two paths: **Streamlit Community Cloud** (recommended for the May 21 demo —
free, always-on, ~10 min) and **Render** (recommended once you have a paying
design partner — custom domain, persistent disk, native cron).

---

## Path A: Streamlit Community Cloud (RECOMMENDED FOR DEMO)

### One-time setup

#### 1. Push the repo to GitHub

```bash
# from /Users/davidandgaellegmail.com/dev/amlagents
gh repo create trustsphere-partners/aml-agents --private --source=. --remote=origin --push
# or, if you don't have gh installed:
# 1. Create a new private repo at https://github.com/new
# 2. git remote add origin git@github.com:<you>/aml-agents.git
# 3. git push -u origin main
```

#### 2. Generate a fresh cookie secret

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output — you'll paste it as `cookie.key` in the next step.

#### 3. Generate a bcrypt hash for the demo password

```bash
.venv/bin/python -c "import bcrypt; print(bcrypt.hashpw(b'demo123', bcrypt.gensalt()).decode())"
```

Copy the `$2b$12$...` output.

#### 4. Deploy on Streamlit Cloud

1. Go to <https://share.streamlit.io>, sign in with GitHub
2. Click **New app**, pick the repo, set:
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: e.g. `aml-agents-trustsphere` (becomes
     `https://aml-agents-trustsphere.streamlit.app`)
3. Click **Advanced settings → Secrets** and paste:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."

   auth_yaml = """
   credentials:
     usernames:
       demo:
         email: demo@trustsphere.partners
         name: Demo User
         password: $2b$12$YOUR_BCRYPT_HASH_HERE
         reporting_institution: TrustSphere Bank (demo)
         analyst_name: Demo Analyst
         mlro_name: Demo MLRO
         entity_category: Bank
   cookie:
     name: aml_agents_auth
     key: YOUR_COOKIE_SECRET_HERE
     expiry_days: 30
   pre-authorized:
     emails: []
   """
   ```

4. Click **Deploy**. First boot takes ~3 min while it pip-installs.

The login screen will accept `demo` / `demo123`. Add more users by editing the
secrets block (add to `usernames:`), or let prospects self-register via the
"Create a new account" expander on the login screen.

### Daily news refresh (cron)

Streamlit Cloud has no native cron. Use a GitHub Actions workflow that runs
`generate_articles.py` and commits the output back — Streamlit Cloud auto-redeploys
on every push.

Add `.github/workflows/refresh-news.yml`:

```yaml
name: Refresh jurisdictional news
on:
  schedule:
    - cron: "0 1,9,17 * * *"   # 3x/day at 01:00, 09:00, 17:00 UTC
  workflow_dispatch:           # also runnable manually from the Actions tab

jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: python scripts/generate_articles.py --max 10
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Commit refreshed articles
        run: |
          git config user.name "news-bot"
          git config user.email "bot@trustsphere.partners"
          git add data/generated_articles.yaml
          git diff --cached --quiet || git commit -m "Auto-refresh jurisdictional news ($(date -u +%Y-%m-%d))"
          git push
```

Add `ANTHROPIC_API_KEY` to your GitHub repo secrets (Settings → Secrets and
variables → Actions). Run cost: ~$0.20/refresh × 3/day = ~$0.60/day, ~$18/month.

### What works / what doesn't on Streamlit Cloud

| Feature | Works? | Notes |
|---|---|---|
| Login + signup | ✅ | Credentials come from st.secrets |
| Generate STR narrative | ✅ | Streams from Claude API |
| OpenSanctions screening | ✅ | Public API, no key needed |
| Profile defaults | ✅ | Persist across reruns of same container |
| Avatar upload | ⚠️ | Persists in container, lost on redeploy |
| Obligations register edits | ⚠️ | Same — persist until next redeploy |
| News + horizon RSS | ✅ | Live RSS sweep on demand |
| News auto-refresh | ✅ | Via GitHub Actions cron above |
| Press release scrape | ⚠️ | Works but slow (LLM extraction) — best refreshed via cron, not on-demand |

For demo purposes the ⚠️ rows are fine. When you have a paying customer,
migrate to Render (next section) for proper persistence.

---

## Path B: Render (PRODUCTION-GRADE DEMO)

Choose this when you need a custom domain (e.g.
`app.trustsphere.partners`), persistent disk for avatars/obligations, or
native scheduled jobs.

### One-time setup

1. Push to GitHub (same as Path A step 1)

2. At <https://render.com> → **New Web Service** → connect the repo
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command:
     `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=true`
   - Plan: Free (sleeps after 15min idle, ~30s cold start)
     or Starter $7/mo (always-on)

3. **Environment** tab → add:
   - `ANTHROPIC_API_KEY` = your key
   - `PYTHONUNBUFFERED` = `1`

4. **Disks** tab → add a 1 GB persistent disk mounted at `/opt/render/project/src/data`.
   Avatars, obligations, consortium log, generated articles all persist across
   restarts and redeploys.

5. **Settings** → custom domain → point your DNS A/CNAME at the Render-supplied target.

### Cron on Render

**Cron Job** service type → run `python scripts/generate_articles.py --max 10`
on the same schedule. Render's cron runs in a fresh container each time, so it
needs the same persistent disk mounted at `/opt/render/project/src/data` to
write the refreshed articles.

### Credentials on Render

`auth/credentials.yaml` is gitignored, so the deployed container ships without
it. Two options:
- **Render Secret File** (recommended) — paste the YAML at Settings → Secret
  Files, mount path `/opt/render/project/src/auth/credentials.yaml`. Survives
  redeploys.
- **Streamlit secrets equivalent** — set env var `STREAMLIT_AUTH_YAML` to the
  full YAML string and add a one-line patch in `auth/users.py` to read it. Less
  clean than the Secret File option.

---

## Path C: Fly.io (production single-platform target)

Best long-term home: scale-to-zero machines, persistent volumes, scheduled
machines for cron, ~$2-3/month for low-traffic demo.

```bash
fly launch              # generates fly.toml, picks Python builder
fly volumes create data --size 1
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

Then in `fly.toml`:
```toml
[mounts]
source = "data"
destination = "/app/data"
```
And for cron: deploy a second machine with `[processes] cron = "python scripts/generate_articles.py --max 10"` and a schedule.

---

## Pre-deploy checklist

Before pushing for the first time, run:

```bash
.venv/bin/python scripts/preflight.py
```

This validates: imports, env keys, rubrics, news pipeline, RSS sample, Anthropic
API, OpenSanctions API, PDF generation. All 10 categories must pass.

## Post-deploy smoke test

1. Sign in with the demo account
2. Pick Singapore (STRO) → Bank → load the seeded sample → "Draft narrative"
3. Confirm the narrative streams in within ~25s
4. Open Connectors tab → run a sanctions screening
5. Open News tab → confirm articles render with Read more expanders
6. Logout → confirm cookie clears

If any step fails, check Streamlit Cloud's **Manage app → Logs** for the trace.
