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
]


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
            parsed = feedparser.parse(url, request_headers={"User-Agent": "AML-Agents/0.1"})
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


def _load_generated_articles() -> list[NewsItem]:
    """Load LLM-generated articles from data/generated_articles.yaml.

    Generated by scripts/generate_articles.py on a cron schedule. Returns NewsItem-shaped
    objects with full_article filled in. Empty list if file not yet created.
    """
    from pathlib import Path as _Path
    import yaml as _yaml
    path = _Path(__file__).parent.parent / "data" / "generated_articles.yaml"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            raw = _yaml.safe_load(f) or []
    except Exception:
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
