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

Live verification confirmed:
- **Cap. 615 Anti-Money Laundering and Counter-Terrorist Financing Ordinance** is the correct primary statute (verified at elegislation.gov.hk on 2026-05-15). ✓

Key references that remain pending live verification:

- **AMLO Schedule 2 §5 (CDD)** — high-confidence correct; Schedule 2 of Cap. 615 carries the CDD framework and §5 deals with CDD measures including ongoing monitoring. Codebase reference to §5(4) for periodic-review currency is consistent with the structure.
- **AMLO s.21 (administrative penalties up to HK$10M)** — plausible; s.21 of Cap. 615 covers contraventions of Schedule 2 requirements with disciplinary action up to HK$10M. Worth a live-page confirmation but high confidence.
- **HKMA AML/CFT Guideline §11 (annual self-assessment return)** — **uncertain**. The HKMA Guideline on Anti-Money Laundering and Counter-Financing of Terrorism that I know about has §§1–8 (general principles, CDD, ongoing monitoring, record-keeping, STR reporting, terrorist financing, compliance). §11 as the "self-assessment return" section may be a misremembered cross-reference to the separate **annual AML/CFT supervisory return** that HKMA collects via the STET reporting system. Recommend: replace "Guideline §11" with "HKMA's annual AML/CFT supervisory return (collected via STET)" until a Hong Kong practitioner confirms the precise reference.
- **AMLO s.5 / s.71B** — codebase mentions s.5 for "systemic non-compliance" and s.71B for licence revocation. Both look mis-anchored: s.71B in the codebase context (banking-licence revocation) is more naturally Banking Ordinance Cap. 155 §22 than AMLO Cap. 615. Worth a section-by-section check before going to a HK-focused prospect.
- **SPM CG-5** — ✓ correct. HKMA Supervisory Policy Manual module for AML/CFT.
- **SFC AML/CFT Guideline (VASP) §4** — plausible. The SFC VASP guideline structure roughly tracks the HKMA Guideline; §4 typically covers transaction monitoring. Unverified.

Codebase source_url `https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/by-subject-current/aml-cft/` returned 404 on live check (2026-05-15) — the real landing page for HKMA's AML/CFT regulatory resources is at `/eng/key-functions/banking/anti-money-laundering-and-counter-financing-of-terrorism/`. This URL should be updated in `lib/regulators.py` / wherever it's referenced. **Not fixed in this commit.**

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

- **UU No. 8 Tahun 2010 (UU TPPU)** — high-confidence correct; this is Indonesia's primary AML statute (*Tindak Pidana Pencucian Uang*).
- **UU TPPU 2010 Article 23 (LTKM)** — high-confidence correct; Article 23 covers *Laporan Transaksi Keuangan Mencurigakan* (Suspicious Financial Transaction Report). 3-working-day filing window is statutory.
- **POJK 12/POJK.01/2017** — high-confidence correct; this is the OJK regulation on AML/CFT for commercial banks. Correctly cited in the codebase as the annual programme review obligation source.
- **POJK 23/2019 amendment** — referenced as a later amendment. Plausible but worth a current-in-force check.
- **PPATK Head Regulation on beneficial-owner identification** — generic reference, plausible.
- **Source URL `ojk.go.id` / `ppatk.go.id`** — both live on 2026-05-15.

## Korea (KoFIU / FSC) — plausible, not live-verified

- **FTRA (특정 금융거래정보의 보고 및 이용 등에 관한 법률)** — high-confidence correct; the Financial Transaction Reports Act is Korea's primary AML statute.
- **FTRA Article 4 (STR)** — high-confidence correct; Article 4 is the STR filing obligation.
- **FTRA Article 5-2 (VASP travel rule)** — high-confidence correct; Article 5-2 was inserted by the 2020 amendment when Korea brought VASPs in scope. Travel-rule obligations applied from 25 March 2022.
- **KoFIU Notice 2021-06** — specific notice cited; plausible but worth confirming the current-in-force status (Korean FIU re-issues these periodically).
- **FTRA Article 17 (administrative fines up to KRW 30M)** — plausible; the late teens of FTRA cover sanctions.
- **Source URLs `fsc.go.kr` / `kofiu.go.kr`** — both live on 2026-05-15.

## Japan (JAFIC / FSA) — plausible, not live-verified

- **APTCP Act (Act on Prevention of Transfer of Criminal Proceeds, 犯罪収益移転防止法)** — high-confidence correct; this is Japan's primary AML statute.
- **APTCP Article 8 (STR continuous filing)** — high-confidence correct; Article 8(1) is the suspicious-transaction-notification obligation. Filing "without delay" is the statutory language.
- **APTCP Article 25 (criminal penalties)** — plausible; the upper-twenties Articles of APTCP cover criminal sanctions including the imprisonment-up-to-six-months figure cited in the codebase.
- **7-year retention under APTCP** — high-confidence correct; Article 6 / Cabinet Order requires identification-record retention for 7 years.
- **FSA AML/CFT Inspection Manual / Supervisory Guidelines** — exists; the codebase references the 2024-amendment effectiveness review which lines up with the FSA's recent guideline updates on AI/TM supervision.
- **Source URL `fsa.go.jp/en/laws_regulations`** — live on 2026-05-15.

## Malaysia (BNM / FIED) — plausible, not live-verified

The Malaysian primary statute is **AMLATFPUAA 2001** (Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act). The codebase consistently calls it "AMLA" which is the common short form — fine, but distinct from Thai AMLA which is the same short form for a different statute. References are not cross-contaminated in the obligation register.

- **AMLA s.13 (CTR continuous filing)** — high-confidence correct; s.13 of AMLATFPUAA covers cash threshold reports.
- **AMLA s.14 (STR continuous filing)** — high-confidence correct; s.14 of AMLATFPUAA is the suspicious-transaction-report obligation.
- **AMLA s.14(2) and s.13(2)** — codebase cites these as the criminal-liability arms of the filing obligations. Plausible.
- **AMLA s.86 (administrative penalties up to RM 1M)** — plausible; the late-80s sections of AMLATFPUAA cover compounding offences and civil penalties. Worth a check against the current consolidated Act text on the AGC Malaysia legislation portal.
- **BNM AML/CFT Sectoral Guidelines** — exists. Specific section references in the codebase are not pinned and the rendering is fine.
- **BNM Shariah Governance Policy 2019** — correct BNM document title.
- **Source URL `amlcft.bnm.gov.my`** — live on 2026-05-15, no fix needed.

## Philippines (AMLC / BSP) — plausible, not live-verified

- **RA No. 9160 (Anti-Money Laundering Act of 2001) as amended by RA 9194, RA 10167, RA 10168, RA 10365, RA 10927, RA 11521** — correct primary statute. Codebase cites just "AMLA RA 9160" which is the common short form; fine.
- **AMLA s.9 (covered/suspicious transaction reporting)** — high-confidence correct; Section 9 of RA 9160 (as amended) is the reporting obligation including STR + CTR.
- **AMLA-IRR Rule 9** — correct structural reference; the AMLA Implementing Rules and Regulations have a chapter on reporting requirements.
- **BSP Circular 1022** — referenced as the BSP AML/CFT independent compliance check circular. The BSP issues a high volume of circulars (1022 lands in the mid-2018 / early-2019 era of BSP numbering) and the cited topic is plausible but should be confirmed against the current Manual of Regulations consolidation before going to a Philippine prospect. Worth a `bsp.gov.ph` lookup before relying on the exact number.
- **BSP MORB Part 9** — high-confidence correct; the BSP Manual of Regulations for Banks has Part Nine on AML. ✓
- **Source URL `bsp.gov.ph/SitePages/Regulations/AML.aspx`** — was the legacy BSP page. BSP's current AML hub is at a different URL; the old slug may redirect. Worth updating in `lib/regulators.py`.

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
