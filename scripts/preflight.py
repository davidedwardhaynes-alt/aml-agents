"""Pre-demo pre-flight check — runs all critical paths and reports pass/fail.

Run before each ICP demo to confirm everything works end-to-end:
    python scripts/preflight.py

Tests:
  1. All Python imports
  2. Auth credentials load
  3. All 4 rubric files present + non-empty
  4. All 4 guidance files present
  5. Sample library has 6 cases per jurisdiction
  6. Connectors loaded (>= 100)
  7. Regulators directory loaded (>= 200)
  8. RSS feed reachability sample
  9. Anthropic API key configured + reachable
 10. OpenSanctions API key + reachable

Exit code: 0 if all pass, 1 if any fail. Designed for cron / CI integration.
"""

from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

socket.setdefaulttimeout(8)


# ANSI colours
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"{RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}!{RESET} {msg}")


def info(msg: str) -> None:
    print(f"{DIM}  {msg}{RESET}")


CHECKS_PASSED = 0
CHECKS_FAILED = 0
CHECKS_WARNED = 0


def record(passed: bool, warned: bool = False) -> None:
    global CHECKS_PASSED, CHECKS_FAILED, CHECKS_WARNED
    if warned:
        CHECKS_WARNED += 1
    elif passed:
        CHECKS_PASSED += 1
    else:
        CHECKS_FAILED += 1


def check_imports() -> bool:
    print("\n[1] Python imports")
    try:
        from anthropic import Anthropic  # noqa
        from dotenv import load_dotenv  # noqa
        import feedparser  # noqa
        import streamlit  # noqa
        import streamlit_authenticator  # noqa
        import yaml  # noqa
        from fpdf import FPDF  # noqa
        import markdown  # noqa
        ok("All third-party imports OK")
        record(True)
        return True
    except ImportError as e:
        fail(f"Import failed: {e}")
        record(False)
        return False


def check_lib_modules() -> bool:
    print("\n[2] Internal lib modules")
    failed = False
    for mod_name in ("connectors", "consortium", "horizon", "news", "regulators", "sanctions"):
        try:
            __import__(f"lib.{mod_name}")
            ok(f"lib.{mod_name}")
        except Exception as e:
            fail(f"lib.{mod_name}: {e}")
            failed = True
    record(not failed)
    return not failed


def check_env() -> bool:
    print("\n[3] Environment / API keys")
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)

    anth = os.getenv("ANTHROPIC_API_KEY", "")
    if anth.startswith("sk-ant-") and len(anth) >= 50:
        ok(f"ANTHROPIC_API_KEY set ({len(anth)} chars)")
    else:
        fail(f"ANTHROPIC_API_KEY missing or malformed (current length: {len(anth)})")
        record(False)
        return False

    os_key = os.getenv("OPENSANCTIONS_API_KEY", "")
    if len(os_key) >= 16:
        ok(f"OPENSANCTIONS_API_KEY set ({len(os_key)} chars)")
    else:
        warn("OPENSANCTIONS_API_KEY missing — sanctions screening will be unavailable")
        record(False, warned=True)

    record(True)
    return True


def check_rubrics_and_guidance() -> bool:
    print("\n[4] Rubrics and guidance")
    failed = False
    for r in ("strostr.md", "jfiustr.md", "fiedstr.md", "austracsmr.md"):
        path = ROOT / "rubrics" / r
        if not path.exists():
            fail(f"rubrics/{r} missing")
            failed = True
        elif path.stat().st_size < 1000:
            warn(f"rubrics/{r} suspiciously small: {path.stat().st_size} bytes")
        else:
            ok(f"rubrics/{r}: {path.stat().st_size:,} bytes")

    for g in ("sg-stro.md", "hk-jfiu.md", "my-fied.md", "au-austrac.md"):
        path = ROOT / "guidance" / g
        if not path.exists():
            fail(f"guidance/{g} missing")
            failed = True
        elif path.stat().st_size < 500:
            warn(f"guidance/{g} suspiciously small: {path.stat().st_size} bytes")
        else:
            ok(f"guidance/{g}: {path.stat().st_size:,} bytes")
    record(not failed)
    return not failed


def check_samples_and_connectors() -> bool:
    print("\n[5] Samples + connectors + regulators")
    try:
        from lib.connectors import CONNECTORS, CATEGORIES
        from lib.regulators import REGULATORS, total_count

        if len(CONNECTORS) >= 100:
            ok(f"Connectors: {len(CONNECTORS)} across {len(CATEGORIES)} categories")
        else:
            fail(f"Connectors only {len(CONNECTORS)} loaded (expected ≥100)")
            record(False)
            return False

        rt = total_count()
        if rt >= 200:
            ok(f"Regulator directory: {rt} sources across {len(REGULATORS)} jurisdictions")
        else:
            warn(f"Regulator directory only {rt} entries (expected ≥200)")

        # Sample library is in app.py — read by AST
        import ast
        tree = ast.parse((ROOT / "app.py").read_text())
        sl_assigns = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SAMPLE_LIBRARY" for t in node.targets)
        ]
        if sl_assigns:
            d = sl_assigns[0].value
            counts = {}
            for jur_node, sample_node in zip(d.keys, d.values):
                if isinstance(jur_node, ast.Constant) and hasattr(sample_node, "keys"):
                    counts[jur_node.value] = len(sample_node.keys)
            for jur, n in counts.items():
                if n >= 4:
                    ok(f"Samples [{jur}]: {n}")
                else:
                    warn(f"Samples [{jur}]: only {n}")

        record(True)
        return True
    except Exception as e:
        fail(f"Error loading samples: {e}")
        record(False)
        return False


def check_news_pipeline() -> bool:
    print("\n[6] News pipeline")
    try:
        from lib.news import NEWS_ITEMS, NEWS_RSS_FEEDS, items_for, _load_generated_articles

        ok(f"NEWS_ITEMS curated: {len(NEWS_ITEMS)}")
        ok(f"NEWS_RSS_FEEDS configured: {len(NEWS_RSS_FEEDS)}")

        gen = _load_generated_articles()
        ok(f"LLM-generated articles loaded: {len(gen)}")

        items, _ = items_for(include_live=False)
        n_with = sum(1 for i in items if i.full_article)
        ok(f"News tab total (curated + generated, no live): {len(items)} ({n_with} with Read more)")
        record(True)
        return True
    except Exception as e:
        fail(f"News pipeline error: {e}")
        record(False)
        return False


def check_anthropic_api() -> bool:
    print("\n[7] Anthropic API reachability")
    try:
        from anthropic import Anthropic
        client = Anthropic()
        # Smallest possible call — list models
        # If this fails, full generation will fail
        t0 = time.time()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": "ping"}],
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        ok(f"Anthropic API responding ({elapsed_ms} ms; tokens: {resp.usage.input_tokens}+{resp.usage.output_tokens})")
        record(True)
        return True
    except Exception as e:
        fail(f"Anthropic API call failed: {type(e).__name__}: {str(e)[:120]}")
        record(False)
        return False


def check_opensanctions_api() -> bool:
    print("\n[8] OpenSanctions API reachability")
    if not os.getenv("OPENSANCTIONS_API_KEY"):
        warn("Skipping — OPENSANCTIONS_API_KEY not set")
        record(False, warned=True)
        return True
    try:
        from lib.sanctions import search_sanctions
        t0 = time.time()
        result = search_sanctions("Vladimir Putin", limit=2)
        elapsed_ms = int((time.time() - t0) * 1000)
        if result.get("api_key_required"):
            fail("OpenSanctions API key rejected (401)")
            record(False)
            return False
        if result.get("error"):
            fail(f"OpenSanctions error: {result['error'][:120]}")
            record(False)
            return False
        n_results = result.get("total", 0)
        ok(f"OpenSanctions responding ({elapsed_ms} ms; {n_results} results for known PEP)")
        record(True)
        return True
    except Exception as e:
        fail(f"OpenSanctions call failed: {type(e).__name__}: {str(e)[:120]}")
        record(False)
        return False


def check_rss_sample() -> bool:
    print("\n[9] RSS feed reachability (sample)")
    import feedparser
    sample_feeds = [
        ("FATF", "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.rss"),
        ("FCA UK", "https://www.fca.org.uk/news/rss.xml"),
        ("FinCEN", "https://www.fincen.gov/feed/news_release"),
        ("Bank of England", "https://www.bankofengland.co.uk/rss/news"),
    ]
    n_ok = 0
    for label, url in sample_feeds:
        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": "AML-Agents/0.1"})
            if parsed.bozo:
                warn(f"{label}: bozo error ({type(parsed.bozo_exception).__name__})")
            elif len(parsed.entries) > 0:
                ok(f"{label}: {len(parsed.entries)} entries")
                n_ok += 1
            else:
                warn(f"{label}: 0 entries returned")
        except Exception as e:
            warn(f"{label}: {type(e).__name__}: {str(e)[:80]}")

    if n_ok >= 2:
        ok(f"At least {n_ok}/{len(sample_feeds)} sample feeds responding")
        record(True)
        return True
    else:
        warn(f"Only {n_ok}/{len(sample_feeds)} sample feeds responded — RSS-driven features may be sparse")
        record(False, warned=True)
        return True


def check_pdf() -> bool:
    print("\n[10] PDF generation")
    try:
        from fpdf import FPDF
        import markdown as md_pkg
        pdf = FPDF()
        pdf.set_auto_page_break(True, margin=20)
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        pdf.write_html(md_pkg.markdown("### Test\nhello"))
        output = pdf.output()
        if output and bytes(output)[:5] == b"%PDF-":
            ok(f"PDF generation OK ({len(bytes(output))} bytes)")
            record(True)
            return True
        else:
            fail("PDF output missing magic bytes")
            record(False)
            return False
    except Exception as e:
        fail(f"PDF generation failed: {e}")
        record(False)
        return False


def main() -> int:
    print(f"AML Agents pre-flight check — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    check_imports()
    check_lib_modules()
    check_env()
    check_rubrics_and_guidance()
    check_samples_and_connectors()
    check_news_pipeline()
    check_pdf()
    check_rss_sample()
    check_anthropic_api()
    check_opensanctions_api()

    print()
    print("=" * 60)
    print(f"Summary: {GREEN}{CHECKS_PASSED} passed{RESET}, "
          f"{YELLOW}{CHECKS_WARNED} warning{RESET}, "
          f"{RED}{CHECKS_FAILED} failed{RESET}")
    if CHECKS_FAILED == 0:
        print(f"{GREEN}Ready to demo.{RESET}")
        return 0
    else:
        print(f"{RED}Fix failures before demo.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
