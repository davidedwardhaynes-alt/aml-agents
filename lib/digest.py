"""Daily digest builder — assemble the HTML email body for a subscriber.

Pulls from the same lib functions the live app uses so the digest content
matches what the user sees in the UI:

- lib.news.items_for(...) — curated + LLM-generated + (optionally) live
- lib.obligations.load_obligations()
- lib.horizon.all_items_for_jurisdiction(...)
- lib.podcast.latest_podcast() — for the hero video poster

Output is a self-contained HTML string designed to render in mainstream
email clients (Apple Mail, Gmail, Outlook 365). Inline CSS only — no
<link>, no <script>, no images other than emoji glyphs.

The visual language is "fireside" — warm gradient header, a 16:9 video
poster as the hero where the audio briefing is the *point* rather than a
footnote, then warm cream surfaces for the news / calendar / horizon
sections. See docs/email-wireframes/variant-d-fireside.html for the
static reference mockup this template was ported from.
"""

from __future__ import annotations

import datetime as dt
import html
from dataclasses import dataclass
from typing import Iterable

from lib.horizon import all_items_for_jurisdiction
from lib.news import items_for as news_items_for
from lib.obligations import Obligation, load_obligations
from lib.podcast import latest_podcast
from lib.subscriptions import Subscription


# --- Style tokens -----------------------------------------------------------
# Warm fireside palette — embers + cream paper. Inlined for email clients
# that strip external CSS. Outlook 365 honours inline styles only.
STYLE = {
    "font_stack": (
        "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', "
        "Arial, sans-serif"
    ),
    "serif_stack": "'Iowan Old Style', Georgia, 'Source Serif Pro', serif",
    "canvas_outer": "#1A0F0A",       # outer container, deep ember
    "canvas": "#FBF5EC",             # warm cream paper
    "surface": "#FFFFFF",
    "surface_warm": "#F4ECE0",
    "hairline": "#E8DFD0",
    "hairline_soft": "#F0E7D6",
    "text": "#1F1A14",
    "secondary": "#6E5A48",
    "tertiary": "#9B8770",
    "accent": "#8C3B1F",             # ember red
    "accent_warm": "#D26E3A",        # dusk orange
    "accent_soft": "#FFF1E6",        # warm jurisdictional badge bg
    "warn": "#A8501F",
}

REPO_RAW_BASE = (
    "https://raw.githubusercontent.com/"
    "davidedwardhaynes-alt/aml-agents/main"
)


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _css(d: dict[str, str]) -> str:
    return "; ".join(f"{k}: {v}" for k, v in d.items())


@dataclass
class DigestPayload:
    subject: str
    text: str
    html: str
    sections: dict[str, int]


# ---------------------------------------------------------------------------
# Helpers — filter utilities that respect the subscriber's chosen
# jurisdictions and topics. Empty filters mean "all".
# ---------------------------------------------------------------------------
def _matches(values: list[str], allowed: Iterable[str]) -> bool:
    if not allowed:
        return True
    return any(v in allowed for v in values) if isinstance(values, list) else (values in allowed)


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def _section_eyebrow(label: str) -> str:
    """The fireside-style 'eyebrow' label used to introduce each section."""
    return (
        f'<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; '
        f'font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; '
        f'color: {STYLE["accent"]}; border-top: 1px solid {STYLE["hairline"]}; '
        f'padding-top: 24px;">{_esc(label)}</div>'
    )


# ---------------------------------------------------------------------------
# Hero — the 16:9 fireside video poster. Click goes to today's MP3 (or the
# most recent committed MP3 if today's hasn't been generated yet). When a
# real video gets hosted, the click target swaps in two places.
# ---------------------------------------------------------------------------
def _hero_block(today: dt.date) -> str:
    pod = latest_podcast()
    if pod is None:
        # No podcast yet — render a simple text intro instead of an empty
        # hero so the email still leads with the brand.
        return (
            f'<tr><td style="padding: 24px 36px;">'
            f'<div style="font-family: {STYLE["serif_stack"]}; font-style: italic; '
            f'font-size: 16px; color: {STYLE["secondary"]}; text-align: center;">'
            f'Today\'s briefing is below — the audio edition will join from '
            f'tomorrow.</div></td></tr>'
        )

    mp3_url = f"{REPO_RAW_BASE}/data/podcasts/{pod.date}.mp3"
    feed_url = f"{REPO_RAW_BASE}/data/podcasts/feed.xml"
    duration = _format_duration(pod.duration_seconds)

    # Episode quote — pulled from the podcast title, fallback to a
    # generic line if the title isn't useful.
    quote = pod.title or "Today's briefing"
    if quote.startswith("AML Agents Briefing"):
        # Strip the boilerplate prefix so the quote feels like a real
        # episode title rather than a header.
        quote = today.strftime("%A %d %B")

    return f'''
<tr><td style="padding: 32px 36px 16px 36px;">
<a href="{_esc(mp3_url)}" style="text-decoration: none; color: inherit;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-radius: 16px; overflow: hidden; background: radial-gradient(ellipse at 50% 78%, #FF8A3D 0%, #D26E3A 22%, #8C3B1F 48%, #3A1810 80%, #1A0A05 100%);">
<tr><td style="padding: 0; height: 320px; background: radial-gradient(ellipse at 50% 78%, rgba(255,180,90,0.55) 0%, rgba(210,110,58,0.35) 22%, rgba(140,59,31,0.0) 50%);">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" height="320" style="height: 320px;">
<tr>
<td width="18%" style="vertical-align: bottom; padding: 0 0 0 36px;">
<div style="background: #1A0A05; width: 76px; height: 110px; border-radius: 38px 38px 12px 12px; opacity: 0.88;"></div>
</td>
<td width="64%" style="vertical-align: middle; text-align: center; padding: 0 8px;">
<div style="font-family: {STYLE["serif_stack"]}; font-size: 10px; font-weight: 700; letter-spacing: 0.30em; text-transform: uppercase; color: #FFE3C2; text-shadow: 0 1px 6px rgba(0,0,0,0.45);">TrustSphere · Fireside</div>
<div style="margin-top: 14px;">
<div style="display: inline-block; width: 76px; height: 76px; border-radius: 50%; background: rgba(255,255,255,0.95); color: {STYLE["accent"]}; font-size: 30px; text-align: center; line-height: 72px; box-shadow: 0 10px 32px rgba(0,0,0,0.45);">▶</div>
</div>
<div style="margin-top: 18px; font-family: {STYLE["serif_stack"]}; font-style: italic; font-size: 17px; line-height: 1.32; color: #FFFFFF; text-shadow: 0 1px 8px rgba(0,0,0,0.55); max-width: 420px; display: inline-block;">"{_esc(quote)}"</div>
<div style="margin-top: 10px; font-size: 12px; color: #FFE3C2; letter-spacing: 0.06em;">Alex &amp; Jordan{f" · {duration}" if duration else ""}</div>
</td>
<td width="18%" style="vertical-align: bottom; padding: 0 36px 0 0; text-align: right;">
<div style="display: inline-block; background: #1A0A05; width: 76px; height: 110px; border-radius: 38px 38px 12px 12px; opacity: 0.88;"></div>
</td>
</tr>
</table>
</td></tr>
</table>
</a>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 14px;">
<tr>
<td style="vertical-align: middle;">
<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: {STYLE["accent"]};">Today's fireside · {_esc(today.strftime("%A %d %B"))}</div>
<div style="font-size: 13px; color: {STYLE["secondary"]}; margin-top: 4px;">{_esc(duration) or "Audio briefing"} · transcript &amp; show notes below</div>
</td>
<td style="vertical-align: middle; text-align: right; font-size: 11px; color: {STYLE["tertiary"]};">
<a href="{_esc(mp3_url)}" style="color: {STYLE["accent"]}; text-decoration: none; font-weight: 600;">▶ Audio</a> &nbsp;·&nbsp;
<a href="{_esc(feed_url)}" style="color: {STYLE["tertiary"]}; text-decoration: underline;">Subscribe</a>
</td>
</tr>
</table>
</td></tr>
'''


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
        rows.append(
            f'''
<tr><td style="padding: 14px 0; border-bottom: 1px solid {STYLE["hairline_soft"]};">
<span style="display: inline-block; background: {STYLE["accent_soft"]}; color: {STYLE["accent"]}; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 8px; border-radius: 4px;">{_esc(it.jurisdiction)}</span>
<div style="font-size: 16px; font-weight: 600; color: {STYLE["text"]}; margin-top: 8px; line-height: 1.35;">{_esc(it.title)}</div>
<div style="font-size: 14px; color: {STYLE["secondary"]}; margin-top: 4px; line-height: 1.55;">{_esc((it.summary or "")[:240])}{"…" if it.summary and len(it.summary) > 240 else ""}</div>
{f'<div style="font-size: 12px; margin-top: 8px;"><a href="{_esc(it.url)}" style="color: {STYLE["accent"]}; text-decoration: none; font-weight: 600;">Read more →</a> <span style="color: {STYLE["tertiary"]}; margin-left: 8px;">{_esc(it.source)}</span></div>' if getattr(it, "url", None) else ""}
</td></tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 8px 36px;">'
        + _section_eyebrow("If you'd rather read")
        + f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 10px;">'
        + "".join(rows)
        + '</table></td></tr>'
    )
    return block, len(selected)


def _obligations_block(sub: Subscription, today: dt.date) -> tuple[str, int]:
    """Obligations due within the next 60 days, jurisdiction-filtered."""
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
            due_label = f"{due.strftime('%-d %b')}<br><span style='color: {STYLE['tertiary']}; font-weight: 400; font-size: 12px;'>{days_left} days</span>"
            risk_marker = ""
            if days_left < 0:
                risk_marker = (
                    f'<div style="color: {STYLE["accent"]}; font-weight: 600; '
                    f'font-size: 12px; margin-top: 2px;">Overdue</div>'
                )
            elif days_left <= 14:
                risk_marker = (
                    f'<div style="color: {STYLE["warn"]}; font-weight: 600; '
                    f'font-size: 12px; margin-top: 2px;">Due soon</div>'
                )
        except ValueError:
            due_label = _esc(o.due_date)
            risk_marker = ""

        rows.append(
            f'''
<tr>
<td style="padding: 12px 0; border-top: 1px solid {STYLE["hairline_soft"]}; vertical-align: top; width: 60px; color: {STYLE["accent"]}; font-weight: 700; letter-spacing: 0.08em; font-size: 12px;">{_esc(o.jurisdiction)}</td>
<td style="padding: 12px 0; border-top: 1px solid {STYLE["hairline_soft"]}; color: {STYLE["text"]};">
<div style="font-weight: 600; font-size: 14px;">{_esc(o.title)}</div>
{f'<div style="color: {STYLE["secondary"]}; font-size: 12px; margin-top: 2px;">{_esc(o.description or "")}</div>' if o.description else ""}
{risk_marker}
</td>
<td style="padding: 12px 0; border-top: 1px solid {STYLE["hairline_soft"]}; text-align: right; white-space: nowrap; color: {STYLE["text"]}; font-weight: 600;">{due_label}</td>
</tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 8px 36px;">'
        + _section_eyebrow("On your calendar")
        + f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 14px; font-size: 14px;">'
        + "".join(rows)
        + '</table></td></tr>'
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
<tr><td style="padding: 6px 0; font-size: 14px; line-height: 1.6; color: {STYLE["text"]};"><strong style="color: {STYLE["accent"]};">{_esc(it.jurisdiction)}</strong> · {_esc(it.title)}{f' — {_esc((it.summary or "")[:160])}' if it.summary else ""}</td></tr>'''
        )

    block = (
        f'<tr><td style="padding: 24px 36px 32px 36px;">'
        + _section_eyebrow("Looking ahead")
        + f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 14px;">'
        + "".join(rows)
        + '</table></td></tr>'
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
    blocks: list[str] = [_hero_block(today)]

    if sub.include_obligations:
        block, n = _obligations_block(sub, today)
        sections["obligations"] = n
        if block:
            blocks.append(block)
    if sub.include_news:
        block, n = _news_block(sub, today)
        sections["news"] = n
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
        f"filings ({sections['obligations']})" if sections["obligations"] else "",
        f"horizon ({sections['horizon']})" if sections["horizon"] else "",
    ]
    summary = " · ".join(p for p in parts if p) or "fireside only"
    subject = f"TrustSphere fireside — {today.strftime('%A %-d %B')} — {summary}"

    body_html = "".join(blocks)
    unsub_url = f"{base_url}/?unsubscribe={sub.unsubscribe_token}"

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<title>{_esc(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background: {STYLE["canvas_outer"]}; font-family: {STYLE["font_stack"]}; color: {STYLE["text"]};">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background: {STYLE["canvas_outer"]};">
<tr><td align="center" style="padding: 32px 12px;">

<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="640" style="max-width: 640px; background: {STYLE["canvas"]}; border-radius: 20px; overflow: hidden;">

<!-- Warm gradient masthead -->
<tr><td style="background: linear-gradient(135deg, #F4A56A 0%, #D26E3A 50%, #8C3B1F 100%); padding: 36px 36px 28px 36px; text-align: center;">
<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; font-weight: 700; letter-spacing: 0.30em; text-transform: uppercase; color: #FFE9D4;">TrustSphere · Fireside</div>
<h1 style="margin: 12px 0 6px 0; font-family: {STYLE["serif_stack"]}; font-size: 32px; line-height: 1.08; letter-spacing: -0.018em; font-weight: 700; color: #FFFFFF; font-style: italic;">Five minutes by the fire</h1>
<div style="font-size: 13px; color: #FFE9D4; letter-spacing: 0.04em; margin-top: 8px;">{_esc(today.strftime('%A, %-d %B %Y'))} &nbsp;·&nbsp; {_esc(sub.label_timezone())}</div>
</td></tr>

{body_html}

<!-- Footer -->
<tr><td style="padding: 28px 36px 32px 36px; background: {STYLE["surface_warm"]}; border-top: 1px solid {STYLE["hairline"]};">
<div style="font-size: 12px; color: {STYLE["secondary"]}; line-height: 1.7;">
Pulled up a chair for <strong style="color: {STYLE["text"]};">{_esc(sub.email)}</strong> at 07:00 {_esc(sub.label_timezone())}.<br>
<a href="{base_url}" style="color: {STYLE["accent"]}; text-decoration: none; font-weight: 600;">Open dashboard</a> &nbsp;·&nbsp;
<a href="{_esc(unsub_url)}" style="color: {STYLE["secondary"]}; text-decoration: underline;">Unsubscribe</a> &nbsp;·&nbsp;
<a href="{base_url}" style="color: {STYLE["secondary"]}; text-decoration: underline;">Manage preferences</a>
</div>
<div style="font-size: 11px; color: {STYLE["tertiary"]}; margin-top: 14px; line-height: 1.55; font-style: italic;">
Informational only — confirm filing dates against the regulator's authoritative source before acting. The conversation is generated from publicly-available regulator notices and curated industry news.
</div>
</td></tr>

</table>

<div style="font-family: {STYLE["serif_stack"]}; font-size: 11px; color: #8C7766; margin-top: 18px; letter-spacing: 0.06em; font-style: italic;">TrustSphere Partners · trustsphere.ai</div>

</td></tr>
</table>
</body>
</html>'''

    pod = latest_podcast()
    text_lines = [
        f"TrustSphere Fireside — {today.isoformat()}",
        f"For {sub.email} at 07:00 {sub.label_timezone()}",
        "",
    ]
    if pod is not None:
        mp3_url = f"{REPO_RAW_BASE}/data/podcasts/{pod.date}.mp3"
        text_lines.extend([
            f"Today's fireside ({_format_duration(pod.duration_seconds)}):",
            f"  {mp3_url}",
            "",
        ])
    text_lines.extend([
        f"Today's items: {summary}",
        "",
        f"Open TrustSphere: {base_url}",
        f"Unsubscribe: {unsub_url}",
    ])
    text = "\n".join(text_lines)

    return DigestPayload(
        subject=subject,
        text=text,
        html=full_html,
        sections=sections,
    )
