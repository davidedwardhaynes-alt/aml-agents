# Demo morning checklist — 2026-04-30

## Live URL
**https://amlagents.streamlit.app**

## Login
- Username: `demo`
- Password: `demo123`

## 5 minutes before the demo (sanity test)

1. **Open the URL on your demo machine.** If it shows "Your app is in the oven", wait 30s — Streamlit Cloud spins down idle apps; first-request wakeup is ~15s.

2. **Sign in.** If login fails: secrets got corrupted. Recovery: in Streamlit Cloud → ⋮ → Settings → Secrets → click Save (without changing anything) → Reboot. Falls back to last-known-good secrets within ~90s.

3. **Click Configuration → Sample case → keep "Trade-based ML — fintech wholesale" → Load.** Form should populate with ACME Trading Pte Ltd, transaction lines for HK-XYZ Ltd / Mohammed A. / Beach Holdings, and **5 Risk Signals from connectors** (ComplyAdvantage UN sanctions, TrustSphere Risk Index 87/100, Hawk AI structuring, Sayari shell-company, ThreatMetrix VPN).

4. **Scroll down to "Generate STR narrative" → click.** Narrative should stream in within ~25s. Look for `[A]` and `[I]` audit-trail tags. Spot-check that the narrative cites at least 2 connector names by name (e.g., "ComplyAdvantage matched Mohammed A. against UN..." or "Hawk AI's TBM-014 rule fired...").

5. **Click the Connectors tab.** OpenSanctions row should show "Live"; the page should not error out.

If any of those 5 steps fails, see the **Recovery** section below.

---

## Demo flow (suggested — ~10 min)

### Act 1: The ICP problem (1 min)
"MLROs at MAS-licensed banks spend 90 minutes hand-drafting each STR. Half their day is paperwork instead of investigation. I built this to compress that to under 5 minutes — let me show you."

### Act 2: The drafting workflow (4 min)
1. Login screen → frosted-glass Apple aesthetic, demo creds visible
2. Hero card: V0 · SINGAPORE blue badge, MAS / STRO / SPF authority chips on the right — shows we know the regulator hierarchy
3. Configuration card: jurisdiction switching reskins the entire app for HK / MY / AU
4. Click Load — the case pre-fills, plus the **Risk signals from connectors** card list appears (ComplyAdvantage / Hawk AI / Sayari / ThreatMetrix / TrustSphere Risk Index). **This is the new feature — say:** "These are the structured findings from upstream connectors. The narrative will cite them by name. Today this is seed data; in production it pipes from BioCatch, Chainalysis, ComplyAdvantage's actual APIs."
5. Click Generate STR narrative — narrative streams. Highlight the `[A]` / `[I]` tags ("every fact tagged: A = analyst-supplied, I = inferred from analyst input. Never fabricated. Audit-defensible.")
6. Scroll to the bottom — Download PDF button. Show that the artefact is ready for STRO/JFIU submission.

### Act 3: The 161 connectors story (2 min)
1. Click Connectors tab. Browse the categories briefly.
2. Pick OpenSanctions → click — show the live screening from a public sanctions database (proves we ship working integrations, not Figma).
3. Highlight the TrustSphere Risk Index entry at the top — that's the composite score that goes back into the STR.

### Act 4: The defensibility story (2 min)
1. Click Obligation register tab — show the regulator obligations populated.
2. Click Horizon scanning tab — live RSS feeds across 70 sources.
3. Click Jurisdictional news tab — 67 articles with Read more. **Say:** "Cron refreshes this 3 times a day from APAC regulator press releases. Compliance teams stay current without a manual scan."

### Act 5: The ask (1 min)
"I'm looking for one design-partner bank in Singapore who'll co-build for 6 months at a discounted rate. In exchange, you get an STR drafter that lives inside your fence with your taxonomies. Who in your team should I introduce myself to?"

---

## Common questions you'll get

**Q: Where does customer data go?**
A: Today — Anthropic Claude API (US-hosted, SOC 2 Type II, BAA-eligible). Production target: customer-hosted Bedrock or Anthropic regional endpoint. No training on customer data.

**Q: Who owns the IP of the drafted narrative?**
A: The bank does. I'm a service provider, not a co-creator.

**Q: What about audit / model risk?**
A: The `[A]` / `[I]` tagging is the audit story. Every sentence cites whether the fact was analyst-supplied or model-inferred. Nothing is fabricated — the rubric forbids it. We can hand a regulator a per-sentence trace.

**Q: Why Streamlit and not Next.js?**
A: This is v0 demo-grade. Production migration to Next.js + Supabase Auth + customer-hosted infra happens with the first signed design partner.

**Q: What about HK / MY / AU?**
A: Switch the jurisdiction dropdown. Different rubric, different authority chips, different sample cases. v0 ships SG / HK / MY / AU.

---

## Recovery (if something breaks during the demo)

| Symptom | Action |
|---|---|
| App is "in the oven" | Wait 60s. Refresh. Streamlit Cloud is doing a cold-start. |
| Login fails | Streamlit Cloud → ⋮ → Reboot app. Wait 90s. Try again. |
| "Generate" button does nothing | Check that ANTHROPIC_API_KEY is in Streamlit Cloud Secrets. If yes → Reboot. |
| OpenSanctions shows "Not connected" | OPENSANCTIONS_API_KEY not in Secrets. Fix as above. |
| Connector signals card list missing | Click Clear, then Load again. The signals load with the sample case. |
| Tab content is blank | Streamlit hot-reload glitch. Refresh the page. |

If anything else: **calmly say "give me one second to refresh"**, then refresh the browser. 90% of issues clear with a hard refresh.

---

## After the demo

If it went well, the close is:
- "Can I send you the URL and a 2-page brief tonight?"
- "Who in your team should evaluate this?"
- "Are you the budget owner, or who is?"

If they want to try it themselves: `https://amlagents.streamlit.app` → demo / demo123. They can browse without breaking anything.

---

## What's live (for your reference)

- 67 articles in the News tab (32 curated + 35 LLM-generated, all with Read more long-form analysis)
- 161 connectors across 7 categories in the Connectors tab
- 6 sample cases with connector-signal seed data (SG STRO, HK JFIU baseline + VASP darknet + casino-junket layering, MY FIED, AU AUSTRAC) — picking another sample will simply hide the connector-signals section, no error
- Cron auto-refreshes news 3×/day via GitHub Actions (next run: see GitHub Actions tab)
- 25 individually crafted connector signals citing real regulatory frameworks (MAS Notice 626, AMLO §25A, SFC VASP Code §11, AUSTRAC AML/CTF Act §41, etc.)

---

## What's NOT yet live (defer to v0.1)

- The "more classy and modern UI" pass — currently Apple-style v1, will iterate after demo feedback
- Connector signals for cases beyond the six listed above (loading those cases just hides the section — no error)
- Production hosting (Render / Fly.io with custom domain, persistent disk for avatars/obligations)
- Adverse-media API (currently manual paste)
- Voice / Whisper input
- Consortium-intelligence scoring methodology

If anyone asks about these, the line is: "On the v0.1 roadmap once we have a signed design partner."

---

Good luck. Stay calm. The hard work is done — you just have to walk people through it.
