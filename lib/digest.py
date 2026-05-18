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
# Fireside palette — warm amber/ember/cream. Inline only (email clients
# strip <style>). Body font sans for compatibility; serif accent on the
# masthead and pull-quotes for a "briefing memo" feel.
STYLE = {
    "font_stack": (
        "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', "
        "Arial, sans-serif"
    ),
    "serif_stack": (
        "'Iowan Old Style', 'Charter', Georgia, 'Times New Roman', serif"
    ),
    # Surfaces
    "canvas": "#1A0F0A",          # the dark "outside" — only visible at the page margin
    "surface": "#FBF5EC",          # warm cream — main card body
    "footer_surface": "#F4ECE0",  # slightly darker cream — footer band
    # Brand
    "accent": "#8C3B1F",           # ember red — links + section accents
    "accent_warm": "#D26E3A",      # amber — gradient stops
    "accent_soft": "rgba(140,59,31,0.10)",
    "ember_glow": "#FF8A3D",       # bright orange — gradient highlight
    "night": "#1A0A05",            # near-black — armchair silhouettes
    # Type
    "text": "#1F1A14",             # warm near-black body text
    "secondary": "#6E5A48",        # warm grey — captions
    "tertiary": "#9B8770",         # muted warm grey — disclaimers
    "hairline": "#E8DFD0",         # soft cream divider
    "hairline_warm": "#F0E7D6",   # softer divider inside sections
    # Risk badges (warmer take, still legible)
    "risk_critical_bg": "#F8D9CC",
    "risk_critical_fg": "#9C2018",
    "risk_warning_bg": "#FFEEDA",
    "risk_warning_fg": "#9A4F00",
    "risk_info_bg": "#FFF1E6",
    "risk_info_fg": "#8C3B1F",
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
  <td style="padding: 14px 0; border-bottom: 1px solid {STYLE['hairline_warm']};">
    <span style="display: inline-block; background: {STYLE['risk_info_bg']}; color: {STYLE['risk_info_fg']}; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 8px; border-radius: 4px;">{_esc(it.jurisdiction)} · {_esc(topic_label)}</span>
    <div style="font-size: 16px; font-weight: 600; color: {STYLE['text']}; line-height: 1.35; margin-top: 8px;">
      {_esc(it.title)}
    </div>
    <div style="font-size: 14px; color: {STYLE['secondary']}; line-height: 1.55; margin-top: 4px;">
      {_esc((it.summary or '')[:280])}{'…' if it.summary and len(it.summary) > 280 else ''}
    </div>
    <div style="font-size: 12px; margin-top: 8px;">
      <a href="{_esc(it.url)}" style="color: {STYLE['accent']}; text-decoration: none; font-weight: 600;">Read more →</a>
      <span style="color: {STYLE['tertiary']}; margin-left: 10px;">{_esc(it.date)} · {_esc(it.source)}</span>
    </div>
  </td>
</tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 8px 36px;">'
        f'<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: {STYLE["accent"]}; border-top: 1px solid {STYLE["hairline"]}; padding-top: 24px;">'
        f"If you'd rather read &nbsp;&middot;&nbsp; {len(selected)} stor{'y' if len(selected) == 1 else 'ies'}"
        f'</div>'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 8px;">'
        + "".join(rows)
        + '</table>'
        f'</td></tr>'
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
                chip_bg, chip_fg, chip_text = STYLE["risk_critical_bg"], STYLE["risk_critical_fg"], f"Overdue {-days_left}d"
            elif days_left <= 14:
                chip_bg, chip_fg, chip_text = STYLE["risk_warning_bg"], STYLE["risk_warning_fg"], f"Due in {days_left}d"
            else:
                chip_bg, chip_fg, chip_text = STYLE["risk_info_bg"], STYLE["risk_info_fg"], f"Due in {days_left}d"
            deadline_chip = (
                f'<span style="background: {chip_bg}; color: {chip_fg}; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 11px; font-weight: 700;">{chip_text}</span>'
            )
            due_display = due.strftime("%-d %b")
        except ValueError:
            deadline_chip = ""
            due_display = o.due_date

        priority_pill = ""
        if o.priority in ("Critical", "High"):
            priority_pill = (
                f'<span style="display: inline-block; background: {STYLE["risk_critical_bg"] if o.priority == "Critical" else STYLE["risk_warning_bg"]}; '
                f'color: {STYLE["risk_critical_fg"] if o.priority == "Critical" else STYLE["risk_warning_fg"]}; '
                f'font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; '
                f'padding: 2px 7px; border-radius: 4px; margin-right: 6px;">{_esc(o.priority)}</span>'
            )

        rows.append(
            f'''
<tr>
  <td style="padding: 12px 0; border-top: 1px solid {STYLE['hairline_warm']}; width: 70px; vertical-align: top; color: {STYLE['accent']}; font-weight: 700; letter-spacing: 0.08em; font-size: 12px;">
    {_esc(o.jurisdiction.split(' (')[0])}
  </td>
  <td style="padding: 12px 0; border-top: 1px solid {STYLE['hairline_warm']}; color: {STYLE['text']};">
    <div style="font-weight: 600; font-size: 14px; line-height: 1.4;">
      {priority_pill}{_esc(o.title)}
    </div>
    {f'<div style="color: {STYLE["secondary"]}; font-size: 12px; margin-top: 3px;">{_esc(o.statute_or_notice)}</div>' if o.statute_or_notice else ''}
  </td>
  <td style="padding: 12px 0; border-top: 1px solid {STYLE['hairline_warm']}; text-align: right; white-space: nowrap; color: {STYLE['text']}; font-weight: 600; font-size: 13px;">
    {_esc(due_display)}<br>
    <span style="color: {STYLE['secondary']}; font-weight: 400; font-size: 11px;">{deadline_chip}</span>
  </td>
</tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 8px 36px;">'
        f'<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: {STYLE["accent"]}; border-top: 1px solid {STYLE["hairline"]}; padding-top: 24px;">'
        f"On your calendar &nbsp;&middot;&nbsp; {len(selected)} filing{'' if len(selected) == 1 else 's'} due in 60 days"
        f'</div>'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 14px; font-size: 13px; border-collapse: collapse;">'
        + "".join(rows)
        + '</table>'
        f'</td></tr>'
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
  <td style="padding: 8px 0; font-size: 14px; line-height: 1.6; color: {STYLE['text']};">
    <strong style="color: {STYLE['accent']};">{_esc(it.jurisdiction)}</strong>
    <span style="color: {STYLE['tertiary']};"> &middot; {_esc(it.date)} &middot; impact {_esc(it.impact or 'Standard')}</span><br>
    <span style="color: {STYLE['text']};">{_esc(it.title)}</span>
    <span style="color: {STYLE['secondary']}; font-size: 13px;"> — {_esc((it.summary or '')[:200])}{'…' if it.summary and len(it.summary) > 200 else ''}</span>
  </td>
</tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 8px 36px;">'
        f'<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: {STYLE["accent"]}; border-top: 1px solid {STYLE["hairline"]}; padding-top: 24px;">'
        f"Looking ahead &nbsp;&middot;&nbsp; next 6 months"
        f'</div>'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 12px;">'
        + "".join(rows)
        + '</table>'
        f'</td></tr>'
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
    podcast_base: str = "https://raw.githubusercontent.com/davidedwardhaynes-alt/aml-agents/main/data/podcasts",
) -> DigestPayload:
    """Render the digest payload for one subscriber. Returns the subject,
    plain-text fallback, and the HTML body — in the fireside design.

    The hero block is a CSS-rendered fireside scene linking to the day's
    podcast MP3. The body is split into three section blocks (news,
    obligations, horizon) styled to match the fireside palette."""
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
    subject = f"TrustSphere · {today.strftime('%A %-d %B')} — {summary}"

    podcast_url = f"{podcast_base}/{today.isoformat()}.mp3"

    if total == 0:
        body_html = (
            f'<tr><td style="padding: 36px; text-align: center; color: {STYLE["secondary"]}; '
            f'font-family: {STYLE["font_stack"]};">'
            f'<p style="margin: 0; font-size: 15px;">Quiet morning — no new items match your filters today.</p>'
            f'<p style="margin: 8px 0 0 0; font-size: 13px;">'
            f'Adjust your subscription preferences anytime — see footer.</p>'
            f'</td></tr>'
        )
    else:
        body_html = "".join(blocks)

    unsub_url = f"{base_url}/?unsubscribe={sub.unsubscribe_token}"

    jurisdiction_label = ", ".join(sub.jurisdictions) if sub.jurisdictions else "All APAC jurisdictions"

    # --- Hero block — fireside video poster -----------------------------
    # Big circular play overlay + episode metadata. Click goes to today's
    # MP3 on raw.githubusercontent. If the MP3 doesn't exist yet (cron
    # race condition), the link 404s gracefully; we don't pre-check.
    hero_html = f'''
<tr><td style="padding: 32px 36px 16px 36px;">
<a href="{_esc(podcast_url)}" style="text-decoration: none; color: inherit;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-radius: 16px; overflow: hidden; background: radial-gradient(ellipse at 50% 78%, {STYLE['ember_glow']} 0%, {STYLE['accent_warm']} 22%, {STYLE['accent']} 48%, #3A1810 80%, {STYLE['night']} 100%);">
<tr><td style="padding: 0; height: 320px;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" height="320" style="height: 320px;">
<tr>
<td width="18%" style="vertical-align: bottom; padding: 0 0 0 36px;">
<div style="background: {STYLE['night']}; width: 70px; height: 110px; border-radius: 35px 35px 12px 12px; opacity: 0.85;"></div>
</td>
<td width="64%" style="vertical-align: middle; text-align: center; padding: 0 8px;">
<div style="font-family: {STYLE['serif_stack']}; font-size: 10px; font-weight: 700; letter-spacing: 0.30em; text-transform: uppercase; color: #FFE3C2; text-shadow: 0 1px 6px rgba(0,0,0,0.45);">TrustSphere · Fireside</div>
<div style="margin-top: 14px;">
<div style="display: inline-block; width: 76px; height: 76px; border-radius: 50%; background: rgba(255,255,255,0.95); color: {STYLE['accent']}; font-size: 30px; text-align: center; line-height: 74px; box-shadow: 0 10px 28px rgba(0,0,0,0.45);">▶</div>
</div>
<div style="margin-top: 16px; font-family: {STYLE['serif_stack']}; font-style: italic; font-size: 17px; line-height: 1.32; color: #FFFFFF; text-shadow: 0 1px 8px rgba(0,0,0,0.55); max-width: 420px; display: inline-block;">
Today's briefing — {_esc(today.strftime('%A %-d %B'))}
</div>
<div style="margin-top: 8px; font-size: 12px; color: #FFE3C2; letter-spacing: 0.06em;">Alex &amp; Jordan &nbsp;·&nbsp; 5 min</div>
</td>
<td width="18%" style="vertical-align: bottom; padding: 0 36px 0 0; text-align: right;">
<div style="display: inline-block; background: {STYLE['night']}; width: 70px; height: 110px; border-radius: 35px 35px 12px 12px; opacity: 0.85;"></div>
</td>
</tr>
</table>
</td></tr>
</table>
</a>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 14px;">
<tr>
<td style="vertical-align: middle;">
<div style="font-family: {STYLE['serif_stack']}; font-size: 11px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: {STYLE['accent']};">Today's fireside</div>
<div style="font-size: 13px; color: {STYLE['secondary']}; margin-top: 4px;">{_esc(summary)}</div>
</td>
<td style="vertical-align: middle; text-align: right; font-size: 11px; color: {STYLE['tertiary']};">
<a href="{_esc(podcast_url)}" style="color: {STYLE['accent']}; text-decoration: none; font-weight: 600;">▶ Audio</a> &nbsp;·&nbsp;
<a href="{base_url}" style="color: {STYLE['tertiary']}; text-decoration: underline;">Open dashboard</a>
</td>
</tr>
</table>
</td></tr>
'''

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<title>{_esc(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background: {STYLE['canvas']}; font-family: {STYLE['font_stack']}; color: {STYLE['text']};">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background: {STYLE['canvas']};">
<tr><td align="center" style="padding: 32px 12px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="640" style="max-width: 640px; background: {STYLE['surface']}; border-radius: 20px; overflow: hidden;">

<!-- Masthead -->
<tr><td style="background: linear-gradient(135deg, {STYLE['accent_warm']} 0%, {STYLE['accent']} 50%, #5A2410 100%); padding: 36px 36px 28px 36px; text-align: center; color: #FFFFFF;">
<div style="font-family: {STYLE['serif_stack']}; font-size: 11px; font-weight: 700; letter-spacing: 0.30em; text-transform: uppercase; color: #FFE9D4;">TrustSphere · Daily Briefing</div>
<h1 style="margin: 12px 0 6px 0; font-family: {STYLE['serif_stack']}; font-size: 34px; line-height: 1.06; letter-spacing: -0.018em; font-weight: 700; color: #FFFFFF; font-style: italic;">{_esc(today.strftime('%A, %-d %B %Y'))}</h1>
<div style="font-size: 13px; color: #FFE9D4; letter-spacing: 0.04em;">{_esc(sub.label_timezone())} &nbsp;·&nbsp; {_esc(jurisdiction_label)}</div>
</td></tr>

{hero_html}

{body_html}

<!-- Footer -->
<tr><td style="padding: 28px 36px 36px 36px; background: {STYLE['footer_surface']}; border-top: 1px solid {STYLE['hairline']};">
<div style="font-size: 12px; color: {STYLE['secondary']}; line-height: 1.7;">
Pulled up a chair for <strong style="color: {STYLE['text']};">{_esc(sub.email)}</strong> at 07:00 {_esc(sub.label_timezone())}.<br>
<a href="{base_url}" style="color: {STYLE['accent']}; text-decoration: none; font-weight: 600;">Open dashboard</a> &nbsp;·&nbsp;
<a href="{_esc(unsub_url)}" style="color: {STYLE['tertiary']}; text-decoration: underline;">Unsubscribe</a> &nbsp;·&nbsp;
<a href="{base_url}" style="color: {STYLE['tertiary']}; text-decoration: underline;">Manage preferences</a>
</div>
<div style="font-size: 11px; color: {STYLE['tertiary']}; margin-top: 14px; line-height: 1.55; font-style: italic;">
Informational only — confirm filing dates against the regulator's authoritative source before acting. The fireside conversation is generated from publicly-available regulator notices and curated industry news.
</div>
</td></tr>

</table>
<div style="font-family: {STYLE['serif_stack']}; font-size: 11px; color: {STYLE['tertiary']}; margin-top: 18px; letter-spacing: 0.06em; font-style: italic;">TrustSphere Partners · trustsphere.ai</div>
</td></tr>
</table>
</body>
</html>'''

    text_lines = [
        f"TrustSphere — Daily Briefing — {today.strftime('%A, %-d %B %Y')}",
        f"For {sub.email} at 07:00 {sub.label_timezone()}",
        "",
        f"Today's fireside: {summary}",
        "",
        f"Audio: {podcast_url}",
        f"Open dashboard: {base_url}",
        f"Unsubscribe: {unsub_url}",
    ]
    text = "\n".join(text_lines)

    return DigestPayload(
        subject=subject,
        text=text,
        html=full_html,
        sections=sections,
    )
