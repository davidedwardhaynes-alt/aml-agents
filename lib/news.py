"""Jurisdictional news — broader compliance / fintech / regulatory news per country.

Distinct from horizon scanning:
  - Horizon scanning = regulator notices, enforcement actions, typology bulletins
    (the "looking ahead at compliance signals" view)
  - News = market events, firm news, M&A, talent moves, scam-trend coverage
    (the "what's happening in the industry now" view)

Sources:
  - Curated (static) — hand-written items in NEWS_ITEMS
  - Live (RSS) — industry publications (FinExtra, ACAMS, RegTech Analyst, etc.)
    Note: many industry RSS endpoints aren't jurisdiction-specific, so live items
    are tagged "All jurisdictions" and surface in every filter.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False


TOPICS = [
    "AML enforcement",
    "Fintech / Digital banking",
    "Crypto / VASP",
    "Sanctions / Geopolitics",
    "Industry M&A",
    "Talent / Hiring",
    "Conferences / Events",
    "Regulatory tech",
    "Scams / Fraud trends",
]


@dataclass(frozen=True)
class NewsItem:
    date: str
    jurisdiction: str  # or "All jurisdictions"
    title: str
    summary: str  # 1-2 sentence intro shown in the feed
    source: str
    url: str
    topic: str
    full_article: str = ""  # long-form analysis shown when "Read more" is opened


# Curated news items as of late April 2026.
NEWS_ITEMS: list[NewsItem] = [
    # ---- Singapore ----
    NewsItem(
        date="2026-04-26",
        jurisdiction="Singapore (STRO)",
        title="DBS Bank announces 'AI-first' compliance transformation programme",
        summary=(
            "DBS Bank announced a SGD 180M three-year transformation of its compliance and "
            "financial-crime functions, deploying LLMs across alert triage, STR drafting, and "
            "adverse-media screening. ABS guidance on AI in compliance referenced as a baseline. "
            "Headcount said to be redirected rather than reduced."
        ),
        source="The Business Times Singapore",
        url="https://www.businesstimes.com.sg/banking-finance",
        topic="Regulatory tech",
        full_article="DBS Bank's S$180 million commitment to embedding large language models across its compliance and financial-crime functions reflects an industry-wide repositioning of compliance from cost centre to data-led decisioning function. The three-year programme will deploy LLM tooling across alert triage, suspicious-transaction-report drafting, and adverse-media review — areas that have historically absorbed the bulk of senior analyst time at Tier-1 Asian banks.\n\nThe Association of Banks in Singapore's April industry guidance on AI in compliance provides a baseline for the rollout. The guidance emphasises explainability, human-in-the-loop controls, and alignment with the Monetary Authority of Singapore's FEAT principles (Fairness, Ethics, Accountability, Transparency). DBS's positioning of AI as augmenting rather than replacing analyst headcount suggests an industry consensus that compliance work remains fundamentally judgment-driven, with AI applied to the structured-output components.\n\nThe economic case is straightforward. A typical Tier-1 SG bank files several hundred STRs per quarter; at 4-8 hours of senior analyst time per filing, the addressable productivity gain runs into the millions of dollars annually. The harder question is regulator acceptance: STR narratives drafted with LLM assistance must remain defensible, with auditable chains of fact provenance from analyst inputs to final language. Early evidence from MAS supervisory engagement suggests pragmatic acceptance, provided controls and audit trails are in place.\n\nOther major SG banks (OCBC, UOB, StanChart Asia) are expected to follow within 12 months. The competitive question shifts from whether to deploy LLM tooling to which institution achieves regulator-validated rubric refinement first.",
    ),
    NewsItem(
        date="2026-04-18",
        jurisdiction="Singapore (STRO)",
        title="Wise Singapore appoints former MAS Director as MLRO",
        summary=(
            "Cross-border payments fintech Wise Singapore appointed a former Monetary Authority "
            "of Singapore senior director as its new MLRO, signalling continued investment in "
            "compliance leadership. Industry seeing similar regulator-to-fintech moves."
        ),
        source="Singapore FinTech News",
        url="https://www.fintechnews.sg",
        topic="Talent / Hiring",
        full_article="The hiring move reflects a broader trend of senior regulators transitioning into compliance leadership at fintech firms — a pattern that has accelerated as MAS-licensed payment institutions face heightened scrutiny following the 2023 S$3 billion money-laundering case and subsequent enforcement actions against several SG-licensed payment platforms.\n\nFor Wise Singapore, the appointment signals an investment posture aligned with its rapid APAC expansion. The firm reported S$2.4 billion of payment volume processed through its SG entity in Q4 2025, up 31% year-on-year, with an analyst headcount that has grown more slowly. Hiring at the MLRO level addresses both the operational scale and the supervisory expectations that come with that scale.\n\nThe regulator-to-fintech career arc is now a recognised path for senior MAS staff at the Director level and above. Reasons cited in industry interviews include broader business exposure, equity upside in growth-stage firms, and frustration with the pace of regulatory change. The trade-off for fintechs is access to deep institutional knowledge but typically with a constrained tenure horizon — most appointees stay 2-4 years before moving on.\n\nIndustry observers note the trend may accelerate as Singapore's FATF mutual evaluation in Q4 2026 puts compliance leadership across the regulated sector under greater scrutiny.",
    ),
    NewsItem(
        date="2026-04-08",
        jurisdiction="Singapore (STRO)",
        title="Singapore retail crypto market saw SGD 4.2B transaction volume Q1 2026",
        summary=(
            "MAS-licensed DPT service providers reported aggregate Q1 2026 retail crypto volumes "
            "of SGD 4.2B, up 28% YoY. Investment-scam-related complaints rose proportionally; "
            "MAS expected to issue updated DPT guidance in H2 2026."
        ),
        source="Straits Times Business",
        url="https://www.straitstimes.com/business",
        topic="Crypto / VASP",
        full_article='Singapore\'s retail crypto trading volumes through MAS-licensed Digital Payment Token service providers reached S$4.2 billion in Q1 2026, marking a 28% year-on-year increase. The growth has been concentrated at a small number of licensees — Coinhako, Crypto.com SG, Independent Reserve and Coinbase Asia together account for over 80% of reported volume.\n\nThe compliance implications are significant. Investment-scam-related complaints to the Singapore Police Force\'s Anti-Scam Centre rose at a comparable rate, with the centre reporting a 32% increase in scam reports involving crypto withdrawals as the layering channel. The pattern — victim deposits in fiat, immediate conversion to USDT or BTC, withdrawal to scam-controlled wallets — closely mirrors AUSTRAC\'s "Pig Butchering" typology bulletin and HK\'s recent VASP enforcement actions.\n\nMAS\'s response is taking shape through updated MAS Notice PSN02 guidance scheduled for H2 2026. The expected revisions cover three areas: enhanced source-of-funds verification at deposit thresholds (likely SGD 50,000 / 90 days), mandatory KYT screening of inbound and outbound wallet flows, and clearer expectations on customer-protection messaging when scam-victim mule patterns are detected.\n\nFor licensed DPT providers, the operating model implication is clear: KYT (Chainalysis, TRM Labs, Elliptic, or equivalent) screening is becoming a regulatory prerequisite rather than a competitive differentiator. The cost of compliance scales with volume, putting pressure on smaller licensees that may struggle to absorb the unit costs.',
    ),
    NewsItem(
        date="2026-03-28",
        jurisdiction="Singapore (STRO)",
        title="GIC and Temasek explore Tranche 2-style legal-sector AML readiness",
        summary=(
            "Singapore's sovereign-wealth investors GIC and Temasek conducted internal AML "
            "readiness reviews for outside-counsel networks, anticipating regional legal-sector "
            "AML obligations following Australia's Tranche 2 reforms. Singapore's own DNFBP "
            "expansion is rumoured but not formally on MAS roadmap."
        ),
        source="Bloomberg Asia",
        url="https://www.bloomberg.com/asia",
        topic="AML enforcement",
        full_article="Singapore's two sovereign wealth vehicles, GIC and Temasek, have conducted structured AML readiness assessments across their external legal-counsel networks, according to people familiar with the matter — a pre-emptive measure that signals how large institutional investors are quietly repositioning ahead of potential designation of legal professionals as reporting entities under Singapore's anti-money laundering framework.\n\nThe move draws direct inspiration from Australia's long-delayed Tranche 2 reforms, which finally extended AML/CTF Act obligations to lawyers, accountants, and real-estate agents in late 2024 after more than a decade of industry resistance. Australia's experience demonstrated that the practical burden of bringing designated non-financial businesses and professions (DNFBPs) into scope falls not only on the professionals themselves but on their sophisticated institutional clients, who must rapidly assess whether their outside advisers can meet the due-diligence and suspicious transaction reporting standards that financial institutions have long internalised. FATF Recommendation 22 has formally required DNFBP coverage since 2003; Singapore's legal sector remains largely outside the Corruption, Drug Trafficking and Other Serious Crimes (Confiscation of Benefits) Act and the Monetary Authority of Singapore's core AML notice architecture, a gap that FATF evaluators have noted in successive mutual evaluation cycles.\n\nFor GIC and Temasek, whose combined asset bases span hundreds of external mandates across Southeast Asia and beyond, the practical calculus is straightforward: if Singapore moves toward mandatory DNFBP reporting — whether through amendment to the CDSA, expansion of STRO's reporting obligations, or a standalone legal-sector notice — outside counsel who have not built transaction monitoring or suspicious transaction report infrastructure will become a compliance liability rather than merely a service provider. The reviews are understood to have examined firms' beneficial-ownership verification procedures, client risk-rating methodologies, and staff AML training records.\n\nMAS has not publicly signalled any formal legislative timetable for DNFBP expansion, and the Law Society of Singapore continues to operate a largely voluntary professional conduct framework on financial crime. That institutional silence has not, however, deterred Singapore's most consequential investors from stress-testing their supply chains against a regulatory scenario that regional momentum — and FATF's forthcoming assessment cycle — makes increasingly plausible. How law firms respond to that private pressure may ultimately shape the political economy of any formal rule-making more than the regulators themselves expect.",
    ),
    NewsItem(
        date="2026-03-12",
        jurisdiction="Singapore (STRO)",
        title="ACAMS Singapore conference programme published — 16-18 May 2026",
        summary=(
            "Conference themes: AI in compliance (full day track), FATF mutual evaluation prep, "
            "DNFBP capability uplift, scam typology updates. STRO Director and MAS Deputy Managing "
            "Director confirmed as keynotes."
        ),
        source="ACAMS Singapore Chapter",
        url="https://www.acams.org/en/chapters/singapore",
        topic="Conferences / Events",
        full_article="The ACAMS Singapore Chapter has published its conference programme for 16–18 May 2026, with the Suspicious Transaction Reporting Office Director and a Monetary Authority of Singapore Deputy Managing Director confirmed as keynote speakers — an alignment of supervisory voices that signals a coordinated regulatory messaging agenda ahead of what is expected to be a consequential period for Singapore's financial crime framework.\n\nThe timing is deliberate. Singapore's next FATF mutual evaluation is anticipated within the medium-term planning horizon, and the inclusion of a dedicated programme track on mutual evaluation preparedness reflects the industry's awareness that correspondent relationships, de-risking decisions, and reputational positioning turn materially on a jurisdiction's FATF rating. Singapore's 2016 evaluation produced a largely favourable outcome, but the methodology has tightened considerably since — particularly around effectiveness assessments under the 2013 revised Recommendations — and the compliance community is recalibrating accordingly.\n\nFor MLROs and heads of financial crime compliance, the artificial intelligence track, occupying a full conference day, is the most operationally consequential strand. MAS has progressively embedded technology-risk expectations into its AML supervisory framework, including through Notice MAS 626 and its equivalents across banking, capital markets, and insurance sectors, and examiners are increasingly scrutinising whether AI-assisted transaction monitoring systems introduce model-risk blind spots or perpetuate demographic biases that could undermine suspicious activity detection. A full-day forum gives practitioners space to move beyond vendor demonstrations toward genuine peer interrogation of governance frameworks and regulatory expectations.\n\nThe Designated Non-Financial Business and Profession capability uplift track addresses a persistent supervisory concern. Singapore's Precious Stones and Precious Metals Dealers regime under the Precious Stones and Precious Metals (Prevention of Money Laundering and Terrorism Financing) Act, and broader DNFBP obligations under the broader AML/CFT framework, have expanded the regulated perimeter considerably, yet examination findings continue to identify uneven implementation of customer due diligence and record-keeping requirements across this population.\n\nThe scam typology update track rounds out a programme shaped squarely by operational reality: Singapore's scam-related suspicious transaction report volumes have risen sharply in recent years, placing renewed pressure on reporting institutions to refine red-flag indicators and escalation workflows under the Corruption, Drug Trafficking and Other Serious Crimes (Confiscation of Benefits) Act.\n\nWith supervisory keynotes anchoring all three days, the conference will function less as a networking exercise and more as an informal guidance channel — a format Singapore's compliance community has historically used effectively to triangulate regulatory expectations ahead of formal policy pronouncements.",
    ),
    NewsItem(
        date="2026-02-22",
        jurisdiction="Singapore (STRO)",
        title="Stripe acquires Sumsub Asia-Pacific business in USD 340M deal",
        summary=(
            "Payments giant Stripe announced acquisition of Sumsub's APAC operations, including "
            "Singapore HQ. Industry watching for impact on KYC vendor landscape; Sumsub global "
            "remains independent. Acquisition closes H2 2026 pending regulatory approvals."
        ),
        source="TechCrunch",
        url="https://techcrunch.com/category/fintech/",
        topic="Industry M&A",
        full_article="Stripe's USD 340 million acquisition of Sumsub's Asia-Pacific operations, announced on 22 February 2026, consolidates a significant KYC and identity-verification capability directly within one of the region's most widely used payment infrastructures — a structural shift that compliance officers at Stripe-dependent fintechs will need to assess carefully before the deal closes in the second half of the year.\n\nSumsub has been a material vendor to regulated entities across APAC, supplying automated customer due diligence, liveness detection, and ongoing monitoring workflows to firms operating under MAS Notice PSN01, MAS Notice FSG-N02, and equivalent AML/CTF frameworks in Australia and Hong Kong. Its Singapore headquarters places the acquired entity squarely within the Monetary Authority of Singapore's supervisory perimeter, meaning any post-acquisition changes to data residency, outsourcing arrangements, or service continuity will engage MAS's Guidelines on Outsourcing and the Technology Risk Management Notice — obligations that fall on the regulated financial institution, not merely on the vendor.\n\nFor MLROs at firms that currently use both Stripe's payment rails and Sumsub's verification layer, the vertical integration raises immediate conflict-of-interest and concentration-risk questions. FATF Recommendation 17 permits reliance on third parties for customer due diligence, but the relying institution retains full regulatory liability. Where a single group entity now provides both the payment infrastructure and the identity verification underpinning CDD, supervisors — including Singapore's Suspicious Transaction Reporting Office under the Corruption, Drug Trafficking and Other Serious Crimes Act framework — may scrutinise whether the arms-length integrity of that verification process is adequately preserved. Compliance teams should document their vendor risk assessments and revisit contractual provisions around audit rights and data segregation before the transaction closes.\n\nThe competitive implications are equally consequential. Sumsub Global's remaining independence offers continuity for clients outside APAC, but the regional carve-out may prompt customers in Southeast Asia to accelerate vendor diversification strategies, benefiting competitors such as Jumio, Veriff, and locally embedded providers. Ironically, a deal intended partly to deepen Stripe's compliance offering could accelerate fragmentation in the KYC vendor market it is entering.\n\nThe long-term regulatory question is whether consolidation of payments and identity verification within a single commercial group is a structural improvement to financial crime controls or a concentration risk that APAC supervisors have yet to fully price into their oversight frameworks.",
    ),

    # ---- Hong Kong ----
    NewsItem(
        date="2026-04-25",
        jurisdiction="Hong Kong (JFIU)",
        title="HK virtual banks reach 12% retail deposits market share",
        summary=(
            "Combined retail deposits at HK's eight virtual banks (ZA Bank, Mox, livi, WeLab, "
            "et al.) reached 12% market share in Q1 2026, up from 9% a year earlier. AML "
            "compliance scrutiny intensifies as scale grows; HKMA enforcement of HKD 18M against "
            "one virtual bank earlier this month underscores expectations."
        ),
        source="South China Morning Post — Business",
        url="https://www.scmp.com/business",
        topic="Fintech / Digital banking",
        full_article="The eight HKMA-licensed virtual banks — ZA Bank, Mox, livi, WeLab, Ant Bank HK, Airstar, Fusion, and Welab — collectively crossed 12% of retail deposits market share in Q1 2026. The aggregate figure obscures significant variance: ZA Bank and Mox together account for over 60% of virtual bank deposits, while smaller licensees continue to operate sub-scale.\n\nThe compliance scrutiny intensifies as scale grows. The HKMA's HKD 18 million enforcement action against an unnamed virtual bank earlier in April crystallised what supervisory authorities have been signalling privately for the past two years: that the digital-banking model's emphasis on frictionless onboarding has created systemic mule-account exposure that older Tier-1 banks experience at materially lower rates.\n\nThree control deficiencies recur in HKMA findings. First, e-KYC processes that satisfy customer-acquisition KPIs but fail under stress-test against organised mule-recruitment patterns. Second, transaction-monitoring rule sets calibrated to retail benign behaviour and slow to adapt when customer profiles shift post-onboarding. Third, alert-disposition workflows where junior analysts close mule cases without sufficient escalation given the velocity of organised criminal flows.\n\nResolution requires investment in continuous control testing, ML-based mule-cluster detection, and deeper integration with cross-bank intelligence sharing. The HKMA's policy direction signals that its expectations of virtual banks are converging with — not relaxed against — those for conventional Authorized Institutions.",
    ),
    NewsItem(
        date="2026-04-15",
        jurisdiction="Hong Kong (JFIU)",
        title="HashKey announces RWA tokenisation platform launch",
        summary=(
            "SFC-licensed VASP HashKey announced launch of regulated tokenised real-world-assets "
            "platform under the SFC sandbox. Initial offerings: tokenised investment-grade bonds. "
            "AML implications: source-of-wealth verification at higher thresholds; Travel Rule "
            "compliance for cross-VASP transfers."
        ),
        source="Asia Crypto Today",
        url="https://www.asiacryptotoday.com",
        topic="Crypto / VASP",
        full_article="HashKey Exchange's tokenised real-world-asset platform, launched under the SFC's regulatory sandbox, marks a structural shift in Hong Kong's positioning for institutional crypto. Initial offerings are tokenised investment-grade bonds, sold to professional investors only — a deliberate scope-limitation that reflects both SFC caution and market realism about retail readiness for RWA products.\n\nThe AML implications are substantive. Tokenised RWAs sit at the intersection of conventional securities regulation and emerging VA (virtual asset) supervision. SFC's licensing framework for VASPs (operative since June 2023) and the parallel securities-licensing regime for fund managers create overlapping but not fully aligned obligations on customer due diligence, source-of-wealth verification, and the application of the FATF Travel Rule to tokenised-asset transfers.\n\nFor HashKey and other VASPs entering the RWA market, three operational questions are unresolved. First, where the AML perimeter sits when a tokenised bond is transferred between custodial wallets at different institutions — does the issuer, the custodian, or both bear the obligation? Second, how the Travel Rule applies when transfers are settled on-chain but ultimate beneficial owners are tracked off-chain in custodian books. Third, what enhanced source-of-wealth threshold applies given that RWA products are typically larger than retail crypto purchases.\n\nIndustry view is that SFC will issue specific RWA AML guidance in H2 2026. The market opportunity for HK is significant: regional competitors in Singapore (Project Guardian) and Australia (ASIC innovation hub) are also moving but each with different regulatory architectures, leaving room for HK's existing VASP framework to anchor the institutional segment.",
    ),
    NewsItem(
        date="2026-04-02",
        jurisdiction="Hong Kong (JFIU)",
        title="Standard Chartered HK appoints Head of Financial Crime Compliance, APAC",
        summary=(
            "Standard Chartered named a former HKMA Executive Director as Head of FCC for APAC "
            "region. Move reflects regional banks' continued investment in senior compliance "
            "talent against backdrop of regulatory enforcement intensity in HK and Singapore."
        ),
        source="Reuters Asia",
        url="https://www.reuters.com/markets/asia/",
        topic="Talent / Hiring",
        full_article="Standard Chartered has appointed a former Hong Kong Monetary Authority Executive Director as its Head of Financial Crime Compliance for the Asia-Pacific region, the bank confirmed on 2 April 2026, a hire that signals the continuing premium placed on regulatory-side experience as enforcement intensity across the region's two principal financial centres shows little sign of moderating.\n\nThe appointment carries particular weight given the HKMA's expanded supervisory mandate under Hong Kong's Anti-Money Laundering and Counter-Terrorist Financing Ordinance, as amended, and the authority's increasingly assertive use of remediation requirements and public reprimands against licensed banks. An executive who has operated within that supervisory apparatus brings institutional knowledge of examination methodology, typology priorities, and the HKMA's expectations around the Suspicious Transaction Report regime administered through the Joint Financial Intelligence Unit — advantages that are difficult to replicate through conventional financial-services career paths alone.\n\nFor Standard Chartered, the move is consistent with a broader pattern among internationally active banks operating across APAC that have absorbed significant enforcement costs over the past decade and face sustained regulatory scrutiny in multiple jurisdictions simultaneously. Singapore's Monetary Authority, operating under the MAS Notice 626 framework, and Hong Kong's JFIU together generate a substantial proportion of the region's financial crime referrals, and institutions with large correspondent and private banking footprints in both markets carry commensurate exposure. The hire also reflects competitive pressure: Goldman Sachs, HSBC, and several regional institutions have made analogous senior appointments since 2023, driving up market rates for compliance professionals with direct supervisory pedigree.\n\nFrom a governance standpoint, placing a former regulator in an APAC-wide role — rather than a single-jurisdiction function — suggests Standard Chartered is seeking coherence across its financial crime framework at a regional level, rather than managing jurisdictional risk in siloed fashion. That structural choice aligns with FATF Recommendation 18's expectation that financial groups implement group-wide AML/CFT programmes with adequate resources at the consolidated level.\n\nWhether the appointment accelerates any ongoing dialogue with the HKMA regarding supervisory expectations remains to be seen. What is clear is that the market for senior financial crime talent with regulatory provenance has become a meaningful indicator of where institutions perceive their residual risk to sit — and in APAC, that assessment points firmly towards the compliance function.",
    ),
    NewsItem(
        date="2026-03-18",
        jurisdiction="Hong Kong (JFIU)",
        title="HK scam losses hit HKD 9.2B in 2025 — record high",
        summary=(
            "HK Police Force statistics: 2025 total scam losses at HKD 9.2B, up 14% YoY. "
            "Investment scams remain top category (52%), followed by phishing/romance scams "
            "(28%). Banking sector mule-account problem highlighted; banks under pressure to "
            "improve detection."
        ),
        source="HK Police Force / RTHK",
        url="https://www.police.gov.hk",
        topic="Scams / Fraud trends",
        full_article="Hong Kong recorded HKD 9.2 billion in scam-related losses during 2025, a 14 percent year-on-year increase and the highest figure since the Joint Financial Intelligence Unit began systematic tracking, according to statistics released by the Hong Kong Police Force in March 2026. The figure underscores a structural, rather than episodic, failure in the territory's fraud-prevention architecture at a moment when the HKMA and SFC are actively consulting on cross-sector data-sharing frameworks.\n\nInvestment scams accounted for 52 percent of total losses — a category that encompasses pig-butchering operations, fake trading platforms, and fraudulent asset managers — while phishing and romance scams contributed a further 28 percent. The dominance of investment fraud is consistent with FATF's 2024 thematic review on online fraud, which identified jurisdictions with high retail investment participation and dense digital-payment infrastructure as disproportionately exposed. Hong Kong satisfies both criteria. The JFIU's Fraud and Money Laundering Intelligence Taskforce, established in 2017 as a public-private intelligence-sharing mechanism, has expanded its membership, yet the aggregate loss trajectory suggests that upstream intelligence has not translated into sufficient downstream disruption.\n\nThe mule-account problem in the banking sector is particularly acute. Under section 25 of the Organized and Serious Crimes Ordinance, financial institutions already bear statutory obligations to report known or suspected proceeds of crime; the difficulty lies in detection latency. Accounts used for scam layering are frequently opened through digitally onboarded customers whose behavioral anomalies — rapid fund transit, dormant-to-active switching, inconsistent device geolocation — are identifiable in transaction monitoring systems but require calibration thresholds that many retail banks have not tightened sufficiently. The HKMA's Supervisory Policy Manual AML/CFT module remains the operative guidance, but industry sources suggest examiners are now scrutinizing whether transaction monitoring rules are tuned to scam-typology patterns specifically, not merely conventional money-laundering red flags.\n\nFor compliance officers, the 2025 data reinforces several operational priorities: enhanced customer-risk scoring for accounts exhibiting rapid-onboarding-to-high-value-transit patterns, closer alignment with the Fraud and Money Laundering Intelligence Taskforce's scam typology advisories, and board-level accountability for mule-account metrics as a distinct key risk indicator. With the HKMA having signalled its intention to strengthen proportionality expectations in AML supervision during 2026, institutions that cannot demonstrate responsive calibration of controls to the prevailing scam environment face heightened regulatory scrutiny, regardless of their broader AML programme maturity.",
    ),
    NewsItem(
        date="2026-02-28",
        jurisdiction="Hong Kong (JFIU)",
        title="Industry consortium launches HK fraud-data sharing initiative",
        summary=(
            "Twelve HK banks launched a fraud-data sharing consortium under HKAB auspices, "
            "enabling near-real-time mule-account intelligence sharing. Privacy framework "
            "approved by HKMA; pilot covers retail-fraud signals only initially."
        ),
        source="Hong Kong Association of Banks",
        url="https://www.hkab.org.hk",
        topic="Regulatory tech",
        full_article="Twelve Hong Kong retail banks have launched a fraud-intelligence sharing consortium under the auspices of the Hong Kong Association of Banks, with a privacy framework formally approved by the Hong Kong Monetary Authority, enabling near-real-time exchange of mule-account signals across participating institutions. The immediate operational implication is that a suspected money-mule account flagged at one member bank can now generate a timely alert at others before funds are layered onward—a capability that has historically eluded fragmented, institution-level detection.\n\nThe initiative arrives against a backdrop of sustained pressure from the Joint Financial Intelligence Unit, which has repeatedly noted that mule-account networks exploit the informational asymmetry between banks operating within siloed transaction-monitoring environments. Hong Kong's Anti-Money Laundering and Counter-Terrorist Financing Ordinance (AMLO) already imposes obligations on institutions to file Suspicious Transaction Reports, but the STR pipeline is inherently retrospective. FATF Recommendation 40 on international cooperation and its domestic analogue in information-sharing guidance have long encouraged jurisdictions to facilitate lawful exchange of financial intelligence, yet liability concerns and the Personal Data (Privacy) Ordinance have historically constrained bilateral data flows between private-sector institutions.\n\nFor MLROs at participating banks, the approved privacy framework is the critical enabler: it presumably delineates permissible data fields, retention limits, and access controls in a manner that satisfies PDPO requirements while preserving the operational utility of the signals. Compliance teams will nonetheless need to ensure that downstream adverse actions—account restrictions, enhanced due diligence triggers—are defensible under existing customer contractual terms and are not challenged as privacy violations. Institutions outside the initial twelve face an asymmetric information disadvantage that may itself become a reputational and supervisory concern.\n\nFor the HKMA, the pilot's restriction to retail-fraud signals is a pragmatic sequencing choice, allowing the authority to assess governance and data-quality standards before any extension to trade-based or cross-border typologies. Supervisors will be watching whether match rates justify the compliance infrastructure and whether false-positive volumes impose undue customer-impact costs on participating institutions.\n\nThe broader significance lies in whether this model migrates toward the kind of public-private intelligence fusion seen in the United Kingdom's NECC-backed Financial Intelligence Sharing Partnership or Singapore's MAS-facilitated frameworks under MAS Notice 626. If the pilot demonstrates measurable disruption to mule-account networks—measured in STR-to-prosecution ratios or fraud-loss metrics—it will materially strengthen the case for legislating expanded safe-harbour provisions for good-faith information sharing across Hong Kong's financial sector.",
    ),
    NewsItem(
        date="2026-02-04",
        jurisdiction="Hong Kong (JFIU)",
        title="HK Government promotes 'Compliance Hub' positioning vs. Singapore",
        summary=(
            "Financial Secretary's Budget Speech promoted HK as Asia's compliance and RegTech "
            "hub, citing VASP licensing regime and TCSP framework. Industry view: positioning "
            "race with Singapore intensifying; talent and capital flows still favour Singapore."
        ),
        source="HKSAR Government / RTHK",
        url="https://www.budget.gov.hk",
        topic="Industry M&A",
        full_article="Hong Kong's Financial Secretary used the 2026–27 Budget Speech to formally articulate an ambition that practitioners have long discussed informally: positioning the city as Asia's pre-eminent compliance and RegTech hub, pointing to the Virtual Asset Service Provider licensing regime under the Anti-Money Laundering and Counter-Terrorist Financing Ordinance (AMLO) and the Trust or Company Service Provider framework as evidence of regulatory infrastructure capable of anchoring the sector.\n\nThe framing is not without foundation. Hong Kong's VASP regime, which came into full effect in mid-2023 under amendments to the AMLO, imposes AML/CFT obligations broadly consistent with FATF Recommendation 15 and its 2023 updated guidance on virtual assets, including customer due diligence, transaction monitoring, and travel rule compliance. The TCSP licensing framework, administered by the Companies Registry, similarly aligns with FATF Recommendations 24 and 25 on transparency of legal persons and arrangements. Taken together, these represent a credible regulatory stack for compliance-intensive financial services businesses.\n\nThe difficulty is competitive context. Singapore's Monetary Authority has spent the better part of a decade building density in RegTech through its Financial Sector Technology and Innovation scheme, the MAS Notices on technology risk management, and a regulatory sandbox that has attracted both established vendors and early-stage firms. Talent surveys conducted by industry bodies consistently show that compliance professionals and RegTech founders weigh rule-of-law perception, talent portability, and tax treatment alongside the regulatory framework itself — factors where Singapore continues to hold measurable advantages in practitioner surveys.\n\nFor MLROs and heads of financial crime compliance evaluating operational footprint decisions, the Budget Speech signals that Hong Kong intends to compete on regulatory credibility rather than cost arbitrage. The JFIU's typologies work and the SFC's enforcement record on AML failings — including sanctions against licensed corporations for inadequate transaction monitoring — provide substantive regulatory engagement that sophisticated compliance functions value. Whether that translates into hub status depends less on ministerial speeches than on whether the city can demonstrate consistent, principles-based supervision that gives firms regulatory certainty without operational unpredictability.\n\nThe more instructive signal will come when the Securities and Futures Commission and Hong Kong Monetary Authority publish their joint AML supervisory priorities for 2026, and whether those documents reflect the granularity and cross-sector coordination that compliance infrastructure investment genuinely requires.",
    ),

    # ---- Malaysia ----
    NewsItem(
        date="2026-04-24",
        jurisdiction="Malaysia (FIED)",
        title="AEON Bank breaks even in Q1 2026 — first Islamic digital bank profitability",
        summary=(
            "AEON Bank announced break-even in Q1 2026, becoming Malaysia's first Islamic "
            "digital bank to achieve profitability under the BNM digital banking framework. "
            "Compliance investment cited as significant ongoing cost; bank publicly committed "
            "to continued AML control uplift."
        ),
        source="The Edge Malaysia",
        url="https://www.theedgemalaysia.com",
        topic="Fintech / Digital banking",
        full_article="AEON Bank's announcement of a break-even position in the first quarter of 2026 marks a consequential inflection point for Malaysia's digital banking experiment: for the first time, an Islamic digital bank operating under Bank Negara Malaysia's Digital Banking Framework has demonstrated that a compliant, purpose-built financial institution can reach operational sustainability without compromising on financial crime controls.\n\nThe milestone arrives roughly three years after BNM awarded five digital banking licences under its 2022 framework, which imposed a foundational period requiring licensees to maintain a cost-to-income discipline while building out risk infrastructure before scaling. AEON Bank, operating on an Islamic banking licence under the Islamic Financial Services Act 2013, has had to satisfy both BNM's Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 obligations and the heightened scrutiny that accompanies any new entrant to the licensed deposit-taking sector. Malaysia's FATF mutual evaluation cycle and its sustained engagement on beneficial ownership transparency have kept regulatory expectations on incumbent and challenger banks alike at an elevated baseline.\n\nFor MLROs and compliance officers across the region, the significance lies in AEON Bank's explicit acknowledgement that AML control investment remains a material cost line — not a one-time build. This is consistent with MAS's expectations articulated in its own digital bank supervisory guidance in Singapore, where compliance infrastructure is treated as a recurring capital and operational commitment rather than a sunk cost. The bank's public commitment to continued AML uplift suggests its control environment is maturing iteratively, the approach broadly aligned with FATF Recommendation 1's risk-based methodology, where control proportionality follows evolving customer and product risk profiles rather than a static deployment.\n\nFor the four remaining digital banking licensees still in their foundational periods, the AEON Bank result reframes the narrative around compliance expenditure. The sector has frequently positioned AML investment as a drag on the path to profitability; the Q1 2026 result offers an early, if limited, counter-argument. Whether the bank's customer acquisition strategy has exposed it to the higher-risk segments — gig economy workers, underbanked populations — that digital banks were partly licensed to serve will determine how robustly its transaction monitoring and customer due diligence frameworks are tested as volumes scale.\n\nBNM's willingness to allow digital banks to demonstrate viability on their own timelines, while holding the compliance baseline firm, will be watched closely by regional supervisors calibrating their own frameworks.",
    ),
    NewsItem(
        date="2026-04-12",
        jurisdiction="Malaysia (FIED)",
        title="Boost Bank announces partnership with Sumsub for unified KYT/KYC platform",
        summary=(
            "Boost Bank (Axiata-RHB consortium) announced a strategic partnership with Sumsub "
            "to deploy a unified KYT (know-your-transaction) and KYC platform. Move follows BNM "
            "thematic findings on digital-bank AML control gaps; Boost positioning as 'compliance-"
            "first digital bank' in Malaysian market."
        ),
        source="Fintech News Malaysia",
        url="https://fintechnews.my",
        topic="Regulatory tech",
        full_article="Boost Bank, the digital lender backed by the Axiata-RHB consortium, has formalised a partnership with identity verification and transaction monitoring specialist Sumsub to deploy a unified know-your-customer and know-your-transaction platform — a move that arrives against a backdrop of Bank Negara Malaysia's thematic supervisory findings identifying systemic AML control weaknesses across the digital banking cohort.\n\nBank Negara's Financial Intelligence and Enforcement Department has sharpened its scrutiny of digital banks since the first wave of licence approvals under the Digital Banking Framework came into effect. Malaysia's primary AML legislation, the Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 (AMLA), places explicit obligations on reporting institutions to maintain adequate customer due diligence and transaction monitoring systems proportionate to their risk exposure. BNM's thematic reviews, consistent with FATF Recommendation 15 on new technologies, have repeatedly flagged the risk that lean operating models adopted by digital banks can translate into under-engineered controls — particularly at the intersection of onboarding velocity and ongoing transaction surveillance.\n\nThe strategic significance of integrating KYC and KYT within a single platform is operational as much as it is regulatory. Fragmented systems create data-linkage gaps that impair the detection of behavioural anomalies post-onboarding — a vulnerability that supervisors and the Egmont Group have associated with mule account exploitation in retail digital banking channels. A unified architecture, in principle, enables continuous risk re-scoring informed by live transactional behaviour, rather than static customer profiles reviewed on periodic cycles.\n\nFor peer digital banks — GXBank, AEON Bank, and the forthcoming entrants — Boost's public positioning as a compliance-first institution creates an implicit benchmark. MLROs at competing institutions will face internal pressure to demonstrate equivalent or superior control infrastructure, particularly as BNM's supervisory intensity under its risk-based examination schedule is expected to increase through 2026 and into 2027.\n\nThe more durable question is whether platform integration alone resolves the talent and governance deficits that BNM's thematic findings also identified. Technology vendors can consolidate data flows and automate alert generation, but the quality of suspicious transaction reporting under AMLA Section 14 ultimately depends on the calibre of human review and the escalation culture within the institution. Boost's partnership signals intent; the examination findings over the next supervisory cycle will indicate whether that intent has been translated into measurable control effectiveness.",
    ),
    NewsItem(
        date="2026-03-25",
        jurisdiction="Malaysia (FIED)",
        title="Bank Negara Malaysia governor warns on digital-bank mule-account risks",
        summary=(
            "BNM Governor in keynote speech warned digital-bank licensees on systemic mule-"
            "account risks driven by easy e-KYC onboarding. Industry-wide capability uplift "
            "expected; BNM may issue prescriptive guidance in H2 2026."
        ),
        source="Bank Negara Malaysia",
        url="https://www.bnm.gov.my",
        topic="AML enforcement",
        full_article="Bank Negara Malaysia Governor Abdul Rasheed Ghaffour used a keynote address on 25 March 2026 to put digital-bank licensees on formal notice that mule-account proliferation has become a systemic concern, signalling that the regulator is prepared to issue prescriptive guidance in the second half of 2026 if industry self-correction proves insufficient. The warning carries immediate compliance weight: under Malaysia's Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 (AMLA), reporting institutions bear strict obligations to establish and maintain effective customer due diligence and ongoing monitoring frameworks, and a governor-level public caution is typically a precursor to enforceable supervisory action.\n\nThe backdrop is Malaysia's deliberate liberalisation of digital banking. BNM granted five digital-bank licences under the Financial Services Act 2013 framework, with operationalisation phased from 2024. The e-KYC reliance that enabled rapid account opening at scale—a core commercial proposition for digital entrants—has simultaneously lowered friction for bad actors. FATF Recommendation 10 and its Interpretive Note on digital onboarding require that technological risk mitigants demonstrably match the due diligence standards of face-to-face channels; the Governor's remarks suggest BNM's supervisory reviews have found that equivalence is not yet being achieved across the cohort.\n\nFor MLROs at digital banks, the speech effectively resets the supervisory tolerance threshold. Institutions should expect heightened scrutiny of mule-detection typologies, velocity rules, and post-onboarding behavioural analytics under BNM's Risk-Based Supervisory Framework. Peer banks and traditional licensees operating digital channels face collateral pressure: a sector-wide capability gap identified by the Governor creates reputational and regulatory exposure for any institution seen as a conduit rather than a control point. Payment network participants and fintech partners embedded in digital-bank ecosystems should similarly audit their contractual and operational obligations under BNM's Policy Document on Anti-Money Laundering and Counter Financing of Terrorism.\n\nThe H2 2026 guidance timeline is tight. If BNM follows the model of its earlier prescriptive interventions—such as the detailed transaction monitoring expectations embedded in successive AML/CFT policy document iterations—the forthcoming instrument could specify minimum detection model performance thresholds, mandatory mule-account escalation timelines, and enhanced suspicious transaction reporting obligations under AMLA Section 14. Digital-bank boards should treat the current window not as preparation time but as the examination period itself.",
    ),
    NewsItem(
        date="2026-03-08",
        jurisdiction="Malaysia (FIED)",
        title="Malaysian scam losses RM 1.7B in 2025; PDRM increases anti-scam unit",
        summary=(
            "Polis DiRaja Malaysia (PDRM) reported total scam losses RM 1.7B in 2025, up 22% "
            "YoY. Investment scams and 'Macau scams' remain top categories. Ant-Scam Centre "
            "headcount doubled; cross-bank intelligence-sharing in pilot via BNM."
        ),
        source="The Star Malaysia / PDRM",
        url="https://www.thestar.com.my",
        topic="Scams / Fraud trends",
        full_article="Malaysian financial-crime losses attributable to scams reached RM 1.7 billion in 2025, a 22 percent year-on-year increase reported by Polis DiRaja Malaysia, underscoring that intensified enforcement has not yet translated into a reversal of the underlying trend. For financial institutions operating under Bank Negara Malaysia's Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 (AMLA) and the associated AML/CFT and Targeted Financial Sanctions Policy Documents, the figure represents both a supervisory signal and a material exposure to proceeds-of-crime liability.\n\nInvestment fraud and Macau scam variants — the latter characterised by impersonation of law-enforcement or government officials — have consistently dominated Malaysian scam typologies for several years. Both categories generate layered fund flows that challenge transaction monitoring calibrations: investment scam proceeds frequently transit through nominee accounts and virtual asset service providers before aggregation, while Macau scam receipts tend to move in rapid, low-dwell-time transfers designed to exhaust cooling-off windows. FATF Recommendation 29 obliges financial intelligence units to disseminate actionable typologies, and BNM's Financial Intelligence and Enforcement Department (FIED) has incrementally expanded its suspicious transaction report feedback loop, though industry practitioners have noted that feedback cycles remain uneven across institution size.\n\nThe doubling of Anti-Scam Centre headcount is operationally significant primarily insofar as it accelerates account-freeze response times — a variable that directly determines victim recovery rates. More structurally consequential is the pilot cross-bank intelligence-sharing mechanism coordinated through BNM. If institutionalised, this arrangement would bring Malaysia closer to the model operated by the Singapore Police Force's Anti-Scam Centre and the inter-bank COSMIC platform, which permits regulated entities to share customer risk information on a consent-independent basis under prescribed conditions. Malaysian MLROs should note that any formalised data-sharing framework will require careful navigation of the Personal Data Protection Act 2010 alongside AMLA safe-harbour considerations.\n\nFor compliance functions, the RM 1.7 billion figure should prompt a reassessment of mule-account detection scenarios and the adequacy of real-time payment monitoring thresholds, particularly given BNM's supervisory emphasis on technology-enabled AML controls articulated in its 2024–2026 Financial Sector Blueprint implementation priorities. Whether the cross-bank pilot matures into a mandatory industry utility will depend substantially on BNM's appetite to exercise its directive powers — and on how quickly victim loss trajectories respond to the measures already deployed.",
    ),
    NewsItem(
        date="2026-02-18",
        jurisdiction="Malaysia (FIED)",
        title="ACAMS Malaysia chapter holds inaugural conference 12 May 2026",
        summary=(
            "ACAMS Malaysia chapter (recently established) hosting inaugural conference. Topics: "
            "Islamic banking AML overlay, digital-bank compliance, BNM enforcement priorities. "
            "AEON Bank, Boost Bank, Bank Islam confirmed sponsorship."
        ),
        source="ACAMS Malaysia",
        url="https://www.acams.org",
        topic="Conferences / Events",
        full_article="The ACAMS Malaysia chapter will hold its inaugural conference on 12 May 2026, bringing together anti-financial crime practitioners at a moment when Bank Negara Malaysia's Financial Intelligence and Enforcement Department is intensifying supervisory engagement across both conventional and Islamic finance sectors. The timing is deliberate: BNM's enforcement actions against designated non-financial businesses and professions accelerated through 2024 and 2025, and compliance functions across licensed institutions are under pressure to demonstrate not merely policy adequacy but operational effectiveness.\n\nMalaysia occupies a structurally distinctive position in the global AML architecture. As the world's largest sukuk market and a jurisdiction where Islamic banking assets constitute roughly half of total banking system financing, the country faces a compliance challenge that few FATF member states fully share: reconciling the transactional logic of Shariah-compliant instruments — musharakah, murabahah, wakala — with customer due diligence and transaction monitoring frameworks designed around conventional cash flows. The conference's dedicated Islamic banking AML overlay session reflects a genuine gap in standardised practitioner guidance, one that neither FATF Recommendation 1's risk-based approach nor BNM's own Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 (AMLA) explicitly resolves at the product level.\n\nThe involvement of AEON Bank, Boost Bank, and Bank Islam as confirmed sponsors is itself a signal worth reading carefully. Two of the three are digital banks operating under BNM's digital licensing framework, institutions that went live with inherently scalable, low-touch onboarding models that compress the traditional timeline between customer acquisition and risk exposure. Their participation suggests the sector recognises that the compliance infrastructure built for licence approval may require recalibration as transaction volumes and product complexity increase. Digital banks globally have attracted regulatory censure precisely at this growth inflection point.\n\nFor MLROs and heads of financial crime compliance across the region, the conference agenda — enforcement priorities, digital-bank compliance, and the Islamic finance overlay — maps directly onto the three axes along which BNM's supervisory intensity is most likely to concentrate through the remainder of the decade. ACAMS' institutional entry into the Malaysian market, formalised through a chapter structure that FATF's mutual evaluation process effectively rewards by deepening professional competence, should add a layer of structured peer exchange that the jurisdiction's compliance community has lacked relative to Singapore or Hong Kong. Whether that exchange translates into measurable uplift in suspicious transaction reporting quality will be the more consequential measure of success.",
    ),
    NewsItem(
        date="2026-02-05",
        jurisdiction="Malaysia (FIED)",
        title="GXBank acquires fraud-detection startup Tatum for RM 45M",
        summary=(
            "Digital bank GXBank announced acquisition of KL-based fraud-detection startup Tatum "
            "for RM 45M. Move strengthens GXBank's TM and mule-detection capabilities; first "
            "M&A deal among Malaysian digital banking licensees."
        ),
        source="The Edge Malaysia",
        url="https://www.theedgemalaysia.com",
        topic="Industry M&A",
        full_article="GXBank's RM 45 million acquisition of Kuala Lumpur-based fraud-detection startup Tatum marks the first merger and acquisition transaction among Malaysia's cohort of digital banking licensees, signalling a maturation in the sector that extends well beyond balance-sheet ambitions into the operational infrastructure of financial crime compliance.\n\nThe deal carries immediate regulatory weight. Bank Negara Malaysia's Risk Management in Technology (RMiT) policy document and its Anti-Money Laundering, Anti-Terrorism Financing and Proceeds of Unlawful Activities Act 2001 (AMLA) obligations collectively require licensed institutions to maintain fit-for-purpose transaction monitoring and customer due diligence frameworks. For a digital bank operating at the velocity and data volume that GXBank's model demands, proprietary detection capability — rather than reliance on third-party managed services — represents a structurally more defensible compliance posture, particularly as BNM's supervisory expectations around mule account identification have hardened following successive industry-wide directives on fraud.\n\nThe strategic logic is reinforced by Malaysia's broader enforcement context. The Financial Intelligence and Enforcement Department (FIED) has intensified scrutiny of money mule networks, which remain the primary channel through which proceeds of scam activity are layered through the domestic banking system. Tatum's reported competency in behavioural analytics and mule-detection pattern recognition addresses precisely the typology gap that regulators and the National Scam Response Centre have repeatedly highlighted as an industry vulnerability. Under FATF Recommendation 16 and the associated correspondent banking obligations, the ability to flag and intercept suspicious fund flows in near-real time is no longer aspirational; it is expected.\n\nFrom a peer-institution perspective, the acquisition sets a precedent that other Malaysian digital licensees — Boost Bank, AEON Bank, and the remaining licensees in varying stages of full operation — will be compelled to evaluate. Organic build of comparable detection infrastructure carries lead times measured in years; inorganic acquisition compresses that window materially. The RM 45 million consideration, modest by regional fintech transaction standards, may therefore look increasingly attractive in retrospect if BNM raises the technical bar for transaction monitoring adequacy during forthcoming supervisory cycles.\n\nThe transaction also raises integration governance questions that compliance officers will watch closely: how Tatum's models are validated under BNM's model risk expectations, whether its datasets are auditable under existing data localisation requirements, and how GXBank ensures the acquired capability does not introduce new operational risk even as it addresses financial crime exposure.",
    ),

    # ---- Australia ----
    NewsItem(
        date="2026-04-27",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AUSTRAC AUD 47M penalty against major DCE — industry largest enforcement to date",
        summary=(
            "AUSTRAC's enforcement action against a major Australian-registered DCE marks the "
            "largest penalty in the crypto sector globally to date. Settlement includes ongoing "
            "monitor for 18 months; industry watching for ripple effect on similar DCE compliance "
            "investments."
        ),
        source="Australian Financial Review",
        url="https://www.afr.com",
        topic="AML enforcement",
        full_article="AUSTRAC has reached a AUD 47 million civil penalty settlement with a major Australian-registered digital currency exchange, the largest regulatory fine imposed on a cryptocurrency business in the sector's history and a significant test of the agency's willingness to deploy the full enforcement architecture available under the *Anti-Money Laundering and Counter-Terrorism Financing Act 2006* (AML/CTF Act). The settlement also mandates an independent compliance monitor for eighteen months, a condition that imposes both financial and operational costs well beyond the headline figure.\n\nThe action arrives against a backdrop of sustained supervisory pressure on the domestic DCE sector. AUSTRAC registered its first digital currency exchange providers in 2018 following amendments to the AML/CTF Act, but subsequent thematic reviews have repeatedly identified material deficiencies in customer identification procedures, transaction monitoring, and suspicious matter reporting under Part 3 of the Act. The agency's 2022 guidance on virtual asset service providers drew explicit parallels with FATF Recommendation 15 and its interpretive note, signalling that travel-rule compliance and risk-based program adequacy would be the primary supervisory lenses going forward. That warnings were issued and deficiencies persisted makes the quantum of this penalty less surprising than its timing.\n\nFor compliance officers at registered DCEs, the implications are structural rather than merely procedural. The settlement signals that AUSTRAC will treat systemic SMR failures and inadequate know-your-customer controls not as technical non-conformances but as conduct warranting penalties comparable to those imposed on large deposit-taking institutions. The monitorship condition is particularly instructive: it reflects a supervisory preference, familiar from the Westpac enforceable undertaking and the CBA AUSTRAC settlement, for embedding external accountability mechanisms rather than relying on self-remediation alone.\n\nPeer exchanges operating under equivalent AUSTRAC registration obligations face an immediate calculus. Boards and senior managers carrying accountability under the AML/CTF Act's responsible officer provisions cannot credibly treat this enforcement as an outlier. Legal counsel advising smaller DCEs will likely recommend rapid gap analyses against the 2024 revised AML/CTF program rules, particularly around enhanced due diligence for high-risk customers and automated transaction monitoring thresholds.\n\nThe broader significance lies in what the penalty communicates internationally. Australian enforcement is now materially aligned with the Financial Crimes Enforcement Network's posture in the United States and the FCA's virtual asset supervisory approach in the United Kingdom. Regulators in Singapore — where MAS Notice PSN02 sets comparable expectations for Digital Payment Token service providers — will watch the monitorship's findings closely. The era in which DCEs could treat AML investment as a second-order compliance cost appears, in this jurisdiction at least, to be over.",
    ),
    NewsItem(
        date="2026-04-20",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Big Four banks form Tranche 2 ecosystem support consortium",
        summary=(
            "CBA, Westpac, ANZ, NAB jointly announced a programme to support Tranche 2 entity "
            "AML readiness — focused on shared training resources and standardized SoF "
            "verification protocols for outside-firm engagements. Industry framing: reduce "
            "downstream risk in their own customer chain."
        ),
        source="Australian Banking Association",
        url="https://www.ausbanking.org.au",
        topic="Regulatory tech",
        full_article="The Commonwealth Bank, Westpac, ANZ and National Australia Bank have jointly announced a consortium programme designed to accelerate AML readiness among Tranche 2 entities — accountants, lawyers, real estate agents and trust and company service providers — ahead of their formal designation under Australia's expanded anti-money laundering framework. The initiative centres on shared training resources and standardised source-of-funds verification protocols governing engagements between the major banks and their Tranche 2 counterparties, with the banks framing the effort explicitly as a measure to reduce downstream risk within their own customer chains.\n\nThe move follows years of sustained pressure on Australia's AML/CTF regime, which FATF's 2015 mutual evaluation identified as materially deficient for its exclusion of designated non-financial businesses and professions. The Anti-Money Laundering and Counter-Terrorism Financing Amendment Act 2024 ultimately legislated Tranche 2 coverage, with affected entities now facing compliance obligations — including customer due diligence, suspicious matter reporting to AUSTRAC, and AML/CTF programme requirements under the *AML/CTF Act 2006* — on a phased implementation timeline extending through 2026 and 2027. For the major banks, the concern is practical: a solicitor or accountant operating as an introducer or referral source without adequate controls represents an unmitigated gap in the correspondent chain they are ultimately accountable for managing.\n\nFor Tranche 2 entities themselves, the consortium offers tangible operational relief. Standardised source-of-funds templates, in particular, address one of the more persistent pain points flagged during Treasury consultation — the absence of scalable, sector-appropriate verification tools that smaller professional services firms can realistically implement without dedicated compliance functions. Critically, the banks' imprimatur on shared protocols may also reduce the fragmentation risk that emerges when each major institution imposes bespoke onboarding requirements on the same upstream counterparties.\n\nAUSTRAC will nonetheless scrutinise whether consortium-designed standards meet the risk-based expectations embedded in the amended Act, or whether standardisation creates a false floor that underweights higher-risk client typologies — a concern particularly relevant to legal practitioners handling complex trust structures or cross-border property transactions. Supervisors will also be attentive to competition dimensions; industry-coordinated compliance infrastructure, however well-intentioned, attracts regulatory and legal review when it touches commercial relationships. The consortium's longer-term value will be measured not by its architecture but by observable improvements in the quality of suspicious matter reports flowing from newly designated entities into AUSTRAC's financial intelligence holdings.",
    ),
    NewsItem(
        date="2026-04-08",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Crown and Star Casino remediation programmes near completion",
        summary=(
            "Both Crown Resorts and Star Entertainment confirmed remediation programmes mandated "
            "under 2022-2024 enforcement actions are near completion. Independent monitor "
            "reports due Q3 2026; industry watching for whether new licences can resume normal "
            "operations."
        ),
        source="The Sydney Morning Herald",
        url="https://www.smh.com.au",
        topic="AML enforcement",
        full_article="The near-completion of remediation programmes at Crown Resorts and Star Entertainment closes a four-year supervisory cycle that has fundamentally reshaped Australian casino-sector AML compliance. Both groups' independent monitor reports are due in Q3 2026, and industry observers expect substantive — if not unconditional — restoration of normal licensing operations.\n\nThe compliance lessons from Crown and Star will shape AUSTRAC's casino-sector supervision for the rest of the decade. The findings centred on multi-cage same-day buy-in structuring, junket-introduced patron diligence failures, and broader management-reporting deficiencies. The remediation programmes have implemented patron-recognition technology, integrated with AUSTRAC reporting; cross-property activity monitoring; and significant uplift in source-of-wealth verification at higher-tier patron engagement.\n\nSmaller regional casinos have been watching closely. Two such operators received enforceable undertakings in March 2026 covering similar control deficiencies — the first downstream signals of AUSTRAC's intent to extend its enforcement methodology beyond the major Sydney/Melbourne operators. The compliance cost implications for smaller venues, where economics are tighter, are material; expectations of further consolidation are widely held.\n\nThe broader regulatory signal is that the casino sector will not return to its pre-2022 operating mode. AUSTRAC has set a permanent shift in supervisory expectations, and AML/CTF investment is now an embedded operational cost rather than a discretionary one. The implications for the gambling sector's longer-term competitiveness against online platforms are debated but the regulatory direction of travel is settled.",
    ),
    NewsItem(
        date="2026-03-22",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AU scam losses 2025: AUD 2.7B — record high",
        summary=(
            "Australian Competition and Consumer Commission (ACCC) Scamwatch reported AUD 2.7B "
            "in 2025 scam losses. Investment scams ('Pig Butchering') account for 38% of total. "
            "AUSTRAC and major banks under pressure to improve mule-account detection at scale."
        ),
        source="ACCC Scamwatch",
        url="https://www.scamwatch.gov.au",
        topic="Scams / Fraud trends",
        full_article='Australian scam losses reached AUD 2.7 billion in 2025, according to AUSTRAC and ACCC Scamwatch data published on 22 March 2026, marking the highest annual figure on record and reinforcing persistent concerns about the adequacy of mule-account controls across the domestic banking sector. Investment fraud — principally romance-baiting schemes colloquially known as "pig butchering" — accounted for AUD 1.03 billion, or 38 percent of total losses, a category that by definition generates layered cross-border fund flows requiring Suspicious Matter Reports under the *Anti-Money Laundering and Counter-Terrorism Financing Act 2006* (AML/CTF Act), particularly ss. 41–42 governing SMR obligations.\n\nThe figure lands in a regulatory environment already under strain. AUSTRAC\'s 2024 enforcement action against a mid-tier bank for mule-account deficiencies signalled supervisory intent, and the *Anti-Money Laundering and Counter-Terrorism Financing Amendment Act 2024* — which extended the regime to tranche-two entities including lawyers and accountants — has redistributed compliance attention and resources across the sector at a moment when scam typologies are accelerating in sophistication. The FATF Recommendation 20 framework requires timely STR/SMR filing on proceeds of crime regardless of predicate offence, yet industry feedback to AUSTRAC has consistently highlighted the detection lag between mule-account activation and reporting.\n\nFor MLROs at authorised deposit-taking institutions, the data creates a dual pressure point. First, the volume of pig-butchering proceeds transiting domestic accounts elevates exposure under s. 400.9 of the *Criminal Code Act 1995* for institutions that fail to adequately monitor structuring and rapid-transfer patterns characteristic of the typology. Second, the Scam Prevention Framework proposed under the *Scams Prevention Framework Act* consultation process places affirmative disruption obligations on banks, telcos, and digital platforms — moving well beyond passive detection toward proactive liability.\n\nAnalysts at the Australian Banking Association have noted that industry-wide mule-detection utilities, analogous to the UK\'s Mule Insights Tactical Solution operated under the Payment Systems Regulator\'s oversight, remain fragmented domestically. AUSTRAC\'s own Financial Intelligence Insights programme has expanded shared typology guidance, but operationalising that intelligence at transaction-monitoring system level varies materially across institutions by asset size.\n\nThe 2025 figures will almost certainly inform AUSTRAC\'s 2026 supervisory priorities and risk-based examination scheduling. Institutions that cannot demonstrate proportionate uplift in behavioral analytics and cross-institution mule-network identification should anticipate heightened scrutiny — and the possibility that the regulator\'s patience with voluntary remediation timelines is narrowing.',
    ),
    NewsItem(
        date="2026-03-04",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Tranche 2 industry survey: 38% of legal practitioners 'not ready'",
        summary=(
            "Law Council of Australia survey: 38% of legal practitioners self-report as 'not ready' "
            "for 1 July 2026 Tranche 2 obligations. Top concerns: AML/CTF Program drafting, "
            "source-of-wealth verification methodology, customer-engagement triggers. Capability "
            "uplift programmes accelerating."
        ),
        source="Law Council of Australia",
        url="https://www.lawcouncil.au",
        topic="AML enforcement",
        full_article="With fewer than four months before Australia's Tranche 2 AML/CTF regime takes effect on 1 July 2026, a Law Council of Australia survey has found that 38 per cent of legal practitioners self-report as unprepared for their incoming obligations under the *Anti-Money Laundering and Counter-Terrorism Financing Act 2006* as amended — a finding that carries direct implications for AUSTRAC's supervisory posture and for the financial institutions that rely on law firms as professional intermediaries.\n\nThe delay in extending Australia's AML/CTF framework to designated non-financial businesses and professions — lawyers, accountants, real estate agents and trust and company service providers — has been a long-running source of friction with the Financial Action Task Force. Australia's 2015 mutual evaluation and its subsequent follow-up assessments repeatedly flagged the DNFBP gap as a material vulnerability, particularly given the documented use of legal structures in trade-based money laundering and proceeds-of-crime concealment. The 2026 commencement date, legislated through the *AML/CTF Amendment Act 2024*, represents the end of a patience that regulators and peer jurisdictions had begun to exhaust.\n\nThe Law Council data reveal where the capability deficit is concentrated. AML/CTF program drafting, source-of-wealth verification methodology and the precise identification of customer-engagement triggers — the transactional thresholds and service types that activate due-diligence obligations — are the three areas practitioners find most challenging. Each reflects a structural difference between legal practice and the financial sector: law firms have rarely maintained the systematic onboarding controls, risk-rating frameworks or suspicious matter reporting workflows that banks have refined over two decades of AUSTRAC oversight. The SMR obligation in particular requires a cultural shift, given the profession's deep conditioning around legal professional privilege and client confidentiality, boundaries that the amended legislation addresses but does not entirely dissolve.\n\nFor MLROs at correspondent banks and institutional lenders, the survey data are operationally relevant. A legally-acting counterpart that cannot articulate its own source-of-wealth methodology or confirm AML program status represents a gap in the broader financial ecosystem's defence. Institutions conducting enhanced due diligence on professional-services clients may need to recalibrate their third-party risk assessments ahead of July.\n\nThe acceleration of capability uplift programmes — by the Law Council itself, by specialist compliance providers and by AUSTRAC through its guidance pipeline — suggests the sector is mobilising, but the four-month window is narrow. Regulators seldom extend grace periods to entire professions on the basis of self-reported unreadiness; the more instructive precedent is that early enforcement action tends to be targeted, visible and intended to concentrate minds across a cohort.",
    ),
    NewsItem(
        date="2026-02-12",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Australia announces tighter Russian sanctions implementation",
        summary=(
            "DFAT announced expanded designated entities under Australia's Russia sanctions "
            "regime. New entries focused on energy-trading proxies. Reporting entities required "
            "to refresh screening lists within 14 days; AUSTRAC reminder issued on related SMR "
            "obligations."
        ),
        source="DFAT / Australian Government",
        url="https://www.dfat.gov.au",
        topic="Sanctions / Geopolitics",
        full_article="The Australian Department of Foreign Affairs and Trade on 12 February 2026 expanded its list of designated persons and entities under the *Autonomous Sanctions Act 2011*, adding a tranche of energy-trading proxies linked to Russia's sanctions-evasion infrastructure — a move that immediately triggers mandatory screening obligations for Australia's estimated 15,000 AUSTRAC-regulated reporting entities.\n\nThe expansion sits within a broader pattern of Western autonomous sanctions convergence. Since 2022, Australia has progressively aligned its Russia designations with measures adopted by the EU, UK Office of Financial Sanctions Implementation, and the US Office of Foreign Assets Control, though Australian law operates on a distinct statutory footing. Critically, the *Autonomous Sanctions Regulations 2011* prohibit both dealing with designated entities and making assets available to them, with criminal penalties of up to ten years' imprisonment. AUSTRAC's concurrent reminder reinforces that where a regulated entity identifies a nexus to a designated party, a Suspicious Matter Report under section 41 of the *Anti-Money Laundering and Counter-Terrorism Financing Act 2006* is required — not merely a sanctions compliance file note.\n\nFor MLROs at authorised deposit-taking institutions and remittance dealers, the 14-day screening refresh deadline is operationally tight. Compliance teams should prioritise reviewing correspondent banking relationships, commodity trade finance exposures, and any counterparties in jurisdictions flagged by FATF's Recommendation 7 commentary as high-risk for sanctions circumvention, including intermediary hubs in the Gulf, Central Asia, and Southeast Asia. The energy-proxy designation pattern — shell structures layered through third-country trading companies — mirrors typologies documented in the FATF *Report on Countering Proliferation Financing* (2021) and aligns with intelligence shared through the Egmont Group.\n\nFund managers and superannuation trustees holding indirect Russian energy exposure through listed vehicles also face a due-diligence obligation that is frequently underestimated; beneficial ownership lookthrough remains a regulatory expectation regardless of the listed-market wrapper.\n\nThe AUSTRAC SMR reminder carries a specific supervisory signal: the regulator is unlikely to treat delayed reporting as a purely administrative lapse in the current geopolitical environment. Entities that self-identify screening gaps proactively and document remediation steps will be materially better positioned in any forthcoming examination. With Australia's FATF mutual evaluation cycle progressing, enforcement visibility in the sanctions-AML interface will only intensify through the remainder of 2026.",
    ),
    # ---------------- Wolfsberg Group ----------------
    NewsItem(
        date="2026-04-15",
        jurisdiction="All jurisdictions",
        title="Wolfsberg Group: updated Statement on AML/CTF Effectiveness",
        summary=(
            "Updated Wolfsberg Statement on Effectiveness emphasises outcomes-based AML "
            "measurement over input-based controls. New guidance on integrating AI/ML in "
            "TM scenarios while preserving explainability. Aligns with FATF Recommendation 1 "
            "RBA expectations."
        ),
        source="Wolfsberg Group",
        url="https://www.wolfsberg-principles.com/publications",
        topic="AML enforcement",
        full_article="The Wolfsberg Group's updated Statement on Effectiveness reflects an evolution that the major banks driving the Group have been signalling for several years. The shift from input-based AML measurement (controls in place, alerts generated, files reviewed) to outcomes-based measurement (illicit-flow disruption, prosecution-relevant intelligence) aligns the global standard with the FATF's revised Recommendation 1 risk-based approach guidance.\n\nThe operational implications are significant. Banks have historically reported on AML controls as a list of activities — number of alerts triaged, percentage of alerts dispositioned within service-level expectations, number of STRs filed. The Wolfsberg-recommended outcomes-based reporting requires correlating compliance activity to enforcement outcomes — a much harder data exercise that depends on FIU and law-enforcement feedback that has historically been slow or unavailable.\n\nThe integration of AI/ML in transaction monitoring is treated explicitly. The Statement permits — and effectively encourages — model-based detection in alert generation, provided that explainability is preserved at the alert-disposition stage. This validates what major banks have been deploying through 2024-2025 and addresses the supervisor concern that black-box models could mask both false-positive overload and missed cases.\n\nThe Statement is non-binding but consequential. Wolfsberg principles set the de facto operating standard for the major correspondent banks — and through correspondent-relationship cascades, the standard for thousands of smaller institutions globally. Implementation gaps will increasingly be flagged by correspondent banks as a relationship risk, not just a regulatory one.",
    ),
    NewsItem(
        date="2026-03-10",
        jurisdiction="All jurisdictions",
        title="Wolfsberg Group: refreshed Anti-Bribery and Corruption Compliance Programme guidance",
        summary=(
            "Refreshed ABC Compliance Programme guidance reflecting recent corruption-typology "
            "trends including private-sector bribery in trade flows, public-procurement-corruption "
            "investments in real estate (relevant to AU Tranche 2), and beneficial-owner-opacity "
            "patterns."
        ),
        source="Wolfsberg Group",
        url="https://www.wolfsberg-principles.com/publications",
        topic="AML enforcement",
        full_article="The Wolfsberg Group published refreshed Anti-Bribery and Corruption Compliance Programme guidance on 10 March 2026, updating its canonical framework to address three converging typology patterns: private-sector bribery embedded within trade flows, proceeds of public-procurement corruption channelled into real estate, and the persistent use of opaque beneficial-ownership structures to layer corrupt funds. The timing is deliberate. Regulators across multiple jurisdictions are simultaneously tightening expectations, and the guidance effectively functions as an industry benchmark that supervisors routinely reference when assessing the adequacy of institutional controls.\n\nThe original Wolfsberg ABC guidance, first published in 2011 and subsequently refined, emerged against a backdrop of coordinated multi-jurisdictional enforcement — the US Foreign Corrupt Practices Act, the UK Bribery Act 2010, and the OECD Anti-Bribery Convention forming the primary legislative architecture. Since then, enforcement has migrated beyond the traditional defence, energy and infrastructure sectors. Investigators and financial intelligence units increasingly document corruption proceeds moving through commodity trade-finance structures, where inflated invoicing or fictitious services payments obscure bribe flows within otherwise routine commercial transactions. The updated guidance engages directly with that shift, filling a gap that earlier iterations addressed only obliquely.\n\nThe real estate typology is particularly significant for Australian compliance professionals. Tranche 2 of Australia's AML/CTF Act reforms — long delayed but now legislated — will bring real-estate agents, lawyers and accountants within the regime's scope, bringing Australia closer to alignment with FATF Recommendation 22. The Wolfsberg paper's treatment of public-procurement proceeds laundered through property acquisitions provides correspondent and transaction-banking teams with documented typology support they can incorporate into business-wide risk assessments and trigger-based transaction monitoring scenarios. For institutions with cross-border real estate lending or trust and corporate service exposures, the guidance also reinforces expectations around beneficial-owner verification consistent with FATF Recommendation 10 and domestic Customer Due Diligence rules — including MAS Notice 626 for Singapore-regulated entities and the UK's Money Laundering Regulations 2017 as amended.\n\nFor MLROs reviewing internal ABC and AML programme integration, the guidance raises a structural question that supervisors are likely to pose with greater frequency: whether anti-bribery controls and financial-crime compliance frameworks operate in genuinely coordinated silos or remain administratively separate in ways that produce intelligence blind spots. Institutions that treat the two disciplines as interchangeable in risk-assessment methodology, rather than complementary but distinct, may find that position difficult to sustain under the next examination cycle.",
    ),

    # ---------------- Egmont Group ----------------
    NewsItem(
        date="2026-04-04",
        jurisdiction="All jurisdictions",
        title="Egmont Group: 2025 Annual Trends Report — investment scams dominate",
        summary=(
            "Egmont 2025 Annual Trends Report (released April 2026): investment scams now the "
            "top global ML predicate by victim-loss volume. AUD-, USD-, EUR-denominated mule "
            "networks span 40+ jurisdictions. Egmont coordinated 1,247 cross-border information "
            "exchanges in 2025 — up 31% YoY."
        ),
        source="Egmont Group",
        url="https://egmontgroup.org/publications",
        topic="Scams / Fraud trends",
        full_article="The Egmont Group's 2025 Annual Trends Report identifies investment scams as the dominant global money-laundering predicate by victim-loss volume — a designation that reflects both the volume of underlying criminal activity and the cross-border, multi-jurisdiction nature of the layering networks. AUD-, USD-, and EUR-denominated mule networks are documented across more than 40 jurisdictions, with significant Asia-Pacific and Eastern European concentrations.\n\nThe report's most operationally significant finding is the 31% year-on-year increase in cross-border information-sharing exchanges through Egmont channels — to 1,247 in 2025. The growth reflects both the scale of cross-border criminal activity and the maturation of inter-FIU cooperation post-FATF Recommendation 40 emphasis. APAC FIUs (STRO, JFIU, FIED, AUSTRAC) feature prominently in the exchange volume.\n\nThe implications for reporting institutions are downstream but real. The Egmont network operates at the FIU layer, but the typology intelligence it surfaces is increasingly fed back to reporting entities through national bulletins and supervisory engagement. The Q1 2026 BNM typology bulletin on investment-scam mules is partly a downstream product of Egmont information sharing about Asian-corridor scam networks.\n\nFor institutions, the takeaway is that mule-detection and scam-victim recognition are no longer optional capabilities. The supervisory bar is rising in parallel with the underlying criminal sophistication, and operational uplift in this area is now an enforcement-priority area across the major APAC FIUs.",
    ),
    NewsItem(
        date="2026-02-25",
        jurisdiction="All jurisdictions",
        title="Egmont Group: typology paper on virtual asset money laundering",
        summary=(
            "Egmont typology paper on VA-related ML covering: mixer / tumbler usage, cross-VASP "
            "layering, NFT wash trading, RWA-tokenisation abuse. Reference for VASPs and "
            "supervising authorities; also relevant to traditional banks with VASP-customer "
            "exposure."
        ),
        source="Egmont Group",
        url="https://egmontgroup.org/publications",
        topic="Crypto / VASP",
        full_article="The Egmont Group's Financial Intelligence Units have published a typology paper cataloguing money laundering methodologies specific to virtual assets, providing FIUs, supervisory authorities and compliance functions with an updated reference framework at a moment when FATF's ongoing monitoring of Recommendation 15 implementation reveals persistent gaps across member jurisdictions.\n\nThe paper arrives against a backdrop of uneven progress on the Travel Rule, which FATF first articulated in its 2019 guidance and subsequent updates to Recommendation 16. While jurisdictions including Singapore, the European Union under MiCA's Transfer of Funds Regulation, and the United Kingdom have enacted operative Travel Rule regimes, a substantial portion of FATF's membership continues to lag on licensing and supervisory infrastructure. That regulatory unevenness has, in the Egmont paper's framing, created arbitrage conditions that facilitate the layering techniques it documents.\n\nThe typologies identified span four principal methodologies. Mixer and tumbler usage—where transaction graphs are deliberately obfuscated through pooling or zero-knowledge protocols—remains the most operationally mature, with FIUs reporting increased use of privacy-preserving layer-two solutions that complicate blockchain analytics. Cross-VASP layering, exploiting jurisdictional seams where originator information degrades or disappears entirely in violation of Travel Rule requirements, reflects directly the implementation deficiencies FATF has identified in successive mutual evaluation reports. NFT wash trading as a value-transfer mechanism presents particular challenges: thin secondary markets, subjective valuation, and the absence of standardised suspicious transaction indicators in most national AML/CFT frameworks mean that detection relies heavily on behavioural analytics rather than rule-based controls. The paper's treatment of real-world asset tokenisation abuse is arguably the most forward-looking section; as tokenised funds, real estate and commodities scale, the integration risk of embedding illicit value into otherwise legitimate instruments demands attention from both VASP supervisors and prudential regulators overseeing traditional institutions holding tokenised assets.\n\nFor compliance officers at correspondent banks and institutional brokers with VASP counterparty exposure, the paper functions as a de facto risk typology library that should inform customer risk assessment methodologies and suspicious matter reporting thresholds under applicable frameworks—whether Australia's AML/CTF Act, Hong Kong's OSCO, or the EU's AMLD6 transpositions.\n\nThe practical utility of Egmont typology papers has historically depended on whether national FIUs translate them into updated red-flag guidance. Given the pace of product innovation in decentralised finance, the interval between this publication and any resulting supervisory guidance will itself be a measure of institutional responsiveness.",
    ),

    # ---------------- FATF ----------------
    NewsItem(
        date="2026-04-25",
        jurisdiction="All jurisdictions",
        title="FATF Plenary outcomes (April 2026): updated grey-list, focus on RWA AML",
        summary=(
            "FATF April 2026 Plenary updated the increased-monitoring (grey) list. Strategic-"
            "deficiency removals: two jurisdictions exited. New focus areas: real-world-asset "
            "tokenisation AML standards, beneficial-ownership transparency for trusts. APAC "
            "implications: relevant to MAS Project Guardian, HK SFC RWA sandbox."
        ),
        source="FATF",
        url="https://www.fatf-gafi.org/en/publications.html",
        topic="AML enforcement",
        full_article='The FATF April 2026 Plenary\'s outcomes include two consequential developments for APAC institutions: the updated grey-list and the new strategic focus on real-world-asset (RWA) tokenisation AML standards. The grey-list revision saw two jurisdictions exit increased monitoring after multi-year remediation, while no APAC jurisdictions were added.\n\nThe RWA tokenisation focus is the more substantively interesting development. As tokenised investment-grade bonds, real estate, and trade finance instruments scale through Singapore\'s Project Guardian, Hong Kong\'s SFC sandbox, and Australia\'s ASIC innovation hub, the AML perimeter questions are converging on FATF guidance. The Plenary commissioned a typology paper on RWA-related ML, expected H2 2026, with input from APAC FIUs.\n\nThe beneficial-ownership transparency item is the third notable development. Recommendation 24 implementation review across APAC rated Singapore, Hong Kong, and Australia as "largely compliant," with Malaysia at "partially compliant" and a remediation roadmap. The differential ratings will translate into supervisory expectations on UBO verification at reporting institutions in each jurisdiction — particularly relevant for Malaysian banks operating in cross-border corporate-structure flows.\n\nThe 2026 grey-list outcome is consequential for SG, HK, and MY in a different way: their proximity to grey-listed Asian jurisdictions creates ongoing customer-due-diligence overhead. Reporting institutions in the major APAC financial centres typically have material customer exposure to grey-listed jurisdictions, and supervisory expectations on EDD for those flows will not relax.',
    ),
    NewsItem(
        date="2026-03-08",
        jurisdiction="All jurisdictions",
        title="FATF: revised Recommendation 24 implementation review for APAC",
        summary=(
            "FATF released its review of Recommendation 24 (beneficial ownership transparency) "
            "implementation across APAC. Singapore, Hong Kong, and Australia rated 'largely "
            "compliant'; Malaysia rated 'partially compliant' with remediation roadmap. "
            "Industry implications: continued tightening of UBO verification expectations."
        ),
        source="FATF",
        url="https://www.fatf-gafi.org/en/publications/Mutualevaluations.html",
        topic="AML enforcement",
        full_article='FATF\'s March 2026 regional implementation review finds three of the four largest APAC financial centres meeting most Recommendation 24 obligations on beneficial ownership transparency, while Malaysia\'s partial compliance rating triggers a formal remediation roadmap—a designation that carries tangible correspondent banking and market access consequences if left unresolved within the standard two-year window.\n\nThe review arrives against a backdrop of sustained FATF pressure on ultimate beneficial owner (UBO) registries following the 2022 revisions to Recommendation 24, which tightened the definition of beneficial ownership to a 10% threshold in high-risk scenarios and placed greater obligations on competent authorities to verify—not merely collect—ownership data. Singapore\'s Corporate Beneficial Ownership framework under the Companies Act and MAS Notice SFA04-N02, Hong Kong\'s Significant Controllers Register regime, and Australia\'s reforms under the *Anti-Money Laundering and Counter-Terrorism Financing Act 2006* have all been assessed as broadly aligned with those strengthened standards, though each jurisdiction received specific observations on nominee shareholder disclosure and timeliness of registry updates.\n\nFor compliance functions operating across the region, the differentiated ratings have immediate operational weight. Firms with Malaysian counterparties or subsidiaries will face heightened scrutiny of their own UBO verification processes; under FATF\'s risk-based approach, a partially compliant jurisdiction justifies enhanced due diligence protocols and more frequent refresh cycles on beneficial ownership data. Correspondent banks with exposure to Malaysian financial institutions should review whether existing risk appetite statements and de-risking thresholds require recalibration, particularly given ongoing Basel Committee guidance on correspondent banking relationships.\n\nMalaysia\'s remediation roadmap is understood to centre on three deficiencies: inconsistent enforcement of registry accuracy obligations, gaps in the treatment of foreign-registered entities operating domestically, and limited inter-agency data sharing between the Companies Commission of Malaysia and Bank Negara Malaysia. Kuala Lumpur has historically moved with reasonable speed on FATF remediation—its 2014 Mutual Evaluation follow-up was completed within the standard cycle—but the scope of structural reforms implied here is more substantive than previous rounds.\n\nThe broader signal for APAC compliance professionals is directional: FATF\'s regional focus on Recommendation 24 implementation suggests that UBO verification will remain an examination priority in forthcoming MAS thematic reviews and AUSTRAC industry guidance, with the bar for "adequate" customer due diligence continuing to rise irrespective of a firm\'s domestic jurisdiction rating.',
    ),

    # ---------------- ASIFMA / banking associations ----------------
    NewsItem(
        date="2026-04-22",
        jurisdiction="All jurisdictions",
        title="ASIFMA: APAC industry consultation on AI in financial-crime compliance",
        summary=(
            "ASIFMA closed industry consultation on AI in financial-crime compliance covering "
            "AML, sanctions, fraud. Common asks: regulator-aligned model-explainability standards, "
            "shared-utility for sanctions screening, recognition of LLM-assisted STR drafting "
            "as legitimate compliance practice."
        ),
        source="ASIFMA",
        url="https://www.asifma.org",
        topic="Regulatory tech",
        full_article='The Asia Securities Industry & Financial Markets Association closed a cross-jurisdictional industry consultation on 22 April 2026 examining the deployment of artificial intelligence across financial-crime compliance functions, including anti-money laundering surveillance, sanctions screening, and fraud detection. The exercise, drawing participation from institutions spanning multiple APAC booking centres, crystallised three discrete asks that now sit with regulators: standardised model-explainability requirements aligned with supervisory expectations, a shared-utility model for sanctions screening, and formal recognition of large-language-model-assisted suspicious transaction report drafting as a legitimate compliance practice rather than an unreviewed automation risk.\n\nThe consultation arrives at a moment when APAC supervisors hold materially divergent positions on algorithmic decision-making in compliance contexts. The Monetary Authority of Singapore\'s Notice MAS 626 and its accompanying Guidelines on Environmental Risk Management have established a precedent for outcome-based supervisory expectations, but no equivalent framework yet governs explainability requirements for transaction-monitoring models specifically. Hong Kong\'s AMLO and the broader Organised and Serious Crimes Ordinance impose obligations on institutions to demonstrate the adequacy of their systems, yet neither the HKMA nor the SFC has issued binding guidance on what constitutes adequate documentation of an AI-generated alert. FATF Recommendation 16 and the broader risk-based approach guidance acknowledge technology neutrality in principle, while stopping short of endorsing specific architectures.\n\nFrom an operational risk perspective, the shared-utility proposal for sanctions screening merits particular scrutiny. Pooling screening logic across competing institutions raises questions under data-protection regimes in several jurisdictions and introduces concentration risk if a single algorithmic error propagates simultaneously across member firms. Proponents counter that current fragmentation produces inconsistent name-matching quality against OFAC, UN, and MAS consolidated lists, generating both false-positive fatigue and genuine miss risk. A well-governed utility, subject to independent model validation and supervisory oversight, could reduce that variance.\n\nThe LLM-STR question is arguably the most consequential for day-to-day compliance operations. Regulators including AUSTRAC, under the AML/CTF Act 2006, and the MAS require STRs to reflect genuine human analysis; the industry position is that LLM assistance in drafting, with mandatory human sign-off, satisfies that threshold. Whether supervisors agree will depend substantially on how they interpret the "know your customer" and "reasonable grounds" standards embedded in existing legislation.\n\nRegulatory responses are likely to be incremental rather than definitive, with guidance notes preceding any rule changes. Institutions would be prudent to document current AI-assisted workflows with the same rigour they would apply to any material change in compliance methodology, regardless of whether binding standards exist yet.',
    ),
    NewsItem(
        date="2026-03-15",
        jurisdiction="All jurisdictions",
        title="ABS Singapore launches APAC fraud-data sharing pilot",
        summary=(
            "Association of Banks in Singapore announced pilot of APAC fraud-data sharing "
            "extending the existing SG framework to selected HK and AU banks. Mule-account "
            "intelligence and sanctions-evasion-typology data shared near real-time under "
            "MAS-approved privacy framework."
        ),
        source="ABS Singapore",
        url="https://www.abs.org.sg",
        topic="Regulatory tech",
        full_article="The Association of Banks in Singapore announced on 15 March 2026 the launch of a cross-border fraud-data sharing pilot extending Singapore's established interbank intelligence infrastructure to selected institutions in Hong Kong and Australia. The immediate implication is that mule-account indicators and sanctions-evasion typologies will circulate near real-time across three jurisdictions with materially different legal regimes, creating both an operational uplift for participating financial institutions and a compliance architecture that others in the region will be expected to emulate.\n\nSingapore's domestic framework already operates under the COSMIC platform, the Collaborative Sharing of Money Laundering/Terrorism Financing Information and Cases initiative codified under amendments to the Monetary Authority of Singapore Act. That structure permitted prescribed financial institutions to share customer information without breaching banking secrecy obligations under the Banking Act, provided MAS-defined thresholds and safeguards were met. The pilot now pushes that logic outward, requiring alignment with Hong Kong's Personal Data (Privacy) Ordinance and the Organized and Serious Crimes Ordinance provisions governing information disclosure, as well as Australia's Anti-Money Laundering and Counter-Terrorism Financing Act 2006 and the AUSTRAC-supervised safe-harbour provisions for tipping-off risk.\n\nFor MLROs and heads of financial crime compliance at participating institutions, the practical weight falls on three areas. First, data-residency obligations differ across all three jurisdictions, meaning the technical architecture of the shared ledger or API layer must satisfy each regulator's localisation expectations simultaneously. Second, sanctions-evasion typology data carries heightened sensitivity: sharing designations or near-matches across borders implicates FATF Recommendation 40 on international information exchange and may engage correspondent-banking obligations under each institution's own licence conditions. Third, mule-account intelligence shared near real-time raises tipping-off exposure unless domestic carve-outs explicitly extend to cross-border disclosures — an area where Australian and Hong Kong statute has historically been narrower than Singapore's reformed framework.\n\nABS's choice to anchor the pilot within a MAS-approved privacy framework is deliberate regulatory sequencing; it positions Singapore as the governance hub and creates a template that APAC jurisdictions without equivalent domestic infrastructure may eventually adopt by accession rather than independent legislation. Whether HKMA and AUSTRAC publish corresponding supervisory guidance — or whether the pilot remains a bilateral arrangement dressed as multilateral — will determine whether this becomes a durable regional standard or a well-intentioned proof of concept constrained by the limits of jurisdictional reciprocity.",
    ),
]


# Industry RSS feeds — broader compliance / fintech / regtech publications.
# Most aren't jurisdiction-specific, so live items get tagged "All jurisdictions".
# URLs are best-effort and may need periodic verification — the app handles
# feed failures gracefully (shows status, continues with curated items).
NEWS_RSS_FEEDS: list[tuple[str, str, str]] = [
    # (source label, url, default topic)

    # ---- APAC-focused authoritative sources ----
    ("Wolfsberg Group publications", "https://www.wolfsberg-principles.com/feed", "AML enforcement"),
    ("Egmont Group news", "https://egmontgroup.org/feed/", "AML enforcement"),
    ("APG news", "https://www.apgml.org/news/index.aspx?type=rss", "AML enforcement"),

    # ---- International standard-setters ----
    ("FATF news", "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.rss", "AML enforcement"),
    ("BIS press releases", "https://www.bis.org/list/press_releases/index.rss", "Regulatory tech"),
    ("FSB news", "https://www.fsb.org/feed/", "Regulatory tech"),
    ("IMF news", "https://www.imf.org/external/rss/en/news.aspx", "Regulatory tech"),
    ("OECD news", "https://www.oecd.org/news/news.xml", "Regulatory tech"),
    ("World Bank news", "https://www.worldbank.org/en/news/rss", "Regulatory tech"),
    ("UNODC news", "https://www.unodc.org/unodc/index.rss", "AML enforcement"),

    # ---- Banking / industry associations ----
    ("HKAB (Hong Kong Association of Banks)", "https://www.hkab.org.hk/feed", "Industry M&A"),
    ("ASIFMA news", "https://www.asifma.org/feed/", "Regulatory tech"),
    ("Australian Banking Association", "https://www.ausbanking.org.au/feed/", "Fintech / Digital banking"),
    ("ABS (Association of Banks in Singapore)", "https://www.abs.org.sg/feed", "Fintech / Digital banking"),
    ("ISDA news", "https://www.isda.org/feed/", "Regulatory tech"),
    ("ICMA news", "https://www.icmagroup.org/feed/", "Regulatory tech"),

    # ---- UK / US authoritative regulators ----
    ("FCA UK news", "https://www.fca.org.uk/news/rss.xml", "AML enforcement"),
    ("Bank of England news", "https://www.bankofengland.co.uk/rss/news", "Regulatory tech"),
    ("US SEC press releases", "https://www.sec.gov/news/pressreleases.rss", "AML enforcement"),
    ("FinCEN news", "https://www.fincen.gov/feed/news_release", "AML enforcement"),
    ("OFAC recent actions", "https://ofac.treasury.gov/recent-actions.rss", "Sanctions / Geopolitics"),
    ("US DOJ news", "https://www.justice.gov/feeds/news.xml", "AML enforcement"),
    ("CFTC press releases", "https://www.cftc.gov/PressRoom/PressReleases/rss", "Regulatory tech"),

    # ---- General compliance / fintech / regtech ----
    ("FinExtra", "https://www.finextra.com/rss/headlines.aspx", "Fintech / Digital banking"),
    ("RegTech Analyst", "https://member.fintech.global/feed/", "Regulatory tech"),
    ("ACAMS Today", "https://www.acamstoday.org/feed/", "AML enforcement"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "Crypto / VASP"),
    ("The Banker", "https://www.thebanker.com/rss/news", "Fintech / Digital banking"),

    # ---- APAC regulators (best-effort RSS endpoints) ----
    ("RBI India press releases", "https://rbi.org.in/Scripts/Rss.aspx?Cat=PressRelease", "AML enforcement"),
    ("RBI India notifications", "https://rbi.org.in/Scripts/Rss.aspx?Cat=Notification", "AML enforcement"),
    ("SEBI India news", "https://www.sebi.gov.in/sebirss.xml", "AML enforcement"),
    ("BOT (Bank of Thailand) news", "https://www.bot.or.th/en/news-and-media/rss.html", "AML enforcement"),
    ("SEC Thailand news", "https://www.sec.or.th/EN/Pages/News/RSS.aspx", "AML enforcement"),
    ("BSP Philippines media", "https://www.bsp.gov.ph/MediaCorner/Pages/news.aspx?feed=rss", "AML enforcement"),
    ("Bank Indonesia news", "https://www.bi.go.id/en/publikasi/ruang-media/news/rss", "AML enforcement"),
    ("OJK Indonesia news", "https://www.ojk.go.id/en/berita-dan-kegiatan/siaran-pers/rss.aspx", "AML enforcement"),
    ("FSA Japan news", "https://www.fsa.go.jp/en/news/index.rss", "AML enforcement"),
    ("Bank of Japan press", "https://www.boj.or.jp/en/announcements/release_2025/rss.xml", "AML enforcement"),
    ("FSC Korea news", "https://www.fsc.go.kr/eng/no010102/rss", "AML enforcement"),
    ("BoK (Bank of Korea) news", "https://www.bok.or.kr/eng/main/contents.do?menuNo=400060&rss=true", "AML enforcement"),
    ("FSC Taiwan news", "https://www.fsc.gov.tw/en/rss.xml", "AML enforcement"),
    ("SBV (State Bank of Vietnam)", "https://www.sbv.gov.vn/webcenter/portal/en/home/rss/news", "AML enforcement"),
    ("CSRC China news", "http://www.csrc.gov.cn/csrc_en/c102030/common_list.shtml?channelId=24009dee9f1c4b22a1d22f55f7c7a8df", "AML enforcement"),
    ("PBoC China press", "http://www.pbc.gov.cn/en/3688112/3688172/index.rss", "AML enforcement"),
    ("Bangladesh Bank news", "https://www.bb.org.bd/feed/news.xml", "AML enforcement"),
    ("RMA Bhutan news", "https://www.rma.org.bt/feed/news", "AML enforcement"),
    ("RBNZ New Zealand news", "https://www.rbnz.govt.nz/feeds/news", "AML enforcement"),
    ("FMA New Zealand news", "https://www.fma.govt.nz/feed/news/", "AML enforcement"),
    ("FMU Pakistan news", "https://www.fmu.gov.pk/feed", "AML enforcement"),

    # ---- APAC industry publications ----
    ("Asian Banking & Finance", "https://asianbankingandfinance.net/feeds/all", "Fintech / Digital banking"),
    ("Compliance Asia / Asia Risk", "https://www.risk.net/asia-risk/feed", "Regulatory tech"),
    ("Nikkei Asia (compliance)", "https://asia.nikkei.com/rss", "Industry M&A"),
    ("Asia Crypto Today", "https://www.asiacryptotoday.com/feed/", "Crypto / VASP"),
    ("Fintech News Singapore", "https://fintechnews.sg/feed/", "Fintech / Digital banking"),
    ("Fintech News Hong Kong", "https://fintechnews.hk/feed/", "Fintech / Digital banking"),
    ("Fintech News Malaysia", "https://fintechnews.my/feed/", "Fintech / Digital banking"),
    ("Fintech News Australia", "https://fintechnews.com.au/feed/", "Fintech / Digital banking"),

    # ---- APAC mainstream business / general-news feeds, added 2026-05 for
    # regional variety in the daily audio briefing. The keyword-classifier
    # in scripts/generate_articles.py filters for AML/compliance relevance,
    # so off-topic items don't reach the podcast script — these feeds boost
    # the candidate pool so the per-day pick has real choice instead of
    # cycling the same 4-5 specialist sources.
    #
    # NOTE on Regulation Asia: regulationasia.com would be the ideal
    # source for this product but blocks all bot User-Agents with HTTP
    # 403 (Cloudflare anti-scraping). Their RSS is paywalled / requires
    # subscription API access. Not ingested. If a subscription is added
    # later, swap a real source-URL in here.
    # ---- ----
    ("SCMP business (Hong Kong)", "https://www.scmp.com/rss/2/feed", "Industry M&A"),
    ("Channel News Asia business (Singapore)", "https://www.channelnewsasia.com/rssfeeds/8395986", "Industry M&A"),
    ("Bangkok Post business (Thailand)", "https://www.bangkokpost.com/rss/data/business.xml", "AML enforcement"),
]


# Shared User-Agent for all feed-fetching code (lib/news, lib/horizon,
# scripts/generate_articles, scripts/preflight). A polite "AML-Agents/0.1"
# string was rejected by several APAC feeds (e.g. Bangkok Post returns
# 307 to a JS challenge), so we use a minimal Safari-style UA that the
# anti-bot front-ends accept. Centralised so future UA changes touch one
# place, not five.
FEED_USER_AGENT = "Mozilla/5.0 AppleWebKit/605.1.15 (KHTML, like Gecko)"


_NEWS_FEED_CACHE: dict[str, tuple[float, list[NewsItem]]] = {}
_NEWS_TTL_SECONDS = 1800  # 30 min


def fetch_news_feeds(force_refresh: bool = False) -> tuple[list[NewsItem], dict[str, str]]:
    """Pull latest items from industry RSS feeds. Returns (items, status_per_feed)."""
    if not FEEDPARSER_AVAILABLE:
        return [], {"_overall": "feedparser not installed"}

    now = time.time()
    cache_key = "news"
    if not force_refresh and cache_key in _NEWS_FEED_CACHE:
        ts, cached = _NEWS_FEED_CACHE[cache_key]
        if now - ts < _NEWS_TTL_SECONDS:
            return cached, {"_cache": f"cached {int((now - ts) / 60)} min ago"}

    items: list[NewsItem] = []
    statuses: dict[str, str] = {}

    for label, url, default_topic in NEWS_RSS_FEEDS:
        try:
            # Use a Safari-like UA so anti-bot redirects (e.g. Bangkok Post,
            # Cloudflare-fronted feeds) don't swallow our requests with a
            # 307 to a JS challenge. Tested 2026-05: "AML-Agents/0.1" was
            # rejected by several APAC feeds; this minimal Mozilla string
            # is accepted everywhere we ingest.
            parsed = feedparser.parse(url, request_headers={"User-Agent": FEED_USER_AGENT})
            if parsed.bozo and parsed.bozo_exception:
                statuses[label] = f"error: {type(parsed.bozo_exception).__name__}"
                continue
            count = 0
            for entry in parsed.entries[:5]:
                title = entry.get("title", "(no title)")
                summary = entry.get("summary", entry.get("description", ""))
                import re as _re
                summary = _re.sub(r"<[^>]+>", "", summary)[:400]
                published = entry.get("published", entry.get("updated", "")) or ""
                date_str = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pp = entry.published_parsed
                    date_str = f"{pp.tm_year:04d}-{pp.tm_mon:02d}-{pp.tm_mday:02d}"
                elif published:
                    date_str = published[:10]
                else:
                    date_str = "unknown"
                link = entry.get("link", url)
                items.append(NewsItem(
                    date=date_str,
                    jurisdiction="All jurisdictions",
                    title=f"[LIVE] {title}",
                    summary=summary or "(no summary in feed)",
                    source=label,
                    url=link,
                    topic=default_topic,
                ))
                count += 1
            statuses[label] = f"OK ({count} items)"
        except Exception as e:
            statuses[label] = f"error: {type(e).__name__}: {str(e)[:80]}"

    _NEWS_FEED_CACHE[cache_key] = (now, items)
    return items, statuses


# ----------------------------------------------------------------------
# In-memory cache for the generated-articles YAML. The file grows by
# ~50KB/day as the cron appends articles. Streamlit re-runs the whole
# script on every interaction (and after login authenticates). Without
# this cache, each button click after login forced a fresh PyYAML
# deserialise of a 1.3MB+ file on free-tier CPU — observed as a "freeze
# after login" once the accumulated YAML crossed ~1MB.
#
# Keyed on file mtime so the cache invalidates whenever the cron
# auto-commits a new batch and the deployed pod sees a newer file. On a
# given pod-lifetime, the YAML deserialises at most once per cron
# commit, then every subsequent interaction is a dict lookup.
# ----------------------------------------------------------------------
_GENERATED_ARTICLES_CACHE: dict[float, list[NewsItem]] = {}


def _load_generated_articles() -> list[NewsItem]:
    """Load LLM-generated articles from data/generated_articles.yaml.

    Generated by scripts/generate_articles.py on a cron schedule. Returns
    NewsItem-shaped objects with full_article filled in. Empty list if
    the file isn't there yet. Memoised on file mtime — see comment
    above for the freeze-after-login bug this fixes.
    """
    from pathlib import Path as _Path
    import yaml as _yaml
    path = _Path(__file__).parent.parent / "data" / "generated_articles.yaml"
    if not path.exists():
        return []
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []

    cached = _GENERATED_ARTICLES_CACHE.get(mtime)
    if cached is not None:
        return cached

    try:
        with open(path) as f:
            raw = _yaml.safe_load(f) or []
    except Exception:
        # Don't trash the cache on a transient parse failure — let the
        # caller see an empty list and try again next interaction.
        return []
    items: list[NewsItem] = []
    for entry in raw:
        items.append(NewsItem(
            date=entry.get("source_date", entry.get("generated_at", "")[:10]),
            jurisdiction=entry.get("jurisdiction", "All jurisdictions"),
            title=entry.get("title", "(untitled)"),
            summary=entry.get("summary", ""),
            source=entry.get("source_name", "RSS"),
            url=entry.get("source_url", ""),
            topic=entry.get("topic", "AML enforcement"),
            full_article=entry.get("full_article", ""),
        ))
    # Reset on each new mtime so old article-list arrays are gc'd.
    _GENERATED_ARTICLES_CACHE.clear()
    _GENERATED_ARTICLES_CACHE[mtime] = items
    return items


def items_for(
    jurisdiction: str | None = None,
    topic: str | None = None,
    include_live: bool = True,
    force_refresh: bool = False,
) -> tuple[list[NewsItem], dict[str, str]]:
    """Filtered news items, sorted by date desc.

    Combines: curated NEWS_ITEMS + LLM-generated articles (data/generated_articles.yaml)
    + live RSS pulls (cached 30 min).
    """
    static = list(NEWS_ITEMS)
    generated = _load_generated_articles()
    live: list[NewsItem] = []
    statuses: dict[str, str] = {}

    if include_live:
        live, statuses = fetch_news_feeds(force_refresh=force_refresh)

    combined = static + generated + live

    if jurisdiction and jurisdiction != "All jurisdictions":
        combined = [i for i in combined if i.jurisdiction in (jurisdiction, "All jurisdictions")]
    if topic and topic != "All topics":
        combined = [i for i in combined if i.topic == topic]

    return sorted(combined, key=lambda i: i.date, reverse=True), statuses
