# TrustSphere — Hong Leong Bank Berhad pilot scope
## Proposed terms — 30-day evaluation, May/June 2026

---

### Pilot summary

| | |
|---|---|
| **Duration** | 30 days from kick-off |
| **Users** | 2 named (MLRO + 1 deputy or senior financial-crime analyst) |
| **Content tier** | Standard — all 10 APAC jurisdictions, Malaysia-weighted |
| **Cost during pilot** | Zero |
| **Cost if extended** | MYR 12,000 / month, monthly billing |
| **Notice period (post-pilot)** | 30 days written, any time, no penalty |
| **Auto-renewal** | None |

---

### Scope IN

- **Daily email digest** at 07:00 MYT to both named users.
- **Five-minute audio briefing** as MP3 plus RSS feed — listen via the web player or any podcast app.
- **Web dashboard access** — obligation register, STR rubric, curated news feed, sample STR cases.
- **Malaysia-weighted content tier** — BNM circulars, FIED filings, AMLA developments at depth; cross-border coverage of HK, SG, TH, ID, AU at standard depth.
- **Pre-loaded obligation register** — FIED statutory filings and cross-border equivalents marked Critical / High where applicable; entities-impacted and penalties surfaced per item.
- **STR rubric tuned to FIED narrative practice** — the AMLA s.14 narrative drafting assistant, with the [A] / [I] sentence tagging convention reviewed in week 2.

### Scope OUT

- **No integration** with HLBB's internal case management, transaction-monitoring stack, or any other production system. Pilot is read-only consumption.
- **No customer or transaction data ingestion.** TrustSphere does not receive any HLBB customer, account, or transaction data at any point. The pilot is strictly one-way: publicly-available regulator notices and curated news flow into HLBB.
- **No bespoke regulatory advice.** TrustSphere is informational. Not legal advice. HLBB's MLRO retains all filing decisions and regulatory interpretation.
- **No regulatory submissions on HLBB's behalf.** TrustSphere never files to FIED, BNM, or any other regulator.

---

### Success criteria — measured at week-4 review

1. **Engagement.** At least one daily email opened per named user per week, in four of four pilot weeks.
2. **Audit-trail signal.** At least two documented moments where TrustSphere surfaced a regulatory development before HLBB's internal sources flagged it. Tracked in a simple shared log maintained jointly during the pilot.
3. **Practitioner conviction.** At the week-4 review, both named users rate "would extend" at 8/10 or higher on a simple Likert scale.

**If two of the three criteria are met, the pilot is deemed successful.** HLBB has a clean off-ramp to the standard tier, or — equally clean — to a no-fault exit (see Conversion off-ramp below).

---

### Pilot timeline

| Week | Milestone |
|---|---|
| **Week 0** | Kick-off call (30 min) — onboard 2 named users; confirm MY-weighted content tier; agree the audit-trail logging convention. |
| **Week 1** | First check-in (15 min) — content velocity, friction points, any FIED-specific items missing. |
| **Week 2** | Sample STR demo (45 min) — apply the FIED rubric to a HLBB-simulated case using synthetic data only. |
| **Week 3** | Obligation-register walkthrough (30 min) — confirm pre-loaded FIED filings match HLBB's own register; flag any gaps. |
| **Week 4** | Review (45 min) — score the three success criteria; decide on extension or off-ramp. |

---

### Commercial terms

- **Cost during pilot:** Zero.
- **Standard tier post-pilot:** MYR 12,000 / month, billed monthly in advance, no minimum commitment.
- **Notice period:** 30 days written notice to terminate, any time post-pilot, no penalty.
- **Auto-renewal:** None. Extension requires a positive written confirmation from HLBB.
- **Step-down option:** Single-user tier available at lower price-point if 2 named users isn't sustainable.

### Data handling

- **What we store:** Subscription email addresses of the two named users (for email delivery only).
- **What we never receive:** HLBB customer, account, transaction, or internal compliance data of any kind. The pilot is information-into-HLBB only.
- **Source material:** Publicly-available regulator notices and curated industry news. Full source list available on request.
- **Storage location:** Resend (US/EU hosting, encrypted at rest) for delivery; GitHub Actions secrets (encrypted) for the production pipeline. A DPA is available on request.

---

### Conversion off-ramp

If HLBB elects not to extend after the 30-day pilot:

- Within 30 days of pilot end, all HLBB-associated data — named user emails, engagement logs, joint audit-trail entries — is deleted.
- Written confirmation of deletion provided to HLBB.
- HLBB owes nothing.
- Optional: a 60-minute exit interview captures what didn't work. Anonymised input feeds the product roadmap; nothing attributed to HLBB without explicit consent.

---

### Contact

**David Edward Haynes** — david@trustsphere.ai
**TrustSphere Partners** — trustsphere.ai

*Pilot terms proposed 2026-05-15. Subject to mutual written agreement. This document is not a binding offer until countersigned.*
