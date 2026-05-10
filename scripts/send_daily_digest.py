"""Daily digest sender — runs from GitHub Actions cron at the UTC hours
that map to 7am local across the supported timezones.

For each subscription:
  1. Check whether `due_for_send` is True now (timezone-aware, idempotent).
  2. Build the digest HTML + plain-text fallback.
  3. Send via the Resend API if `RESEND_API_KEY` is set; otherwise log a
     stub line so the cron run still verifies plumbing without sending.
  4. Mark the subscription as sent so we don't double-send.

Resend is the v0 transport because:
- generous free tier (3,000 emails/month, 100/day) suits a demo
- modern HTTPS+JSON API with strict TLS, DKIM/DMARC handled
- one secret to manage (RESEND_API_KEY)

Switch to SES / SendGrid / Mailgun later if volume warrants it — only
`_send_via_resend` needs to change.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

socket.setdefaulttimeout(30)

from lib.digest import build_digest  # noqa: E402
from lib.subscriptions import (  # noqa: E402
    Subscription,
    due_for_send,
    load_subscriptions,
    mark_sent,
)

# Resend HTTPS endpoint. No SDK dependency — keep the cron container small.
RESEND_ENDPOINT = "https://api.resend.com/emails"

# The "From" address. Until DNS for trustsphere.partners is set up with
# Resend, fall back to Resend's testing sender that works without DNS.
DEFAULT_FROM = os.getenv("RESEND_FROM", "AML Agents <onboarding@resend.dev>")
REPLY_TO = os.getenv("RESEND_REPLY_TO", "david@trustsphere.partners")


def _send_via_resend(
    *,
    api_key: str,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> tuple[bool, str]:
    """POST the email to Resend. Returns (ok, info_string)."""
    payload = {
        "from": DEFAULT_FROM,
        "to": [to],
        "reply_to": REPLY_TO,
        "subject": subject,
        "html": html_body,
        "text": text_body,
        # Email clients that strip <head> still get the right title via
        # the message-id and the "List-Unsubscribe" header for one-click
        # unsubscribe in Gmail / Apple Mail.
        "headers": {
            "List-Unsubscribe": (
                f"<{os.getenv('AML_AGENTS_BASE_URL', 'https://amlagents.streamlit.app')}>"
            ),
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
        "tags": [{"name": "category", "value": "daily-digest"}],
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Cloudflare sits in front of api.resend.com and blocks the
            # default urllib User-Agent (`Python-urllib/3.x`) with error
            # code 1010. A realistic UA + Accept pair gets through.
            "Accept": "application/json",
            "User-Agent": "AML-Agents-Daily/1.0 (+https://trustsphere.ai)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return True, f"sent ({resp.status}); resend_id={data[:120]}"
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        return False, f"HTTP {e.code}: {err_body[:200]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _send_one(
    sub: Subscription,
    *,
    api_key: str | None,
    dry_run: bool,
) -> tuple[bool, str]:
    """Build and (optionally) send one digest. Returns (ok, info_string)."""
    payload = build_digest(sub)
    counts = payload.sections
    summary = (
        f"news={counts.get('news', 0)} obs={counts.get('obligations', 0)} "
        f"horizon={counts.get('horizon', 0)}"
    )
    if dry_run:
        return True, f"[dry-run] would send to {sub.email}; {summary}"
    if not api_key:
        return True, f"[stub: no RESEND_API_KEY] would send to {sub.email}; {summary}"

    ok, info = _send_via_resend(
        api_key=api_key,
        to=sub.email,
        subject=payload.subject,
        html_body=payload.html,
        text_body=payload.text,
    )
    if ok:
        mark_sent(sub.id)
    return ok, f"{info}; {summary}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Daily digest sender")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build digests but do not call Resend.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Bypass the timezone / 7am gate and send to all active "
            "subscribers right now. For manual smoke-testing."
        ),
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Only send to a single email address (case-insensitive).",
    )
    args = parser.parse_args()

    api_key = os.getenv("RESEND_API_KEY")
    subs = load_subscriptions()
    print(f"Loaded {len(subs)} subscription(s).")
    if not subs:
        print("Nothing to do.")
        return 0

    sent = 0
    skipped = 0
    failed = 0
    for sub in subs:
        if args.only and sub.email.lower() != args.only.lower():
            continue
        if not args.force and not due_for_send(sub):
            skipped += 1
            continue
        ok, info = _send_one(sub, api_key=api_key, dry_run=args.dry_run)
        flag = "✓" if ok else "✗"
        print(f"{flag} {sub.email} ({sub.label_timezone()}) — {info}")
        if ok:
            sent += 1
        else:
            failed += 1

    print(
        f"\nSummary: {sent} sent · {skipped} skipped (off-window) · {failed} failed."
    )
    print(f"Time UTC: {dt.datetime.utcnow().isoformat(timespec='seconds')}Z")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
