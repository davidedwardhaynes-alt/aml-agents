"""One-off: generate full_article long-form content for curated NEWS_ITEMS that lack it.

Identifies NEWS_ITEMS in lib/news.py without a full_article= field, generates a
250-400 word FT/Regulation-Asia-voice analysis via Claude Sonnet, and rewrites
the file in place.

Run once. After running, all 32 curated items will have Read more long-form content.
"""

from __future__ import annotations

import os
import re
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

socket.setdefaulttimeout(30)

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from lib.news import NEWS_ITEMS  # noqa: E402

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1100

PROMPT_SYSTEM = """You are a senior financial-crime journalist writing for an audience of \
MLROs, Heads of FCC, AML supervisors, and compliance professionals. Voice: Financial Times, \
The Economist, top-tier regulatory analysis. Authoritative, balanced, specific. No hyperbole. \
No "shocking" or "groundbreaking." Reference real regulatory frameworks (FATF Recommendations, \
MAS Notices, OSCO, AMLA, AML/CTF Act sections, etc.) where relevant.

Structure:
- Lead paragraph: concrete fact + immediate implication
- Context paragraph: regulatory or market history that frames the news
- Multiple stakeholder perspectives or implications
- Forward-looking closing observation

Length: 250-400 words. Output ONLY the article body in markdown paragraphs. No meta-commentary, \
no headlines, no "Here is the article:" preamble."""


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set.")
        return 1

    items_to_expand = [i for i in NEWS_ITEMS if not i.full_article]
    print(f"Found {len(items_to_expand)} curated items lacking full_article")
    if not items_to_expand:
        print("Nothing to do.")
        return 0

    client = Anthropic()
    file_path = ROOT / "lib" / "news.py"
    content = file_path.read_text()

    total_in = 0
    total_out = 0
    n_updated = 0

    for i, item in enumerate(items_to_expand, 1):
        prompt = (
            f"Source publication: {item.source}\n"
            f"Date: {item.date}\n"
            f"Jurisdiction: {item.jurisdiction}\n"
            f"Topic: {item.topic}\n"
            f"Headline: {item.title}\n"
            f"Summary so far: {item.summary}\n"
            f"Source URL: {item.url}\n\n"
            f"Write the analysis article."
        )
        try:
            print(f"[{i}/{len(items_to_expand)}] {item.title[:70]}", flush=True)
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=PROMPT_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            article_text = response.content[0].text.strip()
            total_in += response.usage.input_tokens
            total_out += response.usage.output_tokens

            # Locate this NewsItem in the file by date+title and inject full_article
            # Find a NewsItem block whose date and title match
            date_str = item.date
            title_first_8_words = " ".join(item.title.split()[:8])

            # Search for "NewsItem(" blocks; check each
            updated_this = False
            i_search = 0
            while True:
                idx = content.find("NewsItem(", i_search)
                if idx < 0:
                    break
                # Find matching )
                depth = 0
                j = idx
                in_str = False
                str_ch = ""
                end = -1
                while j < len(content):
                    ch = content[j]
                    if in_str:
                        if ch == "\\":
                            j += 2
                            continue
                        if ch == str_ch:
                            in_str = False
                    else:
                        if ch in '"\'':
                            in_str = True
                            str_ch = ch
                        elif ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth -= 1
                            if depth == 0:
                                end = j
                                break
                    j += 1
                if end < 0:
                    break
                block = content[idx:end + 1]
                # Match by date string AND a unique fragment of the title
                if (
                    f'date="{date_str}"' in block
                    and title_first_8_words in block.replace("\\", "")
                    and "full_article=" not in block
                ):
                    # Insert before the closing )
                    article_repr = repr(article_text)
                    inner = block[:-1].rstrip()
                    if not inner.endswith(","):
                        inner += ","
                    new_block = inner + f"\n        full_article={article_repr},\n    )"
                    content = content[:idx] + new_block + content[end + 1:]
                    updated_this = True
                    n_updated += 1
                    break
                i_search = end + 1

            if not updated_this:
                print(f"          (could not locate item in source)")
            time.sleep(0.5)
        except Exception as e:
            print(f"          ERROR: {type(e).__name__}: {e}")
            continue

    file_path.write_text(content)
    cost = (total_in / 1_000_000) * 3 + (total_out / 1_000_000) * 15
    print(f"\nUpdated {n_updated} NEWS_ITEM entries with full_article.")
    print(f"Tokens: {total_in:,} in / {total_out:,} out (~${cost:.3f}).")

    # Quick syntax check after rewrite
    import ast
    try:
        ast.parse(file_path.read_text())
        print("Syntax check: OK")
    except SyntaxError as e:
        print(f"SYNTAX ERROR INTRODUCED: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
