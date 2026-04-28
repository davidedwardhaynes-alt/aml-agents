"""Press-release scraping for regulators that don't expose RSS.

Many APAC regulators publish press releases on their website but don't expose
RSS feeds. This module fetches HTML, sends to Claude Haiku for structured
extraction, and caches results — providing a flexible alternative to per-source
HTML parsers.

Cost: Haiku at ~$0.005-0.015 per page fetch (input + output tokens).
With 4-hour TTL cache and ~30 regulators, daily cost ~$1-3.

Usage:
    from lib.press_releases import fetch_all_press_releases
    items = fetch_all_press_releases(force_refresh=False)
    # Each item: {"title", "summary", "date", "url", "source", "jurisdiction"}
"""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

# Don't let any single fetch hang the whole run
socket.setdefaulttimeout(15)


CACHE_PATH = Path(__file__).parent.parent / "data" / "press_release_cache.yaml"
CACHE_TTL_SECONDS = 4 * 60 * 60  # 4 hours
MAX_HTML_CHARS = 60_000  # cap input HTML to keep extraction cost predictable
EXTRACTOR_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class PressReleasePage:
    """Configured regulator press-release page."""
    label: str
    url: str
    jurisdiction: str  # maps to product jurisdictions or "All jurisdictions"
    type: str = "regulator"


# Press release pages — regulators where RSS is unavailable but the press
# release index page is HTML-scrapable.
PRESS_RELEASE_PAGES: list[PressReleasePage] = [
    # ---- Singapore ----
    PressReleasePage("MAS news releases", "https://www.mas.gov.sg/news", "Singapore (STRO)"),
    PressReleasePage("MAS speeches", "https://www.mas.gov.sg/news?type=speeches", "Singapore (STRO)"),
    PressReleasePage("MAS enforcement actions", "https://www.mas.gov.sg/news/enforcement-actions", "Singapore (STRO)"),
    PressReleasePage("ACRA news", "https://www.acra.gov.sg/news-events/news", "Singapore (STRO)"),
    PressReleasePage("CCCS press releases", "https://www.cccs.gov.sg/media-and-publications/media-releases", "Singapore (STRO)"),
    PressReleasePage("CPIB press releases", "https://www.cpib.gov.sg/press-room/press-releases", "Singapore (STRO)"),
    PressReleasePage("PDPC news", "https://www.pdpc.gov.sg/news-and-events/announcements", "Singapore (STRO)"),
    PressReleasePage("SGX regulation news", "https://www.sgx.com/regulation/news", "Singapore (STRO)"),
    PressReleasePage("STRO news", "https://www.police.gov.sg/Advisories/Commercial-Crimes/Suspicious-Transaction-Reporting-Office", "Singapore (STRO)"),

    # ---- Hong Kong ----
    PressReleasePage("HKMA press releases", "https://www.hkma.gov.hk/eng/news-and-media/press-releases/", "Hong Kong (JFIU)"),
    PressReleasePage("HKMA speeches", "https://www.hkma.gov.hk/eng/news-and-media/speeches/", "Hong Kong (JFIU)"),
    PressReleasePage("SFC news", "https://www.sfc.hk/en/News-and-announcements", "Hong Kong (JFIU)"),
    PressReleasePage("SFC enforcement", "https://www.sfc.hk/en/News-and-announcements/Enforcement-news", "Hong Kong (JFIU)"),
    PressReleasePage("ICAC press releases", "https://www.icac.org.hk/en/press/index.html", "Hong Kong (JFIU)"),
    PressReleasePage("HKEX news", "https://www.hkex.com.hk/News/News-Release", "Hong Kong (JFIU)"),
    PressReleasePage("Insurance Authority HK news", "https://www.ia.org.hk/en/news/", "Hong Kong (JFIU)"),
    PressReleasePage("MPFA news", "https://www.mpfa.org.hk/en/news-press-releases/press-releases", "Hong Kong (JFIU)"),
    PressReleasePage("PCPD news", "https://www.pcpd.org.hk/english/news_events/media_statements/media_statements.html", "Hong Kong (JFIU)"),

    # ---- Malaysia ----
    PressReleasePage("BNM speeches and press", "https://www.bnm.gov.my/press-releases", "Malaysia (FIED)"),
    PressReleasePage("BNM AML/CFT", "https://amlcft.bnm.gov.my/", "Malaysia (FIED)"),
    PressReleasePage("SC Malaysia media", "https://www.sc.com.my/resources/media-releases", "Malaysia (FIED)"),
    PressReleasePage("Bursa Malaysia announcements", "https://www.bursamalaysia.com/about_bursa/media_centre/news", "Malaysia (FIED)"),
    PressReleasePage("MACC / SPRM news", "https://www.sprm.gov.my/index.php?page_id=20", "Malaysia (FIED)"),

    # ---- Australia ----
    PressReleasePage("AUSTRAC media releases", "https://www.austrac.gov.au/about-us/news-and-media/media-releases", "Australia (AUSTRAC SMR)"),
    PressReleasePage("ASIC media releases", "https://asic.gov.au/about-asic/news-centre/find-a-media-release/", "Australia (AUSTRAC SMR)"),
    PressReleasePage("APRA media", "https://www.apra.gov.au/news-and-publications", "Australia (AUSTRAC SMR)"),
    PressReleasePage("ACCC media releases", "https://www.accc.gov.au/about-us/media-centre/media-releases", "Australia (AUSTRAC SMR)"),
    PressReleasePage("AFP news", "https://www.afp.gov.au/news-media", "Australia (AUSTRAC SMR)"),
    PressReleasePage("RBA media releases", "https://www.rba.gov.au/media-releases/", "Australia (AUSTRAC SMR)"),
    PressReleasePage("DFAT sanctions news", "https://www.dfat.gov.au/international-relations/security/sanctions", "Australia (AUSTRAC SMR)"),

    # ---- Other APAC regulators ----
    PressReleasePage("RBI press releases", "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx", "All jurisdictions"),
    PressReleasePage("SEBI press releases", "https://www.sebi.gov.in/media/press-releases.html", "All jurisdictions"),
    PressReleasePage("Bank of Thailand news", "https://www.bot.or.th/en/news-and-media.html", "All jurisdictions"),
    PressReleasePage("SEC Thailand news", "https://www.sec.or.th/EN/Pages/News/News.aspx", "All jurisdictions"),
    PressReleasePage("BSP Philippines media", "https://www.bsp.gov.ph/SitePages/MediaAndResearch/News.aspx", "All jurisdictions"),
    PressReleasePage("AMLC Philippines news", "https://www.amlc.gov.ph/news", "All jurisdictions"),
    PressReleasePage("Bank Indonesia news", "https://www.bi.go.id/en/publikasi/ruang-media/news-release/default.aspx", "All jurisdictions"),
    PressReleasePage("OJK Indonesia news", "https://www.ojk.go.id/en/berita-dan-kegiatan/siaran-pers/default.aspx", "All jurisdictions"),
    PressReleasePage("FSA Japan news", "https://www.fsa.go.jp/en/news/index.html", "All jurisdictions"),
    PressReleasePage("Bank of Japan press", "https://www.boj.or.jp/en/announcements/release_2025/index.htm", "All jurisdictions"),
    PressReleasePage("FSC Korea news", "https://www.fsc.go.kr/eng/no010101", "All jurisdictions"),
    PressReleasePage("FSS Korea news", "https://www.fss.or.kr/eng/main/main.do?menuNo=200042", "All jurisdictions"),
    PressReleasePage("Bank of Korea news", "https://www.bok.or.kr/eng/main/contents.do?menuNo=400060", "All jurisdictions"),
    PressReleasePage("KoFIU news", "https://www.kofiu.go.kr/eng/main/main.do", "All jurisdictions"),
    PressReleasePage("FSC Taiwan news", "https://www.fsc.gov.tw/en/home.jsp?id=121&parentpath=0,2", "All jurisdictions"),
    PressReleasePage("CSRC China news", "http://www.csrc.gov.cn/csrc_en/c102030/", "All jurisdictions"),
    PressReleasePage("PBoC China press", "http://www.pbc.gov.cn/en/3688110/3688172/index.html", "All jurisdictions"),
    PressReleasePage("FMU Pakistan news", "https://www.fmu.gov.pk/news/", "All jurisdictions"),
    PressReleasePage("State Bank of Pakistan news", "https://www.sbp.org.pk/press/index.html", "All jurisdictions"),
    PressReleasePage("RBNZ news", "https://www.rbnz.govt.nz/hub/news", "All jurisdictions"),
    PressReleasePage("FMA New Zealand news", "https://www.fma.govt.nz/news/all-releases/", "All jurisdictions"),

    # ---- International / standard-setters ----
    PressReleasePage("FATF news", "https://www.fatf-gafi.org/en/news.html", "All jurisdictions"),
    PressReleasePage("APG news", "https://www.apgml.org/news/default.aspx", "All jurisdictions"),
    PressReleasePage("Egmont Group news", "https://egmontgroup.org/news/", "All jurisdictions"),
    PressReleasePage("Wolfsberg Group publications", "https://www.wolfsberg-principles.com/publications", "All jurisdictions"),
    PressReleasePage("BIS press releases", "https://www.bis.org/list/press_releases.htm", "All jurisdictions"),
    PressReleasePage("FSB press releases", "https://www.fsb.org/press/", "All jurisdictions"),
]


EXTRACTION_PROMPT = """Extract the most recent press releases / news items from this regulator's web page. Return JSON only — an array of objects with these keys:
  - title: the press release headline
  - date: publication date in YYYY-MM-DD format (use today's date if unclear)
  - summary: 1-2 sentence summary if visible, else empty string
  - url: absolute URL to the full press release (resolve relative URLs against the page's base URL)

Return at most 10 items, the most recent ones. Skip navigation links, advertisements, footer items.

If the page has no recognizable press releases, return an empty array.

Output ONLY the JSON array — no markdown fences, no preamble."""


def _strip_html_for_extraction(html: str) -> str:
    """Trim HTML to a reasonable size for LLM input.

    Drop <script>, <style>, <nav>, <footer> blocks and collapse whitespace.
    Preserves <a> tags with hrefs which is what we need for URL extraction.
    """
    import re
    # Remove script/style/svg blocks
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<svg[^>]*>.*?</svg>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Collapse whitespace
    html = re.sub(r"\s+", " ", html)
    # Cap length
    if len(html) > MAX_HTML_CHARS:
        html = html[:MAX_HTML_CHARS]
    return html


def _load_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        yaml.dump(cache, f, default_flow_style=False, sort_keys=False)


def _fetch_html(url: str) -> str | None:
    """Fetch a regulator page. Returns None on any error."""
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36 AML-Agents/0.1"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def _extract_with_llm(client, html: str, page: PressReleasePage) -> list[dict[str, str]]:
    """Use Claude Haiku to extract structured press release items from HTML."""
    cleaned = _strip_html_for_extraction(html)
    user_prompt = (
        f"Source: {page.label}\n"
        f"Page URL: {page.url}\n"
        f"Page HTML (cleaned):\n{cleaned}\n\n"
        f"{EXTRACTION_PROMPT}"
    )
    try:
        response = client.messages.create(
            model=EXTRACTOR_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        # Strip code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
        items = json.loads(text)
        if not isinstance(items, list):
            return []
        return [i for i in items if isinstance(i, dict) and i.get("title")]
    except Exception:
        return []


def fetch_all_press_releases(
    force_refresh: bool = False,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Fetch press releases from all configured pages.

    Returns a list of normalized item dicts:
      {key, title, summary, url, source, date, jur_hint}
    Compatible with generate_articles.py's RSS-candidate format.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        if verbose:
            print("ANTHROPIC_API_KEY not set; skipping press-release extraction.")
        return []

    from anthropic import Anthropic
    client = Anthropic()

    cache = _load_cache()
    now = time.time()
    all_items: list[dict[str, Any]] = []

    n_pages = len(PRESS_RELEASE_PAGES)
    n_cached = 0
    n_fetched = 0
    n_err = 0
    for idx, page in enumerate(PRESS_RELEASE_PAGES, 1):
        cache_key = page.url
        cached = cache.get(cache_key)
        if (
            not force_refresh
            and cached
            and cached.get("ts") and now - cached["ts"] < CACHE_TTL_SECONDS
        ):
            items = cached.get("items", [])
            n_cached += 1
        else:
            html = _fetch_html(page.url)
            if html is None:
                n_err += 1
                continue
            items = _extract_with_llm(client, html, page)
            cache[cache_key] = {"ts": now, "items": items, "label": page.label}
            n_fetched += 1
            time.sleep(0.5)  # gentle rate limit

        # Normalize to candidate format
        for item in items:
            url = item.get("url") or page.url
            date = item.get("date") or time.strftime("%Y-%m-%d")
            title = item.get("title", "")
            summary = item.get("summary", "")
            if not title:
                continue
            import hashlib
            key = hashlib.sha256(url.encode()).hexdigest()[:16]
            all_items.append({
                "key": key,
                "title": title,
                "summary": summary or title,
                "url": url,
                "source": page.label,
                "date": date,
                "jur_hint": page.jurisdiction,
            })

        if verbose and idx % 10 == 0:
            print(f"  ... press: {idx}/{n_pages} pages ({n_cached} cached, {n_fetched} fresh, {n_err} err)", flush=True)

    if verbose:
        print(f"  Press releases: {n_pages} pages ({n_cached} cached, {n_fetched} fresh, {n_err} err); {len(all_items)} candidate items", flush=True)

    _save_cache(cache)
    return all_items
