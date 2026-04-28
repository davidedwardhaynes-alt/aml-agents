# Demo Guide — for ICP meetings (Singapore Fraud & Financial Crime event, 21 May 2026)

This guide is for live demos to MLROs, Heads of FCC, Heads of AML, Heads of Risk at banks, fintechs, crypto exchanges, and DNFBPs across SG / HK / MY / AU.

Three formats — pick by audience and time.

---

## 30-second pitch (elevator)

> "We've built an AI tool that drafts STR narratives for compliance analysts in 30 seconds, using their case data, sanctions screening, and uploaded documents. Trained on STRO, JFIU, FIED, and AUSTRAC requirements. Banks pay 4–8 hours of analyst time per STR; we get that to under 30 minutes including review. We're piloting with Asian fintechs and digital banks now — would your team be a fit?"

**When to use**: passing conversations, conference floor, networking events.

**Key claim**: "4–8 hrs to under 30 min" — anchor on time saved.

**Close**: ask if they'd be a fit. Get them talking.

---

## 5-minute demo (the workhorse)

Use when you have someone's attention sat down with a laptop. This is your primary format for the event.

### Setup before you start
- Have AML Agents already open in browser (logged in)
- Toolbar set to **Singapore (STRO)** by default (closest to most APAC buyers)
- Sample case dropdown set to "Trade-based ML — fintech wholesale"
- One real recent regulatory news item open in another tab as a fallback talking point

### The 5-minute flow

**[0:00–0:30] — Open with the pain**

> "How long does your team spend drafting an STR narrative end-to-end? *[wait for answer — usually 4–8 hours]* And how many STRs do you file in a typical month? *[wait]* OK so that's [Nx] hours of senior analyst time monthly on writing alone."

**[0:30–1:30] — Click "Load sample case"**

> "Let me show you a case my SME network flagged last week — fintech with three rapid international transfers, mainland CN counterparty, sanctions hit on one beneficiary. Watch how this works."

→ Click **Load sample case** in toolbar
→ Form populates with structured case data
→ Point out: "This is what your TM platform might surface as alert metadata — Hawk, Sardine, Unit21, your in-house tools. We connect to all of them."
→ Show the **Connectors** tab briefly: "Here's our integration catalogue — TrustSphere Risk Index featured at top, then Hawk, Unit21, Sumsub, ComplyAdvantage, Chainalysis. We're already wired to OpenSanctions for sanctions/PEP."

**[1:30–2:30] — Sanctions screening**

→ Click **Screen against sanctions / PEP lists** at the customer name field
→ Result shows green if clean, red if hit
→ For the sample case, screen one of the counterparties (e.g., "Mohammed A.") — likely returns OFAC/UN matches
→ Say: "Real-time screening, hashed for privacy, links to source records on OpenSanctions"

**[2:30–3:30] — Upload a document**

→ Drag a sample PDF (a bank statement or KYC letter) into the **Supporting documents** field
> "Now watch this — Claude reads the PDF natively. No OCR pre-processing, no separate vendor."
→ Click **Generate STR narrative**

**[3:30–4:30] — Read the output**

→ Narrative appears in 5–15 seconds, structured in 8 sections
→ Point out **[A]** and **[I]** tags on every sentence: "A is analyst-stated facts, I is inferred from those facts. Audit trail per sentence."
→ Scroll to section 7 — "See how it references SONAR + Corppass authentication for STRO filing. Same product knows JFIU's STREAMS for HK, FINS for Malaysia, AUSTRAC Online for Australia."
→ Show the **File this STR via SONAR →** button: "When the analyst is ready, one click takes them to the regulator portal."

**[4:30–5:00] — The close**

> "Three things we'd love to learn from your team: [1] does the rubric output match your filing standard? [2] which connectors do you actually use today? [3] would you be open to a 60-day free pilot — your data stays on your infrastructure, we provide the rubric refinement and integration support? *[pause]* Can I get 30 minutes with your MLRO next week to scope this?"

**Three asks, one specific next step**. Always close with a calendar offer.

---

## 15-minute deep-dive (when you have real interest)

Use when an MLRO or FCC head has clearly engaged and wants to see depth.

### Cover the additional tabs:

**[0–5min]** — Same as 5-minute flow above, faster.

**[5–7min]** — **Filing guidance** panel (collapsible, above the form)

> "Every jurisdiction tab has the live filing guidance: legal basis, who must file, threshold, timing, tipping-off, retention, penalties. Sourced from CDSA / OSCO / AMLA / AML-CTF Act."

Point at the **Useful resources** section: "Direct links to MAS Notices, HKMA Guidelines, BNM Sectoral Guidelines, AUSTRAC Industry Guidance. Your team uses these every day."

**[7–10min]** — **Obligation register** tab

> "Every regulatory obligation your firm tracks lives here. Annual MAS attestation, BNM CTR review, AUSTRAC Part A program review, HK self-assessment return. Per-jurisdiction filtering, status tracking, due dates."

Add a sample obligation live: "Let me show you. *[clicks Add new]* — your team's actual workflow."

**[10–12min]** — **Horizon scanning** + **Jurisdictional news**

> "Two real-time feeds. Horizon scanning pulls regulator RSS — MAS, HKMA, BNM, AUSTRAC, FATF, plus enforcement actions and typology bulletins. Jurisdictional news pulls Regulation Asia, Wolfsberg, Egmont Group, FATF, banking associations. So your team sees what's hitting other institutions before it hits yours."

Point out the **Refresh** button and live feed status.

**[12–14min]** — **Consortium (beta)**

> "This is the differentiator. When you submit a filed STR to our consortium, we hash the subject identifiers — names never stored — and log structured tags. If three other institutions have already filed STRs for the same subject hash, your analyst sees a consortium score before they decide on a recommendation."

Show the consortium card under a generated narrative — score, breakdown, hash, "Submit" button.

> "Inter-bank intel sharing without the privacy headache. Like FATF Recommendation 22 sharing operationalised."

**[14–15min]** — Close hard

> "What we want from a design partner: [1] one MLRO + 2 hrs/month feedback for 60 days, [2] real anonymised cases (synthetic is fine for v0), [3] honest critique of the rubric. What we offer: [1] free 60-day pilot, [2] direct line to me + product team, [3] 50% off year-1 pricing if you sign on, [4] custom rubric tuning to your filing standard. Can we book that 30 minutes?"

---

## Common objections + responses

### "Sounds like a wrapper around ChatGPT"

> "Three differences. One — we have versioned SME-written rubrics for each FIU's filing standard. The model wouldn't know STRO Online auth requires Corppass without that. Two — we tag every sentence as analyst-stated vs inferred, audit trail per filing. Generic LLMs don't. Three — we read uploaded PDFs and images natively, integrate with your sanctions feed, and connect to your TM platform. It's the rubric + integration that takes a year of compliance background to build, not the LLM."

### "We can't share data with a third party — DPA review takes 6 months"

> "Three things. One — design-partner phase uses synthetic data only, no production data needed, so no DPA on the critical path. Two — production deployment is self-host or your-cloud option (we run in your AWS Singapore region or Azure HK). Three — model API calls go to Anthropic, who is SOC2 Type II + ISO 27001 + HIPAA-eligible; we can co-sign their DPA template if your legal needs it. The 6-month DPA cycle is the production rollout, not the pilot."

### "Our internal team is building this with our own LLM"

> "Great — what's been the timeline so far? *[listen]* Most internal builds get to a demo in 3 months and stall on rubric refinement and connector integration for 9–12 more. Three reasons people end up partnering with us instead of building: [1] we have rubrics validated against FIU standards across 4 jurisdictions out of the box, [2] we maintain integrations with the 40+ TM/KYC/sanctions platforms your team uses, [3] when MAS amends Notice 626 we update the rubric for everyone in 48 hours. You can build the LLM wrapper in a week; the maintenance is what kills internal projects."

### "We file 30 STRs a year. The cost can't justify a tool."

> "Two responses. One — at 30 STRs at 4 hours each = 120 hours of senior analyst time. At your loaded cost per analyst, that's [SGD 30k–60k]. We're a fraction of that. Two — the tool isn't priced per-STR. It's per-seat for the analyst team. Once the SoC builds the workflow, marginal cost of next-100 STRs is near zero. Quality-of-narrative also matters — a poorly-drafted STR gets bounced or escalated; rejection rate is your hidden cost."

### "What about hallucinations / fabricated facts?"

> "Two safeguards. One — the rubric explicitly forbids fabrication. The model uses only analyst-supplied inputs; missing fields render as `[detail not provided by analyst]`. Two — every sentence gets tagged `[A]` if all facts come from analyst, `[I]` if anything is inferred. So your reviewer sees exactly what's grounded in the case file. We're not pretending the model is perfect — we're making the model's claims auditable."

### "How do you handle Chinese / Bahasa / Tamil customer names?"

> "Names are passed verbatim to the model, which handles 100+ languages including Chinese, Bahasa, Tamil. Sanctions screening via OpenSanctions handles Latin transliteration plus native scripts. The narrative output language is whatever the analyst chooses — we default to English for FIU filings (which is FIU-required in SG/HK/MY/AU)."

### "What's your pricing?"

> "Honest answer — we're not pricing the SaaS yet. Pilot phase is free for design partners through 60 days. Production pricing will be per-seat per-month, banded by jurisdiction count, in the SGD 200–600 / seat / month range — comparable to Hummingbird, Unit21 entry tiers. We're also exploring per-STR-filed pricing for occasional users (DNFBPs, smaller fintechs). Happy to share the term sheet when we've validated with the first three pilots — would you want to be one of those three?"

---

## End-of-meeting checklist (always do these)

- [ ] Capture: name, role, institution, jurisdiction(s) they file in, current TM platform, current sanctions vendor
- [ ] Get their **direct email** (not the reception/info@ alias)
- [ ] Confirm: are they an MLRO / SAR-decision-maker, or do they need to escalate?
- [ ] Specific objection or feature gap they raised
- [ ] Their pilot openness: high / medium / low — record gut-feel score
- [ ] Concrete next step: "I'll send you a follow-up + Calendly link tomorrow morning"

---

## Files referenced

- `/docs/design-partner-pitch.md` — the DP ask script
- `/docs/follow-up-templates.md` — within-24h, 1-week, 2-week emails
- `/docs/event-prep.md` — pre-event + day-of + post-event checklist
