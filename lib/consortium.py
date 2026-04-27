"""Consortium (beta) — cross-institution STR intelligence sharing.

The mechanism:
  1. Each STR filed via AML Agents can be submitted to the consortium log.
  2. The submission stores HASHED identifiers (not raw subject names) plus
     structured tags, jurisdiction, entity category, alert source, amount band.
  3. When a new STR is being drafted, the consortium can be queried by hash
     and tag overlap — returning a "consortium score" indicating how many
     other institutions have filed similar STRs.

Privacy model:
  - Subject names are SHA256-hashed (with a configurable salt) before storage.
  - Reporting institutions are also hashed.
  - Original narrative content is never stored — only structured metadata.
  - Each consortium entry has a unique anonymous ID.

For v0, the consortium log is local (single-machine, single-tenant). Production
deployment requires:
  - Backend API for distributed submission and lookup
  - Privacy / data-residency review per jurisdiction
  - Legal framework (US Patriot Act 314(b), AMLA s.66B in SG, etc.)
  - Anti-collusion controls (you can see hits but not original filer)

Scoring algorithm: PLACEHOLDER for v0. User will refine tomorrow with their
methodology. Currently:
  - Exact subject-hash match = 50 points
  - Same jurisdiction + entity category = 10 points
  - Each shared typology tag = 5 points (capped at 30)
  - Total capped at 100
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONSORTIUM_PATH = Path(__file__).parent.parent / "data" / "consortium.yaml"

# Hash salt — in production this would be a per-deployment secret read from env.
# For v0 it's a fixed value so demo runs are reproducible.
HASH_SALT = "amlagents-v0-consortium-salt"


def _hash(value: str) -> str:
    """SHA256 hash with salt, truncated to 16 hex chars for display."""
    s = (value or "").strip().lower()
    return hashlib.sha256((HASH_SALT + s).encode()).hexdigest()[:16]


def subject_hash(name: str, identifier: str = "") -> str:
    """Hash a subject identifier — combination of name + ID for canonical form."""
    canonical = f"{(name or '').strip().lower()}|{(identifier or '').strip().lower()}"
    return _hash(canonical)


def institution_hash(institution: str) -> str:
    """Hash a reporting institution for anonymized storage."""
    return _hash(institution)


# Typology tag dictionary — maps keywords to canonical tag names.
# Simple keyword detection on red flags + analyst notes for v0.
# Production: replace with LLM-based tag extraction or rule-based classification.
TAG_KEYWORDS: dict[str, list[str]] = {
    "sanctions": ["sanctions", "ofac", "un security council", "sdn list", "dfat", "designated"],
    "pep": ["pep", "politically exposed", "rca", "domestic prominent"],
    "structuring": ["structuring", "smurfing", "below threshold", "ttr threshold", "ctr threshold"],
    "trade-based-ml": ["over-invoic", "under-invoic", "phantom shipment", "trade-based", "tbml"],
    "mule-account": ["mule", "money mule", "scam victim", "pig butchering", "investment scam"],
    "shell-company": ["shell company", "shell entity", "bvi", "cayman", "nominee director"],
    "casino-junket": ["junket", "casino", "vip room", "chip-walking", "chip walking"],
    "crypto-mixer": ["mixer", "tornado cash", "darknet", "kyt", "chainalysis", "crypto"],
    "shariah-product-abuse": ["tawarruq", "murabahah", "wakalah", "musharakah", "ijarah"],
    "cross-border-cn": ["mainland", "shenzhen", "guangzhou", "shanghai", "cnh", "rmb"],
    "vasp-onboarding": ["e-kyc", "digital onboarding", "vasp", "dpt", "dce", "dae"],
    "tranche-2": ["tranche 2", "real estate agent", "lawyer", "accountant", "conveyancer", "precious metals"],
    "high-risk-jurisdiction": ["iran", "north korea", "dprk", "russia", "myanmar"],
    "round-tripping": ["round-trip", "round trip", "cyclic", "circular flow"],
    "adverse-media": ["adverse media", "icac", "press release", "investigation"],
}


def extract_tags(*text_blocks: str) -> list[str]:
    """Extract canonical typology tags from analyst input text."""
    combined = " ".join(t.lower() for t in text_blocks if t)
    found = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            found.append(tag)
    return found


def amount_band(transactions_text: str) -> str:
    """Coarse amount band derived from transaction text. Best-effort regex."""
    import re

    if not transactions_text:
        return "unknown"
    # Match common patterns: 1,234,567 or 1.5M etc.
    nums = re.findall(r"(\d{1,3}(?:,\d{3})+)", transactions_text)
    nums_int = [int(n.replace(",", "")) for n in nums if n]
    if not nums_int:
        return "unknown"
    max_amount = max(nums_int)
    if max_amount < 50_000:
        return "<50k"
    if max_amount < 500_000:
        return "50k-500k"
    if max_amount < 5_000_000:
        return "500k-5M"
    if max_amount < 50_000_000:
        return "5M-50M"
    return ">50M"


@dataclass
class ConsortiumEntry:
    id: str = field(default_factory=lambda: f"CON-{uuid.uuid4().hex[:12]}")
    filed_at: str = ""
    subject_hash_value: str = ""
    institution_hash_value: str = ""
    jurisdiction: str = ""
    entity_category: str = ""
    alert_source: str = ""
    typology_tags: list[str] = field(default_factory=list)
    amount_band: str = ""
    risk_score: int = 0  # the TrustSphere Risk Index score from filing
    str_reference_hash: str = ""  # so the filer can later prove ownership without revealing reference


def load_log() -> list[ConsortiumEntry]:
    if not CONSORTIUM_PATH.exists():
        return []
    with open(CONSORTIUM_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [ConsortiumEntry(**item) for item in raw]


def save_log(entries: list[ConsortiumEntry]) -> None:
    CONSORTIUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSORTIUM_PATH, "w") as f:
        yaml.dump([asdict(e) for e in entries], f, default_flow_style=False, sort_keys=False)


def submit(
    *,
    subject_name: str,
    subject_id: str,
    institution: str,
    jurisdiction: str,
    entity_category: str,
    alert_source: str,
    typology_tags: list[str],
    amount_band_value: str,
    risk_score: int,
    str_reference: str,
) -> ConsortiumEntry:
    """Submit an STR to the consortium log."""
    entries = load_log()
    entry = ConsortiumEntry(
        filed_at=time.strftime("%Y-%m-%d"),
        subject_hash_value=subject_hash(subject_name, subject_id),
        institution_hash_value=institution_hash(institution),
        jurisdiction=jurisdiction,
        entity_category=entity_category or "",
        alert_source=alert_source,
        typology_tags=typology_tags,
        amount_band=amount_band_value,
        risk_score=int(risk_score),
        str_reference_hash=_hash(str_reference) if str_reference else "",
    )
    entries.append(entry)
    save_log(entries)
    return entry


def lookup(
    *,
    subject_name: str,
    subject_id: str,
    jurisdiction: str,
    entity_category: str,
    typology_tags: list[str],
    institution: str,
) -> dict[str, Any]:
    """Look up consortium matches for a draft STR (without submitting it).

    Returns:
        score — placeholder consortium score 0..100
        breakdown — string describing how score was computed
        matches — list of dicts with anonymized match info
        own_filings — N entries previously submitted by the same institution
    """
    s_hash = subject_hash(subject_name, subject_id)
    inst_hash = institution_hash(institution)

    entries = load_log()

    # Exact subject match
    subject_matches = [e for e in entries if e.subject_hash_value == s_hash]
    other_subject_matches = [e for e in subject_matches if e.institution_hash_value != inst_hash]
    own_filings = sum(1 for e in subject_matches if e.institution_hash_value == inst_hash)

    # Same jurisdiction + entity category match
    jur_cat_matches = [
        e for e in entries
        if e.jurisdiction == jurisdiction
        and e.entity_category == entity_category
        and e.institution_hash_value != inst_hash
    ]

    # Tag overlap match
    tag_overlap_count = 0
    for e in entries:
        if e.institution_hash_value == inst_hash:
            continue
        shared = set(e.typology_tags) & set(typology_tags)
        if shared:
            tag_overlap_count += len(shared)

    # PLACEHOLDER scoring formula — user to refine tomorrow
    score = 0
    breakdown_parts: list[str] = []

    if other_subject_matches:
        score += 50
        breakdown_parts.append(
            f"Exact subject match across {len(other_subject_matches)} other institution(s): +50"
        )
    if jur_cat_matches:
        score += 10
        breakdown_parts.append(
            f"{len(jur_cat_matches)} other STR(s) in same jurisdiction + entity category: +10"
        )
    tag_pts = min(tag_overlap_count * 5, 30)
    if tag_pts > 0:
        score += tag_pts
        breakdown_parts.append(
            f"{tag_overlap_count} shared typology-tag occurrence(s): +{tag_pts}"
        )

    score = min(score, 100)
    if score == 0:
        breakdown_parts.append(
            "No consortium matches found — this appears to be a novel pattern."
        )

    return {
        "score": score,
        "breakdown": breakdown_parts,
        "subject_match_count": len(other_subject_matches),
        "jurisdiction_match_count": len(jur_cat_matches),
        "tag_overlap_count": tag_overlap_count,
        "own_filings_for_this_subject": own_filings,
        "subject_hash": s_hash,
    }
