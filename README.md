# AML Agents

AI-drafted STR narratives for compliance teams. Analyst-supplied facts only — never fabricated. v0 ships Singapore (STRO); JFIU / FIED / AUSTRAC follow as rubric files.

## Run locally

```bash
cd ~/dev/amlagents
source .venv/bin/activate
streamlit run app.py
```

Browser opens at http://localhost:8501.

## Setup (first time only)

```bash
# 1. Copy the env template and add your Anthropic API key
cp .env.example .env
# then edit .env — paste your key from https://console.anthropic.com

# 2. (If venv was deleted, recreate)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Files

- `app.py` — Streamlit UI and Anthropic API call
- `rubrics/strostr.md` — STRO STR drafting rubric (system prompt). **This is where the SME work lives.** Edit to refine narratives.
- `.env` — your API key (never commit; `.gitignore` excludes it)
- `requirements.txt` — Python dependencies

## v0 design rules

1. Never fabricate facts — model uses only analyst-supplied inputs
2. Every sentence tagged `[A]` (analyst-stated) or `[I]` (inferred) for audit trail
3. Defensible language only — "appears to," "is consistent with"
4. No tipping-off content (CDSA s.48 compliance)

## Roadmap

- v0 (now): Singapore STRO STR
- v0.1: Hong Kong JFIU STR rubric
- v0.2: Malaysia FIED STR + Australia AUSTRAC SMR rubrics
- v0.3: .docx export, document upload for KYC parsing
- v1: Auth + persistence (Supabase, ap-southeast-1)
- v2: Migration to Next.js for production scale
