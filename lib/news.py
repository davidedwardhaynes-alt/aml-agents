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
    summary: str
    source: str
    url: str
    topic: str


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

    # ---------------- Authoritative sources — Regulation Asia ----------------
    NewsItem(
        date="2026-04-28",
        jurisdiction="All jurisdictions",
        title="Regulation Asia: APAC FIUs sign tripartite intelligence-sharing MoU",
        summary=(
            "STRO (Singapore), JFIU (Hong Kong) and AUSTRAC (Australia) signed a tripartite MoU "
            "for cross-border AML intelligence sharing focused on scam-victim mule networks. "
            "Operational protocols to be published Q3 2026; first inter-FIU shared analytics "
            "platform in APAC."
        ),
        source="Regulation Asia",
        url="https://www.regulationasia.com",
        topic="AML enforcement",
    ),
    NewsItem(
        date="2026-04-21",
        jurisdiction="All jurisdictions",
        title="Regulation Asia commentary: APAC virtual bank AML control gaps",
        summary=(
            "Editorial review of HKMA's HKD 18M penalty, BNM digital-bank thematic findings, "
            "and Singapore MAS expectations for digital banks. Common thread: e-KYC mule-detection "
            "deficiencies. Key article for any digital banking AML readiness benchmarking."
        ),
        source="Regulation Asia",
        url="https://www.regulationasia.com",
        topic="Fintech / Digital banking",
    ),
    NewsItem(
        date="2026-04-09",
        jurisdiction="All jurisdictions",
        title="Regulation Asia: tokenisation pilots accelerate across Singapore, HK, Australia",
        summary=(
            "Tokenised real-world assets (RWA) regulatory frameworks compared across MAS Project "
            "Guardian, SFC sandbox (HK), and ASIC innovation hub. AML implications: source-of-"
            "wealth checks at higher thresholds; Travel Rule application to RWA transfers."
        ),
        source="Regulation Asia",
        url="https://www.regulationasia.com",
        topic="Crypto / VASP",
    ),
    NewsItem(
        date="2026-03-20",
        jurisdiction="All jurisdictions",
        title="Regulation Asia: APAC anti-scam coordination — government task forces compared",
        summary=(
            "Comparative analysis: Singapore Anti-Scam Centre (SPF), HK Anti-Deception "
            "Coordination Centre (ADCC), Malaysia National Scam Response Centre (NSRC), "
            "Australia National Anti-Scam Centre (NASC). Operational maturity ranking and "
            "industry coordination effectiveness."
        ),
        source="Regulation Asia",
        url="https://www.regulationasia.com",
        topic="Scams / Fraud trends",
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
    ("Regulation Asia", "https://www.regulationasia.com/feed/", "AML enforcement"),
    ("Wolfsberg Group publications", "https://www.wolfsberg-principles.com/feed", "AML enforcement"),
    ("Egmont Group news", "https://egmontgroup.org/feed/", "AML enforcement"),

    # ---- Banking / industry associations ----
    ("HKAB (Hong Kong Association of Banks)", "https://www.hkab.org.hk/feed", "Industry M&A"),
    ("ASIFMA news", "https://www.asifma.org/feed/", "Regulatory tech"),
    ("Australian Banking Association", "https://www.ausbanking.org.au/feed/", "Fintech / Digital banking"),
    ("ABS (Association of Banks in Singapore)", "https://www.abs.org.sg/feed", "Fintech / Digital banking"),

    # ---- General compliance / fintech / regtech ----
    ("FinExtra", "https://www.finextra.com/rss/headlines.aspx", "Fintech / Digital banking"),
    ("RegTech Analyst", "https://member.fintech.global/feed/", "Regulatory tech"),
    ("ACAMS Today", "https://www.acamstoday.org/feed/", "AML enforcement"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "Crypto / VASP"),
    ("The Banker", "https://www.thebanker.com/rss/news", "Fintech / Digital banking"),
    ("FATF news", "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.rss", "AML enforcement"),
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


def items_for(
    jurisdiction: str | None = None,
    topic: str | None = None,
    include_live: bool = True,
    force_refresh: bool = False,
) -> tuple[list[NewsItem], dict[str, str]]:
    """Filtered news items, sorted by date desc."""
    static = list(NEWS_ITEMS)
    live: list[NewsItem] = []
    statuses: dict[str, str] = {}

    if include_live:
        live, statuses = fetch_news_feeds(force_refresh=force_refresh)

    combined = static + live

    if jurisdiction and jurisdiction != "All jurisdictions":
        # Include items tagged with this jurisdiction OR "All jurisdictions" (live items)
        combined = [i for i in combined if i.jurisdiction in (jurisdiction, "All jurisdictions")]
    if topic and topic != "All topics":
        combined = [i for i in combined if i.topic == topic]

    return sorted(combined, key=lambda i: i.date, reverse=True), statuses
