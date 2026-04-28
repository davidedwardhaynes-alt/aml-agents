"""Auto-generate jurisdictional news articles from RSS feeds.

Run this on a cron / launchd schedule throughout the day. Each invocation:
  1. Loads existing generated articles from data/generated_articles.yaml
  2. Pulls latest items from configured RSS feeds (horizon + news)
  3. Filters: items < 14 days old, not already processed
  4. Picks N items (default 1 per run; configurable via --max)
  5. Calls Claude to write a 250-400 word FT/Regulation-Asia voice article
  6. Auto-classifies jurisdiction + topic
  7. Saves to YAML, appended to feed
  8. Caps at MAX_PER_DAY to bound API spend

Cron example (~1 article every 30 min, max 30/day):
    */30 * * * * cd ~/dev/amlagents && .venv/bin/python scripts/generate_articles.py >> /tmp/amlagents-news.log 2>&1

Usage:
    python scripts/generate_articles.py          # default: 1 article per run
    python scripts/generate_articles.py --max 3  # up to 3 articles in this run
    python scripts/generate_articles.py --dry-run  # show what would be generated, don't call API
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Make repo root importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

try:
    import feedparser
except ImportError:
    print("feedparser not installed. Run: pip install feedparser")
    sys.exit(1)

from lib.horizon import RSS_FEEDS as HORIZON_FEEDS
from lib.news import NEWS_RSS_FEEDS, TOPICS

GENERATED_PATH = ROOT / "data" / "generated_articles.yaml"
MAX_PER_DAY = 30
MAX_AGE_DAYS = 14  # don't generate articles for news older than this
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1200


# Topic classification keywords (single-word matches OK; combined ranking)
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AML enforcement": ["enforcement", "penalty", "fine", "aml", "money laundering", "STR", "SAR", "fiu"],
    "Fintech / Digital banking": ["digital bank", "neobank", "fintech", "challenger bank", "virtual bank"],
    "Crypto / VASP": ["crypto", "vasp", "blockchain", "bitcoin", "btc", "eth", "stablecoin", "tokeni", "dce", "dpt"],
    "Sanctions / Geopolitics": ["sanction", "ofac", "russia", "iran", "dprk", "designat", "embargo"],
    "Industry M&A": ["acqui", "merger", "investment", "fundrais", "ipo"],
    "Talent / Hiring": ["appoint", "hire", "ceo", "mlro", "compliance officer", "joins"],
    "Conferences / Events": ["conference", "summit", "symposium", "event", "keynote"],
    "Regulatory tech": ["regtech", "ai ", "machine learning", "automation", "regulatory technology"],
    "Scams / Fraud trends": ["scam", "fraud", "phishing", "pig butchering", "romance scam", "investment scam"],
}

JURISDICTION_KEYWORDS: dict[str, list[str]] = {
    "Singapore (STRO)": ["singapore", "mas", "stro", "sgd", "monetary authority of singapore"],
    "Hong Kong (JFIU)": ["hong kong", "hkma", "jfiu", "sfc", " hkd ", "icac"],
    "Malaysia (FIED)": ["malaysia", "bnm", "bank negara", "ringgit", "fied", "myr"],
    "Australia (AUSTRAC SMR)": ["australia", "austrac", "asic", "apra", "rba", "aud"],
}


@dataclass
class GeneratedArticle:
    id: str = field(default_factory=lambda: f"art-{dt.date.today().isoformat()}-{uuid.uuid4().hex[:6]}")
    generated_at: str = ""
    source_name: str = ""
    source_url: str = ""
    source_date: str = ""
    title: str = ""
    jurisdiction: str = "All jurisdictions"
    topic: str = "AML enforcement"
    summary: str = ""
    full_article: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def load_generated() -> list[GeneratedArticle]:
    if not GENERATED_PATH.exists():
        return []
    with open(GENERATED_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [GeneratedArticle(**item) for item in raw]


def save_generated(items: list[GeneratedArticle]) -> None:
    GENERATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GENERATED_PATH, "w") as f:
        yaml.dump([asdict(a) for a in items], f, default_flow_style=False, sort_keys=False)


def url_hash(url: str) -> str:
    """Stable identifier for an RSS item URL — used to dedupe across runs."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def classify_topic(text: str) -> str:
    text_low = text.lower()
    scores: dict[str, int] = {t: 0 for t in TOPICS}
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_low:
                scores[topic] = scores.get(topic, 0) + 1
    return max(scores.items(), key=lambda x: x[1])[0] if any(scores.values()) else "AML enforcement"


def classify_jurisdiction(text: str, source_label: str) -> str:
    text_low = (text + " " + source_label).lower()
    scores: dict[str, int] = {}
    for jur, keywords in JURISDICTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_low:
                scores[jur] = scores.get(jur, 0) + 1
    if not scores:
        return "All jurisdictions"
    return max(scores.items(), key=lambda x: x[1])[0]


def collect_candidate_items() -> list[dict[str, Any]]:
    """Pull from all RSS feeds; return unique items keyed by URL."""
    candidates: dict[str, dict[str, Any]] = {}
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MAX_AGE_DAYS)

    feed_specs: list[tuple[str, str, str, str]] = []
    # Horizon feeds: dict[jurisdiction] -> [(label, url, category)]
    for jur, feeds in HORIZON_FEEDS.items():
        for label, url, category in feeds:
            feed_specs.append((label, url, jur, category))
    # News feeds: list of (label, url, default_topic)
    for label, url, topic in NEWS_RSS_FEEDS:
        feed_specs.append((label, url, "All jurisdictions", topic))

    for label, url, jur_hint, _topic_hint in feed_specs:
        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": "AML-Agents/0.1"})
            if parsed.bozo:
                continue
            for entry in parsed.entries[:8]:
                link = entry.get("link", "")
                if not link:
                    continue
                # Date filter
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pp = entry.published_parsed
                    item_date = dt.datetime(pp.tm_year, pp.tm_mon, pp.tm_mday, tzinfo=dt.timezone.utc)
                    if item_date < cutoff:
                        continue
                    date_str = f"{pp.tm_year:04d}-{pp.tm_mon:02d}-{pp.tm_mday:02d}"
                else:
                    date_str = entry.get("published", "")[:10] or dt.date.today().isoformat()

                title = entry.get("title", "(no title)")
                summary = entry.get("summary", entry.get("description", ""))
                import re as _re
                summary = _re.sub(r"<[^>]+>", "", summary)[:1200]

                key = url_hash(link)
                if key not in candidates:
                    candidates[key] = {
                        "key": key,
                        "title": title,
                        "summary": summary,
                        "url": link,
                        "source": label,
                        "date": date_str,
                        "jur_hint": jur_hint,
                    }
        except Exception:
            continue

    return list(candidates.values())


ARTICLE_SYSTEM_PROMPT = """You are a senior financial-crime journalist writing for an audience of \
MLROs, Heads of FCC, AML supervisors, and compliance professionals. Voice: Regulation Asia, Financial \
Times, The Economist. Authoritative, balanced, specific. No hyperbole. No "shocking" or "groundbreaking." \
Reference real regulatory frameworks (FATF Recommendations, MAS Notices, OSCO, AMLA, AML/CTF Act \
sections, etc.) where relevant.

Structure:
- Lead paragraph: concrete fact + immediate implication
- Context paragraph: regulatory or market history that frames the news
- Multiple stakeholder perspectives or implications
- Forward-looking closing observation

Length: 250-400 words. Output ONLY the article body in markdown paragraphs. No meta-commentary, no \
headlines, no "Here is the article:" preamble."""


def generate_article(client: Anthropic, item: dict[str, Any]) -> GeneratedArticle:
    user_prompt = (
        f"Source publication: {item['source']}\n"
        f"Date: {item['date']}\n"
        f"Headline: {item['title']}\n"
        f"Summary from source: {item['summary']}\n"
        f"Source URL: {item['url']}\n\n"
        f"Write the analysis article."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    article_text = response.content[0].text.strip()
    # Auto-classify
    classifier_text = item["title"] + " " + item["summary"]
    topic = classify_topic(classifier_text)
    # Use jurisdiction hint from feed, or auto-classify if generic
    if item["jur_hint"] in JURISDICTION_KEYWORDS:
        jurisdiction = item["jur_hint"]
    else:
        jurisdiction = classify_jurisdiction(classifier_text, item["source"])

    # Build a 2-sentence summary for the feed view
    sentences = [s.strip() for s in article_text.replace("\n", " ").split(".")[:2]]
    feed_summary = ". ".join(s for s in sentences if s) + "."

    return GeneratedArticle(
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        source_name=item["source"],
        source_url=item["url"],
        source_date=item["date"],
        title=item["title"],
        jurisdiction=jurisdiction,
        topic=topic,
        summary=feed_summary,
        full_article=article_text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


def articles_today(items: list[GeneratedArticle]) -> int:
    today = dt.date.today().isoformat()
    return sum(1 for a in items if a.generated_at.startswith(today))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate jurisdictional news articles from RSS feeds")
    parser.add_argument("--max", type=int, default=1, help="Maximum articles to generate this run")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated; don't call API")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Skipping.")
        return 1

    existing = load_generated()
    today_count = articles_today(existing)
    if today_count >= MAX_PER_DAY:
        print(f"Daily cap reached ({today_count}/{MAX_PER_DAY}). No articles generated.")
        return 0

    remaining_budget = min(args.max, MAX_PER_DAY - today_count)
    if remaining_budget <= 0:
        print(f"Already at daily cap ({today_count}/{MAX_PER_DAY}).")
        return 0

    print(f"Today: {today_count}/{MAX_PER_DAY} articles. Budget for this run: up to {remaining_budget}.")

    seen_urls = {a.source_url for a in existing}
    candidates = collect_candidate_items()
    fresh = [c for c in candidates if c["url"] not in seen_urls]
    print(f"Found {len(candidates)} RSS candidates ({len(fresh)} fresh, {len(candidates) - len(fresh)} already processed).")

    if not fresh:
        print("Nothing new to write up. Sleeping until next run.")
        return 0

    # Sort: prefer items closest to today
    fresh.sort(key=lambda c: c["date"], reverse=True)
    pick = fresh[:remaining_budget]

    if args.dry_run:
        print(f"DRY RUN — would generate {len(pick)} article(s):")
        for c in pick:
            print(f"  - [{c['date']}] {c['source']}: {c['title'][:80]}")
        return 0

    client = Anthropic()
    new_articles: list[GeneratedArticle] = []
    total_in = 0
    total_out = 0
    for i, item in enumerate(pick, 1):
        try:
            print(f"[{i}/{len(pick)}] Generating: {item['title'][:80]}")
            article = generate_article(client, item)
            new_articles.append(article)
            total_in += article.input_tokens
            total_out += article.output_tokens
            print(f"          → jurisdiction={article.jurisdiction}, topic={article.topic}, "
                  f"tokens={article.input_tokens}+{article.output_tokens}")
            time.sleep(1)  # gentle rate limit
        except Exception as e:
            print(f"          ERROR: {type(e).__name__}: {e}")
            continue

    if new_articles:
        save_generated(existing + new_articles)
        cost_estimate = (total_in / 1_000_000) * 3 + (total_out / 1_000_000) * 15  # Sonnet pricing
        print(f"\nSaved {len(new_articles)} new article(s). "
              f"Tokens this run: {total_in:,} in / {total_out:,} out (~${cost_estimate:.3f}).")
        print(f"Today's total: {today_count + len(new_articles)}/{MAX_PER_DAY}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
