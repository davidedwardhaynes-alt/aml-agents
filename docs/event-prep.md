# Event Prep Checklist — Singapore Fraud & Financial Crime, 21 May 2026

23 days out. Use this as your pre-event runbook.

---

## T-21 days (today): Foundation

- [ ] **Brand finalisation** — decide if AML Agents is the public brand or if we're rebranding. **Trademark check on IPOS Class 9 + 42** before any printed material.
- [ ] **Domain confirmed** — amlagents.ai is owned. Set up `demo.amlagents.ai` to point at hosted instance.
- [ ] **Hosting decision** — Streamlit Community Cloud (free, public) vs Railway ($5/mo, more control). Recommend Railway for the event, will let you private-link.
- [ ] **Public hosted URL working end-to-end** — login, generate, sanctions screening all working from a clean browser.
- [ ] **Test the full demo flow with all 4 jurisdictions** — no errors, sanctions screening returns matches, narrative generates in <15 sec, PDF downloads.
- [ ] **Stress-test with bad inputs** — empty fields, garbled documents, wrong API key. Make sure errors are graceful.

## T-14 days: Sales materials final

- [ ] **One-pager PDF** — single page, branded. Title, problem, solution, 3 differentiators, screenshot, contact details.
- [ ] **Term sheet** — `docs/design-partner-pitch.md` formatted as a clean PDF with TrustSphere Partners letterhead.
- [ ] **Demo video backup** — record a 90-second screen capture of the perfect demo flow. Loom is fine. Email-able if wifi at the event is bad.
- [ ] **Lead-tracker spreadsheet** — Google Sheet, columns: contact, role, institution, jurisdiction, TM platform, sanctions vendor, interest level (1-5), specific objection raised, next-step due date, status.
- [ ] **Calendly account** with 30-min "Pilot scoping call" availability — Tue/Thu/Fri afternoons SGT.
- [ ] **LinkedIn profile updated** — title says "Founder, AML Agents (TrustSphere Partners)" so prospects can verify you.

## T-7 days: Dry runs

- [ ] **Three dry-run demos** with people who know AML — your network of MLRO contacts. Tell them "rip it apart, what would make you say no?" Capture every objection.
- [ ] **Refine the demo guide** based on dry-run feedback.
- [ ] **Memorise the 30-second pitch** — say it out loud 20 times until it's natural.
- [ ] **Memorise the close** — three asks (rubric match, connectors used, pilot openness) + calendar offer.
- [ ] **Pre-load demo laptop** — sample case loaded, browser tab pinned, mobile hotspot tested as wifi backup.
- [ ] **Print 50 one-pagers + 20 term sheets** — bring extras.
- [ ] **Business cards** — 100 cards. Include amlagents.ai URL + your direct phone.

## T-3 days: Final polish

- [ ] **Trademark check passed?** If "AML Agents" is contested, pivot to "TrustSphere Partners — AI-Powered STR Drafting" framing for materials.
- [ ] **Email signature updated** — line about the event: "Meet us at the SG Fraud & Financial Crime event, 21 May 2026 — [demo URL]"
- [ ] **Rehearse difficult objections** — "we're building this internally", "DPA cycle is 6 months", "our analysts are already overworked". You should answer in <30 seconds.
- [ ] **Hosted demo health check** — visit demo.amlagents.ai in private browser, run through full flow, confirm no errors.
- [ ] **Backup laptop** if possible. If not, full local copy on USB drive.

## Day before (T-1)

- [ ] **Charge everything** — laptop, phone, mobile hotspot, backup battery
- [ ] **Pack two laptop chargers** (one stays in bag, one out)
- [ ] **Print copy of demo guide** to refer to between meetings (don't read during a meeting, but glance between)
- [ ] **Confirm event attendee list** — pre-identify 5–10 must-meet ICPs. LinkedIn-stalk their backgrounds. Note their current institution + role.
- [ ] **Set 3 specific outcomes for the day**:
  - At least 1 signed term sheet (or verbal yes)
  - At least 5 quality conversations with MLRO/FCC heads
  - At least 10 LinkedIn connection requests sent during/after meetings

## Day of (May 21)

### Morning before the event

- [ ] Coffee, breakfast, water bottle in bag
- [ ] Re-read 30-second pitch one final time
- [ ] Open hosted demo in browser, log in, check sample case loads
- [ ] Phone on silent + Do Not Disturb except for known contacts

### At the event

- [ ] **Don't camp at one spot** — keep moving, work the room
- [ ] **Don't pitch in the queue for coffee** — get coffee, then identify who you're pitching to
- [ ] **Listen first** — let them tell you their pain. Then mention how AML Agents addresses it specifically.
- [ ] **One ask per conversation** — not 5. Either: "Can I get 30 minutes with your MLRO?" or "Would you forward me to your Head of FCC?"
- [ ] **Capture every contact within 5 minutes of meeting them** — voice memo on phone, lead tracker spreadsheet on phone after

### Evening of event

- [ ] **Lead tracker fully updated** before you sleep — every contact, every objection, every next-step
- [ ] **LinkedIn connection requests sent** to everyone met — short personalised message: "Great meeting you at the event today — let's stay in touch"
- [ ] **Top-priority follow-up emails drafted** — at least the 3–5 highest-interest prospects

## T+1 (day after)

- [ ] **All within-24h follow-up emails sent** — every conversation gets one. Use template in `docs/follow-up-templates.md`.
- [ ] **Calendar invites sent** to anyone who said yes to a follow-up call
- [ ] **Term sheet sent** to anyone who explicitly asked for it

## T+3

- [ ] **Personal review** — what worked, what didn't, what to change for the next event
- [ ] **Update demo flow** based on objections you couldn't answer well
- [ ] **First pilot kickoff scheduled** with at least one design partner

## T+7

- [ ] **1-week nudge emails** sent to anyone who hasn't replied
- [ ] **First feedback meeting** with any signed design partner

---

## Success metrics for May 21

Quantitative:
- Conversations: target 15+ MLRO / FCC head conversations
- Demos completed (5min+): target 8+
- Calendly bookings post-event: target 4+
- Signed term sheets within 14 days: target 1+
- Verbal yes-to-pilot within 7 days: target 2+

Qualitative:
- Specific objections captured and answered
- Network expanded by 30+ relevant connections
- Three pieces of product-feedback that change the v1 roadmap

---

## What NOT to do at the event

- ❌ **Don't open a laptop in a crowded conversation** — pull people aside, don't try to demo over coffee chatter
- ❌ **Don't promise pricing** — say "still validating with first three pilots"
- ❌ **Don't claim regulator endorsement** — say "rubrics align with [statute]" not "approved by MAS"
- ❌ **Don't pitch competitors negatively** — "Hummingbird's a great product; we're focused specifically on the SME-validated rubric layer for APAC"
- ❌ **Don't oversell features that aren't shipped** — voice input, autocomplete are roadmap items, not current
- ❌ **Don't skip dinner** — long days, your stamina matters more than one extra coffee meeting
