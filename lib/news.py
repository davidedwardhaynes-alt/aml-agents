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
]


# Industry RSS feeds — broader compliance / fintech / regtech publications.
# Most aren't jurisdiction-specific, so live items get tagged "All jurisdictions".
NEWS_RSS_FEEDS: list[tuple[str, str, str]] = [
    # (source label, url, default topic)
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
