"""Programme tracker — break each AML/CFT obligation into actionable
sub-tasks owned by team members, with due dates, status, and meeting/
checkpoint cadence.

A reporting institution's compliance team rarely treats an obligation
as a single deliverable. The MAS Notice 626 §13 annual independent
audit, for example, is a portfolio of: scope agreement with the audit
committee, test plan, sample selection, fieldwork, draft report,
remediation tracker, board paper, supervisor file. This module gives
each obligation its own lightweight project plan.

Tasks are persisted to a single YAML file (data/tasks.yaml). Each task
links back to its parent obligation by obligation_id. For v0 this is
a shared file; per-tenant persistence comes with the production
migration to a managed backend.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

TASKS_PATH = Path(__file__).parent.parent / "data" / "tasks.yaml"

TASK_STATUSES = ["Not started", "In progress", "Blocked", "Done"]


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    obligation_id: str = ""
    """ID of the parent Obligation (lib/obligations.py). One obligation
    may have many tasks; one task belongs to exactly one obligation."""
    title: str = ""
    description: str = ""
    owner: str = ""
    due_date: str = ""  # ISO YYYY-MM-DD
    status: str = "Not started"  # one of TASK_STATUSES
    meeting_cadence: str = ""
    """Free-text cadence/checkpoint hint, e.g. 'Weekly FCC stand-up
    Thursdays 09:00 SGT' or 'Audit committee 15 December 2025'."""
    completed_at: str = ""
    notes: str = ""
    created_at: str = field(
        default_factory=lambda:
            dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    )


def _coerce(item: dict[str, Any]) -> Task:
    known = {f for f in Task.__dataclass_fields__}
    safe = {k: v for k, v in (item or {}).items() if k in known}
    return Task(**safe)


def load_tasks() -> list[Task]:
    """Load all tasks from disk. Returns empty list on first run."""
    if not TASKS_PATH.exists():
        return _seed_tasks()
    with open(TASKS_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [_coerce(item) for item in raw]


def save_tasks(tasks: list[Task]) -> None:
    try:
        TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_PATH, "w") as f:
            yaml.dump(
                [asdict(t) for t in tasks],
                f,
                default_flow_style=False,
                sort_keys=False,
            )
    except (OSError, PermissionError):
        # Read-only filesystem on managed hosts — fail soft.
        pass


def tasks_for(obligation_id: str) -> list[Task]:
    """All tasks tied to a given obligation, sorted by status (Not
    started → In progress → Blocked → Done) then by due_date."""
    rank = {"Not started": 0, "In progress": 1, "Blocked": 2, "Done": 3}
    return sorted(
        [t for t in load_tasks() if t.obligation_id == obligation_id],
        key=lambda t: (rank.get(t.status, 9), t.due_date or "9999-12-31"),
    )


def add_task(
    *,
    obligation_id: str,
    title: str,
    description: str = "",
    owner: str = "",
    due_date: str = "",
    status: str = "Not started",
    meeting_cadence: str = "",
    notes: str = "",
) -> Task:
    items = load_tasks()
    new = Task(
        obligation_id=obligation_id,
        title=title,
        description=description,
        owner=owner,
        due_date=due_date,
        status=status,
        meeting_cadence=meeting_cadence,
        notes=notes,
    )
    items.append(new)
    save_tasks(items)
    return new


def update_task(task_id: str, **changes: Any) -> bool:
    items = load_tasks()
    for t in items:
        if t.id == task_id:
            for k, v in changes.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            # Auto-stamp completed_at when status flips to Done
            if changes.get("status") == "Done" and not t.completed_at:
                t.completed_at = (
                    dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
                )
            save_tasks(items)
            return True
    return False


def delete_task(task_id: str) -> bool:
    items = load_tasks()
    new_items = [t for t in items if t.id != task_id]
    if len(new_items) != len(items):
        save_tasks(new_items)
        return True
    return False


def reseed_tasks() -> list[Task]:
    """Discard persisted tasks and rewrite the seed list."""
    seeds = _seed_tasks()
    save_tasks(seeds)
    return seeds


def task_progress(obligation_id: str) -> tuple[int, int, float]:
    """Return (done_count, total_count, percent_complete) for an obligation."""
    items = [t for t in load_tasks() if t.obligation_id == obligation_id]
    if not items:
        return 0, 0, 0.0
    done = sum(1 for t in items if t.status == "Done")
    return done, len(items), (done / len(items)) * 100


# ---------------------------------------------------------------------------
# Seed task templates for the 8 high-priority legacy obligations.
#
# Each obligation gets a 4-6 task project plan that an MLRO can clone-and-
# adapt to their institution. obligation_id matches the seed Obligation IDs,
# but those IDs are uuid-generated each time _seed_obligations() runs; so
# we instead match on a stable signature (jurisdiction + title-prefix) and
# resolve at runtime via lib/obligations.load_obligations().
#
# To keep the seed deterministic we use deterministic IDs here; the linking
# function in app.py joins on obligation_id at render time.
# ---------------------------------------------------------------------------

# Stable obligation-key constants used by the seed-resolution helper.
_LEGACY_OBLIGATION_KEYS = {
    "sg_mas_626_audit": "MAS Notice 626 §13 — FY2025 annual independent",
    "hk_hkma_11":       "HKMA AML/CFT Guideline §11 — CY 2024",
    "sg_psn02":         "MAS Notice PSN02 — DPT EDD",
    "au_part_13":       "AUSTRAC AML/CTF Rules Part 13 — CY 2024",
    "id_pojk_12":       "POJK 12/POJK.01/2017 — CY 2024",
    "ph_bsp_1022":      "BSP Circular 1022 — CY 2024",
    "nz_act_s59":       "AML/CFT Act 2009 s.59 — biennial independent",
    "kr_ftra_5_2":      "FTRA Article 5-2 — VASP travel-rule",
}


def _seed_tasks() -> list[Task]:
    """Lightweight seed list. Real obligation_ids are filled in at first
    render by `relink_seed_tasks_to_obligations()` in lib.obligations
    (called from app.py once per session). We seed with empty
    obligation_id and the title-prefix in the task description so the
    linker can resolve them."""
    today = dt.date.today()
    iso = today.isoformat()

    def in_days(n: int) -> str:
        return (today + dt.timedelta(days=n)).isoformat()

    seeds: list[Task] = []

    # ---- MAS Notice 626 §13 — FY2025 annual independent audit ----
    for t in [
        Task(
            title="Agree FY2025 audit scope with Audit Committee",
            description="Risk-based scope: CDD, EDD, monitoring, screening, STR governance, training, record-keeping. Confirm sample sizes per MAS thematic priority.",
            owner="Head of Internal Audit",
            due_date=in_days(-90),
            status="Done",
            meeting_cadence="Audit Committee, monthly",
        ),
        Task(
            title="Test plan + sample selection",
            description="Cover all eight Notice 626 control areas; sample 5% of high-risk customers + 100% of PEPs.",
            owner="Internal Audit Manager",
            due_date=in_days(-60),
            status="In progress",
        ),
        Task(
            title="Fieldwork — controls testing across the 8 Notice 626 areas",
            description="Fieldwork by 30 November so report can land at December audit committee.",
            owner="Internal Audit Manager",
            due_date=in_days(-30),
            status="In progress",
        ),
        Task(
            title="Draft audit report + management response",
            description="Findings, management response, remediation plan with owner+date for each open item.",
            owner="Head of Internal Audit",
            due_date=in_days(-15),
            status="Not started",
            meeting_cadence="Audit Committee 15 December 2025",
        ),
        Task(
            title="Close out FY2024 prior-year findings",
            description="Critical — MAS examiners read prior-year-finding closure as a leading indicator of programme maturity.",
            owner="MLRO + Head of FCC",
            due_date=iso,
            status="Blocked",
            notes="Two FY2024 findings (sample-size inadequacy, EDD-on-PEP documentation) still open; plan submitted but evidence not yet collected.",
        ),
        Task(
            title="Submit MAS S140 supervisory-information return",
            description="If requested by MAS as part of FY2026 inspection cycle.",
            owner="MLRO",
            due_date=in_days(30),
            status="Not started",
        ),
    ]:
        t.notes = f"[seed-link:sg_mas_626_audit] {t.notes}".strip()
        seeds.append(t)

    # ---- HKMA AML/CFT Guideline §11 CY 2024 self-assessment ----
    for t in [
        Task(
            title="Respond to HKMA Q4 2025 deficiency letter",
            description="60-day response window from issuance. Include remediation plan with closure dates.",
            owner="MLRO",
            due_date=in_days(-30),
            status="In progress",
            meeting_cadence="Weekly FCC stand-up — Thursdays 09:00 HKT",
        ),
        Task(
            title="Internal Audit independent validation refresh",
            description="HKMA examiners cited validation as too thin; engage external counsel for AMLO Schedule 2 testing.",
            owner="Head of Internal Audit",
            due_date=in_days(-7),
            status="In progress",
        ),
        Task(
            title="Board minute extract + Risk Committee endorsement of response",
            description="HKMA expects board-level oversight of any rating below 'Effective'.",
            owner="Company Secretary",
            due_date=in_days(7),
            status="Not started",
            meeting_cadence="Board Risk Committee 12 May 2026",
        ),
        Task(
            title="Re-rate the 4 control areas flagged below 'Effective'",
            description="Self-rating must be supported by evidence. Re-rate Risk Assessment / EDD / Monitoring / Screening.",
            owner="MLRO",
            due_date=in_days(14),
            status="Not started",
        ),
    ]:
        t.notes = f"[seed-link:hk_hkma_11] {t.notes}".strip()
        seeds.append(t)

    # ---- MAS Notice PSN02 — DPT EDD amendments effective 1 Jan 2026 ----
    for t in [
        Task(
            title="KYT vendor go-live (Chainalysis / TRM / Elliptic)",
            description="Inbound + outbound screening. Alert dispositioning logs auditable. Q1 2026 thematic review found 6/11 providers behind.",
            owner="Head of Crypto-AML",
            due_date=in_days(-1),
            status="In progress",
        ),
        Task(
            title="Lower SGD 50,000 / 90-day EDD threshold trigger",
            description="Configure TM to trigger EDD (not just an alert) at the new threshold.",
            owner="Head of Compliance Engineering",
            due_date=iso,
            status="In progress",
        ),
        Task(
            title="In-app scam-victim messaging — coordinate with SPF Anti-Scam Centre",
            description="Pattern-triggered, not blanket. Align messaging content with ASC.",
            owner="Head of Customer Risk + Marketing",
            due_date=in_days(7),
            status="Blocked",
            notes="ASC liaison meeting requested; awaiting confirmation.",
        ),
        Task(
            title="MLRO attestation pack ready for MAS thematic review response",
            description="Vendor contracts, integration go-live attestation, alert disposition log, EDD-trigger log, screen captures.",
            owner="MLRO",
            due_date=in_days(14),
            status="Not started",
        ),
    ]:
        t.notes = f"[seed-link:sg_psn02] {t.notes}".strip()
        seeds.append(t)

    # ---- AUSTRAC AML/CTF Rules Part 13 — CY 2024 annual compliance report ----
    for t in [
        Task(
            title="CY 2024 attestation evidence binder",
            description="One sub-binder per attestation point. Cross-reference SMR + TTR + IFTI numbers against AUSTRAC Online logs.",
            owner="AML/CTF Compliance Officer",
            due_date=in_days(-7),
            status="In progress",
        ),
        Task(
            title="Board / governance committee endorsement before lodgement",
            description="AUSTRAC s.137 criminal exposure if the attestation is misleading — board endorsement is the control.",
            owner="Company Secretary",
            due_date=iso,
            status="Not started",
            meeting_cadence="Risk Committee, monthly",
        ),
        Task(
            title="Lodge via AUSTRAC Online with timestamp captured",
            description="Lodge before 23:00 with capacity to cure technical issues; every minute past midnight is a continuing breach.",
            owner="AML/CTF Compliance Officer",
            due_date=in_days(7),
            status="Not started",
        ),
        Task(
            title="Tranche 2 first-cohort scoping review (if applicable)",
            description="Lawyers / accountants / RE agents — common error is over-broad or under-broad scoping. Use AUSTRAC's first-cohort guidance examples.",
            owner="Tranche 2 Compliance Lead",
            due_date=in_days(21),
            status="Blocked",
        ),
    ]:
        t.notes = f"[seed-link:au_part_13] {t.notes}".strip()
        seeds.append(t)

    # ---- POJK 12/POJK.01/2017 — CY 2024 annual AML/CFT review ----
    for t in [
        Task(
            title="BI-FAST transaction-monitoring rule recalibration close-out",
            description="OJK examiners specifically test BI-FAST migration impact on rule calibration.",
            owner="Pejabat Penanggung Jawab APU-PPT",
            due_date=in_days(-14),
            status="In progress",
        ),
        Task(
            title="Pemilik Manfaat (BO) verification cross-check",
            description="Cross-check institution's own register against MoU-shared corporate registry data.",
            owner="Head of CDD Operations",
            due_date=iso,
            status="In progress",
        ),
        Task(
            title="Tipologi BCM detection logic refresh",
            description="Update TM rules per the 2021 PPATK advisory on investment-scam mule-victim layering.",
            owner="Compliance Engineering",
            due_date=in_days(14),
            status="Not started",
        ),
        Task(
            title="Active presentation to Dewan Komisaris (Board of Commissioners)",
            description="Two-tier governance — Dewan Direksi alone is not sufficient. Komisaris must engage actively.",
            owner="MLRO + Company Secretary",
            due_date=in_days(21),
            status="Not started",
            meeting_cadence="Dewan Komisaris quarterly",
        ),
    ]:
        t.notes = f"[seed-link:id_pojk_12] {t.notes}".strip()
        seeds.append(t)

    # ---- BSP Circular 1022 — CY 2024 annual independent compliance check ----
    for t in [
        Task(
            title="Close BSP Q4 2025 examination findings",
            description="60-90 day closure windows on findings — past March 2026, escalation to formal supervisory action.",
            owner="MLRO",
            due_date=in_days(-7),
            status="In progress",
        ),
        Task(
            title="EDD-on-PEP documentation upgrade",
            description="BSP examiners cited documentation as too thin — substantive source-of-wealth narrative required, not just a flag.",
            owner="Head of CDD",
            due_date=in_days(7),
            status="In progress",
        ),
        Task(
            title="AMLC Portal acknowledgement reconciliation",
            description="Submission ≠ acknowledgement. Reconcile internal STR log against AMLC Portal acks.",
            owner="MLRO",
            due_date=in_days(14),
            status="Not started",
        ),
        Task(
            title="EMI: e-wallet rapid in/out monitoring rule calibration for AMLC BCM-mule typology",
            description="Generic thresholds miss the BCM pattern; calibrate specifically for AMLC's published typology.",
            owner="Compliance Engineering",
            due_date=in_days(21),
            status="Blocked",
        ),
    ]:
        t.notes = f"[seed-link:ph_bsp_1022] {t.notes}".strip()
        seeds.append(t)

    # ---- AML/CFT Act 2009 s.59 — biennial independent audit ----
    for t in [
        Task(
            title="Engage qualified AML/CFT auditor (independence + competence)",
            description="Supervisor tests for both. Internal Audit acceptable only if it has not designed or operated any control being tested.",
            owner="AML/CFT Compliance Officer",
            due_date=iso,
            status="In progress",
        ),
        Task(
            title="Risk-based audit plan + sample selection",
            description="Cover institutional risk assessment; CDD/EDD; monitoring; PTR + SAR governance; goAML reconciliation; sanctions; training; record-keeping.",
            owner="Internal Audit",
            due_date=in_days(14),
            status="Not started",
        ),
        Task(
            title="Fieldwork + draft report",
            description="Aim to complete fieldwork by end of next quarter to bring the institution back into compliance.",
            owner="Internal Audit",
            due_date=in_days(60),
            status="Not started",
        ),
        Task(
            title="Supervisor-availability requirement: file in retrievable form",
            description="RBNZ / FMA / DIA can require production on request — store such that the report can be produced rapidly.",
            owner="Compliance Records Officer",
            due_date=in_days(75),
            status="Not started",
        ),
    ]:
        t.notes = f"[seed-link:nz_act_s59] {t.notes}".strip()
        seeds.append(t)

    # ---- FTRA Article 5-2 — VASP travel-rule annual compliance review ----
    for t in [
        Task(
            title="Travel-rule data exchange completeness sample (≥5%)",
            description="Sample qualifying transfers; verify all required fields per KoFIU Notice 2021-06.",
            owner="VASP Compliance Officer",
            due_date=in_days(-3),
            status="In progress",
        ),
        Task(
            title="Foreign-counterparty exception log audit",
            description="Each non-Korean counterparty exception must have a documented attempt + rationale per transfer.",
            owner="VASP Compliance Analyst",
            due_date=in_days(7),
            status="In progress",
        ),
        Task(
            title="High-risk wallet screening — confirm both inbound AND outbound coverage",
            description="Article 5-2 covers both directions; many providers screen only outbound.",
            owner="Head of KYT",
            due_date=in_days(14),
            status="Not started",
        ),
        Task(
            title="Verify travel-rule provider data-format complies with KoFIU Notice 2021-06",
            description="Some US/EU providers exchange data in non-KoFIU-compliant formats.",
            owner="Head of Vendor Management",
            due_date=in_days(14),
            status="Blocked",
        ),
        Task(
            title="Review report to FSC + KoFIU + remediation tracker",
            description="Q2 2026 thematic review focuses on travel-rule data-exchange completeness.",
            owner="VASP Compliance Officer",
            due_date=in_days(21),
            status="Not started",
        ),
    ]:
        t.notes = f"[seed-link:kr_ftra_5_2] {t.notes}".strip()
        seeds.append(t)

    return seeds


def relink_seed_tasks_to_obligations(
    obligations: list[Any],
) -> int:
    """Walk the persisted task list and resolve any [seed-link:KEY]
    placeholders to real obligation_ids by matching the obligation's
    title prefix against _LEGACY_OBLIGATION_KEYS. Returns the number
    of tasks linked. Idempotent — safe to call multiple times.

    Called once per Streamlit session at obligation-tab render time."""
    items = load_tasks()
    changed = 0
    for t in items:
        if t.obligation_id:
            continue
        # Find the seed-link tag in notes
        if "[seed-link:" not in (t.notes or ""):
            continue
        try:
            tag = t.notes.split("[seed-link:", 1)[1].split("]", 1)[0]
        except Exception:
            continue
        prefix = _LEGACY_OBLIGATION_KEYS.get(tag)
        if not prefix:
            continue
        match = next(
            (
                o for o in obligations
                if (o.title or "").startswith(prefix)
            ),
            None,
        )
        if match:
            t.obligation_id = match.id
            t.notes = t.notes.replace(f"[seed-link:{tag}]", "").strip()
            changed += 1
    if changed:
        save_tasks(items)
    return changed
