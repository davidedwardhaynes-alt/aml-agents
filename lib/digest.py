"""Daily digest builder — assemble the HTML email body for a subscriber.

Pulls from the same lib functions the live app uses so the digest content
matches what the user sees in the UI:

- lib.news.items_for(...) — curated + LLM-generated + (optionally) live
- lib.obligations.load_obligations()
- lib.horizon.all_items_for(...)

Output is a self-contained HTML string designed to render in mainstream
email clients (Apple Mail, Gmail, Outlook 365). Inline CSS only — no
<link>, no <script>, no images other than emoji glyphs. The brand
typography matches the app: SF Pro stack with conservative fallbacks for
older Outlook.
"""

from __future__ import annotations

import datetime as dt
import html
from dataclasses import dataclass
from typing import Iterable

from lib.horizon import all_items_for_jurisdiction
from lib.news import items_for as news_items_for
from lib.obligations import Obligation, load_obligations
from lib.subscriptions import Subscription


# --- Style tokens -----------------------------------------------------------
# Apple-style palette + typography, inlined for email clients that strip
# external CSS. Outlook 365 honours inline styles only.
STYLE = {
    "font_stack": (
        "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', "
        "Arial, sans-serif"
    ),
    "canvas": "#F5F5F7",
    "surface": "#FFFFFF",
    "hairline": "#E5E5EA",
    "text": "#1D1D1F",
    "secondary": "#6E6E73",
    "tertiary": "#86868B",
    "accent": "#0071E3",
    "accent_soft": "rgba(0,113,227,0.10)",
}


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _css(d: dict[str, str]) -> str:
    return "; ".join(f"{k}: {v}" for k, v in d.items())


@dataclass
class DigestPayload:
    subject: str
    text: str
    html: str
    sections: dict[str, int]  # counts per section (news, obligations, horizon)


# ---------------------------------------------------------------------------
# Helpers — filter utilities that respect the subscriber's chosen
# jurisdictions and topics. Empty filters mean "all".
# ---------------------------------------------------------------------------
def _matches(values: list[str], allowed: Iterable[str]) -> bool:
    if not allowed:
        return True
    return any(v in allowed for v in values) if isinstance(values, list) else (values in allowed)


# ---------------------------------------------------------------------------
# Section builders — each returns (html_block, item_count). Empty sections
# are omitted so subscribers don't get a wall of "No items today" rows.
# ---------------------------------------------------------------------------

def _news_block(sub: Subscription, today: dt.date) -> tuple[str, int]:
    """Pull news items matching the subscriber's filters. Take only items
    dated within the last 14 days so the digest is genuinely 'latest'."""
    items, _statuses = news_items_for(
        jurisdiction="All jurisdictions",
        topic="All topics",
        include_live=False,
    )
    cutoff = (today - dt.timedelta(days=14)).isoformat()
    selected = []
    for it in items:
        if it.date and it.date < cutoff:
            continue
        if sub.jurisdictions and it.jurisdiction not in sub.jurisdictions:
            continue
        if sub.topics and it.topic not in sub.topics:
            continue
        selected.append(it)
        if len(selected) >= 8:
            break

    if not selected:
        return "", 0

    rows = []
    for it in selected:
        topic_label = (it.topic or "").split(" / ")[0] or "News"
        rows.append(
            f'''
<tr>
  <td style="padding: 12px 0; border-bottom: 1px solid {STYLE['hairline']};">
    <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: {STYLE['accent']}; margin-bottom: 4px;">
      {_esc(it.date)} · {_esc(it.jurisdiction)} · {_esc(topic_label)}
    </div>
    <div style="font-size: 15px; font-weight: 600; color: {STYLE['text']}; line-height: 1.35; margin-bottom: 6px;">
      {_esc(it.title)}
    </div>
    <div style="font-size: 13px; color: {STYLE['secondary']}; line-height: 1.5; margin-bottom: 6px;">
      {_esc((it.summary or '')[:280])}{'…' if it.summary and len(it.summary) > 280 else ''}
    </div>
    <div style="font-size: 12px;">
      <a href="{_esc(it.url)}" style="color: {STYLE['accent']}; text-decoration: none;">Read more →</a>
      <span style="color: {STYLE['tertiary']}; margin-left: 8px;">{_esc(it.source)}</span>
    </div>
  </td>
</tr>'''
        )

    block = (
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 24px;">'
        f'<tr><td style="padding-bottom: 8px; border-bottom: 2px solid {STYLE["text"]};">'
        f'<div style="font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase; color: {STYLE["text"]};">'
        f'Jurisdictional news · {len(selected)}</div>'
        f'</td></tr>'
        + "".join(rows)
        + '</table>'
    )
    return block, len(selected)


def _obligations_block(sub: Subscription, today: dt.date) -> tuple[str, int]:
    """Obligations due within the next 60 days, optionally jurisdiction-
    filtered."""
    obs: list[Obligation] = load_obligations()
    horizon = (today + dt.timedelta(days=60)).isoformat()

    selected = []
    for o in obs:
        if sub.jurisdictions and o.jurisdiction not in sub.jurisdictions:
            continue
        if not o.due_date:
            continue
        if o.due_date > horizon:
            continue
        if o.status == "Closed":
            continue
        selected.append(o)
    selected.sort(key=lambda o: (o.due_date, o.jurisdiction))
    if not selected:
        return "", 0

    rows = []
    for o in selected[:6]:
        try:
            due = dt.date.fromisoformat(o.due_date)
            days_left = (due - today).days
            if days_left < 0:
                deadline_chip = (
                    f'<span style="background: #FFE5E5; color: #C92A2A; padding: 2px 8px; '
                    f'border-radius: 980px; font-size: 11px; font-weight: 600;">'
                    f'Overdue {-days_left}d</span>'
                )
            elif days_left <= 14:
                deadline_chip = (
                    f'<span style="background: #FFF4E5; color: #B45309; padding: 2px 8px; '
                    f'border-radius: 980px; font-size: 11px; font-weight: 600;">'
                    f'Due in {days_left}d</span>'
                )
            else:
                deadline_chip = (
                    f'<span style="background: {STYLE["accent_soft"]}; color: {STYLE["accent"]}; '
                    f'padding: 2px 8px; border-radius: 980px; font-size: 11px; font-weight: 600;">'
                    f'Due in {days_left}d</span>'
                )
        except ValueError:
            deadline_chip = ""

        rows.append(
            f'''
<tr>
  <td style="padding: 12px 0; border-bottom: 1px solid {STYLE['hairline']};">
    <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: {STYLE['secondary']}; margin-bottom: 4px;">
      {_esc(o.jurisdiction)} · Due {_esc(o.due_date)} {deadline_chip}
    </div>
    <div style="font-size: 15px; font-weight: 600; color: {STYLE['text']}; line-height: 1.35; margin-bottom: 6px;">
      {_esc(o.title)}
    </div>
    <div style="font-size: 13px; color: {STYLE['secondary']}; line-height: 1.5;">
      {_esc(o.description or '')}
    </div>
    {f'<div style="font-size: 12px; color: {STYLE["tertiary"]}; margin-top: 6px;">Reference: {_esc(o.statute_or_notice)}</div>' if o.statute_or_notice else ''}
  </td>
</tr>'''
        )

    block = (
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 32px;">'
        f'<tr><td style="padding-bottom: 8px; border-bottom: 2px solid {STYLE["text"]};">'
        f'<div style="font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase; color: {STYLE["text"]};">'
        f'Obligations due · next 60 days · {len(selected)}</div>'
        f'</td></tr>'
        + "".join(rows)
        + '</table>'
    )
    return block, len(selected)


def _horizon_block(sub: Subscription, today: dt.date) -> tuple[str, int]:
    """Horizon-scanning items, jurisdiction-filtered."""
    items, _statuses = all_items_for_jurisdiction(
        jurisdiction=None,
        include_live=False,
    )
    selected = []
    for it in items:
        if sub.jurisdictions and it.jurisdiction not in sub.jurisdictions:
            continue
        selected.append(it)
        if len(selected) >= 5:
            break

    if not selected:
        return "", 0

    rows = []
    for it in selected:
        rows.append(
            f'''
<tr>
  <td style="padding: 12px 0; border-bottom: 1px solid {STYLE['hairline']};">
    <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: {STYLE['secondary']}; margin-bottom: 4px;">
      {_esc(it.date)} · {_esc(it.jurisdiction)} · Impact: {_esc(it.impact or 'Standard')}
    </div>
    <div style="font-size: 15px; font-weight: 600; color: {STYLE['text']}; line-height: 1.35; margin-bottom: 6px;">
      {_esc(it.title)}
    </div>
    <div style="font-size: 13px; color: {STYLE['secondary']}; line-height: 1.5;">
      {_esc((it.summary or '')[:240])}{'…' if it.summary and len(it.summary) > 240 else ''}
    </div>
  </td>
</tr>'''
        )

    block = (
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 32px;">'
        f'<tr><td style="padding-bottom: 8px; border-bottom: 2px solid {STYLE["text"]};">'
        f'<div style="font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase; color: {STYLE["text"]};">'
        f'Horizon scanning · {len(selected)}</div>'
        f'</td></tr>'
        + "".join(rows)
        + '</table>'
    )
    return block, len(selected)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_digest(
    sub: Subscription,
    *,
    today: dt.date | None = None,
    base_url: str = "https://amlagents.streamlit.app",
) -> DigestPayload:
    """Render the digest payload for one subscriber. Returns the subject,
    plain-text fallback, and the HTML body."""
    today = today or dt.date.today()

    sections = {"news": 0, "obligations": 0, "horizon": 0}
    blocks: list[str] = []

    if sub.include_news:
        block, n = _news_block(sub, today)
        sections["news"] = n
        if block:
            blocks.append(block)
    if sub.include_obligations:
        block, n = _obligations_block(sub, today)
        sections["obligations"] = n
        if block:
            blocks.append(block)
    if sub.include_horizon:
        block, n = _horizon_block(sub, today)
        sections["horizon"] = n
        if block:
            blocks.append(block)

    total = sum(sections.values())
    parts = [
        f"news ({sections['news']})" if sections["news"] else "",
        f"obligations ({sections['obligations']})" if sections["obligations"] else "",
        f"horizon ({sections['horizon']})" if sections["horizon"] else "",
    ]
    summary = " · ".join(p for p in parts if p) or "no items today"
    subject = f"AML Agents daily — {today.isoformat()} — {summary}"

    if total == 0:
        body_html = (
            f'<div style="padding: 32px; text-align: center; color: {STYLE["secondary"]}; '
            f'font-family: {STYLE["font_stack"]};">'
            f'<p style="margin: 0; font-size: 15px;">No new items match your filters today.</p>'
            f'<p style="margin: 8px 0 0 0; font-size: 13px;">'
            f'Adjust your subscription preferences anytime — see footer.</p>'
            f'</div>'
        )
    else:
        body_html = "".join(blocks)

    unsub_url = f"{base_url}/?unsubscribe={sub.unsubscribe_token}"

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background: {STYLE['canvas']}; font-family: {STYLE['font_stack']};">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: {STYLE['canvas']};">
<tr>
<td align="center" style="padding: 24px 12px;">
<table cellpadding="0" cellspacing="0" border="0" width="640" style="max-width: 640px; background: {STYLE['surface']}; border: 1px solid {STYLE['hairline']}; border-radius: 16px;">
<tr>
<td style="padding: 32px 32px 0 32px;">

<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td>
<div style="font-size: 11px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase; color: {STYLE['accent']};">
AML Agents · Daily digest
</div>
<h1 style="margin: 6px 0 4px 0; font-size: 26px; line-height: 1.2; letter-spacing: -0.026em; font-weight: 700; color: {STYLE['text']};">
{_esc(today.strftime('%A, %d %B %Y'))}
</h1>
<div style="font-size: 13px; color: {STYLE['secondary']};">
{_esc(sub.label_timezone())} · {_esc(', '.join(sub.jurisdictions) if sub.jurisdictions else 'All 6 jurisdictions')}
</div>
</td>
</tr>
</table>

{body_html}

</td>
</tr>
<tr>
<td style="padding: 24px 32px 32px 32px; border-top: 1px solid {STYLE['hairline']}; margin-top: 24px;">
<div style="font-size: 12px; color: {STYLE['tertiary']}; line-height: 1.55;">
Sent to <strong>{_esc(sub.email)}</strong> at 07:00 {_esc(sub.label_timezone())} by AML Agents.<br>
<a href="{base_url}" style="color: {STYLE['accent']}; text-decoration: none;">Open AML Agents →</a>
&nbsp;·&nbsp;
<a href="{_esc(unsub_url)}" style="color: {STYLE['tertiary']}; text-decoration: underline;">Unsubscribe</a>
&nbsp;·&nbsp;
<a href="{base_url}" style="color: {STYLE['tertiary']}; text-decoration: underline;">Manage preferences</a>
</div>
<div style="font-size: 11px; color: {STYLE['tertiary']}; margin-top: 12px;">
This digest aggregates publicly-available regulator notices, curated news, and the obligations register
configured for your account. It is informational only — confirm filing deadlines against the regulator's
authoritative source before acting.
</div>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>'''

    text_lines = [
        f"AML Agents — Daily digest — {today.isoformat()}",
        f"For {sub.email} at 07:00 {sub.label_timezone()}",
        "",
        f"Today's items: {summary}",
        "",
        f"Open AML Agents: {base_url}",
        f"Unsubscribe: {unsub_url}",
    ]
    text = "\n".join(text_lines)

    return DigestPayload(
        subject=subject,
        text=text,
        html=full_html,
        sections=sections,
    )
