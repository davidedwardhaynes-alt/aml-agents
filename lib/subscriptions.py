"""Daily digest subscriptions — register an email address to receive the
news / obligations / horizon-scanning roll-up every morning.

For v0 the subscriptions are persisted to a single shared YAML file. Per-
tenant persistence and proper unsubscribe-token handling come with
production migration to a managed backend.

Each subscription carries:
- a stable ID + opaque unsubscribe token (HMAC-style URL-safe)
- email
- timezone (one of a curated APAC + global list — drives the cron-hour
  selection so the user gets the digest at ~7am local)
- jurisdiction filter (subset of the 6 supported jurisdictions, or all)
- topic filter (subset of news topics, or all)
- whether to include obligations + horizon scanning (default: yes)
- created_at, last_sent_at, status (active / paused / unsubscribed)

Send-eligibility logic lives here too — `due_for_send` returns True if a
subscription's local-time matches 7am within the current cron hour.
"""

from __future__ import annotations

import datetime as dt
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

SUBSCRIPTIONS_PATH = Path(__file__).parent.parent / "data" / "subscriptions.yaml"

# Curated list of timezones we offer, ordered by relevance to the demo's
# APAC focus. UI uses these labels; persistence stores the IANA name.
TIMEZONES: list[tuple[str, str]] = [
    ("Singapore (SGT)", "Asia/Singapore"),
    ("Hong Kong (HKT)", "Asia/Hong_Kong"),
    ("Kuala Lumpur (MYT)", "Asia/Kuala_Lumpur"),
    ("Manila (PHT)", "Asia/Manila"),
    ("Jakarta (WIB)", "Asia/Jakarta"),
    ("Sydney (AEST/AEDT)", "Australia/Sydney"),
    ("Tokyo (JST)", "Asia/Tokyo"),
    ("Seoul (KST)", "Asia/Seoul"),
    ("Taipei (TST)", "Asia/Taipei"),
    ("Bangkok (ICT)", "Asia/Bangkok"),
    ("Mumbai (IST)", "Asia/Kolkata"),
    ("London (GMT/BST)", "Europe/London"),
    ("Frankfurt (CET/CEST)", "Europe/Berlin"),
    ("New York (EST/EDT)", "America/New_York"),
    ("San Francisco (PST/PDT)", "America/Los_Angeles"),
]

TIMEZONE_LABEL_BY_IANA = {iana: label for label, iana in TIMEZONES}
TIMEZONE_IANA_BY_LABEL = {label: iana for label, iana in TIMEZONES}

# The local hour we deliver the digest at. 07:00 hits before most morning
# stand-ups and ICA risk-committee briefings.
DELIVERY_HOUR_LOCAL = 7


@dataclass
class Subscription:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    unsubscribe_token: str = field(
        default_factory=lambda: secrets.token_urlsafe(24)
    )
    email: str = ""
    timezone: str = "Asia/Singapore"  # IANA name
    jurisdictions: list[str] = field(default_factory=list)  # [] = all
    topics: list[str] = field(default_factory=list)  # [] = all
    include_news: bool = True
    include_obligations: bool = True
    include_horizon: bool = True
    status: str = "active"  # active / paused / unsubscribed
    created_at: str = ""
    last_sent_at: str = ""

    def label_timezone(self) -> str:
        return TIMEZONE_LABEL_BY_IANA.get(self.timezone, self.timezone)


def _coerce(item: dict[str, Any]) -> Subscription:
    """Build a Subscription from a YAML dict, dropping unknown keys
    (forward-compat) and supplying defaults for missing keys
    (backward-compat)."""
    known = {f for f in Subscription.__dataclass_fields__}
    safe = {k: v for k, v in (item or {}).items() if k in known}
    return Subscription(**safe)


def load_subscriptions() -> list[Subscription]:
    if not SUBSCRIPTIONS_PATH.exists():
        return []
    with open(SUBSCRIPTIONS_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [_coerce(item) for item in raw]


def save_subscriptions(subs: list[Subscription]) -> None:
    try:
        SUBSCRIPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SUBSCRIPTIONS_PATH, "w") as f:
            yaml.dump(
                [asdict(s) for s in subs],
                f,
                default_flow_style=False,
                sort_keys=False,
            )
    except (OSError, PermissionError):
        # Read-only filesystem (managed hosts) — fail soft, keep the
        # in-memory state authoritative for this session.
        pass


def add_subscription(
    *,
    email: str,
    timezone: str,
    jurisdictions: list[str] | None = None,
    topics: list[str] | None = None,
    include_news: bool = True,
    include_obligations: bool = True,
    include_horizon: bool = True,
) -> Subscription:
    """Add a subscription. If the email + timezone combo already exists
    and is active, return the existing record (idempotent). Otherwise
    create a new record. Email is normalised to lowercase."""
    email = (email or "").strip().lower()
    subs = load_subscriptions()
    for s in subs:
        if (
            s.email == email
            and s.timezone == timezone
            and s.status == "active"
        ):
            # Update filters on the existing record so re-submitting the form
            # acts as an "update" rather than creating a duplicate.
            s.jurisdictions = jurisdictions or []
            s.topics = topics or []
            s.include_news = include_news
            s.include_obligations = include_obligations
            s.include_horizon = include_horizon
            save_subscriptions(subs)
            return s
    new = Subscription(
        email=email,
        timezone=timezone,
        jurisdictions=jurisdictions or [],
        topics=topics or [],
        include_news=include_news,
        include_obligations=include_obligations,
        include_horizon=include_horizon,
        created_at=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
    subs.append(new)
    save_subscriptions(subs)
    return new


def find_by_token(token: str) -> Subscription | None:
    for s in load_subscriptions():
        if s.unsubscribe_token == token:
            return s
    return None


def find_by_email(email: str) -> list[Subscription]:
    email = (email or "").strip().lower()
    return [s for s in load_subscriptions() if s.email == email]


def unsubscribe(token: str) -> bool:
    subs = load_subscriptions()
    for s in subs:
        if s.unsubscribe_token == token and s.status != "unsubscribed":
            s.status = "unsubscribed"
            save_subscriptions(subs)
            return True
    return False


def pause(token: str) -> bool:
    subs = load_subscriptions()
    for s in subs:
        if s.unsubscribe_token == token and s.status == "active":
            s.status = "paused"
            save_subscriptions(subs)
            return True
    return False


def resume(token: str) -> bool:
    subs = load_subscriptions()
    for s in subs:
        if s.unsubscribe_token == token and s.status == "paused":
            s.status = "active"
            save_subscriptions(subs)
            return True
    return False


def mark_sent(sub_id: str, when: dt.datetime | None = None) -> None:
    """Record that we sent today's digest to a given subscription."""
    when = when or dt.datetime.utcnow()
    subs = load_subscriptions()
    for s in subs:
        if s.id == sub_id:
            s.last_sent_at = when.isoformat(timespec="seconds") + "Z"
    save_subscriptions(subs)


def due_for_send(
    sub: Subscription,
    *,
    now_utc: dt.datetime | None = None,
) -> bool:
    """True iff the subscription's local time falls within the current UTC
    hour AND the local hour matches DELIVERY_HOUR_LOCAL (07:00) AND we
    haven't already sent today's digest."""
    if sub.status != "active":
        return False
    if not sub.include_news and not sub.include_obligations and not sub.include_horizon:
        return False
    now_utc = now_utc or dt.datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    try:
        tz = ZoneInfo(sub.timezone)
    except Exception:
        return False
    local = now_utc.astimezone(tz)
    if local.hour != DELIVERY_HOUR_LOCAL:
        return False
    # Don't double-send within the same local-day.
    if sub.last_sent_at:
        try:
            last = dt.datetime.fromisoformat(
                sub.last_sent_at.replace("Z", "+00:00")
            ).astimezone(tz).date()
            if last == local.date():
                return False
        except Exception:
            pass
    return True
