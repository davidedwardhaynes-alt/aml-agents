"""Obligation register — track regulatory compliance obligations.

Simple per-institution obligation tracker. Persisted to a local YAML file.
For v0, single shared file. Per-user / per-tenant persistence comes with
production migration.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

OBLIGATIONS_PATH = Path(__file__).parent.parent / "data" / "obligations.yaml"


@dataclass
class Obligation:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    jurisdiction: str = "Singapore (STRO)"
    statute_or_notice: str = ""
    due_date: str = ""  # ISO date string
    status: str = "Open"  # Open / In progress / Closed / Overdue
    owner: str = ""
    notes: str = ""


STATUSES = ["Open", "In progress", "Closed", "Overdue"]


def load_obligations() -> list[Obligation]:
    """Load obligations from disk. Returns seed data on first run."""
    if not OBLIGATIONS_PATH.exists():
        return _seed_obligations()
    with open(OBLIGATIONS_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [Obligation(**item) for item in raw]


def save_obligations(items: list[Obligation]) -> None:
    """Persist obligations to disk."""
    OBLIGATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OBLIGATIONS_PATH, "w") as f:
        yaml.dump([asdict(o) for o in items], f, default_flow_style=False, sort_keys=False)


def add_obligation(
    *,
    title: str,
    description: str,
    jurisdiction: str,
    statute_or_notice: str,
    due_date: str,
    status: str,
    owner: str,
    notes: str,
) -> Obligation:
    items = load_obligations()
    new = Obligation(
        title=title,
        description=description,
        jurisdiction=jurisdiction,
        statute_or_notice=statute_or_notice,
        due_date=due_date,
        status=status,
        owner=owner,
        notes=notes,
    )
    items.append(new)
    save_obligations(items)
    return new


def update_obligation(obligation_id: str, **changes: Any) -> bool:
    items = load_obligations()
    for o in items:
        if o.id == obligation_id:
            for k, v in changes.items():
                if hasattr(o, k):
                    setattr(o, k, v)
            save_obligations(items)
            return True
    return False


def delete_obligation(obligation_id: str) -> bool:
    items = load_obligations()
    new_items = [o for o in items if o.id != obligation_id]
    if len(new_items) != len(items):
        save_obligations(new_items)
        return True
    return False


def _seed_obligations() -> list[Obligation]:
    """Seed obligations for first-time use, covering all 4 jurisdictions."""
    seeds = [
        Obligation(
            title="MAS Notice 626 annual AML/CFT attestation",
            description="Board-level annual attestation on AML/CFT controls, RBA, and MLRO independence.",
            jurisdiction="Singapore (STRO)",
            statute_or_notice="MAS Notice 626 §10",
            due_date="2026-12-31",
            status="Open",
            owner="Head of Compliance",
            notes="Aligns with FY2026 board cycle. Pre-board paper due Q3.",
        ),
        Obligation(
            title="STRO STR statistics quarterly reconciliation",
            description="Reconcile internal STR submission log against STRO acknowledgments.",
            jurisdiction="Singapore (STRO)",
            statute_or_notice="MAS Notice 626 §6.13",
            due_date="2026-07-15",
            status="In progress",
            owner="MLRO",
            notes="Q2 2026 reconciliation; STRO latency ~5 working days from filing.",
        ),
        Obligation(
            title="HKMA AML/CFT self-assessment return",
            description="Annual AML/CFT self-assessment return to HKMA covering all key controls.",
            jurisdiction="Hong Kong (JFIU)",
            statute_or_notice="HKMA AML/CFT Guideline §11",
            due_date="2026-09-30",
            status="Open",
            owner="MLRO + Internal Audit",
            notes="Format: HKMA-prescribed Excel template. Independent assurance required.",
        ),
        Obligation(
            title="VASP licensing — quarterly KYT effectiveness review",
            description="Per SFC AML/CFT Guideline for VASPs, quarterly review of KYT (Chainalysis/TRM/Elliptic) effectiveness.",
            jurisdiction="Hong Kong (JFIU)",
            statute_or_notice="SFC AML/CFT Guideline (VASP) §4.10",
            due_date="2026-06-30",
            status="Open",
            owner="Head of FCC (VASP)",
            notes="Sample at least 5% of inbound deposits; document hop-distance analysis methodology.",
        ),
        Obligation(
            title="BNM AMLA s.13 CTR review",
            description="Review FY2025 cash transaction reports for completeness and timeliness.",
            jurisdiction="Malaysia (FIED)",
            statute_or_notice="AMLA s.13 + BNM AML/CFT Sectoral Guidelines",
            due_date="2026-06-30",
            status="In progress",
            owner="Head of FCC",
            notes="RM 25,000 threshold. Coordinate with branch operations on un-filed batches.",
        ),
        Obligation(
            title="Shariah Governance Framework — annual Shariah audit on AML overlap",
            description="Annual Shariah Audit covering AML touchpoints (Tawarruq, Wakalah, Hibah).",
            jurisdiction="Malaysia (FIED)",
            statute_or_notice="BNM Shariah Governance Framework + IFSA 2013",
            due_date="2026-12-31",
            status="Open",
            owner="Shariah Committee + MLRO",
            notes="Coordinate with Shariah Risk Management; Tawarruq commodity-trade documentation testing.",
        ),
        Obligation(
            title="AUSTRAC AML/CTF Program Part A annual review",
            description="Annual board-level review and approval of the AML/CTF Program Part A.",
            jurisdiction="Australia (AUSTRAC SMR)",
            statute_or_notice="AML/CTF Act 2006 s.84 + AML/CTF Rules Part 8",
            due_date="2026-08-31",
            status="Open",
            owner="AML/CTF Compliance Officer",
            notes="Aligns with FY2026 board cycle. Independent review required every 2 years.",
        ),
        Obligation(
            title="Tranche 2 enrolment — pre-commencement window",
            description="Pre-commencement registration with AUSTRAC for Tranche 2 obligations from 1 July 2026.",
            jurisdiction="Australia (AUSTRAC SMR)",
            statute_or_notice="AML/CTF Amendment Act 2024",
            due_date="2026-06-30",
            status="Open",
            owner="Managing Partner + appointed AML/CTF CO",
            notes="Applies to legal practitioners, accountants, real estate agents, conveyancers, precious metals dealers.",
        ),
    ]
    save_obligations(seeds)
    return seeds
