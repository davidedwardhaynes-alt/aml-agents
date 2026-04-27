"""Horizon scanning — curated feed of recent regulatory updates per jurisdiction.

For v0, the feed is a static curated list. Production roadmap: pull from
RSS feeds where available (MAS, HKMA, AUSTRAC, BNM all publish news feeds),
plus LLM summarization of regulatory bulletins.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HorizonItem:
    date: str  # YYYY-MM-DD
    jurisdiction: str
    title: str
    summary: str
    source: str
    url: str
    impact: str  # "High" / "Medium" / "Low"


# Curated snapshot of regulatory updates as of late April 2026.
# Real production deployment would refresh this from regulator RSS / news feeds.
HORIZON_ITEMS: list[HorizonItem] = [
    # ---- Singapore ----
    HorizonItem(
        date="2026-04-22",
        jurisdiction="Singapore (STRO)",
        title="MAS issues updated guidance on DPT service providers — VA-related ML risks",
        summary=(
            "Updated guidance for MAS-licensed Digital Payment Token (DPT) service providers on "
            "specific VA-related typologies including mixer exposure, dark-net market provenance, "
            "and the integration of KYT findings into transaction monitoring. Aligns SG with HK SFC "
            "VASP regime expectations. Effective immediately for MAS Notice PSN02 entities."
        ),
        source="MAS",
        url="https://www.mas.gov.sg/news/media-releases",
        impact="High",
    ),
    HorizonItem(
        date="2026-04-08",
        jurisdiction="Singapore (STRO)",
        title="STRO releases 2025 annual STR statistics",
        summary=(
            "Annual statistics show STR volumes up 18% YoY, driven by fintech-sector growth. "
            "Top filing categories: investment scams (28%), unlicensed money lending (14%), "
            "TBML (11%). Crypto-related filings up 41% YoY."
        ),
        source="STRO / Singapore Police Force",
        url="https://www.police.gov.sg/Advisories/Commercial-Crimes/Suspicious-Transaction-Reporting-Office",
        impact="Medium",
    ),
    HorizonItem(
        date="2026-03-15",
        jurisdiction="Singapore (STRO)",
        title="MAS Notice 626 amendments — politically exposed persons",
        summary=(
            "Amended PEP definition to include domestic prominent functions (post-FATF Recommendation 12 "
            "alignment). Effective 1 July 2026 for all MAS-regulated FIs. EDD on domestic PEPs at "
            "onboarding now mandatory."
        ),
        source="MAS",
        url="https://www.mas.gov.sg/regulation/notices/notice-626",
        impact="High",
    ),
    HorizonItem(
        date="2026-02-26",
        jurisdiction="Singapore (STRO)",
        title="FATF mutual evaluation prep — IMF / FATF onsite Q4 2026",
        summary=(
            "Singapore's next FATF mutual evaluation onsite scheduled for Q4 2026. MAS coordinating "
            "national risk assessment update across regulated sectors. Reporting institutions advised "
            "to refresh AML/CFT risk assessment documentation."
        ),
        source="MAS / FATF",
        url="https://www.fatf-gafi.org/en/countries/detail/Singapore.html",
        impact="High",
    ),

    # ---- Hong Kong ----
    HorizonItem(
        date="2026-04-18",
        jurisdiction="Hong Kong (JFIU)",
        title="HKMA guidance on cross-border RMB / CNH AML controls",
        summary=(
            "Updated supervisory expectations on RMB/CNH cross-border flows, particularly mainland CN "
            "counterparty due diligence and pass-through structures. Reinforces 2024 guidance with "
            "specific examples of trade-shell layering patterns. Banks expected to integrate into "
            "TM scenarios within 6 months."
        ),
        source="HKMA",
        url="https://www.hkma.gov.hk/eng/news-and-media/press-releases/",
        impact="High",
    ),
    HorizonItem(
        date="2026-03-29",
        jurisdiction="Hong Kong (JFIU)",
        title="SFC issues VASP enforcement priorities note for 2026",
        summary=(
            "SFC announces 2026 VASP enforcement focus on KYT effectiveness, segregation-of-funds "
            "controls, and adequacy of AML/CTF programs. Following 2024–2025 enforcement actions, "
            "SFC has heightened expectations on Chainalysis/TRM-equivalent screening hop-distance methodology."
        ),
        source="SFC",
        url="https://www.sfc.hk/en/News-and-announcements",
        impact="High",
    ),
    HorizonItem(
        date="2026-03-12",
        jurisdiction="Hong Kong (JFIU)",
        title="JFIU STREAMS upgrade — new submission schema",
        summary=(
            "JFIU announces updated STREAMS reporting schema with additional structured fields for "
            "VA-related STRs (wallet addresses, KYT scores, blockchain). Mandatory effective Jan 2027; "
            "voluntary adoption from Q3 2026."
        ),
        source="JFIU",
        url="https://www.jfiu.gov.hk",
        impact="Medium",
    ),
    HorizonItem(
        date="2026-02-20",
        jurisdiction="Hong Kong (JFIU)",
        title="ICAC public-procurement corruption investigation — industry alert",
        summary=(
            "ICAC investigation into mainland CN-linked public-procurement corruption ring. "
            "Multiple HK-incorporated entities named. Banks and TCSPs advised to review customer "
            "registers for named entities and conduct EDD on UBO chains."
        ),
        source="ICAC + HKMA peer-bank intel sharing",
        url="https://www.icac.org.hk",
        impact="Medium",
    ),

    # ---- Malaysia ----
    HorizonItem(
        date="2026-04-25",
        jurisdiction="Malaysia (FIED)",
        title="BNM typology bulletin — investment scams and money mules (Q1 2026)",
        summary=(
            "BNM publishes updated typology bulletin focused on investment scams routed through "
            "digital banks and crypto exchanges. Mule-account indicators: rapid post-onboarding "
            "velocity spike, inbound from multiple unrelated retail senders, immediate crypto "
            "withdrawal to mixer-tagged wallets. Digital banks specifically targeted."
        ),
        source="BNM FIED",
        url="https://amlcft.bnm.gov.my/typologies",
        impact="High",
    ),
    HorizonItem(
        date="2026-03-30",
        jurisdiction="Malaysia (FIED)",
        title="SC Malaysia — Digital Asset Exchange enforcement update",
        summary=(
            "SC Malaysia announces enforcement action against an unregistered DAE for AML failings. "
            "Reinforces requirement for SC registration and adherence to SC AML/CFT Guidelines. "
            "Existing registered DAEs subject to thematic review in H2 2026."
        ),
        source="Securities Commission Malaysia",
        url="https://www.sc.com.my/regulation/enforcement",
        impact="Medium",
    ),
    HorizonItem(
        date="2026-03-08",
        jurisdiction="Malaysia (FIED)",
        title="BNM digital banking — pilot AML control benchmark study",
        summary=(
            "BNM releases benchmark study on AML control effectiveness across the five digital "
            "banking licensees (Boost, GXBank, AEON, KAF Digital, Sea/YTL). Common themes: e-KYC "
            "control gaps in mule-account detection, low-friction onboarding pressure on TM. "
            "Specific guidance to follow Q3 2026."
        ),
        source="BNM",
        url="https://www.bnm.gov.my/-/digital-bank-licensing-framework",
        impact="High",
    ),
    HorizonItem(
        date="2026-02-15",
        jurisdiction="Malaysia (FIED)",
        title="FIED publishes 2025 annual STR statistics",
        summary=(
            "FIED 2025 statistics: STR volume up 24% YoY. Top sectors: banking (52%), MSB (18%), "
            "DAEs (11%). Common predicate: investment scam (32%), drug trafficking (12%), "
            "1MDB-related (8% — legacy)."
        ),
        source="BNM FIED",
        url="https://www.bnm.gov.my/financial-intelligence-and-enforcement-department",
        impact="Low",
    ),

    # ---- Australia ----
    HorizonItem(
        date="2026-04-26",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AUSTRAC Tranche 2 industry guidance — legal practitioners",
        summary=(
            "AUSTRAC publishes detailed Tranche 2 industry guidance for legal practitioners. "
            "Covers customer-engagement triggers, source-of-wealth diligence in conveyancing, "
            "legal-professional-privilege carve-outs, SMR submission practicalities. Phase 2 "
            "obligations commence 1 July 2026."
        ),
        source="AUSTRAC",
        url="https://www.austrac.gov.au/business/new-to-the-regulated-sector",
        impact="High",
    ),
    HorizonItem(
        date="2026-04-10",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AUSTRAC online wagering — scam-victim mule typology bulletin",
        summary=(
            "Updated typology bulletin on scam-victim mule patterns in online wagering. "
            "Pattern: scam victims deposit to wagering accounts → minimal play → withdraw to "
            "scammer-controlled accounts. AUSTRAC expects wagering operators to detect rapid "
            "deposit-withdraw without play."
        ),
        source="AUSTRAC",
        url="https://www.austrac.gov.au/business/how-comply-and-report-guidance-and-resources",
        impact="High",
    ),
    HorizonItem(
        date="2026-03-22",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AUSTRAC enforcement — gambling sector follow-up",
        summary=(
            "AUSTRAC issues follow-up enforceable undertakings to two regional casinos following "
            "Star/Crown precedent. Specific findings: chip-walking pattern detection gaps, "
            "customer source-of-wealth deficiencies, SMR timing breaches."
        ),
        source="AUSTRAC",
        url="https://www.austrac.gov.au/about-us/news-and-media/media-releases",
        impact="Medium",
    ),
    HorizonItem(
        date="2026-02-28",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="DFAT consolidated sanctions list — significant updates",
        summary=(
            "Substantial update to DFAT consolidated sanctions list reflecting Q1 2026 designations. "
            "New entries focused on Iran / Russia / DPRK proliferation networks. Reporting entities "
            "advised to refresh screening lists immediately."
        ),
        source="DFAT",
        url="https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list",
        impact="High",
    ),
]


def items_for_jurisdiction(jurisdiction: str | None = None) -> list[HorizonItem]:
    """Return items for the given jurisdiction, or all if None."""
    items = sorted(HORIZON_ITEMS, key=lambda i: i.date, reverse=True)
    if jurisdiction is None:
        return items
    return [i for i in items if i.jurisdiction == jurisdiction]
