"""Horizon scanning — curated + live feed of recent regulatory updates per jurisdiction.

The feed combines two sources:
  - Curated (static) — hand-written items in HORIZON_ITEMS, refreshed manually
  - Live (RSS) — fetched from regulator RSS feeds, cached with TTL

For RSS feeds, we use feedparser which handles RSS 1/2 + Atom + most variants.
Network failures fall through gracefully — live results just empty, curated still shows.

Note: regulator RSS URLs change. The URLs below are best-effort and may need
periodic verification. When in doubt, use the regulator's news landing page URL
and check for an RSS link in the page header.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False


@dataclass(frozen=True)
class HorizonItem:
    date: str  # YYYY-MM-DD
    jurisdiction: str
    title: str
    summary: str
    source: str
    url: str
    impact: str  # "High" / "Medium" / "Low"
    category: str = "Regulatory"  # Regulatory / Enforcement / Industry / Typology / Sanctions


CATEGORIES = ["Regulatory", "Enforcement", "Industry", "Typology", "Sanctions"]


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
        category="Sanctions",
    ),

    # ---------------- Industry news / enforcement / typology additions ----------------
    # Singapore — industry & enforcement news
    HorizonItem(
        date="2026-04-19",
        jurisdiction="Singapore (STRO)",
        title="MAS enforcement: SGD 2.4M penalty against payment institution for AML failings",
        summary=(
            "MAS issued an enforceable undertaking and SGD 2.4M civil penalty against a Singapore-licensed "
            "payment institution for failures in customer risk assessment, transaction monitoring, and "
            "STR timeliness. Senior Compliance Officer accountability cited."
        ),
        source="MAS Enforcement Actions",
        url="https://www.mas.gov.sg/news/enforcement-actions",
        impact="High",
        category="Enforcement",
    ),
    HorizonItem(
        date="2026-04-04",
        jurisdiction="Singapore (STRO)",
        title="ABS publishes guidance on AI use in compliance",
        summary=(
            "Association of Banks in Singapore published industry guidance on the use of LLMs and AI in "
            "compliance functions including STR drafting, alert disposition, and adverse-media review. "
            "Aligns with MAS FEAT principles."
        ),
        source="Association of Banks in Singapore",
        url="https://www.abs.org.sg/",
        impact="Medium",
        category="Industry",
    ),
    HorizonItem(
        date="2026-03-20",
        jurisdiction="Singapore (STRO)",
        title="Typology bulletin: AI-generated voice scams targeting elderly retail customers",
        summary=(
            "STRO and Singapore Police Force flag rising trend of voice-cloning scams targeting "
            "elderly customers. Pattern: AI-cloned family-member voice calls victim, urgent transfer "
            "request to 'help me'. Banks advised to enhance call-back verification on out-of-character "
            "transfers from this demographic."
        ),
        source="STRO / SPF Anti-Scam Centre",
        url="https://www.police.gov.sg/Advisories/Crime/Scams",
        impact="High",
        category="Typology",
    ),
    HorizonItem(
        date="2026-02-12",
        jurisdiction="Singapore (STRO)",
        title="ACAMS Singapore Chapter — annual conference takes place 16-18 May 2026",
        summary=(
            "Annual ACAMS Singapore conference scheduled. Themes include AI in compliance, Tranche 2 "
            "DNFBP onboarding, and FATF mutual evaluation preparation. STRO and MAS representatives "
            "expected to keynote."
        ),
        source="ACAMS Singapore",
        url="https://www.acams.org/en/chapters/singapore",
        impact="Low",
        category="Industry",
    ),

    # Hong Kong — industry & enforcement news
    HorizonItem(
        date="2026-04-21",
        jurisdiction="Hong Kong (JFIU)",
        title="HKMA enforcement: HKD 18M penalty against virtual bank for AML control deficiencies",
        summary=(
            "HKMA imposed a HKD 18M penalty against a HK virtual bank for inadequate transaction-monitoring "
            "rule-set effectiveness, mule-account detection gaps, and STR timeliness. Marks a significant "
            "enforcement signal against the digital-banking cohort. Industry advised to review e-KYC controls."
        ),
        source="HKMA",
        url="https://www.hkma.gov.hk/eng/news-and-media/press-releases/",
        impact="High",
        category="Enforcement",
    ),
    HorizonItem(
        date="2026-04-05",
        jurisdiction="Hong Kong (JFIU)",
        title="HashKey announces tokenisation pilot under SFC sandbox",
        summary=(
            "HashKey Exchange announced a tokenised-RWA (real-world asset) pilot under the SFC regulatory "
            "sandbox, with tokenised investment products targeting professional investors. AML implications "
            "include source-of-wealth verification at higher thresholds."
        ),
        source="SFC / HashKey",
        url="https://www.sfc.hk/en/News-and-announcements",
        impact="Medium",
        category="Industry",
    ),
    HorizonItem(
        date="2026-03-26",
        jurisdiction="Hong Kong (JFIU)",
        title="Typology bulletin: SVF / e-wallet money mule recruitment via job-scam ads",
        summary=(
            "JFIU flags rising pattern of SVF and e-wallet account misuse where victims respond to fake "
            "job ads and provide their account credentials. Stored-value-facility licensees and banks "
            "with linked accounts advised to monitor unusual receive-and-forward patterns."
        ),
        source="JFIU",
        url="https://www.jfiu.gov.hk",
        impact="High",
        category="Typology",
    ),
    HorizonItem(
        date="2026-02-08",
        jurisdiction="Hong Kong (JFIU)",
        title="HKAB working group on AI in compliance — public consultation closing March",
        summary=(
            "Hong Kong Association of Banks ran a working group consultation on AI use in compliance "
            "functions. Topics: STR drafting, KYC document analysis, alert triage. Industry view to "
            "inform HKMA guidance expected H2 2026."
        ),
        source="Hong Kong Association of Banks",
        url="https://www.hkab.org.hk/",
        impact="Medium",
        category="Industry",
    ),

    # Malaysia — industry & enforcement news
    HorizonItem(
        date="2026-04-23",
        jurisdiction="Malaysia (FIED)",
        title="BNM enforcement: RM 8.7M civil penalty against MSB for STR delays",
        summary=(
            "BNM imposed a RM 8.7M civil penalty against a Money Services Business for systematic delays "
            "in STR filing under AMLA s.14, plus deficiencies in customer risk-rating methodology. Largest "
            "MSB-sector penalty in 2026 to date."
        ),
        source="BNM Enforcement",
        url="https://www.bnm.gov.my/-/list-of-enforcement-actions",
        impact="High",
        category="Enforcement",
    ),
    HorizonItem(
        date="2026-04-15",
        jurisdiction="Malaysia (FIED)",
        title="AEON Bank reaches 1 million customers — first Islamic digital bank milestone",
        summary=(
            "AEON Bank announced 1 million customer milestone after 18 months of operations. Industry watching "
            "scaling implications for Shariah-compliant digital banking AML controls. AEON has stated public "
            "commitment to enhanced TM rule-set tuning."
        ),
        source="AEON Bank / The Edge Malaysia",
        url="https://www.aeon-bank.com.my",
        impact="Low",
        category="Industry",
    ),
    HorizonItem(
        date="2026-03-25",
        jurisdiction="Malaysia (FIED)",
        title="Typology bulletin: deep-fake video scams in cross-border e-money flows",
        summary=(
            "BNM FIED flags emerging deep-fake video-call scams targeting Malaysian SMEs in cross-border "
            "trade. Pattern: scammers impersonate suppliers via deep-fake video, request invoice payment "
            "to redirected accounts. E-money issuers and banks advised to flag sudden payment-routing changes."
        ),
        source="BNM FIED",
        url="https://amlcft.bnm.gov.my/typologies",
        impact="High",
        category="Typology",
    ),
    HorizonItem(
        date="2026-02-05",
        jurisdiction="Malaysia (FIED)",
        title="Bank Islam launches AML/CTF analyst certification program",
        summary=(
            "Bank Islam, in partnership with IBFIM, launched an internal certification program for "
            "AML/CTF analysts covering Shariah-compliant product typologies, Tawarruq abuse patterns, "
            "and digital banking mule-detection. Industry first for Islamic banking."
        ),
        source="Bank Islam Malaysia / IBFIM",
        url="https://www.bankislam.com",
        impact="Low",
        category="Industry",
    ),

    # Australia — industry & enforcement news
    HorizonItem(
        date="2026-04-24",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="AUSTRAC enforcement: AUD 47M penalty against major DCE for systemic AML failures",
        summary=(
            "AUSTRAC announced a AUD 47M civil penalty against a major AUSTRAC-registered Digital Currency "
            "Exchange for systemic failures in transaction monitoring, mule-account detection, and SMR "
            "timeliness. The enforcement caps a 12-month investigation into scam-victim mule flow patterns."
        ),
        source="AUSTRAC",
        url="https://www.austrac.gov.au/about-us/news-and-media/media-releases",
        impact="High",
        category="Enforcement",
    ),
    HorizonItem(
        date="2026-04-12",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Law Council of Australia publishes Tranche 2 implementation guide for solicitors",
        summary=(
            "Law Council of Australia released a comprehensive implementation guide for solicitors "
            "preparing for Tranche 2 obligations. Covers AML/CTF Program design, customer engagement "
            "triggers, source-of-wealth diligence, and legal-professional-privilege carve-outs."
        ),
        source="Law Council of Australia",
        url="https://www.lawcouncil.au/",
        impact="High",
        category="Industry",
    ),
    HorizonItem(
        date="2026-03-30",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="Typology bulletin: 'Pig butchering' scam — 2025 victim losses AUD 2.7B",
        summary=(
            "AUSTRAC published 2025 typology bulletin: AUD 2.7B in Australian victim losses to investment "
            "scam ('Pig Butchering') typology. Pattern of victim-deposit → DCE → mixer → scammer continues. "
            "Reporting entities advised to refresh mule-detection rules and customer-protection messaging."
        ),
        source="AUSTRAC",
        url="https://www.austrac.gov.au/business/how-comply-and-report-guidance-and-resources/typology-bulletins",
        impact="High",
        category="Typology",
    ),
    HorizonItem(
        date="2026-02-18",
        jurisdiction="Australia (AUSTRAC SMR)",
        title="ACAMS Australia annual conference — 7-9 April 2026 in Sydney",
        summary=(
            "Annual ACAMS Australia chapter conference covering Tranche 2 readiness, AUSTRAC enforcement "
            "trends, AI in compliance, and DCE supervisory expectations. AUSTRAC CEO confirmed as keynote."
        ),
        source="ACAMS Australia",
        url="https://www.acams.org/en/chapters/australia",
        impact="Low",
        category="Industry",
    ),
]


def items_for_jurisdiction(jurisdiction: str | None = None) -> list[HorizonItem]:
    """Return curated items for the given jurisdiction, or all if None."""
    items = sorted(HORIZON_ITEMS, key=lambda i: i.date, reverse=True)
    if jurisdiction is None:
        return items
    return [i for i in items if i.jurisdiction == jurisdiction]


# ============================================================================
# Live RSS feeds — best-effort URLs per regulator. Fetched with TTL cache.
# ============================================================================

RSS_FEEDS: dict[str, list[tuple[str, str, str]]] = {
    # (label, url, category)
    "Singapore (STRO)": [
        ("MAS news", "https://www.mas.gov.sg/news/rss", "Regulatory"),
        ("MAS enforcement", "https://www.mas.gov.sg/news/enforcement-actions/rss", "Enforcement"),
        ("Singapore Police Force", "https://www.police.gov.sg/Newsroom/News?feed=rss", "Industry"),
        ("ACRA news", "https://www.acra.gov.sg/news-events/rss", "Regulatory"),
        ("CCCS news", "https://www.cccs.gov.sg/rss", "Regulatory"),
        ("PDPC news", "https://www.pdpc.gov.sg/news-and-events/rss", "Regulatory"),
    ],
    "Hong Kong (JFIU)": [
        ("HKMA press releases", "https://www.hkma.gov.hk/eng/rss/press-releases.xml", "Regulatory"),
        ("SFC news", "https://www.sfc.hk/-/media/EN/files/News-and-announcements/News/rss/news.xml", "Regulatory"),
        ("ICAC news", "https://www.icac.org.hk/en/press/rss.xml", "Industry"),
        ("HKEX news", "https://www.hkex.com.hk/-/media/HKEX-Market/News/News-Release/rss/news-release.xml", "Regulatory"),
        ("Insurance Authority HK", "https://www.ia.org.hk/en/news/rss.xml", "Regulatory"),
    ],
    "Malaysia (FIED)": [
        ("BNM announcements", "https://www.bnm.gov.my/rss-announcement", "Regulatory"),
        ("SC Malaysia media releases", "https://www.sc.com.my/api/rss/MediaRelease", "Regulatory"),
        ("Bursa Malaysia announcements", "https://www.bursamalaysia.com/about_bursa/media_centre/news/rss", "Regulatory"),
    ],
    "Australia (AUSTRAC SMR)": [
        ("AUSTRAC media", "https://www.austrac.gov.au/about-us/news-and-media/media-releases/feed", "Enforcement"),
        ("ASIC media releases", "https://asic.gov.au/about-asic/news-centre/find-a-media-release/feed/", "Regulatory"),
        ("APRA news", "https://www.apra.gov.au/news-and-publications/feed", "Regulatory"),
        ("ACCC news", "https://www.accc.gov.au/about-us/news-and-publications/feed", "Regulatory"),
        ("AFP news", "https://www.afp.gov.au/news-media/rss-feeds", "Enforcement"),
        ("RBA news", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "Regulatory"),
        ("DFAT sanctions news", "https://www.dfat.gov.au/news/news/rss", "Sanctions"),
    ],
    # International / Standard-setters — these surface across "All jurisdictions" filter
    "International / Standard-setters": [
        ("FATF news", "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.rss", "Regulatory"),
        ("BIS press releases", "https://www.bis.org/list/press_releases/index.rss", "Regulatory"),
        ("FSB news", "https://www.fsb.org/feed/", "Regulatory"),
        ("OECD news", "https://www.oecd.org/news/news.xml", "Regulatory"),
        ("IMF news", "https://www.imf.org/external/rss/en/news.aspx", "Regulatory"),
        ("World Bank news", "https://www.worldbank.org/en/news/rss", "Regulatory"),
        ("UNODC news", "https://www.unodc.org/unodc/index.rss", "Enforcement"),
        ("APG news", "https://www.apgml.org/news/index.aspx?type=rss", "Enforcement"),
        ("Egmont Group news", "https://egmontgroup.org/feed/", "Enforcement"),
        ("Wolfsberg Group", "https://www.wolfsberg-principles.com/feed", "Regulatory"),
    ],
    # UK + US authoritative feeds — also surface in "All jurisdictions"
    "United Kingdom & United States": [
        ("FCA UK news", "https://www.fca.org.uk/news/rss.xml", "Regulatory"),
        ("Bank of England news", "https://www.bankofengland.co.uk/rss/news", "Regulatory"),
        ("US SEC press releases", "https://www.sec.gov/news/pressreleases.rss", "Regulatory"),
        ("FinCEN news", "https://www.fincen.gov/feed/news_release", "Enforcement"),
        ("OFAC recent actions", "https://ofac.treasury.gov/recent-actions.rss", "Sanctions"),
        ("CFTC press releases", "https://www.cftc.gov/PressRoom/PressReleases/rss", "Regulatory"),
        ("US DOJ news", "https://www.justice.gov/feeds/news.xml", "Enforcement"),
    ],
}

_FEED_CACHE: dict[str, tuple[float, list[HorizonItem]]] = {}
_FEED_TTL_SECONDS = 1800  # 30 minutes


def fetch_live_items(
    jurisdiction: str,
    max_per_feed: int = 5,
    force_refresh: bool = False,
) -> tuple[list[HorizonItem], dict[str, str]]:
    """Fetch live items from RSS feeds for a jurisdiction.

    Returns (items, status_per_feed). status_per_feed maps feed-label to either
    "OK (N items)" or an error message.

    TTL-cached: subsequent calls within 30 minutes return cached results unless
    force_refresh=True.
    """
    if not FEEDPARSER_AVAILABLE:
        return [], {"_overall": "feedparser package not installed"}

    cache_key = jurisdiction
    now = time.time()
    if not force_refresh and cache_key in _FEED_CACHE:
        ts, cached = _FEED_CACHE[cache_key]
        if now - ts < _FEED_TTL_SECONDS:
            return cached, {"_cache": f"cached {int((now - ts) / 60)} min ago"}

    feeds = RSS_FEEDS.get(jurisdiction, [])
    all_items: list[HorizonItem] = []
    statuses: dict[str, str] = {}

    for label, url, category in feeds:
        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": "AML-Agents/0.1"})
            if parsed.bozo and parsed.bozo_exception:
                statuses[label] = f"error: {type(parsed.bozo_exception).__name__}"
                continue
            entries = parsed.entries[:max_per_feed]
            count = 0
            for entry in entries:
                title = entry.get("title", "(no title)")
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary
                import re as _re
                summary = _re.sub(r"<[^>]+>", "", summary)[:500]
                published = entry.get("published", entry.get("updated", "")) or ""
                # Try to coerce to YYYY-MM-DD; fall back to first 10 chars
                date_str = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pp = entry.published_parsed
                    date_str = f"{pp.tm_year:04d}-{pp.tm_mon:02d}-{pp.tm_mday:02d}"
                elif published:
                    date_str = published[:10]
                else:
                    date_str = "unknown"
                link = entry.get("link", url)
                all_items.append(HorizonItem(
                    date=date_str,
                    jurisdiction=jurisdiction,
                    title=f"[LIVE] {title}",
                    summary=summary or "(no summary in feed)",
                    source=label,
                    url=link,
                    impact="Medium",  # default; could be tuned per source
                    category=category,
                ))
                count += 1
            statuses[label] = f"OK ({count} items)"
        except Exception as e:
            statuses[label] = f"error: {type(e).__name__}: {str(e)[:80]}"

    _FEED_CACHE[cache_key] = (now, all_items)
    return all_items, statuses


def all_items_for_jurisdiction(
    jurisdiction: str | None,
    include_live: bool = True,
    force_refresh: bool = False,
) -> tuple[list[HorizonItem], dict[str, str]]:
    """Combined curated + live items, sorted by date desc."""
    curated = items_for_jurisdiction(jurisdiction)
    live: list[HorizonItem] = []
    statuses: dict[str, str] = {}

    if include_live:
        if jurisdiction is None:
            for jur in RSS_FEEDS.keys():
                items, st_map = fetch_live_items(jur, force_refresh=force_refresh)
                live.extend(items)
                for k, v in st_map.items():
                    statuses[f"{jur} — {k}"] = v
        else:
            live, statuses = fetch_live_items(jurisdiction, force_refresh=force_refresh)

    combined = sorted(curated + live, key=lambda i: i.date, reverse=True)
    return combined, statuses
