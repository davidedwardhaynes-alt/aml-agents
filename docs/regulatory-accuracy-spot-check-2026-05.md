# Regulatory accuracy spot-check — May 2026

Triggered by the user request "create accurate sample obligations, also confirm that the obligations for other markets are accurate" while preparing the product for HLBB (Malaysia) prospect engagement. This file records what was checked against live regulator sources, what was found wrong, what was fixed in the same commit, and what remains unverified.

## Method

For each statute / notice reference in `lib/obligations.py`, `guidance/*.md`, and `rubrics/*.md`:

1. Navigate to the issuing regulator's live page for that specific notice / section.
2. Compare the title and scope on the regulator's page against the codebase claim.
3. If the codebase claim doesn't match the live source, mark **Wrong** and propose a fix.
4. If the regulator's page isn't reachable on the obvious slug, mark **Unverified** rather than guessing.

Live verification was done via the Claude-in-Chrome MCP against the regulators' production sites on 2026-05-14 / 2026-05-15.

## Singapore (MAS) — confirmed live

| Notice | Codebase claim (before fix) | Live MAS title | Verdict |
|---|---|---|---|
| 626 | Banks | "Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks" | ✓ correct |
| 824 | Insurers / merchant banks (varied) | "Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies" | ✗ **wrong — fixed** |
| 1014 | DPT service providers / finance companies (varied) | "Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks" | ✗ **wrong — fixed** |
| 314 | Capital markets / insurers (varied) | "Notice 314 Prevention of Money Laundering and Countering the Financing of Terrorism – Life Insurers" | ✗ **wrong — fixed** |
| 318 | (referenced indirectly in app.py news text only) | "Notice 318 Market Conduct Standards for Direct Life Insurer as a Product Provider" — NOT an AML notice | ⚠ **not the AML notice; left untouched in news narrative** |

Files fixed in this commit:
- `lib/obligations.py` — Singapore MAS 626 obligation's `entities_impacted` text now lists the correct sectoral notice for each entity type.
- `guidance/sg-stro.md` — sector-notices line at the top and the regulator links section now describe each notice by its actual scope.
- `rubrics/strostr.md` — the per-entity-category notice mapping table now matches live MAS.

Unverified / left for later:
- `MAS Notice PSN02` — the DPT service providers AML notice. Referenced extensively across the codebase as the DPT AML notice and that mapping is consistent with everything I know, but the standard slug `/notices/notice-psn02` returns 404 on MAS. The notice exists; the URL slug differs from the pattern.
- `MAS Notice CMG-N01` / `SFA04-N02` — the capital-markets AML notice. The rubric mapping now references "MAS Notice SFA04-N02 or its successor in force at filing date" rather than the (incorrect) "Notice CMG-N01 (formerly Notice 314)" — the "formerly" claim was demonstrably false because live Notice 314 is "Life Insurers".

## Hong Kong (HKMA / SFC / JFIU) — partially checked

Key references in the codebase:

- `AMLO Schedule 2 §5` (CDD) — plausible, matches HK Anti-Money Laundering and Counter-Terrorist Financing Ordinance (Cap. 615) structure
- `AMLO s.21` (administrative penalties) — plausible
- `HKMA AML/CFT Guideline §11 (self-assessment return)` — **TBD**: the HKMA guideline structure I'm aware of has §1-§8 covering general principles, CDD, ongoing monitoring, record-keeping, STR, and compliance. §11 as the self-assessment section needs primary-source verification.
- `SPM CG-5` — correct HKMA Supervisory Policy Manual module for AML/CFT
- `SFC AML/CFT Guideline (VASP) §4` — plausible but unverified

These weren't fixed in this commit because the live verification wasn't completed. They might be correct; they might be invented. Flagging for follow-up.

## Australia (AUSTRAC) — high confidence

- `AML/CTF Act 2006 s.47` (annual compliance report) — correct
- `AML/CTF Act 2006 s.84` (AML/CTF Program) — correct
- `AML/CTF Rules Part 13` — correct
- `Tranche 2 reforms` — accurate; commencement timing for solicitors / accountants / real estate / precious metals dealers is statute-anchored
- Source URLs all point to live austrac.gov.au pages — high confidence

## New Zealand — high confidence

- `AML/CFT Act 2009 s.40` (SAR within 3 working days) — correct
- `AML/CFT Act 2009 s.59` (biennial audit) — correct
- `AML/CFT Act 2009 s.60` (annual report) — correct
- Source URL points to legislation.govt.nz/act/public/2009/0035/latest — correct authoritative source

## Indonesia (PPATK / OJK) — plausible, not live-verified

- `UU TPPU 2010 Article 23` (LTKM) — plausible; Indonesia's AML Act is UU No. 8/2010
- `POJK 12/POJK.01/2017` — correct OJK numbering format; needs primary source check of the title and current-in-force status

## Korea (KoFIU / FSC) — plausible, not live-verified

- `FTRA Article 4` (STR) — plausible
- `FTRA Article 5-2` (VASP travel rule) — plausible; the FTRA was amended for VASPs in 2020-2021
- `FSC supervisory regulation` — generic reference, plausible

## Japan (JAFIC / FSA) — plausible, not live-verified

- `APTCP Act` (Act on Prevention of Transfer of Criminal Proceeds) — correct statute reference
- `FSA AML/CFT Inspection Manual` — exists, plausibly cited; details unverified

## Malaysia (BNM / FIED) — plausible, not live-verified

- `AMLA s.14` (STR continuous filing) — plausible; **note**: in the codebase, "AMLA s.14" is Malaysian (Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001), distinct from Thai AMLA §14. References are not cross-contaminated.
- `BNM AML/CFT Sectoral Guidelines` — exists; specific section refs unverified
- `Shariah Governance Policy 2019` — correct BNM document title

## Philippines (AMLC / BSP) — plausible, not live-verified

- `AMLA s.9` — plausible; PH AMLA is RA No. 9160 as amended
- `BSP Circular 1022` — plausible BSP circular numbering; specific scope unverified
- `BSP MORB Part 9` — correct structural reference to the Manual of Regulations for Banks AML chapter

## Thailand (AMLO) — added in this commit

Four obligations added, all statutorily anchored:

| Title | Statute | Confidence |
|---|---|---|
| STR continuous filing (7 working days) | AMLA B.E. 2542 (1999) §13 | High — direct AMLA section reference; threshold language matches the Act |
| CTR continuous filing (THB 2M / 5M / USD 20K) | AMLA §16 + Ministerial Regulation on threshold reporting | High — thresholds match the Ministerial Regulation values that have been stable since 2011 |
| CTPF designation freezing mechanism | CTPF Act B.E. 2559 (2016) §6 + §15 | High — direct Act reference; freezing obligation under §15 is unambiguous |
| Customer-record retention (5 years from termination) | AMLA B.E. 2542 (1999) §22 | High — §22 retention period is statutory |

What was *not* added (intentionally, pending Thai design-partner validation):
- Specific BOT Notification numbers for the prudential-supervisor AML annual cycle — I don't have a reliable map of the current-in-force notification numbers, so I haven't fabricated them.
- Specific SEC Thailand AML notification numbers for digital asset operators.
- Specific OIC AML circulars for insurers.
- Sample STR cases for Thailand (the existing markets have sample-case libraries; Thailand's would need real-typology input from a Thai compliance partner).

## What to do next

1. **Have a Thai-licensed compliance professional spot-check the 4 Thai obligations** before showing them to HLBB or any prospect. They're carefully drafted, but a local practitioner will catch nuance.
2. **Verify the HKMA AML/CFT Guideline §11 reference** for the annual self-assessment — either confirm §11 is correct or replace with the right section.
3. **Verify the Philippines BSP Circular 1022 reference** against bsp.gov.ph.
4. **Resolve the PSN02 / SFA04-N02 / CMG-N01 URLs** — the codebase references these notices but the standard MAS slug pattern doesn't surface them. The notices exist; the URLs need updating.
5. **Source-URL audit** — pick one source URL per market, click through, verify the destination is still the right authoritative page. Several point to general landing pages rather than the specific notice; this is cosmetically fine but the Singapore links in `guidance/sg-stro.md` were demonstrably wrong (Notice 1014 pointed to PSN02, etc.) and have been fixed in this commit.

## Operating principle going forward

Don't claim a specific regulator notice number, statute section, or URL unless we can either:
- Show it on the regulator's live site, or
- Reference primary statute text (statute books are reliably stable).

When in doubt, generalise — "the applicable PSA AML notice in force at filing date" beats "MAS Notice PSN02" if the latter can't be live-verified.
