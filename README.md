# AML Agents — STR Reporting

AI-powered Suspicious Transaction Report drafting for AML compliance teams across **Singapore, Hong Kong, Malaysia, and Australia**. Analyst-supplied facts only — never fabricated. Per-sentence audit trail. Native PDF and image document analysis. Direct filing-portal links.

Built by **TrustSphere Partners** for the May 21 Fraud & Financial Crime event in Singapore.

---

## Quick start

```bash
cd ~/dev/amlagents
~/dev/amlagents/start.sh
```

Default credentials: `demo` / `demo123`. Or create your own account on the login screen.

---

## What it does

### Tabs

1. **Draft STR** — the core flow. Pick jurisdiction, load a sample case (or fill your own), generate a narrative, screen sanctions, attach documents, file via the regulator portal.
2. **Connectors** — 161 platforms across 7 collapsible categories with search. Each connector declares which STR sections it auto-populates when wired up.
3. **Obligation register** — track regulatory obligations across all 4 jurisdictions, status workflow, due dates.
4. **Horizon scanning** — 32 curated regulatory updates + live RSS from regulators (MAS, HKMA, SFC, BNM, AUSTRAC, FATF, etc.).
5. **Jurisdictional news** — 36 curated industry items + 29 RSS feeds (Regulation Asia, Wolfsberg, Egmont, FATF, BIS, FSB, IMF, OECD, ASIFMA, banking associations, FinExtra, ACAMS Today, FCA, BoE, SEC, FinCEN, OFAC, etc.) + **LLM-generated articles via daily cron** (see `docs/news-automation.md`; capped at 30/day, ~$0.72/day Sonnet).

All three feed-driven tabs (Horizon, Obligations, News) also include the **302-source regulator & authority directory** — every URL from the user's tracked-sources list, organized into 33 jurisdictions with search.

### Per-jurisdiction depth

| Jurisdiction | Statute | Filing system | Samples |
|---|---|---|---|
| **Singapore (STRO)** | CDSA, TSOFA, MAS Notices 626/824/1014/314 | SONAR via Corppass | 6 cases — fintech TBML, DPT cash-out, real estate DNFBP, lawyer trust, PSMD gold, capital markets wash trading |
| **Hong Kong (JFIU)** | OSCO s.25A, DTROP s.25A, UNATMO s.12, AMLO | STREAMS | 6 cases — jewelry+sanctions, VASP darknet, casino-junket, virtual bank mule, TCSP shell, MSO remittance |
| **Malaysia (FIED)** | AMLA 2001 s.14 + s.79, FSA 2013, IFSA 2013, BNM Sectoral Guidelines | FINS | 6 cases — palm oil TBML, digital bank mule, Islamic Tawarruq, DAE scam-mule, e-money mule, pawnbroker gold |
| **Australia (AUSTRAC SMR)** | AML/CTF Act 2006 s.41 + s.123, AML/CTF Rules, Tranche 2 (2026) | AUSTRAC Online | 6 cases — crypto DCE, casino chip-walking, Tranche 2 solicitor RE, Tranche 2 real estate agent, Tranche 2 accountant, Tranche 2 PMD |

### Key features

- **Multi-modal document analysis** — Claude natively reads uploaded PDFs and images alongside narrative inputs. Bank statements, KYC letters, screenshots, adverse-media articles all extract structured facts into the narrative.
- **Sanctions / PEP screening** — OpenSanctions integration via `/match/default` endpoint. Auto-screen toggle for in-line lookup as customer name is typed.
- **TrustSphere Risk Index** — composite risk band (0-100) integrated into Triggering activity form, drives narrative context.
- **Filing metadata** — institution / STR ref / date / prepared by / MLRO sign-off, env-var pre-fillable per user.
- **Jurisdiction-aware authority chips** — header swaps MAS/STRO/SPF ↔ HKMA/JFIU/SFC ↔ BNM/FIED/SC ↔ AUSTRAC based on selection.
- **Filing guidance panel** — collapsible, per-jurisdiction reference for legal basis, who must file, threshold, timing, tipping-off, retention, penalties.
- **Direct filing-portal buttons** — SONAR / STREAMS / FINS / AUSTRAC Online links inline after generation.
- **PDF / Markdown / Plain-text downloads** of generated narratives.
- **Email forward (mailto)** — pre-filled subject + body for internal MLRO review (regulators don't accept email for STR filing).
- **Consortium (beta)** — hashed STR fingerprints for cross-institution intelligence sharing. SHA256 of canonical subject + canonical institution. 15 typology tags auto-extracted. Score breakdown shown per case.
- **Login + profile** — bcrypt-hashed local credentials, avatar upload, profile defaults pre-fill filing metadata.
- **Live regulator RSS feeds** — auto-refreshed (30-min cache), graceful fallback if feeds break.
- **LLM-generated articles** — `scripts/generate_articles.py` runs on cron, pulls latest RSS items, writes 250-400 word FT/Regulation-Asia-voice analyses, persists to `data/generated_articles.yaml`. Capped at 30/day. The Jurisdictional news tab merges generated articles with curated and live items.

---

## Architecture

```
app.py                     # Streamlit single-file UI (~2,500 lines)
auth/
  credentials.yaml         # bcrypt-hashed user data (gitignored)
  users.py                 # YAML I/O + avatar handling
data/                      # local persistence (all gitignored)
  obligations.yaml
  consortium.yaml
  generated_articles.yaml  # LLM-generated news (cron-driven)
  avatars/<username>.png|jpg
docs/                      # sales kit + future deployment guide
  demo-guide.md            # 30s/5min/15min demo flows + objection handling
  design-partner-pitch.md  # DP ask script + term sheet
  follow-up-templates.md   # within-24h / 1-week / 2-week emails
  event-prep.md            # T-21/T-14/T-7/T-3/T-1/day-of/T+1 checklist
guidance/                  # per-jurisdiction filing guidance (in-app)
  sg-stro.md hk-jfiu.md my-fied.md au-austrac.md
lib/
  connectors.py            # 161 platforms, 7 categories, search, populates
  consortium.py            # hash + tag extraction + score
  horizon.py               # 32 curated items + 38 regulator RSS feeds
  news.py                  # 36 curated items + 29 industry RSS feeds + LLM-generated
  regulators.py            # 302 sources / 33 jurisdictions / RSS where known
  sanctions.py             # OpenSanctions /match wrapper
scripts/
  generate_articles.py     # cron-driven LLM article generation (30/day cap)
  preflight.py             # pre-demo end-to-end check (10 categories, exit 0/1)
rubrics/                   # SME-written narrative rubrics (the moat)
  strostr.md jfiustr.md fiedstr.md austracsmr.md
.env                       # API keys (gitignored)
.streamlit/config.toml     # Streamlit theme + runOnSave + headless
requirements.txt
start.sh                   # one-command launcher
fix-key.sh                 # clipboard-aware API-key reset
```

### Stack

- **Frontend**: Streamlit 1.50 (Python). Custom CSS for branding.
- **LLM**: Anthropic Claude Sonnet 4.6 / Opus 4.7 with prompt caching on rubric.
- **Auth**: streamlit-authenticator (bcrypt YAML; demo-grade for v0).
- **Sanctions**: OpenSanctions `/match/default` (free tier).
- **PDF**: fpdf2 + markdown package (HTML → PDF). Latin-1 char set (ASCII-safe wrapper).
- **Persistence**: local YAML files. Production roadmap: Supabase or self-hosted Postgres.
- **Python**: 3.9 system Python (no Homebrew needed).

### Data flow for STR generation

```
[User input + uploads]
        │
        ▼
   Multi-modal user message  ─┐
   (text + PDF + images)      │
                              ▼
        ┌─────────────── Anthropic Claude API ───────────────┐
        │  System: jurisdiction-specific rubric (cached)     │
        │  Input:  filing metadata + subject + transactions  │
        │          + alert + analyst notes + adverse media   │
        │          + uploaded documents (raw bytes)          │
        │  Output: 8-section STR narrative                    │
        │          [A]/[I] tags per sentence                  │
        └─────────────────────────────────────────────────────┘
                              │
                              ▼
   Render in browser  ─→  PDF / MD / TXT download
                          ↓
   Email forward (mailto) for internal MLRO review
                          ↓
   File via portal button (SONAR / STREAMS / FINS / AUSTRAC Online)
                          ↓
   (Optional) Submit to consortium — anonymized hash + tags
```

### Configuration via .env

```
ANTHROPIC_API_KEY=sk-ant-...                        # required
OPENSANCTIONS_API_KEY=...                            # required for sanctions screening
DEFAULT_REPORTING_INSTITUTION=Demo Bank Pte Ltd      # optional pre-fill
DEFAULT_ANALYST_NAME=Lim Wei Ling, Senior Analyst    # optional pre-fill
DEFAULT_MLRO_NAME=Tan Boon Heng, MLRO                # optional pre-fill
```

---

## v0 design rules (the rubric layer)

These are enforced in every jurisdiction rubric:

1. **Never fabricate facts.** Use only analyst-supplied inputs. Missing fields render as `[detail not provided by analyst]`.
2. **Per-sentence audit trail.** Every sentence tagged `[A]` (analyst-stated) or `[I]` (inferred from analyst-stated facts).
3. **Defensible language.** Use "appears to," "is consistent with," "the analyst observed." Never assert "the customer laundered funds."
4. **No tipping-off content.** Strict observance of CDSA s.48 / OSCO s.25A(5) / AMLA s.79 / AML-CTF Act s.123.
5. **Plain English.** No legalese unless the source statute requires it.
6. **Sectoral context.** Rubric maps entity category → relevant sectoral notice (MAS Notice 626 for SG banks, HKMA Guideline for HK AIs, BNM Sectoral Guidelines for MY, AML/CTF Rules Chapter for AU, etc.).
7. **Jurisdiction-typical typology recognition.** Rubrics know APP-scam, Tawarruq abuse, Macau-junket layering, Pig-Butchering mule patterns, Tranche 2 real-estate value-shifting, etc.

The rubric layer is the moat. LLM wrappers are easy. Domain-validated rubric refinement requires SME background — that's the differentiator.

---

## Roadmap

### Shipped (v0, May 2026 event-ready)

- 4 full jurisdictions (SG / HK / MY / AU) with rubric, guidance, samples (6 each), entity categories
- Multi-modal document analysis (Claude PDF + image native)
- 161 connectors across 7 categories with search
- Live RSS for horizon scanning + jurisdictional news
- Consortium (beta) — hashed fingerprints + placeholder scoring
- Login + profile + avatar
- 4 sales-kit docs (demo guide, DP pitch, follow-up templates, event prep)

### Next (post-event, Q3 2026)

- **Connector implementation**: Sumsub + ComplyAdvantage (already In development), then Hawk AI, Unit21, Sardine, Chainalysis, TRM, Elliptic
- **Voice / dictate input** via OpenAI Whisper
- **Consortium scoring refinement** (waiting on user methodology examples)
- **Hosted deployment** (Railway or Streamlit Community Cloud)
- **Per-firm rubric tuning** for design partners

### Later (Q4 2026 — H1 2027)

- **Production migration** to Next.js + Supabase Auth (real multi-tenant)
- **Document content extraction at scale** (paid OCR for non-LLM-readable formats)
- **Adverse media API integration** (ComplyAdvantage / Refinitiv)
- **Company autocomplete** via OpenCorporates (free tier limited; paid for production)
- **Per-jurisdiction obligations seed** expanded
- **Internationalization** — Chinese / Bahasa narrative output options

---

## Files of note

| File | Purpose |
|---|---|
| `app.py` | The single-page Streamlit application |
| `rubrics/*.md` | Jurisdiction-specific narrative rubrics (the SME moat) |
| `guidance/*.md` | In-app filing guidance per jurisdiction |
| `lib/sanctions.py` | OpenSanctions `/match/default` wrapper |
| `lib/connectors.py` | 161-platform integration roadmap with status, populates, search |
| `lib/horizon.py` | Horizon scanning curated content + regulator RSS |
| `lib/news.py` | Industry news curated content + RSS |
| `lib/consortium.py` | Hashed-fingerprint cross-institution intel sharing |
| `auth/users.py` | Profile + avatar persistence |
| `docs/demo-guide.md` | Live demo script for ICP meetings |
| `docs/design-partner-pitch.md` | DP ask script + term sheet template |
| `docs/follow-up-templates.md` | Email follow-up templates |
| `docs/event-prep.md` | Event prep checklist (T-21 → T+7) |
| `docs/news-automation.md` | Cron / launchd setup for daily LLM article generation |

---

## Honest constraints

- **Demo-grade auth, not production.** Bcrypt-hashed YAML on local disk. Migrate to Supabase Auth or similar before paying customers.
- **Local YAML persistence.** Obligations, consortium, leads — all single-machine. Multi-user requires backend.
- **PDF: Latin-1 only.** fpdf2 core fonts strip non-ASCII. For full Unicode, ship a TTF font in v1.
- **RSS feeds: best-effort URLs.** Some regulator RSS endpoints change without notice. App handles failures gracefully (shows status, continues with curated content).
- **Connector integrations: 3 are Live.** TrustSphere Risk Index, OpenSanctions, Anthropic Claude. The other 158 are roadmap with realistic build statuses (In development / Q3 2026 / Q4 2026 / 2027 / On request).
- **Consortium scoring is placeholder.** User methodology required to refine; framework in place.
- **Document content extraction: PDFs and images natively via Claude.** `.docx` / `.xlsx` not yet text-extracted (skipped with warning).

For production deployment with paying customers, the migration plan is documented in the roadmap section.

---

## Contact

- Founder / sales: TrustSphere Partners (HK)
- Product brand: AML Agents (`amlagents.ai`)
- Demo: clone, `~/dev/amlagents/start.sh`, login `demo` / `demo123`
