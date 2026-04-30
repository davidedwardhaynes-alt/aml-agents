"""Obligation register — track regulatory compliance obligations.

Simple per-institution obligation tracker. Persisted to a local YAML file.
For v0, single shared file. Per-user / per-tenant persistence comes with
production migration.

Each obligation carries enough detail for an MLRO to read the entry without
flipping to the regulator's source — full prose explanation, deadline
calculation, evidence required on examination, and a 'View source' link.
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
    # ----------------------------------------------------------------------
    # Optional rich-detail fields. Default to empty string so any YAML file
    # written before they were introduced still loads.
    # ----------------------------------------------------------------------
    full_text: str = ""
    """Multi-paragraph plain-prose explanation of what the obligation
    requires — scope, applicability, sanctions for breach. Read it
    without flipping to the source notice."""

    deadline_explanation: str = ""
    """How the deadline is calculated — anniversary date, fixed annual
    cut-off, calendar / financial year, supervisory cycle — and any grace
    period or extension mechanism."""

    evidence: str = ""
    """Artefacts the institution must produce on examination — board
    minutes, sample testing logs, training attestations, KYT sample
    populations, etc."""

    source_url: str = ""
    """Authoritative source URL — regulator notice or statute section.
    Rendered as 'View source →' in the expander footer."""


STATUSES = ["Open", "In progress", "Closed", "Overdue"]


def _coerce(item: dict[str, Any]) -> Obligation:
    """Build an Obligation from a YAML dict, ignoring fields the dataclass
    doesn't know about (forward-compat) and supplying defaults for any
    fields that pre-existing YAML files lack (backward-compat)."""
    known = {f for f in Obligation.__dataclass_fields__}
    safe = {k: v for k, v in (item or {}).items() if k in known}
    return Obligation(**safe)


def load_obligations() -> list[Obligation]:
    """Load obligations from disk. Returns seed data on first run."""
    if not OBLIGATIONS_PATH.exists():
        return _seed_obligations()
    with open(OBLIGATIONS_PATH) as f:
        raw = yaml.safe_load(f) or []
    return [_coerce(item) for item in raw]


def save_obligations(items: list[Obligation]) -> None:
    """Persist obligations to disk."""
    try:
        OBLIGATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OBLIGATIONS_PATH, "w") as f:
            yaml.dump(
                [asdict(o) for o in items],
                f,
                default_flow_style=False,
                sort_keys=False,
            )
    except (OSError, PermissionError):
        # Read-only filesystem (managed hosts): fail soft. Demo session is
        # the source of truth for the current container.
        pass


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
    full_text: str = "",
    deadline_explanation: str = "",
    evidence: str = "",
    source_url: str = "",
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
        full_text=full_text,
        deadline_explanation=deadline_explanation,
        evidence=evidence,
        source_url=source_url,
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


def reseed_obligations() -> list[Obligation]:
    """Discard any persisted obligations and rewrite the seed list from scratch.

    Useful when seed prose is updated and the running container has stale data
    on its writable disk. Triggered from the UI's 'Reset to seed' action.
    """
    seeds = _seed_obligations()
    save_obligations(seeds)
    return seeds


# ---------------------------------------------------------------------------
# Seed obligations — accurate references to live regulatory texts. Each
# obligation has been written to be defensibly close to the underlying
# regulator notice / statute. Where a notice has multiple sub-clauses the
# most material one is named explicitly.
# ---------------------------------------------------------------------------

def _seed_obligations() -> list[Obligation]:
    seeds = [
        # ===================================================================
        # SINGAPORE (STRO)
        # ===================================================================
        Obligation(
            title="MAS Notice 626 — annual independent AML/CFT audit",
            description=(
                "Annual independent audit of the bank's AML/CFT policies, "
                "procedures and controls covering customer due diligence, "
                "ongoing monitoring, screening, STR filing, training and "
                "record-keeping. Findings reported to the board."
            ),
            jurisdiction="Singapore (STRO)",
            statute_or_notice="MAS Notice 626 §13 — independent audit",
            due_date="2026-12-31",
            status="Open",
            owner="Head of Internal Audit + MLRO",
            notes=(
                "Coordinate with FY2026 audit plan; testing periods agreed "
                "with audit committee in Q2."
            ),
            full_text=(
                "MAS Notice 626 §13 requires every bank to subject its AML/CFT "
                "framework to an independent audit on a regular basis. Industry "
                "practice — confirmed by MAS thematic findings — is annual.\n\n"
                "Scope must cover the framework end-to-end: CDD on natural and "
                "legal persons, simplified and enhanced due diligence, beneficial-"
                "ownership identification, screening (sanctions, PEP, adverse "
                "media), ongoing monitoring rule effectiveness, STR governance, "
                "training adequacy, and record-keeping (5 years retention).\n\n"
                "The audit must be conducted by persons independent of the "
                "function being audited. Internal Audit typically runs it; "
                "co-source with external counsel or Big-4 when sample sizes are "
                "high or specialist testing is needed (e.g., trade finance "
                "sanctions screening).\n\n"
                "Findings, management response and remediation plan are reported "
                "to the audit committee and tracked through to closure. Open "
                "items at year-end are disclosed in the §13 attestation cycle."
            ),
            deadline_explanation=(
                "MAS supervises on a calendar-year basis. Audit fieldwork is "
                "typically completed by 30 November so the report can land at "
                "the December board / audit-committee meeting. The 31 December "
                "deadline reflects this practical anchor; supervisors expect "
                "annual cadence rather than a precise calendar date."
            ),
            evidence=(
                "Audit charter / engagement letter; risk-based audit plan; "
                "sample selection methodology; testing workpapers; report to "
                "audit committee; board minutes recording the discussion; "
                "remediation tracker; closure evidence for prior-year findings."
            ),
            source_url="https://www.mas.gov.sg/regulation/notices/notice-626",
        ),
        Obligation(
            title="MAS Notice 626 §6 — quarterly STR governance review",
            description=(
                "Quarterly governance review of all STRs filed: completeness, "
                "timeliness, escalation effectiveness, and STRO acknowledgement "
                "reconciliation."
            ),
            jurisdiction="Singapore (STRO)",
            statute_or_notice="MAS Notice 626 §6 + STRO Online filing system",
            due_date="2026-07-15",
            status="In progress",
            owner="MLRO",
            notes=(
                "Q2 2026 reconciliation. STRO acknowledgement latency ~5 "
                "working days. Track unacknowledged filings older than 14 days."
            ),
            full_text=(
                "MAS Notice 626 §6 places the STR obligation under the MLRO's "
                "personal accountability. The bank's MLRO must be satisfied "
                "that STRs are filed without delay where there is reason to "
                "suspect. Industry practice — and MAS supervisory expectation "
                "— is a quarterly governance review.\n\n"
                "The review covers four things. First, completeness: every "
                "internal alert that escalated to MLRO consideration has either "
                "been filed or has a documented MLRO no-file decision. Second, "
                "timeliness: median time from internal alert to filing, and the "
                "tail (the slowest 5%). MAS examiners increasingly probe the "
                "tail. Third, narrative quality: a sample of filed STRs are "
                "reviewed for completeness against MAS Notice 626 §6 reporting "
                "schema. Fourth, reconciliation: every internal STR-filed "
                "record has a matching STRO Online acknowledgement.\n\n"
                "Findings feed the MLRO's quarterly board / risk-committee "
                "report and any process changes are tracked through Internal "
                "Audit's continuous-monitoring inventory."
            ),
            deadline_explanation=(
                "Quarterly. The 15th of the month following quarter-end is the "
                "house standard at most SG banks — gives operations 10 working "
                "days to assemble the data and the MLRO 5 working days to "
                "review. Q1 by 15 April, Q2 by 15 July, Q3 by 15 October, Q4 "
                "by 15 January (also feeds into the §13 audit)."
            ),
            evidence=(
                "Quarterly STR governance pack; alert-to-filing latency "
                "histogram; STR sample QA scoresheet; STRO acknowledgement "
                "reconciliation; MLRO sign-off; risk-committee minute extract."
            ),
            source_url="https://www.mas.gov.sg/regulation/notices/notice-626",
        ),
        Obligation(
            title="STRO Online — designated officer renewal",
            description=(
                "Renew STRO Online designated-officer credentials and review "
                "user-access list (joiners, movers, leavers since last review)."
            ),
            jurisdiction="Singapore (STRO)",
            statute_or_notice=(
                "Corruption, Drug Trafficking and Other Serious Crimes "
                "(Confiscation of Benefits) Act + STRO operating procedures"
            ),
            due_date="2026-06-30",
            status="Open",
            owner="MLRO",
            notes=(
                "Two designated officers minimum recommended for continuity; "
                "submit renewal at least 10 working days before expiry."
            ),
            full_text=(
                "STRO Online is the primary filing channel for suspicious "
                "transaction reports under CDSA. Each reporting institution "
                "designates one or more officers authorised to file on the "
                "institution's behalf. Designations expire and must be "
                "renewed; STRO communicates renewal windows directly to "
                "named officers.\n\n"
                "Best practice — and resilience expectation — is to maintain "
                "at least two designated officers so a single absence does "
                "not interrupt filing. Joiners are designated on day one of "
                "their MLRO-team rotation; leavers are de-designated on "
                "their last working day in the function.\n\n"
                "User-access reviews should match HR's joiner-mover-leaver "
                "register against the STRO Online roster. Discrepancies are "
                "remediated immediately and the cause logged."
            ),
            deadline_explanation=(
                "STRO renewal cycles are typically 12 months but the precise "
                "expiry varies per officer. Treat this as a rolling obligation "
                "with a 30 June semi-annual review point that catches anyone "
                "whose individual credential lapses in the next 6 months."
            ),
            evidence=(
                "STRO Online renewal correspondence; current designated-"
                "officer roster; HR joiner-mover-leaver report cross-referenced; "
                "MLRO sign-off on the access list."
            ),
            source_url="https://www.police.gov.sg/about-us/organisational-structure/specialist-staff-departments/commercial-affairs-department/stro",
        ),

        # ===================================================================
        # HONG KONG (JFIU)
        # ===================================================================
        Obligation(
            title="HKMA AML/CFT Guideline §11 — annual self-assessment",
            description=(
                "Annual AML/CFT self-assessment return submitted to the HKMA "
                "covering CDD, ongoing monitoring, sanctions screening, STR "
                "filing, training, governance, and independent audit."
            ),
            jurisdiction="Hong Kong (JFIU)",
            statute_or_notice="HKMA AML/CFT Guideline (AI) §11 + SPM CG-5",
            due_date="2026-09-30",
            status="Open",
            owner="MLRO + Internal Audit",
            notes=(
                "Format: HKMA-prescribed Excel template. Independent assurance "
                "required. Engage Internal Audit by end-Q1 to plan testing."
            ),
            full_text=(
                "HKMA AML/CFT Guideline §11 obliges Authorised Institutions "
                "to conduct annual self-assessments of their AML/CFT systems "
                "and submit the prescribed return.\n\n"
                "The return covers eight control areas: institutional risk "
                "assessment, CDD (including beneficial ownership and ongoing), "
                "sanctions screening (transaction and counterparty), suspicious "
                "transaction monitoring and reporting, training, record-keeping, "
                "governance and independent audit, and compliance with the "
                "Anti-Money Laundering and Counter-Terrorist Financing Ordinance "
                "(AMLO) Schedule 2 specific requirements.\n\n"
                "Each control area requires a self-rating (Effective / Largely "
                "Effective / Partially Effective / Ineffective), supporting "
                "narrative, and remediation plan for any rating below Effective. "
                "Internal Audit independently validates a sample.\n\n"
                "Submissions are reviewed by the HKMA's AML Surveillance and "
                "Cooperation Division and may trigger thematic on-site "
                "inspections where ratings or trends flag concern."
            ),
            deadline_explanation=(
                "30 September each year per the HKMA's standard cycle. The "
                "return covers the prior calendar-year reporting period (1 Jan "
                "to 31 Dec). HKMA may extend in exceptional circumstances "
                "(typically system outages or regulator-side IT issues); no "
                "routine extensions are granted."
            ),
            evidence=(
                "Completed self-assessment template; supporting evidence "
                "binder per control area (board approvals, sample testing "
                "results, training completion, audit findings); Internal "
                "Audit independent validation report; submission "
                "acknowledgement from HKMA."
            ),
            source_url="https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/by-subject-current/aml-cft/",
        ),
        Obligation(
            title="SFC AML/CFT Guideline (VASP) §4 — quarterly KYT review",
            description=(
                "Quarterly review of know-your-transaction (KYT) tooling "
                "effectiveness for the VASP licensee — Chainalysis / TRM / "
                "Elliptic alert dispositioning, hop-distance methodology, "
                "darknet-cluster coverage, sanctioned-mixer flagging."
            ),
            jurisdiction="Hong Kong (JFIU)",
            statute_or_notice=(
                "SFC AML/CFT Guideline (VASP) §4 — STR + KYT obligations"
            ),
            due_date="2026-06-30",
            status="Open",
            owner="Head of FCC (VASP)",
            notes=(
                "Sample at least 5% of inbound deposits; document hop-distance "
                "methodology; reconcile vendor risk scores against in-house TM."
            ),
            full_text=(
                "Under the VASP regime that took effect on 1 June 2023, all "
                "licensed virtual-asset trading platforms in Hong Kong are "
                "subject to AML/CFT obligations equivalent in substance to "
                "those for Securities and Futures Commission licensees. The "
                "SFC AML/CFT Guideline for licensed VASPs §4 sets out the "
                "STR threshold and the supporting transaction-monitoring and "
                "KYT (know-your-transaction) requirements.\n\n"
                "KYT is the crypto-native analogue of TM. Licensees must use "
                "blockchain-analytics tooling — typically Chainalysis KYT, TRM "
                "Labs, or Elliptic Lens — to score inbound and outbound flows "
                "against darknet, mixer, sanctions, and scam-cluster exposure. "
                "Quarterly effectiveness review is industry standard.\n\n"
                "The review tests four things: (1) sample-based redispositioning "
                "of vendor alerts to confirm scoring is calibrated to the "
                "platform's risk profile; (2) hop-distance methodology — most "
                "platforms set a 2-hop default but escalate to 5+ hops on hits; "
                "(3) coverage of new threat clusters added to vendor data sets "
                "(e.g., post-Hydra successor markets); (4) reconciliation "
                "between vendor risk scores and the platform's own TM rule "
                "outputs."
            ),
            deadline_explanation=(
                "Quarterly. 30 June for Q2; subsequent quarters track 30 Sep, "
                "31 Dec and 31 Mar. Each review covers the prior 90 days of "
                "transaction data."
            ),
            evidence=(
                "Quarterly KYT review pack; sample population (≥5% of inbound "
                "deposits); alert-disposition QA logs; vendor-risk vs in-house "
                "TM reconciliation; hop-distance documentation; head-of-FCC "
                "sign-off."
            ),
            source_url="https://www.sfc.hk/en/Rules-and-standards/AML-CFT-VASP",
        ),
        Obligation(
            title="AMLO §16 — periodic CDD review (high-risk customers)",
            description=(
                "Periodic CDD review for high-risk customers — minimum annual; "
                "evidence refreshed; risk rating reaffirmed or adjusted; STR "
                "considered if pattern materially changed."
            ),
            jurisdiction="Hong Kong (JFIU)",
            statute_or_notice="AMLO Schedule 2 §5 + HKMA Guideline §4.7",
            due_date="2026-12-31",
            status="In progress",
            owner="MLRO + Relationship Managers",
            notes=(
                "High-risk population at 2026-Q1 = ~7% of book; review backlog "
                "at start of year was 12 customers (3% of high-risk). Target: "
                "zero backlog at 31 Dec."
            ),
            full_text=(
                "AMLO Schedule 2 §5 (and HKMA Guideline §4.7) require CDD "
                "information to be kept up to date and relevant. For high-risk "
                "customers — including PEPs, customers in high-risk "
                "jurisdictions, and customers whose transaction patterns "
                "warrant enhanced monitoring — the practical interpretation is "
                "a periodic review at least annually.\n\n"
                "The review covers: (1) static-data refresh — current address, "
                "occupation, source of wealth, beneficial-ownership chain; (2) "
                "transaction-pattern review — actual flow against expected "
                "profile, with material deviation triggering an alert; (3) "
                "risk-rating reaffirmation — confirm the rating still reflects "
                "the customer's risk drivers, or re-rate; (4) screening — "
                "fresh sanctions, PEP and adverse-media screen against the "
                "current customer record.\n\n"
                "Findings that the pattern has changed materially without "
                "explanation must be considered for STR filing. The review "
                "outcome is logged with the relationship file and sampled by "
                "Internal Audit."
            ),
            deadline_explanation=(
                "Annual minimum. High-risk customers should be on a tracker "
                "with a target review date 12 months from last review. "
                "Year-end (31 December) is the operational anchor — any "
                "high-risk customer not reviewed in the calendar year is in "
                "breach by 1 January."
            ),
            evidence=(
                "Customer review file with refreshed CDD; comparison of "
                "expected-vs-actual transaction profile; risk-rating "
                "reaffirmation note; screening output; STR consideration log; "
                "RM and MLRO sign-offs."
            ),
            source_url="https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/by-subject-current/aml-cft/",
        ),

        # ===================================================================
        # MALAYSIA (FIED)
        # ===================================================================
        Obligation(
            title="AMLA s.14 — STR filing obligation (continuous)",
            description=(
                "Continuous obligation to file Suspicious Transaction Reports "
                "with FIED 'as soon as practicable' after suspicion crystallises. "
                "MLRO accountable; tipping-off prohibited."
            ),
            jurisdiction="Malaysia (FIED)",
            statute_or_notice=(
                "AMLA 2001 s.14 + BNM AML/CFT Sectoral Guidelines for "
                "Banking & Deposit-Taking Institutions"
            ),
            due_date="2026-12-31",
            status="In progress",
            owner="MLRO",
            notes=(
                "Continuous obligation tracked via STR governance KPI: median "
                "alert-to-filing latency target ≤7 calendar days."
            ),
            full_text=(
                "Section 14 of the Anti-Money Laundering, Anti-Terrorism "
                "Financing and Proceeds of Unlawful Activities Act 2001 (AMLA) "
                "imposes the core STR filing obligation on every reporting "
                "institution. The obligation is continuous — there is no "
                "monetary threshold — and crystallises when the institution "
                "has reason to suspect that funds, transactions or attempted "
                "transactions involve proceeds of unlawful activity, terrorism "
                "financing, or related predicate offences.\n\n"
                "Reports are filed to BNM's Financial Intelligence and "
                "Enforcement Department (FIED) via the Financial Intelligence "
                "System (FINS). 'As soon as practicable' has been interpreted "
                "by BNM in supervisory guidance to mean within working days "
                "of MLRO determination — practical industry standard targets "
                "median 7 days from internal alert.\n\n"
                "Failure to file is a criminal offence under AMLA s.14(2). "
                "Tipping-off the customer is a separate offence under s.35.\n\n"
                "MLRO is personally accountable. The bank's STR governance "
                "framework must demonstrate (i) a documented MLRO opinion on "
                "every alert escalated, (ii) a clear no-file rationale for "
                "any closed alert, and (iii) end-to-end filing-latency "
                "tracking at portfolio and country level."
            ),
            deadline_explanation=(
                "AMLA s.14 is a continuous obligation. The 31 December "
                "year-end deadline shown here is a tracking anchor for the "
                "annual STR governance KPI: zero AMLA s.14 timeliness "
                "exceptions outstanding at year-end."
            ),
            evidence=(
                "FINS submission log; MLRO opinion files; alert-to-filing "
                "latency dashboard; tipping-off log (zero entries expected); "
                "MLRO quarterly board pack."
            ),
            source_url="https://amlcft.bnm.gov.my/",
        ),
        Obligation(
            title="BNM AML/CFT Sectoral Guidelines — annual independent audit",
            description=(
                "Annual independent audit of the AML/CFT programme by Internal "
                "Audit or external auditor; findings to board. Minimum scope "
                "and methodology in BNM Sectoral Guidelines for the bank's "
                "sector."
            ),
            jurisdiction="Malaysia (FIED)",
            statute_or_notice=(
                "BNM AML/CFT Sectoral Guidelines + Risk-Based Approach "
                "Supervisory Framework"
            ),
            due_date="2026-12-31",
            status="Open",
            owner="Head of Internal Audit + MLRO",
            notes=(
                "Board approval of audit plan by end-Q1; fieldwork by end-Q3; "
                "report at December board."
            ),
            full_text=(
                "BNM's AML/CFT Sectoral Guidelines (issued separately for "
                "banking, money services business, insurance, capital markets, "
                "and DNFBP sectors) all require annual independent testing of "
                "the institution's AML/CFT programme.\n\n"
                "Scope is identical in substance to MAS Notice 626 §13 and "
                "HKMA §11 — CDD, monitoring, screening, STR governance, "
                "training, record-keeping, governance, and IT control over "
                "AML systems. BNM additionally expects testing of CTR (cash "
                "transaction reports above MYR 25,000) completeness and "
                "timeliness, and a specific assessment of AMLA s.14 STR "
                "filing latency.\n\n"
                "Auditor independence is a key BNM expectation. Internal "
                "Audit is acceptable provided it has not been involved in "
                "designing or operating any of the controls being tested. "
                "External co-source is required where Internal Audit lacks "
                "specialist capability (e.g. crypto / VASP testing for the "
                "few BNM-regulated digital banks)."
            ),
            deadline_explanation=(
                "Annual. BNM's calendar-year supervisory cycle anchors the "
                "31 December year-end deadline. Most banks plan fieldwork "
                "September–November so the report can be tabled at the "
                "December board / audit-committee meeting."
            ),
            evidence=(
                "Board-approved audit plan; testing workpapers; sample "
                "selection (RBA-driven); audit report; management response; "
                "remediation tracker; board minute extract recording the "
                "discussion."
            ),
            source_url="https://amlcft.bnm.gov.my/",
        ),
        Obligation(
            title="Shariah Governance Policy — annual Shariah audit (AML overlap)",
            description=(
                "Annual Shariah audit covering AML touchpoints — Tawarruq "
                "commodity flow, Wakalah agency arrangements, Hibah gift "
                "treatments — to ensure AMLA-compliant CDD overlays are "
                "preserved through Shariah-compliant structures."
            ),
            jurisdiction="Malaysia (FIED)",
            statute_or_notice=(
                "BNM Shariah Governance Policy 2019 + IFSA 2013 + AMLA s.13/14"
            ),
            due_date="2026-12-31",
            status="Open",
            owner="Shariah Committee + MLRO",
            notes=(
                "Tawarruq commodity-trade documentation testing the highest "
                "scope priority; coordinate with Shariah Risk Management."
            ),
            full_text=(
                "The Islamic Financial Services Act 2013 (IFSA) and BNM's "
                "Shariah Governance Policy 2019 require Islamic banking "
                "institutions to conduct an annual Shariah audit. AMLA "
                "obligations apply to Islamic banks identically to "
                "conventional banks; the Shariah audit explicitly covers the "
                "touchpoints where Shariah-compliant structures interact "
                "with AML controls.\n\n"
                "Three structures account for most overlap. Tawarruq "
                "(commodity murabaha) generates a paper trail of commodity "
                "trades that must withstand AML/TBML scrutiny — fictitious "
                "or circular trades present financial-crime as well as "
                "Shariah issues. Wakalah arrangements (agency) introduce "
                "intermediated funds movement that complicates customer "
                "attribution under AMLA s.16 CDD obligations. Hibah (gift) "
                "products must not be used to circumvent the source-of-funds "
                "explanation expected in EDD on high-risk customers.\n\n"
                "The Shariah Audit Committee scopes the AML overlap component "
                "in coordination with the MLRO. Findings are reported to the "
                "Shariah Committee and, where AMLA implications exist, to the "
                "audit committee and board."
            ),
            deadline_explanation=(
                "Annual. BNM Shariah Governance Policy aligns with the bank's "
                "financial year. Most Islamic banks in Malaysia run a calendar-"
                "year cycle, putting the Shariah audit report at the December "
                "Shariah Committee meeting."
            ),
            evidence=(
                "Shariah audit charter; Tawarruq trade-documentation sample; "
                "Wakalah agency-relationship file review; Hibah customer-"
                "messaging review; Shariah Committee minute extract."
            ),
            source_url="https://www.bnm.gov.my/-/shariah-governance-policy-2019",
        ),

        # ===================================================================
        # AUSTRALIA (AUSTRAC SMR)
        # ===================================================================
        Obligation(
            title="AML/CTF Act s.84 — annual AML/CTF Program review",
            description=(
                "Annual board-level review and approval of the AML/CTF "
                "Program (Part A — risk-based systems and controls; Part B — "
                "customer identification programme)."
            ),
            jurisdiction="Australia (AUSTRAC SMR)",
            statute_or_notice="AML/CTF Act 2006 s.84 + AML/CTF Rules Part 8",
            due_date="2026-08-31",
            status="Open",
            owner="AML/CTF Compliance Officer",
            notes=(
                "Aligns with FY2026 board cycle. Independent review of Part A "
                "required at minimum every 2 years per AML/CTF Rule 8.4."
            ),
            full_text=(
                "Section 84 of the Anti-Money Laundering and Counter-"
                "Terrorism Financing Act 2006 requires every reporting entity "
                "to maintain a written AML/CTF Program. Part A documents the "
                "reporting entity's ML/TF risk assessment and the systems and "
                "controls put in place to manage and mitigate that risk. Part "
                "B is the Customer Identification Programme.\n\n"
                "Both Parts must be reviewed regularly to ensure they remain "
                "appropriate. AUSTRAC's interpretation — codified in AML/CTF "
                "Rule 8.4 — is annual board-level review for Part A and a "
                "minimum biennial independent review (internal audit, "
                "external auditor, or qualified consultant).\n\n"
                "The annual review tests four things: (1) currency of the "
                "ML/TF risk assessment against external threat indicators "
                "(including AUSTRAC's annual ML/TF Risk Assessment); (2) "
                "control adequacy — sample testing of key controls; (3) "
                "policy currency — written procedures up to date with "
                "regulatory change; (4) board oversight — board minutes show "
                "active engagement, not pro forma approval.\n\n"
                "Material changes to the AML/CTF Program must be re-approved "
                "by the board and notified to AUSTRAC where they are "
                "substantive (AML/CTF Rule 8.5)."
            ),
            deadline_explanation=(
                "Annual. The 31 August deadline aligns with the post-FY26 "
                "(financial year ending 30 June) board cycle — most ASX-listed "
                "and APRA-regulated reporting entities approve the annual "
                "AML/CTF Program review at the August or September board "
                "meeting. Smaller entities may anchor to calendar year-end."
            ),
            evidence=(
                "Board-approved AML/CTF Program (Parts A and B); ML/TF risk "
                "assessment; control-testing workpapers; independent review "
                "report (where due); board minute extract recording approval."
            ),
            source_url="https://www.austrac.gov.au/business/how-comply-and-report-guidance-and-resources/guidance-resources/aml-ctf-program",
        ),
        Obligation(
            title="Tranche 2 — phased commencement of new reporting entities",
            description=(
                "Pre-commencement registration with AUSTRAC for Tranche 2 "
                "obligations (legal practitioners, accountants, real estate "
                "professionals, conveyancers, dealers in precious metals and "
                "stones, and trust and company service providers)."
            ),
            jurisdiction="Australia (AUSTRAC SMR)",
            statute_or_notice=(
                "AML/CTF Amendment (Reform) Act 2024 + AUSTRAC implementation "
                "schedule"
            ),
            due_date="2026-06-30",
            status="Open",
            owner="Managing Partner + appointed AML/CTF Compliance Officer",
            notes=(
                "Phased: registration window opens early 2026, full obligations "
                "commence 1 July 2026 for in-scope sectors per AUSTRAC schedule."
            ),
            full_text=(
                "The Anti-Money Laundering and Counter-Terrorism Financing "
                "Amendment (Tranche 2) Act 2024 extends Australia's AML/CTF "
                "regime to designated non-financial businesses and "
                "professions (DNFBPs). The reform brings Australia into "
                "alignment with FATF Recommendation 22 — a gap that has "
                "been a recurring finding in successive FATF mutual "
                "evaluations of Australia.\n\n"
                "In-scope sectors: legal practitioners, accountants and "
                "registered tax/BAS agents, real estate professionals, "
                "conveyancers, dealers in precious metals and stones, and "
                "trust and company service providers (TCSPs).\n\n"
                "Implementation is phased. Registration windows opened "
                "progressively from early 2026; full AML/CTF Program "
                "implementation, customer-identification, ongoing-monitoring "
                "and Suspicious Matter Report (SMR) obligations commence on "
                "1 July 2026 for the largest cohort.\n\n"
                "Pre-commencement actions for in-scope firms: (1) appoint an "
                "AML/CTF Compliance Officer; (2) draft Parts A and B of the "
                "AML/CTF Program; (3) implement a customer-identification "
                "procedure for new and existing clients (with risk-based "
                "look-back for existing); (4) register with AUSTRAC; (5) "
                "implement the Independent Review timetable from year 2."
            ),
            deadline_explanation=(
                "30 June 2026 is the AUSTRAC pre-commencement registration "
                "deadline for the first cohort. Some sub-sectors and smaller "
                "firms have later phase-in dates — check the AUSTRAC "
                "implementation schedule for your specific sector."
            ),
            evidence=(
                "AUSTRAC registration confirmation; AML/CTF Compliance "
                "Officer appointment letter; draft AML/CTF Program; CIP "
                "policy; existing-client risk-based look-back plan; staff "
                "training register."
            ),
            source_url="https://www.austrac.gov.au/business/new-to-the-regime-tranche-2-reforms",
        ),
        Obligation(
            title="AML/CTF Rules Part 13 — annual compliance report",
            description=(
                "Annual compliance report to AUSTRAC summarising the reporting "
                "entity's compliance with the AML/CTF Act and Rules over the "
                "preceding 12 months."
            ),
            jurisdiction="Australia (AUSTRAC SMR)",
            statute_or_notice="AML/CTF Act s.47 + AML/CTF Rules Part 13",
            due_date="2026-03-31",
            status="Closed",
            owner="AML/CTF Compliance Officer",
            notes=(
                "FY2025 cycle closed; FY2026 cycle opens January 2027 for "
                "lodgement by 31 March 2027."
            ),
            full_text=(
                "Section 47 of the AML/CTF Act and AML/CTF Rules Part 13 "
                "require all reporting entities (other than those expressly "
                "exempt) to lodge an annual compliance report with AUSTRAC. "
                "The report is lodged through the AUSTRAC Online portal "
                "using the prescribed online form.\n\n"
                "Coverage period is the preceding calendar year (1 January "
                "to 31 December). The report attests to the reporting entity's "
                "compliance with each applicable AML/CTF obligation and "
                "identifies any non-compliance, with explanation and "
                "remediation.\n\n"
                "Wilfully or recklessly making a false or misleading statement "
                "in the annual compliance report attracts criminal penalties "
                "under AML/CTF Act s.137. AUSTRAC's compliance team uses the "
                "report as a primary input into supervisory prioritisation; "
                "discrepancies between the report and observed activity (SMR "
                "patterns, threshold transaction reports, IFTI reports) are a "
                "common trigger for enforcement engagement."
            ),
            deadline_explanation=(
                "31 March each year, covering the preceding calendar year. "
                "AUSTRAC Online opens lodgement around mid-January. No "
                "routine extensions; technical-issue extensions handled "
                "case-by-case."
            ),
            evidence=(
                "AUSTRAC Online lodgement confirmation; supporting evidence "
                "binder for each attestation; board / governance committee "
                "endorsement of the report before lodgement."
            ),
            source_url="https://www.austrac.gov.au/business/how-comply-and-report-guidance-and-resources/reporting/compliance-reports",
        ),
    ]
    save_obligations(seeds)
    return seeds
