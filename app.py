import io
import os
import re
import time
from datetime import date
from pathlib import Path

import markdown as md_pkg
import streamlit as st
import streamlit_authenticator as stauth
from anthropic import Anthropic
from dotenv import load_dotenv
from fpdf import FPDF

from auth.users import (
    get_user_avatar_path,
    get_user_profile,
    load_config,
    save_avatar,
    save_config,
    update_user_profile,
)
from lib.connectors import (
    ALL_STATUSES as CONNECTOR_STATUSES,
    CATEGORIES as CONNECTOR_CATEGORIES,
    STATUS_COLOURS as CONNECTOR_STATUS_COLOURS,
    by_category as connectors_by_category,
    by_status as connectors_by_status,
    search as connectors_search,
)
from lib.regulators import (
    JURISDICTION_ORDER as REG_JURISDICTIONS,
    REGULATORS as REG_DIRECTORY,
    search as regulators_search,
    total_count as reg_total_count,
    total_with_rss as reg_total_with_rss,
)
from lib.consortium import (
    amount_band,
    extract_tags,
    lookup as consortium_lookup,
    submit as consortium_submit,
)
from lib.horizon import all_items_for_jurisdiction, items_for_jurisdiction
from lib.news import TOPICS as NEWS_TOPICS, items_for as news_items_for
from lib.obligations import (
    STATUSES,
    add_obligation,
    delete_obligation,
    load_obligations,
    update_obligation,
)
from lib.sanctions import classify_match, search_sanctions, summarize_entity

# override=True ensures .env changes are picked up on every Streamlit rerun
# (without needing a full server restart). Critical for API key updates.
load_dotenv(override=True)


def render_regulator_directory(key_prefix: str) -> None:
    """Render the regulator directory: search + collapsible-per-jurisdiction.

    Used by Horizon scanning, Obligation register, and Jurisdictional news tabs.
    `key_prefix` must be unique per call site to avoid Streamlit widget key clashes.
    """
    total = reg_total_count()
    with_rss = reg_total_with_rss()
    with st.expander(
        f"Tracked regulator & authority directory — {total} sources across {len(REG_JURISDICTIONS)} jurisdictions",
        expanded=False,
    ):
        st.caption(
            f"{with_rss} regulators expose stable RSS feeds (already in the live-pull config). "
            f"The remainder are reference links — open in a new tab to consult directly. "
            f"This is the same authoritative set across Horizon, Obligations, and News tabs."
        )
        reg_query = st.text_input(
            "Search regulators (name, type, URL)",
            key=f"{key_prefix}_reg_search",
            placeholder="e.g. AUSTRAC, central bank, FIU, sanctions, Singapore...",
        )

        if reg_query.strip():
            results = regulators_search(reg_query)
            if not results:
                st.info(f"No regulators match '{reg_query}'.")
            else:
                st.caption(f"{len(results)} result(s)")
                cols = st.columns(2)
                for i, (jur, r) in enumerate(results):
                    with cols[i % 2]:
                        rss_badge = (
                            ' <span style="background:#10b981;color:white;padding:0.1rem 0.4rem;'
                            'border-radius:3px;font-size:0.65rem;font-weight:600;'
                            'text-transform:uppercase;">RSS</span>'
                            if r.rss_url else ""
                        )
                        st.markdown(
                            f'<div style="border-left:3px solid #1e40af;padding:0.5rem 0.8rem;'
                            f'margin-bottom:0.4rem;background:#f8fafc;border-radius:4px;">'
                            f'<div style="font-weight:600;color:#0f172a;font-size:0.92rem;">'
                            f'<a href="{r.url}" target="_blank" style="color:#1e40af;text-decoration:none;">'
                            f'{r.name}</a>{rss_badge}</div>'
                            f'<div style="font-size:0.74rem;color:#64748b;margin-top:0.15rem;">'
                            f'{jur}  ·  {r.type}</div></div>',
                            unsafe_allow_html=True,
                        )
        else:
            for jur in REG_JURISDICTIONS:
                regs = REG_DIRECTORY.get(jur, [])
                if not regs:
                    continue
                rss_count = sum(1 for r in regs if r.rss_url)
                summary = f"{jur} — {len(regs)} source{'s' if len(regs) != 1 else ''}"
                if rss_count > 0:
                    summary += f" · {rss_count} RSS"
                # Keep a few key jurisdictions auto-expanded
                expanded = jur in ("Singapore", "Hong Kong", "Malaysia", "Australia")
                with st.expander(summary, expanded=expanded):
                    cols = st.columns(2)
                    for i, r in enumerate(regs):
                        with cols[i % 2]:
                            rss_badge = (
                                ' <span style="background:#10b981;color:white;padding:0.1rem 0.4rem;'
                                'border-radius:3px;font-size:0.62rem;font-weight:600;'
                                'text-transform:uppercase;">RSS</span>'
                                if r.rss_url else ""
                            )
                            st.markdown(
                                f'<div style="border-left:2px solid #cbd5e1;padding:0.4rem 0.7rem;'
                                f'margin-bottom:0.3rem;background:#f8fafc;border-radius:4px;">'
                                f'<div style="font-size:0.86rem;color:#0f172a;">'
                                f'<a href="{r.url}" target="_blank" style="color:#1e40af;text-decoration:none;">'
                                f'{r.name}</a>{rss_badge}</div>'
                                f'<div style="font-size:0.7rem;color:#64748b;margin-top:0.12rem;">'
                                f'{r.type}</div></div>',
                                unsafe_allow_html=True,
                            )


def narrative_to_pdf(
    narrative: str,
    str_reference: str,
    reporting_institution: str,
    jurisdiction: str,
) -> bytes:
    """Render the markdown narrative as a PDF via fpdf2's write_html.

    Strips non-Latin-1 chars (fpdf2 core fonts only support Latin-1) and
    converts the markdown to HTML, then renders.
    """

    def ascii_safe(s: str) -> str:
        replacements = {
            "—": "-", "–": "-", "·": "|", "•": "-",
            "“": '"', "”": '"', "‘": "'", "’": "'",
            "…": "...", "→": "->", "←": "<-",
            "✓": "[OK]", "✗": "[X]", "⚠": "[!]",
        }
        for k, v in replacements.items():
            s = s.replace(k, v)
        return s.encode("latin-1", errors="replace").decode("latin-1")

    safe_narrative = ascii_safe(narrative)
    body_html = md_pkg.markdown(safe_narrative, extensions=["extra"])

    header_html = (
        f"<h2>Suspicious Transaction Report</h2>"
        f"<p><i>{ascii_safe(jurisdiction)}  |  Ref: {ascii_safe(str_reference)}</i></p>"
    )
    if reporting_institution:
        header_html += f"<p><i>{ascii_safe(reporting_institution)}</i></p>"
    header_html += "<hr/>"

    full_html = header_html + body_html

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.write_html(full_html)

    output = pdf.output()
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)

ROOT = Path(__file__).parent
RUBRICS = {
    "Singapore (STRO)": ROOT / "rubrics" / "strostr.md",
    "Hong Kong (JFIU)": ROOT / "rubrics" / "jfiustr.md",
    "Malaysia (FIED)": ROOT / "rubrics" / "fiedstr.md",
    "Australia (AUSTRAC SMR)": ROOT / "rubrics" / "austracsmr.md",
}
GUIDANCE = {
    "Singapore (STRO)": ROOT / "guidance" / "sg-stro.md",
    "Hong Kong (JFIU)": ROOT / "guidance" / "hk-jfiu.md",
    "Malaysia (FIED)": ROOT / "guidance" / "my-fied.md",
    "Australia (AUSTRAC SMR)": ROOT / "guidance" / "au-austrac.md",
}
JURISDICTION_LABEL = {
    "Singapore (STRO)": "Singapore",
    "Hong Kong (JFIU)": "Hong Kong",
    "Malaysia (FIED)": "Malaysia",
    "Australia (AUSTRAC SMR)": "Australia",
}
JURISDICTION_AUTHORITIES = {
    "Singapore (STRO)": [
        {"abbr": "MAS", "name": "Monetary Authority of Singapore"},
        {"abbr": "STRO", "name": "Suspicious Transaction Reporting Office"},
        {"abbr": "SPF", "name": "Singapore Police Force"},
    ],
    "Hong Kong (JFIU)": [
        {"abbr": "HKMA", "name": "Hong Kong Monetary Authority"},
        {"abbr": "JFIU", "name": "Joint Financial Intelligence Unit"},
        {"abbr": "SFC", "name": "Securities and Futures Commission"},
    ],
    "Malaysia (FIED)": [
        {"abbr": "BNM", "name": "Bank Negara Malaysia"},
        {"abbr": "FIED", "name": "Financial Intelligence Enforcement Dept"},
        {"abbr": "SC", "name": "Securities Commission Malaysia"},
    ],
    "Australia (AUSTRAC SMR)": [
        {"abbr": "AUSTRAC", "name": "AUS Transaction Reports & Analysis Centre"},
    ],
}

# Reporting entity categories per jurisdiction. Picked by analyst at filing time
# so the model can tailor narrative context (sectoral notice references, etc.).
ENTITY_CATEGORIES = {
    "Singapore (STRO)": [
        "— Select —",
        "Bank (full / wholesale / merchant)",
        "Finance company",
        "Payment institution (PI / MPI)",
        "E-money issuer",
        "Digital payment token (DPT) service provider",
        "Money changer / remittance business",
        "Capital markets services (CMS) licensee",
        "Fund manager (LFMC / RFMC)",
        "Insurer (life / general / composite)",
        "Insurance broker",
        "Financial adviser",
        "Trust company",
        "Lawyer / legal practice (DNFBP)",
        "Accountant / public accounting entity (DNFBP)",
        "Corporate service provider (DNFBP)",
        "Real estate agent / salesperson (DNFBP)",
        "Precious stones and metals dealer (PSMD)",
    ],
    "Hong Kong (JFIU)": [
        "— Select —",
        "Authorized institution — bank",
        "Authorized institution — virtual bank (HKMA-licensed digital, e.g. ZA Bank, Mox, livi, WeLab)",
        "Authorized institution — restricted licence bank / DTC",
        "Licensed corporation (SFC) — Type 1 (dealing in securities)",
        "Licensed corporation (SFC) — Type 4 / 9 (advising / asset management)",
        "Licensed corporation (SFC) — other Types 2/3/5/6/7/8/10/11/12",
        "Authorized insurer",
        "Insurance broker / agent",
        "Money service operator (MSO)",
        "Stored value facility (SVF) — HKMA-licensed",
        "Trust or company service provider (TCSP)",
        "Virtual asset service provider (VASP) — SFC Type 1+7 licensed",
        "Solicitor / law firm (DNFBP)",
        "Accountant (DNFBP)",
        "Estate agent (DNFBP)",
        "Precious metals / stones dealer (DNFBP)",
    ],
    "Malaysia (FIED)": [
        "— Select —",
        "Licensed bank — conventional",
        "Licensed Islamic bank (full-fledged, e.g. Bank Islam, Maybank Islamic)",
        "Islamic banking window (within a conventional bank)",
        "Digital bank — conventional (BNM digital banking licensee, e.g. Boost Bank, GXBank)",
        "Digital bank — Islamic (BNM digital Islamic licensee, e.g. AEON Bank, KAF Digital)",
        "Investment bank",
        "Development financial institution (DFI)",
        "Money services business (MSB)",
        "Insurance / takaful operator",
        "Insurance broker",
        "Capital market intermediary (SC-licensed)",
        "E-money issuer",
        "Digital asset exchange (DAE — SC-registered)",
        "Trust company",
        "Accountant / auditor (DNFBP)",
        "Lawyer (DNFBP)",
        "Company secretary (DNFBP)",
        "Real estate agent (DNFBP)",
        "Precious metals / stones dealer (DNFBP)",
        "Casino / gaming operator",
        "Pawnbroker",
    ],
    "Australia (AUSTRAC SMR)": [
        "— Select —",
        "Authorised deposit-taking institution (ADI) — major bank",
        "ADI — credit union / building society / mutual",
        "ADI — neobank / digital-only bank",
        "Insurer / life insurance product provider",
        "Designated remittance service",
        "Gambling service provider — casino / wagering / bookmaker",
        "Online wagering platform",
        "Bullion dealer",
        "Digital currency exchange (DCE) — AUSTRAC-registered",
        "Securities / derivatives dealer (ASIC-licensed)",
        "Solicitor (Tranche 2 — from 2026)",
        "Accountant / conveyancer (Tranche 2 — from 2026)",
        "Real estate agent (Tranche 2 — from 2026)",
        "Precious metals dealer (Tranche 2 — from 2026)",
    ],
}

# Library of named sample cases per jurisdiction. Each maps to (case_dict_key,
# filing_dict_key) — keys into SAMPLE_CASES and SAMPLE_FILING_METADATAS.
SAMPLE_LIBRARY = {
    "Singapore (STRO)": {
        "Trade-based ML — fintech wholesale": ("Singapore (STRO)", "Singapore (STRO)"),
            'DPT — crypto cash-out via mixer': ('Singapore (STRO) — DPT cash-out', 'Singapore (STRO) — DPT cash-out'),
        'Real estate (DNFBP) — high-value foreign UBO': ('Singapore (STRO) — Real estate DNFBP', 'Singapore (STRO) — Real estate DNFBP'),
        'Lawyer (DNFBP) — trust account misuse': ('Singapore (STRO) — Lawyer trust account misuse', 'Singapore (STRO) — Lawyer trust account misuse'),
        'PSMD — gold cash conversion / structuring': ('Singapore (STRO) — PSMD gold cash conversion', 'Singapore (STRO) — PSMD gold cash conversion'),
        'Capital markets — OTC wash trading': ('Singapore (STRO) — Capital markets OTC wash trading', 'Singapore (STRO) — Capital markets OTC wash trading'),
},
    "Hong Kong (JFIU)": {
        "Jewelry trading + sanctions hit": (
            "Hong Kong (JFIU)", "Hong Kong (JFIU)",
        ),
        "VASP — darknet-tagged inflow + third-party cash-out": (
            "Hong Kong (JFIU) — VASP darknet flow",
            "Hong Kong (JFIU) — VASP darknet flow",
        ),
        "Bank — Macau-junket layering through trade shell": (
            "Hong Kong (JFIU) — Casino-junket bank layering",
            "Hong Kong (JFIU) — Casino-junket bank layering",
        ),
            'Virtual bank — ML-detected mule cluster': ('Hong Kong (JFIU) — Virtual bank mule cluster', 'Hong Kong (JFIU) — Virtual bank mule cluster'),
        'TCSP — shell company nominee abuse': ('Hong Kong (JFIU) — TCSP shell nominee abuse', 'Hong Kong (JFIU) — TCSP shell nominee abuse'),
        'MSO — undocumented remittance corridor': ('Hong Kong (JFIU) — MSO undocumented remittance corridor', 'Hong Kong (JFIU) — MSO undocumented remittance corridor'),
},
    "Malaysia (FIED)": {
        "Palm oil TBML — conventional bank": (
            "Malaysia (FIED)", "Malaysia (FIED)",
        ),
        "Digital bank — money mule + investment scam victim": (
            "Malaysia (FIED) — Digital bank mule", "Malaysia (FIED) — Digital bank mule",
        ),
        "Islamic bank — Tawarruq layering": (
            "Malaysia (FIED) — Islamic Tawarruq", "Malaysia (FIED) — Islamic Tawarruq",
        ),
            'Digital asset exchange (DAE) — scam-mule flow': ('Malaysia (FIED) — Digital asset exchange', 'Malaysia (FIED) — Digital asset exchange'),
        'E-money issuer — wallet-based mule activity': ('Malaysia (FIED) — E-money issuer wallet mule', 'Malaysia (FIED) — E-money issuer wallet mule'),
        'Pawnbroker — gold cash layering': ('Malaysia (FIED) — Pawnbroker gold layering', 'Malaysia (FIED) — Pawnbroker gold layering'),
},
    "Australia (AUSTRAC SMR)": {
        "Crypto DCE — structuring + mule victim": (
            "Australia (AUSTRAC SMR)", "Australia (AUSTRAC SMR)",
        ),
        "Casino — chip-walking + cross-property redemption": (
            "Australia (AUSTRAC SMR) — Casino chip-walking",
            "Australia (AUSTRAC SMR) — Casino chip-walking",
        ),
        "Tranche 2 — real estate corruption-proceeds (post-2026)": (
            "Australia (AUSTRAC SMR) — Tranche 2 real estate cash buyer",
            "Australia (AUSTRAC SMR) — Tranche 2 real estate cash buyer",
        ),
            'Tranche 2 real estate agent — first SMR (post-2026)': ('Australia (AUSTRAC SMR) — Tranche 2 real estate agent', 'Australia (AUSTRAC SMR) — Tranche 2 real estate agent'),
        'Tranche 2 accountant — corporate-structuring advisory': ('Australia (AUSTRAC SMR) — Tranche 2 accountant corporate-structuring', 'Australia (AUSTRAC SMR) — Tranche 2 accountant corporate-structuring'),
        'Tranche 2 precious metals dealer — cash structuring': ('Australia (AUSTRAC SMR) — Tranche 2 precious metals dealer', 'Australia (AUSTRAC SMR) — Tranche 2 precious metals dealer'),
},
}

# Per-jurisdiction sample cases. Each one is a plausible AML typology so an
# MLRO recognizes the pattern when demoing.
SAMPLE_CASES = {
    "Singapore (STRO)": {
        "customer_name": "ACME Trading Pte Ltd",
        "customer_id": "A123456789",
        "customer_kyc": (
            "Singapore-incorporated, electronics wholesale. Declared source of funds: "
            "trading revenue. Expected monthly turnover SGD 200k. Risk rating: Medium "
            "at onboarding (Oct 2025)."
        ),
        "transactions": (
            "2026-04-15 | 480,000 | SGD | HK-XYZ Ltd (Hong Kong shell) | wire\n"
            "2026-04-16 | 350,000 | SGD | Mohammed A. (UAE individual) | wire\n"
            "2026-04-17 | 420,000 | USD | Beach Holdings (Cayman) | wire"
        ),
        "alert_reason": "3x expected monthly volume in 72 hours; new high-risk-jurisdiction counterparties",
        "red_flags": (
            "Rapid-fire international transfers to HK shell, UAE individual, and Cayman entity. "
            "Each transaction structured below the SGD 500k internal threshold. No prior commercial "
            "relationship with any beneficiary. Volume spike inconsistent with declared profile."
        ),
        "analyst_notes": (
            "Relationship manager contacted customer 2026-04-18. Customer stated transfers were for "
            "'new supplier deals' but could not produce contracts or invoices when requested. "
            "Adverse media check on Mohammed A. returned a UN sanctions watchlist hit (Feb 2026). "
            "Account opened 2025-10-15; activity prior to April 2026 was consistent with declared "
            "business (avg SGD 180k/month, predominantly SG counterparties). Customer's explanation "
            "deemed implausible by analyst given lack of documentation and watchlist match."
        ),
    },
    "Hong Kong (JFIU)": {
        "customer_name": "Golden Harbor Holdings Ltd",
        "customer_id": "HK-CR-9876543",
        "customer_kyc": (
            "Hong Kong-incorporated, jewelry and precious stones trading. "
            "Declared SoF: import/export of polished diamonds and gold. "
            "Expected monthly turnover HKD 1,500,000. Risk rating: Medium-High at onboarding (Jan 2025)."
        ),
        "transactions": (
            "2026-04-12 | 2,800,000 | HKD | Shenzhen Lihua Trading Co. Ltd (mainland CN) | wire\n"
            "2026-04-13 | 1,950,000 | HKD | Mohammad Rezaie (Iran-resident individual) | wire\n"
            "2026-04-14 | 3,200,000 | HKD | Macau Lucky Gold Pawn Shop | cash deposit then transfer"
        ),
        "alert_reason": "Volume 4x expected; mainland CN + Iranian counterparties; cash component inconsistent with B2B jewelry trade",
        "red_flags": (
            "Trade-based money laundering pattern: jewelry invoices appear over-priced vs. market. "
            "Counterparty Mohammad Rezaie matches OFAC SDN list. Macau pawn shop counterparty "
            "associated with cross-border casino-junket flows. Cash deposit immediately wired out "
            "(structured layering)."
        ),
        "analyst_notes": (
            "Customer outreach 2026-04-15; customer claimed a 'new high-volume buyer' but could not "
            "produce shipping documents, customs forms, or product photographs. EDD review found "
            "beneficial-owner Mr Chan Wai-Lung holds 51% via a BVI nominee structure undisclosed at "
            "onboarding. Adverse media: Hong Kong Free Press article (March 2026) names Golden Harbor "
            "in a casino-junket-linked layering ring. Mainland CN counterparty Shenzhen Lihua flagged "
            "by HKMA peer-bank inter-bank intelligence (informal)."
        ),
    },
    # HK variants — keyed by SAMPLE_LIBRARY entries
    "Hong Kong (JFIU) — VASP darknet flow": {
        "customer_name": "Cheung Ka-Wai",
        "customer_id": "HK-HKID-A123456(7)",
        "customer_kyc": (
            "Hong Kong individual, age 31, declared occupation: freelance graphic designer. "
            "Declared monthly income HKD 35,000. Source of funds: design work + personal trading. "
            "Onboarded via in-app e-KYC (HKID + selfie liveness). "
            "Expected transaction profile: retail crypto trading, sub-HKD 200k monthly. "
            "Risk rating: Medium at onboarding (June 2025) — adjusted for crypto activity."
        ),
        "transactions": (
            "2026-04-08 | 2.45 BTC (~HKD 1.62M) | inbound from external wallet bc1q...t8x | crypto deposit\n"
            "2026-04-09 | 1.80 BTC (~HKD 1.19M) | inbound from external wallet 1Hu5...kPb | crypto deposit\n"
            "2026-04-10 | 3.10 BTC (~HKD 2.05M) | inbound from external wallet 3Mq2...wRn | crypto deposit\n"
            "2026-04-11 | 7.30 BTC sold | converted to HKD via order book | conversion\n"
            "2026-04-11 | 2,400,000 | HKD | outbound to HSBC HK acct (third-party Mr Lau) | bank withdrawal\n"
            "2026-04-11 | 2,450,000 | HKD | outbound to Standard Chartered HK acct (third-party Ms Wong) | bank withdrawal"
        ),
        "alert_reason": "Inbound BTC sources flagged 60% darknet provenance by Chainalysis; HKD withdrawals to third-party bank accounts (not customer's own); volume 30x declared profile",
        "red_flags": (
            "Internal KYT (Chainalysis-equivalent) screening flagged 60% of inbound BTC as having "
            "darknet-market provenance — wallets bc1q...t8x and 3Mq2...wRn trace within 2 hops to "
            "Hydra-successor markets. Withdrawal addresses are HK bank accounts NOT in the customer's "
            "name (Mr Lau, Ms Wong) — inconsistent with retail crypto trading. Volume 30x declared "
            "monthly profile. Pattern matches SFC/HKMA 2025 'crypto cash-out' typology bulletin: VASP "
            "used as conversion layer between darknet proceeds and retail bank accounts."
        ),
        "analyst_notes": (
            "Customer outreach 2026-04-12; customer claimed Mr Lau and Ms Wong are 'friends helping "
            "with cash management' but provided no documentation of any business relationship. "
            "Asked to explain crypto source-of-funds; customer stated 'private trading' and refused "
            "EDD documentation. KYT screening details escalated to MLRO; SFC AML/CFT Guideline for "
            "VASPs (Chapter 4) crystallises the obligation. Customer assessed as a knowing layering "
            "agent (not a victim); third-party withdrawal pattern is the key indicia. STR + JFIU "
            "consent request appropriate; recommend account freeze pending JFIU response."
        ),
    },
    "Hong Kong (JFIU) — Casino-junket bank layering": {
        "customer_name": "Pearl Maritime Trading Ltd",
        "customer_id": "HK-CR-7654321",
        "customer_kyc": (
            "Hong Kong-incorporated, declared business: marine equipment B2B import/export. "
            "Declared SoF: marine equipment sales to mainland CN buyers. "
            "Expected monthly turnover HKD 8,000,000. "
            "Directors: Mr Wong Tin-Lok (75%), Ms Lam Hui-Yi (25%). "
            "Risk rating: Medium-High at onboarding (Aug 2024) — flagged for cross-border CN exposure."
        ),
        "transactions": (
            "2026-04-15 | 12,500,000 | HKD | Macau Sky Tourism Ltd (junket-linked entity) | wire\n"
            "2026-04-15 | 9,800,000  | USD | Macau Star Resort Travel Co (junket-linked entity) | wire\n"
            "2026-04-16 | 6,200,000  | CNH | outbound to Mr Zhang Wei (Shenzhen individual) | wire\n"
            "2026-04-16 | 5,800,000  | CNH | outbound to Ms Liu Mei (Guangzhou individual) | wire\n"
            "2026-04-16 | 8,400,000  | CNH | outbound to Mr Chen Hua (Shanghai individual) | wire\n"
            "2026-04-17 | round-trip 4,500,000 HKD inbound from Mr Zhang Wei (CN individual)"
        ),
        "alert_reason": "Inbound from Macau junket-tied entities; same-day outflow to multiple unrelated mainland CN individuals; round-trip pattern detected",
        "red_flags": (
            "Inbound counterparties Macau Sky Tourism and Macau Star Resort Travel are both "
            "Macau-junket-linked entities per HKMA peer-bank intel-sharing (informal). "
            "Mainland CN beneficiaries (Zhang Wei, Liu Mei, Chen Hua) are individuals with no apparent "
            "commercial relationship to declared marine equipment business. Round-trip pattern: "
            "Zhang Wei sent funds back to customer within 24 hours. Director Mr Wong Tin-Lok appears "
            "in ICAC March 2026 press release related to cross-border junket licensing irregularities. "
            "HKD/USD/CNH multi-currency layering matches 2025 HKMA typology bulletin on junket-derived "
            "fund movement through trade-shell accounts."
        ),
        "analyst_notes": (
            "EDD review 2026-04-18: customer outreach to Director Mr Wong; he claimed transfers were "
            "for 'consulting services for new mainland CN clients' but produced no contracts, "
            "engagement letters, or scope-of-work documentation. Marine equipment shipment records "
            "for Q1 2026 do not match the volume of inflows. ICAC press release of 2026-03-22 names "
            "Mr Wong in connection with a junket-licensing investigation; customer did not disclose "
            "this at onboarding or upon EDD. Activity is consistent with junket-derived proceeds "
            "being layered through a HK trading shell into mainland CN beneficiary accounts. "
            "Recommend STR + JFIU consent request + account suspension pending response."
        ),
    },
    "Malaysia (FIED)": {
        "customer_name": "Selangor Maju Sdn Bhd",
        "customer_id": "MY-SSM-1234567-A",
        "customer_kyc": (
            "Malaysian-incorporated (Shah Alam), crude palm oil (CPO) trading and export. "
            "Declared SoF: CPO sales to ASEAN buyers. Expected monthly turnover MYR 8,000,000. "
            "Risk rating: Medium at onboarding (March 2025). PEP screening clear at onboarding."
        ),
        "transactions": (
            "2026-04-10 | 4,200,000 | MYR | Bayu Logistics Pte Ltd (Singapore) | wire\n"
            "2026-04-11 | 3,800,000 | MYR | Pacific Lotus Holdings (Cayman shell) | wire\n"
            "2026-04-12 | 1,600,000 | MYR | Cash deposit (Kuala Lumpur branch) | cash"
        ),
        "alert_reason": "Cash deposit inconsistent with B2B CPO trade; trade-based ML invoice mismatch flagged by trade-finance ops",
        "red_flags": (
            "Trade-finance team flagged invoices showing CPO at MYR 6,500/tonne when spot price was "
            "MYR 4,200/tonne — significant over-invoicing. Singapore counterparty Bayu Logistics shares "
            "registered address with three other unrelated trading companies. Cayman shell beneficial "
            "owner not disclosed. MYR 1.6M cash deposit at KL branch unusual for declared B2B model."
        ),
        "analyst_notes": (
            "Branch RM contacted Director En. Ahmad Razali on 2026-04-13. Customer stated cash deposit "
            "'from director's personal property sale' but no SPA produced. EDD found Director En. Ahmad "
            "Razali holds shares in two other entities both with adverse media on illegal gambling "
            "(Sin Chew Daily, Feb 2026). Shipping documents requested; only PDF copies provided, "
            "found to be visually inconsistent with genuine bills of lading. Activity suggests TBML + "
            "potential proceeds-of-unlawful-activity layering."
        ),
    },
    # Malaysia variants — keyed by SAMPLE_LIBRARY entries
    "Malaysia (FIED) — Digital bank mule": {
        "customer_name": "Aiman bin Hassan",
        "customer_id": "MY-NRIC-001124-10-7385",
        "customer_kyc": (
            "Malaysian individual, age 24, declared occupation: software engineer. "
            "Declared monthly income MYR 4,500. Source of funds: salary + freelance projects. "
            "Expected transaction profile: low — typical retail customer. "
            "Onboarded via fully-digital e-KYC (NRIC + selfie liveness + bank link). "
            "Risk rating: Low at onboarding (Feb 2026)."
        ),
        "transactions": (
            "2026-04-08 | 18,500  | USD | inbound from Binance MY (own wallet) | crypto-to-bank\n"
            "2026-04-09 | 22,000  | USD | inbound from CoinGecko exchange (own wallet) | crypto-to-bank\n"
            "2026-04-10 | 15,800  | SGD | inbound from Wise (sender: Tan Wei, SG) | wire\n"
            "2026-04-11 | 41,000  | MYR | inbound from individual ML (sender: Lim X.) | DuitNow\n"
            "2026-04-11 | 38,500  | MYR | outbound to Luno MY (own crypto exchange wallet) | wire\n"
            "2026-04-12 | 47,000  | MYR | outbound to bc1q...mx9 (Tornado Cash-tagged wallet) | crypto withdrawal"
        ),
        "alert_reason": "Volume 50x declared monthly income; rapid in-out flow with crypto exchange + mixer wallet outflow",
        "red_flags": (
            "Total volume MYR 200k+ in 5 days vs. declared monthly income MYR 4,500 — 50x profile. "
            "Pattern matches BNM 2026 typology bulletin on 'investment scam mule accounts': inbound "
            "from foreign retail (likely scam victims) consolidated, then outbound to crypto mixer. "
            "Outbound wallet bc1q...mx9 flagged by Chainalysis as Tornado-Cash-derived address. "
            "Customer onboarding is fully-digital (e-KYC) — no in-person interaction. "
            "Multiple senders are unrelated retail individuals (potential pig-butchering scam victims)."
        ),
        "analyst_notes": (
            "Customer contacted via in-app message 2026-04-13; replied that he is 'investing through "
            "a Telegram trading group' and the inbound transfers are 'returns'. Could not name the "
            "group, the platform, or any account documentation. Shown screenshots of Telegram group; "
            "content matches 'pig-butchering' romance/investment scam playbook (fake portfolio "
            "screenshots, urgent transfer requests). Senders Tan Wei (SG) and Lim X (MY) traced "
            "via cross-bank intel sharing — both reported missing funds to their own banks last week. "
            "Customer assessed as a money-mule victim of an investment scam, not a knowing launderer; "
            "however, the activity meets the AMLA s.14 reason-to-suspect threshold and STR is required."
        ),
    },
    "Malaysia (FIED) — Islamic Tawarruq": {
        "customer_name": "Hijrah Holdings Sdn Bhd",
        "customer_id": "MY-SSM-9988776-K",
        "customer_kyc": (
            "Malaysian-incorporated, halal F&B distribution (frozen halal poultry, packaged foods). "
            "Declared SoF: B2B distribution revenue from supermarket chains. "
            "Expected monthly turnover MYR 800,000. "
            "Tawarruq commodity-financing facility: MYR 5,000,000 limit (granted Oct 2025). "
            "Risk rating: Medium at onboarding (June 2025). Director: En. Razak bin Salleh."
        ),
        "transactions": (
            "2026-04-02 | 5,000,000 | MYR | Tawarruq facility drawdown | internal\n"
            "2026-04-02 | 1,250,000 | MYR | outbound to 'Berkat Niaga Trading' (SME a/c at same bank) | wire\n"
            "2026-04-02 | 1,250,000 | MYR | outbound to 'Saudara Logistics Sdn Bhd' (SME a/c at same bank) | wire\n"
            "2026-04-02 | 1,250,000 | MYR | outbound to 'Bumi Maju Enterprise' (SME a/c at same bank) | wire\n"
            "2026-04-02 | 1,250,000 | MYR | outbound to 'Zahra Suppliers' (SME a/c at same bank) | wire\n"
            "2026-04-04 | 4,950,000 | MYR | inbound from same four entities (combined) | wire — round-trip"
        ),
        "alert_reason": "Tawarruq drawdown + same-day disbursement to four 'suppliers' with funds round-tripping back within 48 hours; pattern repeated 3 times in 90 days",
        "red_flags": (
            "Tawarruq commodity-financing facility appears to be used as a layering channel rather "
            "than for genuine commodity trade. The four 'supplier' SME accounts share UBO connections "
            "to Director En. Razak (Berkat Niaga UBO is brother; Bumi Maju UBO is brother-in-law). "
            "No genuine underlying commodity transfer evident — Shariah audit team requested "
            "commodity ownership transfer documentation, only summary invoices provided. "
            "Pattern (drawdown -> disburse -> round-trip) repeated three times in 90 days. "
            "Halal F&B distribution business does not require this Tawarruq drawdown frequency — "
            "monthly turnover MYR 800k vs. monthly facility utilization MYR 5M."
        ),
        "analyst_notes": (
            "EDD review identified UBO overlap between customer and four 'supplier' counterparties — "
            "all SME accounts at the same Islamic bank. Director En. Razak bin Salleh has adverse "
            "media (Sin Chew Daily, March 2026) regarding alleged commodity-trade fraud at a separate "
            "entity (Razak Trading Berhad, unrelated to Hijrah Holdings on paper). Shariah Audit "
            "non-compliance: insufficient evidence of underlying commodity ownership transfer in the "
            "Tawarruq mechanics; Shariah Committee referred to MLRO. Customer outreach 2026-04-15 — "
            "Director claimed 'commodity trade is genuine' but could not produce LME warehouse receipts "
            "or commodity broker confirmations. Activity is consistent with abuse of Shariah-compliant "
            "financing structure for layering proceeds; AMLA s.14 reason-to-suspect threshold is met."
        ),
    },
    "Australia (AUSTRAC SMR)": {
        "customer_name": "Coastal Crypto Exchange Pty Ltd",
        "customer_id": "AU-ABN-12-345-678-901",
        "customer_kyc": (
            "Australian-registered DCE (digital currency exchange), AUSTRAC-registered. "
            "Retail crypto-to-AUD exchange. Declared SoF: customer trading fees, market-making revenue. "
            "Expected daily processed volume AUD 2,000,000. Risk rating: High (DCE category)."
        ),
        "transactions": (
            "2026-04-20 | 9,800 | AUD | Customer ID 88421 (retail) | bank deposit\n"
            "2026-04-20 | 9,950 | AUD | Customer ID 88421 (retail) | bank deposit\n"
            "2026-04-20 | 9,500 | AUD | Customer ID 88421 (retail) | bank deposit\n"
            "2026-04-20 | onward to mixer wallet bc1q...x9k2 | BTC equivalent ~AUD 28,500 | crypto withdrawal"
        ),
        "alert_reason": "Structuring below AUD 10,000 TTR threshold; immediate conversion and transfer to known mixer wallet",
        "red_flags": (
            "Three deposits totalling AUD 29,250 from same customer within 2 hours, each structured "
            "below the AUD 10,000 TTR threshold. Funds immediately converted to BTC and withdrawn to "
            "wallet bc1q...x9k2 — flagged by Chainalysis as a Tornado Cash-style mixer with prior "
            "associations to investment-scam typologies. Customer KYC review found the three source "
            "bank accounts all opened within last 30 days."
        ),
        "analyst_notes": (
            "Customer outreach attempted 2026-04-21; customer (online retail user) did not respond. "
            "Source bank accounts trace to three different banks, all in the same victim-acquisition "
            "scam pattern AUSTRAC flagged in its 2025 'Pig Butchering' typology bulletin. KYC docs at "
            "onboarding (passport, utility bill) appear genuine but customer-completed risk "
            "questionnaire described occupation as 'student' — inconsistent with sudden AUD 30k flow. "
            "Suspect customer is a money mule victim of a romance/investment scam."
        ),
    },
    # AU variants — keyed by SAMPLE_LIBRARY entries
    "Australia (AUSTRAC SMR) — Casino chip-walking": {
        "customer_name": "Mark Anderson Reilly",
        "customer_id": "AU-DriverLic-NSW-87234561",
        "customer_kyc": (
            "Australian individual, age 43, declared occupation: self-employed building contractor. "
            "Loyalty program member since 2024. Source-of-wealth declared as 'business income, "
            "occasional gambling'. Expected gambling profile: AUD 5–10k per visit, 2–3 visits/month. "
            "Risk rating: Medium at last review (Jan 2026)."
        ),
        "transactions": (
            "2026-04-19 | 9,800  | AUD | cash buy-in at Sydney Harbour Casino main floor (cage A) | cash\n"
            "2026-04-19 | 9,500  | AUD | cash buy-in at same casino (cage C, 2hrs later) | cash\n"
            "2026-04-19 | 9,900  | AUD | cash buy-in at same casino (cage F, 4hrs later) | cash\n"
            "2026-04-19 | minimal play at table (12 hands of baccarat, ~AUD 600 total wagered)\n"
            "2026-04-19 | chips removed from premises (chip-walking) — no redemption at exit\n"
            "2026-04-22 | 28,500 | AUD | redemption of chips at sister-property casino (Melbourne) | cheque"
        ),
        "alert_reason": "Three structured cash buy-ins below AUD 10k TTR threshold same evening; chip-walking off premises; cross-property chip redemption — pattern matches AUSTRAC casino-sector enforcement priorities",
        "red_flags": (
            "Three cash buy-ins of AUD 9,800 / 9,500 / 9,900 same evening, each structured below the "
            "AUD 10,000 TTR threshold. CCTV review confirmed minimal actual gambling activity (~AUD "
            "600 wagered against AUD 29,200 in chips). Customer removed unredeemed chips from "
            "premises (chip-walking) — non-standard behavior. Chips redeemed three days later at "
            "sister property in Melbourne via cheque to bank account. Pattern matches AUSTRAC's "
            "2024–2025 casino-sector enforcement priorities (parallel typology to the Star/Crown "
            "regulatory actions). Customer's banking activity (separate review): inbound cash "
            "deposits of AUD 8–9k three days prior to casino visit, source unknown."
        ),
        "analyst_notes": (
            "Casino's TM team flagged the buy-in pattern via 'multi-cage same-day buy-in below "
            "threshold' rule (AML/CTF Program Part B trigger). Loyalty program data shows customer "
            "visit frequency increased 4x in the prior 60 days. Customer outreach via host: customer "
            "claimed cash was from 'building contract payments' but no invoices produced when asked. "
            "Sister-property redemption raises additional concern — suggests deliberate use of two "
            "venues to obscure trail. Activity is consistent with third-party-sourced cash being "
            "converted via casino as a layering mechanism (not customer's own gambling). "
            "Recommend SMR + customer downgrade to Restricted status."
        ),
    },
    "Australia (AUSTRAC SMR) — Tranche 2 real estate cash buyer": {
        "customer_name": "Pacific Heights Holdings BVI Ltd",
        "customer_id": "BVI-1234567",
        "customer_kyc": (
            "BVI-incorporated company (purchase vehicle). UBO declared as Mr Chan Ka-Lok, "
            "Hong Kong resident, declared occupation: 'private investor'. "
            "Property purchase: Sydney CBD apartment, agreed price AUD 4,500,000 (Apr 2026). "
            "Conveyancing handled by Demo Lawyers Sydney (Tranche 2 reporting entity from 2026). "
            "First-time client of the firm; introduced via offshore wealth-management referral."
        ),
        "transactions": (
            "2026-04-15 | 4,500,000 | AUD | wire from Bank of East Asia HK to Demo Lawyers trust account | wire\n"
            "2026-04-15 | 450,000   | AUD | deposit released to vendor's solicitor on exchange | wire\n"
            "2026-04-22 | 4,050,000 | AUD | balance released on settlement | wire"
        ),
        "alert_reason": "First Tranche 2 SMR for the firm. BVI nominee structure; UBO has adverse media (HK ICAC); purchase price 30% above market comparables; no source-of-wealth documentation provided",
        "red_flags": (
            "BVI nominee company with no operating history. UBO Mr Chan Ka-Lok is named in HK ICAC "
            "press release of 2026-03-22 in connection with a public-procurement corruption "
            "investigation; UBO did not disclose this to the firm. Purchase price AUD 4.5M is "
            "approximately 30% above recent comparable sales for the same building (RP Data review). "
            "Source-of-wealth documentation requested at engagement; UBO replied 'family wealth' but "
            "produced no bank statements, business accounts, or tax records. Transaction proceeded "
            "with unusual speed — no standard pre-purchase building inspection or strata-records "
            "review requested. AUSTRAC has flagged real-estate value-shifting as a Tranche 2 "
            "priority typology in its 2025 sector briefing."
        ),
        "analyst_notes": (
            "This is the firm's first SMR under the Tranche 2 obligations (effective for legal "
            "practitioners from 2026 per the AML/CTF Amendment Act 2024). Firm's senior partner "
            "and AML/CTF Compliance Officer reviewed jointly. UBO due diligence: HK ICAC press "
            "release of 2026-03-22 names Mr Chan Ka-Lok in a public-procurement corruption "
            "investigation; firm became aware only after settlement when conducting closing review. "
            "Source-of-wealth gap remains unresolved despite three written requests to UBO. "
            "Activity is consistent with potential proceeds-of-corruption being invested in "
            "Australian residential real estate. Although settlement has occurred, the SMR "
            "obligation under s.41 has crystallised. Tipping-off restrictions per s.123 strictly "
            "observed in all UBO communications. Recommend retrospective SMR + internal escalation "
            "to firm's risk committee + legal-professional-privilege carve-out review."
        ),
    },
    'Singapore (STRO) — DPT cash-out': {
        'customer_name': 'Vanessa Tan Hui-Min',
        'customer_id': 'DPT-CUST-SG-447821',
        'customer_kyc': "Singapore individual, age 29, declared occupation: business analyst at SG MNC. Declared monthly income SGD 9,500. Declared crypto experience: 'retail trader'. Onboarded via in-app e-KYC (NRIC + selfie liveness). Risk rating: Medium at onboarding (Sep 2025) — adjusted for crypto activity.",
        'transactions': '2026-04-09 | 2.8 BTC (~SGD 245,000) | inbound from external wallet (Tornado Cash output) | crypto deposit\n2026-04-09 | 2.5 BTC | converted to SGD via order book | conversion\n2026-04-10 | 220,000 | SGD | outbound to UOB account (third party Mr Phua Ah-Kow) | bank withdrawal\n2026-04-10 | 25,000  | SGD | retained on platform | balance',
        'alert_reason': 'Inbound BTC traced to Tornado Cash mixer output (≤2 hops, Chainalysis). 25x declared monthly income. Outbound to third-party SG bank account.',
        'red_flags': "KYT screening flagged 100% of inbound BTC as Tornado Cash mixer-output provenance. Outbound HKD bank account is in different name (Mr Phua Ah-Kow) — third-party withdrawal. Volume 25x customer's declared monthly income. Customer refused to provide source-of-wealth documentation when EDD requested. Pattern matches MAS 2025 typology bulletin on DPT cash-out for darknet/scam proceeds.",
        'analyst_notes': "Customer outreach 2026-04-11; customer claimed Mr Phua is 'a friend helping with bank wires' but produced no documentation of business relationship. KYT review found inbound BTC chain links to Hydra-successor darknet markets within 3 hops. MAS Notice PSN02 (DPT service provider AML obligations) applies. STR + account freeze recommended; CDD remediation invoked under our AML/CFT Program.",
    },
    'Singapore (STRO) — Real estate DNFBP': {
        'customer_name': 'Crescent Bay Estate Pte Ltd (purchase vehicle)',
        'customer_id': 'ACRA-SG-202504712E',
        'customer_kyc': "Singapore-incorporated SPV, sole asset purchase vehicle. UBO declared as Mr Wei Jianzhong, Cayman-resident individual. Declared SoF: 'family wealth from manufacturing'. Engaging real estate agent for purchase of SGD 28M Sentosa Cove condominium. First-time client of the agency. No commercial history with the firm.",
        'transactions': "2026-04-15 | 2,800,000  | SGD | option fee deposited via lawyer's trust account | wire\n2026-04-22 | 5,600,000  | SGD | further deposit on exercise | wire\n2026-04-29 | 19,600,000 | SGD | balance on completion | wire (from offshore Cayman bank)",
        'alert_reason': 'DNFBP STR triggered: BVI-Cayman SPV with no operating history, unverifiable source of wealth, purchase price 22% above recent comparables in the building',
        'red_flags': "BVI-domiciled SPV; UBO Cayman-resident with declared 'family manufacturing wealth' but no documents produced. Purchase price SGD 28M is 22% above recent comparable sales in same development (URA caveat data). Funds from offshore Cayman account; no SG-side bank relationship. Adverse media on UBO Mr Wei: 2025 Caixin (PRC) article names him in connection with state-owned enterprise irregularities. Under MAS supervision of real estate agents (SR-licensed), DNFBP STR obligation crystallises.",
        'analyst_notes': 'Real estate agency (Council for Estate Agencies registered) acting as DNFBP under AMLA-equivalent obligations. EDD requested at engagement; UBO produced no source-of-wealth documentation despite 2 written requests. Adverse media check via WorldCheck returned hit on Caixin May 2025 article. Purchase proceeded notwithstanding gap because buyer threatened legal action; firm escalated to MLRO. STRO STR + retrospective CDD documentation required. Tipping-off restrictions per CDSA s.48 strictly observed in all UBO communications post-suspicion.',
    },
    'Singapore (STRO) — Lawyer trust account misuse': {
        'customer_name': 'Apex Legal LLC (law firm — internal STR)',
        'customer_id': 'Internal-STR-2026-LLC-001',
        'customer_kyc': "Subject of STR is the firm's client, Goldcrest Trading Pte Ltd. Goldcrest declared business: international commodity broking. UBO declared as Mr Tan Boon-Hwa (SG-resident). Onboarded as legal client Q4 2025 for 'commercial advisory'. Engagement scope was advisory only — no transactional matter.",
        'transactions': "2026-04-02 | 4,800,000 | SGD | inbound to firm trust account from Goldcrest (SG bank) | wire\n2026-04-03 | 4,750,000 | SGD | outbound from firm trust account to BVI shell (instructed by client) | wire\n2026-04-04 | 50,000    | SGD | retained as 'fees' (no fee invoice issued) | retention",
        'alert_reason': 'Law firm trust account being used as pass-through for funds with no underlying legal-services nexus. Client engaged for advisory only — not transactional.',
        'red_flags': 'Trust account used as pass-through vehicle. Client engagement scope (advisory) does not justify the inbound/outbound flow. No underlying transaction (acquisition, litigation settlement, etc.) supports the flow. BVI destination has no clear commercial nexus to declared SG commodity-broking business. Pattern matches FATF DNFBP risk indicators for legal-sector layering. Goldcrest UBO Mr Tan has prior adverse media (Straits Times, Feb 2026) regarding alleged commodity-fraud syndicate.',
        'analyst_notes': "Filing partner became aware of the BVI transfer instruction during routine file review. The partner who handled the matter (junior, since left firm) accepted the trust-account use without questioning the lack of legal-services nexus. Firm's MLRO escalated to managing partner; engagement letter scope reviewed and confirmed as advisory-only. Activity is consistent with abuse of legal-sector trust-account infrastructure for layering. Under Law Society of Singapore AML/CFT Practice Direction, lawyer's STR obligation applies. Tipping-off restrictions strictly observed. Recommend STR + internal training on trust-account scrutiny + report to Law Society if pattern is found in other client files.",
    },
    'Singapore (STRO) — PSMD gold cash conversion': {
        'customer_name': 'Mr Liu Wenfeng',
        'customer_id': 'FIN-SG-PSMD-CUST-2204',
        'customer_kyc': 'PRC-passport-holder, declared SG visitor visa. Walk-in retail customer at SG PSMD-licensed gold dealer, Marina Bay Branch. No prior relationship. KYC: passport only, no proof of address, no source-of-funds declared at first transaction.',
        'transactions': '2026-04-12 | 8,500   | SGD cash | purchase 100g gold bars (8 × 100g) | over-counter\n2026-04-12 | 8,200   | SGD cash | further purchase same day, different till | over-counter\n2026-04-13 | 9,800   | SGD cash | follow-up purchase next day | over-counter\n2026-04-13 | gold sold to second-hand jeweller cash next street | external (not retained)',
        'alert_reason': 'Multiple cash purchases just below SGD 10,000 threshold; minimal CDD; immediate onward sale to unaffiliated jeweller observed by store staff',
        'red_flags': 'Three structured cash purchases of SGD 8,500 / 8,200 / 9,800 — all below the SGD 10,000 cash-CDD trigger. Customer paid in 100-dollar notes, all from same bank-band wrappers. Same-day repeat with different till staff suggests evasion of internal controls. Store CCTV recorded customer immediately reselling to unaffiliated jeweller next street. Customer used different passport at second-day visit (different name); BR document mismatch ignored by junior staff. Pattern matches PSMD-sector typology of gold as cash-conversion mechanism for proceeds-of-crime.',
        'analyst_notes': "PSMD store is registered with MAS under MAS Notice PSMD-N01 (2019). Branch manager noticed the pattern Day 2 and escalated. Junior till staff did not enforce CDD on second visit despite different-name passport. Activity is consistent with proceeds-of-crime cash being layered via gold and immediately reconverted via informal sale. STRO STR obligation applies (PSMD Notice §6.4). Tipping-off restrictions per CDSA s.48 observed. Recommend additional staff training + customer 'no-future-service' tagging across all branches.",
    },
    'Singapore (STRO) — Capital markets OTC wash trading': {
        'customer_name': 'Helios Asset Management Pte Ltd (CMS licensee)',
        'customer_id': 'CMS-SG-100337',
        'customer_kyc': "MAS Capital Markets Services (CMS) licensee, fund manager. Subject is one of Helios's underlying clients: a high-net-worth individual, Mr Aleksandr V., a Russian-passport-holder with declared SG residency since 2024. Fund holdings include SGD 35M discretionary mandate, predominantly OTC bond and FX positions.",
        'transactions': '2026-04-10 | 8,200,000 | USD | OTC bond buy from Counterparty A (offshore broker) | OTC trade\n2026-04-10 | 8,180,000 | USD | OTC bond sell to Counterparty B (offshore broker) | OTC trade\n2026-04-15 | 7,900,000 | USD | OTC bond buy from Counterparty B | OTC trade\n2026-04-15 | 7,910,000 | USD | OTC bond sell to Counterparty A | OTC trade',
        'alert_reason': 'Pattern of paired buy/sell of identical securities between the same two offshore counterparties at near-identical prices. Apparent wash trading with no economic purpose.',
        'red_flags': "Round-trip OTC trades over multiple days between two offshore brokers, with bond ISIN identical, at near-identical prices, with minimal P&L impact. Counterparty A and Counterparty B share the same Cayman administrator per Helios's counterparty diligence. Activity matches wash-trading typology — typically used to layer funds of unclear origin or to recognize fictitious losses for tax purposes. Customer Mr Aleksandr V. has DFAT-list-adjacent profile (Russia-domiciled until 2024). MAS Notice 314 (CMG-N01) AML obligations apply.",
        'analyst_notes': "Helios's compliance team flagged via routine OTC trade-pattern monitoring. Trades have no economic substance per the firm's investment-rationale documentation. Customer outreach via relationship manager: Mr Aleksandr stated 'rebalancing the portfolio' but could not articulate the economic logic. EDD review found Mr Aleksandr's prior business activities concentrated in sectors with sanctions exposure (energy, metals). Helios's CMS license obligations under MAS Notice 314 trigger STR. Recommend STR + portfolio liquidation per fund's exit clauses + internal escalation to Investment Committee.",
    },
    'Hong Kong (JFIU) — Virtual bank mule cluster': {
        'customer_name': 'Cluster: 7 customers (representative ID below)',
        'customer_id': 'ZA Bank cluster ZA-2026-Q2-CL-118',
        'customer_kyc': "Seven HK virtual-bank customers onboarded via mobile-only e-KYC in March-April 2026. All declared retail occupations (delivery driver, retail assistant, gig-economy worker). All declared similar SoF: 'casual freelance work'. Onboarded within a 3-week window. Common patterns identified by ML-based monitoring: shared device fingerprint family (iOS only, 3 unique device IDs but same iOS version + carrier), referrer-code links to single onboarding originator account.",
        'transactions': 'Aggregate across 7 accounts, 14-day window:\n2026-04-08 to 2026-04-22 | inbound HKD ~HKD 4.8M from 41 unrelated sender accounts | DuitNow / FPS\n2026-04-08 to 2026-04-22 | outbound HKD ~HKD 4.7M to 6 receiver accounts at other HK banks | FPS',
        'alert_reason': 'ML-based mule-cluster detection: shared device fingerprint family, common onboarding referrer, balanced in/out flow with 41 unrelated retail senders matching scam-victim pattern',
        'red_flags': "Cluster identified via virtual-bank's ML-mule-detection model (precision 94%). All 7 accounts opened within 3-week window via single referrer-code chain. Shared device fingerprint family — same iOS + carrier + locale (likely device farm). 41 inbound senders are from 9 different HK banks; cross-checking with HKAB intel-sharing indicates 32 of those senders have themselves filed concerns about being scammed (romance-scam / fake investment platform). Outbound to 6 receiver accounts — these are higher-tier mule accounts that subsequently transfer to crypto or offshore.",
        'analyst_notes': "HKMA virtual bank regime (since 2020) and AML/CFT Guideline expectations for digital banks crystallise the obligation. Cluster identified via internal ML model in late April; manual review confirmed mule-network indicia. All 7 accounts placed on 'restrict outbound' status pending review. Customer outreach attempted via in-app message; 6 of 7 did not respond, 1 customer claimed 'I let a friend use my account' — consistent with mule recruitment. Pattern matches JFIU 2026-03 typology bulletin on SVF / e-wallet mule recruitment via job-scam ads. STR + JFIU consent request + all 7 accounts to be exited.",
    },
    'Hong Kong (JFIU) — TCSP shell nominee abuse': {
        'customer_name': 'Eastpoint Corporate Services (TCSP licensee — internal STR)',
        'customer_id': 'Internal STR Eastpoint-2026-Q2-019',
        'customer_kyc': 'Subject is Eastpoint client, a HK-incorporated shell company: Riverbend Trade Holdings Ltd (CR HK-2024-883091). Eastpoint provides nominee director, registered office, and company-secretarial services. UBO declared at incorporation (Aug 2024) as Mr Tian Hao-Ran, mainland CN-resident. No genuine business activity at registered address; mass-formation pattern observed at the address (43 other shells).',
        'transactions': "Pattern observed during Eastpoint's annual review of dormant clients:\nRiverbend bank account at HK Tier-2 bank shows: \n2026-Q1 | inbound HKD ~HKD 18M from 6 mainland CN trade-shell payers | wire\n2026-Q1 | outbound HKD ~HKD 17.6M to BVI / Cayman shells | wire\nNet retained: minimal. No staff, no premises beyond registered address.",
        'alert_reason': "TCSP annual dormant-client review identified high-volume pass-through activity inconsistent with shell's declared dormancy; mass-formation pattern at registered address",
        'red_flags': 'Registered office is a mass-formation address — Eastpoint provides services to 43 other shells at the same address, several flagged for similar activity. UBO Mr Tian is unreachable at the email and phone provided at incorporation. Quarterly bank statements show pass-through pattern with no apparent commercial substance. Adverse media check on UBO returned a 2026 mainland CN news article naming him in connection with corruption proceedings. Pattern matches HK Companies Registry TCSP Code of Practice §4 risk indicators.',
        'analyst_notes': "Eastpoint is a Hong Kong Companies Registry-licensed TCSP (since 2018 regime). Annual dormant-client review identified 12 shells with similar patterns; this STR covers Riverbend specifically. UBO has not responded to 3 contact attempts under EDD process. TCSP's annual review obligation under AMLO Schedule 2 crystallises the STR threshold. Recommend STR + termination of all services to Riverbend + internal review of mass-formation address risk + report to Companies Registry on the address pattern.",
    },
    'Hong Kong (JFIU) — MSO undocumented remittance corridor': {
        'customer_name': 'Ms Aurora Santos Reyes',
        'customer_id': 'MSO-HK-CUST-RM-2026-7741',
        'customer_kyc': "Filipina domestic worker in HK, age 41, declared employer's salary HKD 5,800/month. Regular remittance customer at HK MSO licensee since 2020. Historical pattern: monthly HKD 4,500 remittance to PHL family account. New behavior from Jan 2026 onwards: weekly multi-receiver remittances at higher amounts.",
        'transactions': "Pattern across 12 weeks:\nJan 2026 onwards | weekly remittances HKD 8,000–9,500 | sent to 4 unrelated PHL receiver accounts (different surnames) | MSO wire\nTotal HKD ~110k in 12 weeks vs. historical HKD 4.5k/month (24x increase). Customer's stated source: 'helping arrange transfers for friends in HK.'",
        'alert_reason': '24x volume increase versus declared salary; multi-receiver pattern inconsistent with personal remittance; customer admits to acting as informal MSO for others',
        'red_flags': "Customer's stated income (HKD 5,800/month) does not support the volume of remittances (~HKD 9,000/week). Customer admits to handling 'transfers for friends' — effectively unlicensed remittance / hawala-style activity. Receivers are unrelated individuals across 4 different PHL accounts. Customer was contacted under MSO's CDD refresh; admitted she 'collects cash from friends in HK and sends home for them' for a small fee. This is unlicensed MSO activity by the customer + tax/labour-rights issues for her domestic-worker status.",
        'analyst_notes': "MSO is C&ED-licensed under HK MSO regime. MSO's CDD refresh process flagged the volume change. Customer outreach was non-confrontational; she did not perceive the activity as suspicious. Activity is consistent with informal value-transfer ('hawala') outside the regulated system, which is a predicate issue under HK AML framework. STR obligation crystallises. Customer should be exited from the MSO and informed (without tipping off about STR — only as customer-relationship matter) that future remittances must be only for her own funds. Recommend STR + customer exit + report to C&ED on the broader pattern (MSO has identified 23 similar customer profiles).",
    },
    'Malaysia (FIED) — Digital asset exchange': {
        'customer_name': 'Encik Hafiz bin Rashid',
        'customer_id': 'DAE-MY-CUST-RM-2026-3318',
        'customer_kyc': 'Malaysian individual, age 34, declared occupation: F&B restaurant owner. Declared monthly income MYR 18,000. Onboarded via in-app e-KYC in Feb 2026 at SC Malaysia-registered DAE. Risk rating: Medium (DAE category). Account-funding via FPX from his Maybank account.',
        'transactions': "2026-04-15 | 145,000 | MYR | FPX inbound from customer's Maybank | bank deposit\n2026-04-15 | 142,000 MYR | converted to USDT via order book | conversion\n2026-04-16 | USDT 30k | outbound to wallet TWb...mq3 (Tron, Sumsub-flagged) | crypto withdrawal\n2026-04-16 | USDT 30k | outbound to wallet TWb...nx7 (Tron, Sumsub-flagged) | crypto withdrawal\n2026-04-16 | USDT 30k | outbound to wallet TWb...kl9 (Tron, Sumsub-flagged) | crypto withdrawal\n2026-04-16 | USDT 18k | outbound to wallet TWb...ze4 (Tron, Sumsub-flagged) | crypto withdrawal",
        'alert_reason': 'Volume 8x declared income; rapid conversion to USDT and immediate split-withdrawal to four Tron wallets, all KYT-flagged as connected to scam syndicates',
        'red_flags': "Total inbound MYR 145k in single day — 8x customer's declared monthly income. Customer onboarded only 2 months prior to this activity. All four outbound Tron wallets flagged by Sumsub KYT as 'high risk — known scam-syndicate clusters'. Pattern matches BNM 2026-04 typology bulletin on investment-scam mule flows via DAEs. Customer's bank-side account history (separate review via Maybank intel share) shows the inbound MYR 145k arrived from 17 unrelated retail senders within the prior 48 hours.",
        'analyst_notes': "DAE is SC Malaysia-registered under SC Guidelines on Recognized Markets — DAEs. AML/CFT Sectoral Guidelines for Capital Market Intermediaries apply via SC. Customer outreach 2026-04-17; customer claimed 'investing in opportunity through Telegram channel' but could not name the platform or counterparties. Customer's F&B business does not generate the volume claimed. Activity is consistent with customer being a money-mule victim of an investment scam, channeling victim funds through DAE to scam-controlled wallets. STR + account suspension + customer-protection outreach recommended. Coordinate with Maybank on the upstream scam victims.",
    },
    'Malaysia (FIED) — E-money issuer wallet mule': {
        'customer_name': 'Sarah binti Ahmad Faizal',
        'customer_id': 'EMI-MY-CUST-2026-RM-9921',
        'customer_kyc': "Malaysian individual, age 22, declared occupation: 'student / part-time'. Declared monthly income MYR 1,500. Onboarded via in-app e-KYC at MY e-money issuer in Mar 2026. Wallet limit: MYR 5,000 standard tier. Account-funding via DuitNow.",
        'transactions': "Pattern observed across 4-week window:\nDaily inbound DuitNow from 8-12 different unrelated sender accounts | total ~MYR 30k/week\nSame-day outbound DuitNow to 3 receiver accounts (other MY banks) | matched amounts\nNet retained: ~MYR 200/week as 'fee'. Wallet tier upgraded to higher limit after 1 week.",
        'alert_reason': 'Wallet velocity 100x declared income; balanced in/out pattern; multiple unrelated retail senders pattern matches mule-recruitment-via-job-ad typology',
        'red_flags': "Customer earnings claim MYR 1,500/month, but wallet sees MYR 30k+ weekly volume (100x). Wallet was upgraded to higher tier within 1 week of onboarding — likely via tiered KYC uplift triggered by activity. Inbound senders are from 7+ different MY banks and include accounts that have themselves filed scam-victim reports (cross-bank intel via interbank fraud-sharing). Customer was contacted; admitted to participating in 'work-from-home Telegram task' where she 'just receives and forwards' funds for a 'small commission'. Self-reports as scam-victim mule.",
        'analyst_notes': "EMI is BNM-licensed e-money issuer; AML/CFT Sectoral Guidelines for E-Money Issuers apply. EMI's TM detection rules flagged the velocity-vs-profile mismatch. Customer outreach via in-app + phone; customer cooperative and openly described the 'job' arrangement — clear case of mule recruitment via fake-job typology. Activity is consistent with proceeds of investment scams being channeled through e-money wallet for layering. STR obligation under AMLA s.14 applies. Recommend STR + customer exit + customer-protection messaging + report to BNM under typology intel-sharing.",
    },
    'Malaysia (FIED) — Pawnbroker gold layering': {
        'customer_name': 'Mr Lim Chong-Wei',
        'customer_id': 'Pawn-MY-CUST-2026-PG-447',
        'customer_kyc': "Malaysian individual, age 51, walk-in customer at Penang pawnbroker (DNFBP under AMLA First Schedule). No prior relationship. Declared occupation: 'businessman'. No KYC documents requested at entry — minimum CDD only applied (NRIC + photo).",
        'transactions': 'Pattern across 6 visits (3 weeks):\nVisit 1 (Apr-04) | pawned 200g gold (24K, recently purchased per receipt) for MYR 40k cash\nVisit 2 (Apr-08) | redeemed gold + paid MYR 41k cash | pattern repeats\nVisits 3-6 | similar pattern with 200-400g gold quantities, MYR 80-120k cash each round\nTotal notional value cycled: ~MYR 480k cash across 3 weeks.',
        'alert_reason': 'Repeated pawn-and-redeem cycles with no economic rationale; customer paying redemption in cash exceeding RM 25k CTR threshold; gold appears recently purchased',
        'red_flags': "Pattern of pawn-redeem-pawn with no economic logic — customer is converting cash to gold receipts (proof of legitimate origin) and back. Gold pawned in some visits shows recent retail-purchase receipts (suggesting gold sourced from cash purchase elsewhere). Cash redemption amounts exceed RM 25,000 CTR threshold but pawnbroker did not file CTR (compliance gap). Adverse media: customer's name appears in 2026 Sin Chew article naming individuals associated with illegal-online-gambling syndicate in Penang. Pattern matches FATF DNFBP typology of pawn-sector layering.",
        'analyst_notes': "Pawnbroker is licensed under Pawnbrokers Act 1972 + AMLA First Schedule. Pawnbroker's MLRO (Mr Tan, owner-operator) flagged the pattern after Visit 4 when staff queried the repeat customer. Customer outreach: customer claimed 'cash flow needs for my business' but produced no business documentation. Cross-reference with police intel-share confirmed customer is on a watch-list related to the Penang gambling investigation. Recommend STR + retrospective CTR filings for the visits exceeding RM 25k + customer no-future-service tagging + report to BNM FIED on broader pawn-sector pattern.",
    },
    'Australia (AUSTRAC SMR) — Tranche 2 real estate agent': {
        'customer_name': 'Crystal Bay Properties Pty Ltd (real estate agency — internal SMR)',
        'customer_id': 'Internal SMR CBP-T2-2026-Q3-001',
        'customer_kyc': "Subject is the agency's purchaser-customer: Mr & Mrs Chen (foreign-domiciled). Purchasing AUD 6.2M waterfront house in Mosman (Sydney). UBO chain runs Mr & Mrs Chen → BVI nominee company → trust (declared 'family trust', no documentation). First-time client of the agency. Engaged April 2026 — within Tranche 2 phase-1 registration window.",
        'transactions': '2026-04-20 | 620,000   | AUD | deposit on exchange (10%) | wire (foreign source)\n2026-05-25 | 5,580,000 | AUD | balance on settlement (planned) | wire (foreign source)',
        'alert_reason': 'First Tranche 2 SMR for this agency. BVI nominee + undocumented family trust; UBO source-of-wealth gap; purchase price 18% above recent comparables',
        'red_flags': "Agency is a real estate agent acting under Tranche 2 obligations effective from 1 July 2026. Customer engaged April 2026 (pre-commencement); agency electing to apply Tranche 2 standards from engagement. UBO chain has BVI nominee + undocumented trust. Source-of-wealth: 'family wealth from agriculture' but no bank statements, tax records, or property-of-origin records produced. Purchase price AUD 6.2M is 18% above recent CoreLogic comparables for Mosman waterfront. Wire from foreign bank not in customer's name — instructed via 'family office'.",
        'analyst_notes': "Real estate agency electing to apply Tranche 2 standards pre-commencement (per AUSTRAC industry guidance encouraging early adoption). Engagement triggered by AUD 6.2M residential purchase. EDD requested at engagement under interim policy; UBO chain produced minimal documentation. Source-of-wealth gap remains material. Activity is consistent with potential value-shifting / proceeds investment in Australian residential real estate. SMR obligation crystallises. Tipping-off restrictions per s.123 strictly observed in all UBO communications. Recommend SMR + management decision on whether to proceed with the transaction (commercial vs. risk trade-off) + escalate to firm's AML/CTF Compliance Officer for sign-off.",
    },
    'Australia (AUSTRAC SMR) — Tranche 2 accountant corporate-structuring': {
        'customer_name': 'Berriman Tax Advisory Pty Ltd (firm — internal SMR)',
        'customer_id': 'Internal SMR Berriman-T2-2026-001',
        'customer_kyc': "Subject is the firm's client: Mr Dmitri V., AU-resident since 2023, formerly Russia-domiciled. Engaged the firm in April 2026 for AUD 12M corporate restructuring advice — establishing AU holding company + BVI subsidiary + Cayman trust. Client declared SoF: 'liquidity from previous Russian business sale'.",
        'transactions': "Engagement scope (advisory, no firm-handled funds):\nAdvised structure: AU Pty Ltd → BVI subsidiary → Cayman discretionary trust\nEstimated AUD 12M to be settled into the structure. Source: Russian bank wire to client's existing AU bank, then onward.\nFirm's role: advisory / drafting; not directly handling funds.",
        'alert_reason': 'Tranche 2 SMR — advisory scope of corporate-structuring advice for client with Russian-domicile background; structure has classic layering characteristics with no clear commercial purpose',
        'red_flags': "Client previously Russia-domiciled; AU residency since 2023. Source-of-wealth claimed from 'Russian business sale' but no documentation (sale-of-business agreement, broker confirmations, tax filings). Proposed structure (AU Pty Ltd → BVI subsidiary → Cayman trust) has classic layering characteristics — multiple jurisdictions, opaque trust structure, no clear commercial purpose articulated. Adverse media via Refinitiv: client's prior Russian business sector (energy trading) has DFAT-list-adjacent profile. Tranche 2 obligations apply to the firm from 1 July 2026; firm electing to apply standards now. Pattern matches FATF DNFBP risk indicators for legal/accounting professional involvement in layering.",
        'analyst_notes': "Firm is a Tranche 2 reporting entity (accountants) effective 2026. Engagement partner escalated to the firm's AML/CTF Compliance Officer (newly-appointed for Tranche 2 readiness). EDD documentation requested at engagement; client provided only summary statements, no source-of-wealth verification. Firm has not yet released the structuring advice documents. Activity is consistent with potential use of professional advisory services for layering proceeds-of-unknown-origin. SMR obligation crystallises notwithstanding advisory-only role. Tipping-off restrictions per s.123 strictly observed. Recommend SMR + firm declines further engagement + internal training on Tranche 2 typology indicators.",
    },
    'Australia (AUSTRAC SMR) — Tranche 2 precious metals dealer': {
        'customer_name': 'Ms Olivia Tran',
        'customer_id': 'T2-PMD-AU-2026-04-CUST-217',
        'customer_kyc': "Walk-in customer at Sydney precious-metals dealer (PMD), May 2026 — within first month of Tranche 2 phase-1 obligations. Declared occupation: 'business owner' (no specifics). KYC: AU driver's licence, no proof of address requested at first transaction. Tranche 2 phased rollout means PMD is applying Tranche 2 standards incrementally.",
        'transactions': "Visit 1 (May-04) | AUD 9,500 cash | 200g gold (24K) | over-counter\nVisit 2 (May-06, different staff) | AUD 9,800 cash | 200g gold | over-counter\nVisit 3 (May-08, different staff) | AUD 9,400 cash | 200g gold | over-counter\nVisit 4 (May-12) | AUD 9,600 cash | 200g gold | over-counter\nTotal cash converted to gold: AUD 38,300 across 8 days. Customer's stated purpose for purchases varied across visits ('investment', 'gift', 'wedding').",
        'alert_reason': 'Multiple cash purchases just below AUD 10,000 TTR threshold across 8 days; pattern of structuring with varying stated purposes; Tranche 2 first-month case',
        'red_flags': "Four cash purchases of AUD 9,400 - 9,800 — all just below AUD 10,000 TTR threshold. Customer rotated between staff/tills across visits — apparent attempt to evade internal pattern-recognition. Cash paid in AUD 100 notes, similar bank-band wraps. Customer's stated purpose for purchases varied (different reasons given to different staff). Declared occupation vague ('business owner'). PMD is operating under Tranche 2 obligations effective from 2026; this is one of the firm's first SMR cases under the new regime.",
        'analyst_notes': "PMD has registered with AUSTRAC under Tranche 2 phase-1 (March 2026). Store manager flagged the pattern after Visit 3; AML/CTF Compliance Officer (newly appointed for Tranche 2) reviewed Visits 1-4 in aggregate. Cross-staff coordination broke down on Visit 2 because new staff didn't recognize Visit 1 customer; AUSTRAC industry guidance for Tranche 2 emphasizes the need for robust customer-recognition across visits. Activity matches FATF DNFBP precious-metals typology for cash layering. SMR obligation under s.41 applies. Recommend SMR + internal staff training + customer no-future-service tagging + retrospective TTR review for any aggregated purchases above AUD 10k that may have escaped reporting.",
    },
}

# Default sample for fallback (when jurisdiction not yet in SAMPLE_CASES)
SAMPLE_CASE = SAMPLE_CASES["Singapore (STRO)"]

# Filing metadata defaults — per-institution values pulled from env vars so the
# user doesn't retype their institution and MLRO name on every case.
FILING_METADATA_DEFAULTS = {
    "input_reporting_institution": os.getenv("DEFAULT_REPORTING_INSTITUTION", ""),
    "input_str_reference": "",
    "input_prepared_by": os.getenv("DEFAULT_ANALYST_NAME", ""),
    "input_mlro_signoff": os.getenv("DEFAULT_MLRO_NAME", ""),
    "input_entity_category": "— Select —",
}

SAMPLE_FILING_METADATAS = {
    "Singapore (STRO)": {
        "input_reporting_institution": "Demo Bank Singapore Pte Ltd (MAS-licensed bank)",
        "input_str_reference": "STR-2026-04-0042",
        "input_prepared_by": "Lim Wei Ling, Senior Compliance Analyst",
        "input_mlro_signoff": "Tan Boon Heng, MLRO",
        "input_entity_category": "Bank (full / wholesale / merchant)",
    },
    "Hong Kong (JFIU)": {
        "input_reporting_institution": "Demo Bank Hong Kong Ltd (HKMA-authorized institution)",
        "input_str_reference": "STR-HK-2026-Q2-0117",
        "input_prepared_by": "Cheung Mei-Ling, AML Analyst",
        "input_mlro_signoff": "Wong Kwok-Hei, MLRO",
        "input_entity_category": "Authorized institution — bank",
    },
    "Hong Kong (JFIU) — VASP darknet flow": {
        "input_reporting_institution": "HashKey Exchange HK Ltd (SFC Type 1 + Type 7 VASP licensee)",
        "input_str_reference": "STR-HK-VASP-2026-04-0089",
        "input_prepared_by": "Lee Ka-Yan, KYT Analyst",
        "input_mlro_signoff": "Tang Wing-Chiu, MLRO",
        "input_entity_category": "Virtual asset service provider (VASP)",
    },
    "Hong Kong (JFIU) — Casino-junket bank layering": {
        "input_reporting_institution": "Demo Commercial Bank HK Ltd (HKMA-authorized institution)",
        "input_str_reference": "STR-HK-CB-2026-04-0341",
        "input_prepared_by": "Yip Hoi-Lam, Senior FCC Analyst",
        "input_mlro_signoff": "Datuk Cheng Wai-Man, MLRO",
        "input_entity_category": "Authorized institution — bank",
    },
    "Malaysia (FIED)": {
        "input_reporting_institution": "Maybank Demo Berhad (BNM-licensed bank)",
        "input_str_reference": "STR-MY-2026-0289",
        "input_prepared_by": "Nurul Aishah binti Hassan, AML Officer",
        "input_mlro_signoff": "Encik Rahman bin Ibrahim, MLRO",
        "input_entity_category": "Licensed bank — conventional",
    },
    "Malaysia (FIED) — Digital bank mule": {
        "input_reporting_institution": "Boost Bank Berhad (BNM-licensed digital bank)",
        "input_str_reference": "STR-MY-DB-2026-04-0521",
        "input_prepared_by": "Nadia Mohd Yusof, Financial Crime Analyst",
        "input_mlro_signoff": "Encik Hafiz bin Abdullah, Head of Financial Crime Compliance",
        "input_entity_category": "Digital bank — conventional (BNM digital banking licensee, e.g. Boost Bank, GXBank)",
    },
    "Malaysia (FIED) — Islamic Tawarruq": {
        "input_reporting_institution": "Bank Islam Malaysia Berhad (BNM-licensed Islamic bank)",
        "input_str_reference": "STR-MY-IB-2026-04-0218",
        "input_prepared_by": "Siti Khairiah binti Ramli, AML Analyst (Shariah-aligned)",
        "input_mlro_signoff": "Datuk Yusof bin Mahmud, MLRO",
        "input_entity_category": "Licensed Islamic bank (full-fledged, e.g. Bank Islam, Maybank Islamic)",
    },
    "Australia (AUSTRAC SMR)": {
        "input_reporting_institution": "Coastal Crypto Exchange Pty Ltd (AUSTRAC-registered DCE)",
        "input_str_reference": "SMR-AU-2026-04-0834",
        "input_prepared_by": "Sarah O'Brien, Compliance Manager",
        "input_mlro_signoff": "James Patterson, AML/CTF Compliance Officer",
        "input_entity_category": "Digital currency exchange (DCE)",
    },
    "Australia (AUSTRAC SMR) — Casino chip-walking": {
        "input_reporting_institution": "Sydney Harbour Casino Pty Ltd (AUSTRAC-registered casino operator)",
        "input_str_reference": "SMR-AU-CSO-2026-04-1247",
        "input_prepared_by": "Emma Whitfield, Senior AML Analyst",
        "input_mlro_signoff": "Damien Schultz, AML/CTF Compliance Officer",
        "input_entity_category": "Gambling service provider — casino / wagering / bookmaker",
    },
    "Australia (AUSTRAC SMR) — Tranche 2 real estate cash buyer": {
        "input_reporting_institution": "Demo Lawyers Sydney (Tranche 2 reporting entity from 2026)",
        "input_str_reference": "SMR-AU-T2-2026-04-0007",
        "input_prepared_by": "Olivia Chen, Senior Associate (AML/Conveyancing)",
        "input_mlro_signoff": "Priya Sharma, Partner & AML/CTF Compliance Officer",
        "input_entity_category": "Solicitor (Tranche 2 — from 2026)",
    },
    'Singapore (STRO) — DPT cash-out': {
        'input_reporting_institution': 'Coinhako SG Pte Ltd (MAS DPT licensee under PSN02)',
        'input_str_reference': 'STR-SG-DPT-2026-04-0411',
        'input_prepared_by': 'Lim Wei Ling, KYT Analyst (DPT)',
        'input_mlro_signoff': 'Tan Boon Heng, MLRO',
        'input_entity_category': 'Digital payment token (DPT) service provider',
    },
    'Singapore (STRO) — Real estate DNFBP': {
        'input_reporting_institution': 'Premier Properties Singapore Pte Ltd (CEA-licensed real estate agency)',
        'input_str_reference': 'STR-SG-REA-2026-04-0078',
        'input_prepared_by': 'Carolyn Goh, Senior Compliance Officer',
        'input_mlro_signoff': 'Mark Lim, Managing Director',
        'input_entity_category': 'Real estate agent / salesperson (DNFBP)',
    },
    'Singapore (STRO) — Lawyer trust account misuse': {
        'input_reporting_institution': 'Apex Legal LLC (Law Society of Singapore — DNFBP)',
        'input_str_reference': 'STR-SG-LAW-2026-04-0019',
        'input_prepared_by': 'Rachel Ng, Risk & Compliance Counsel',
        'input_mlro_signoff': 'James Tan, Managing Partner',
        'input_entity_category': 'Lawyer / legal practice (DNFBP)',
    },
    'Singapore (STRO) — PSMD gold cash conversion': {
        'input_reporting_institution': 'Marina Bay Bullion Pte Ltd (MAS PSMD-N01 registered)',
        'input_str_reference': 'STR-SG-PSMD-2026-04-0123',
        'input_prepared_by': 'Daniel Lee, Compliance Officer',
        'input_mlro_signoff': 'Henry Wong, Director',
        'input_entity_category': 'Precious stones and metals dealer (PSMD)',
    },
    'Singapore (STRO) — Capital markets OTC wash trading': {
        'input_reporting_institution': 'Helios Asset Management Pte Ltd (MAS CMS licensee)',
        'input_str_reference': 'STR-SG-CMS-2026-04-0034',
        'input_prepared_by': 'Priya Menon, Head of FCC',
        'input_mlro_signoff': 'David Chua, MLRO',
        'input_entity_category': 'Capital markets services (CMS) licensee',
    },
    'Hong Kong (JFIU) — Virtual bank mule cluster': {
        'input_reporting_institution': 'ZA Bank Ltd (HKMA-licensed virtual bank)',
        'input_str_reference': 'STR-HK-VB-2026-04-1182',
        'input_prepared_by': 'Lily Cheng, Senior Mule Detection Analyst',
        'input_mlro_signoff': 'Henry Wong, MLRO',
        'input_entity_category': 'Authorized institution — virtual bank (HKMA-licensed digital, e.g. ZA Bank, Mox, livi, WeLab)',
    },
    'Hong Kong (JFIU) — TCSP shell nominee abuse': {
        'input_reporting_institution': 'Eastpoint Corporate Services Ltd (HK Companies Registry-licensed TCSP)',
        'input_str_reference': 'STR-HK-TCSP-2026-04-0019',
        'input_prepared_by': 'Yvonne Lai, Risk Officer',
        'input_mlro_signoff': 'Daniel Yeung, Managing Director',
        'input_entity_category': 'Trust or company service provider (TCSP)',
    },
    'Hong Kong (JFIU) — MSO undocumented remittance corridor': {
        'input_reporting_institution': 'Pacific Express Money Services Ltd (C&ED-licensed MSO)',
        'input_str_reference': 'STR-HK-MSO-2026-04-0287',
        'input_prepared_by': 'Carmen Ng, AML Officer',
        'input_mlro_signoff': 'Patrick Lee, Director',
        'input_entity_category': 'Money service operator (MSO)',
    },
    'Malaysia (FIED) — Digital asset exchange': {
        'input_reporting_institution': 'Luno Malaysia Sdn Bhd (SC Malaysia-registered DAE)',
        'input_str_reference': 'STR-MY-DAE-2026-04-0289',
        'input_prepared_by': 'Muhammad Faiz, KYT Analyst',
        'input_mlro_signoff': 'Aishwarya Kumar, MLRO',
        'input_entity_category': 'Digital asset exchange (DAE — SC-registered)',
    },
    'Malaysia (FIED) — E-money issuer wallet mule': {
        'input_reporting_institution': "Touch 'n Go eWallet Sdn Bhd (BNM-licensed e-money issuer)",
        'input_str_reference': 'STR-MY-EMI-2026-04-1147',
        'input_prepared_by': 'Nurul Iman binti Yusof, AML Analyst',
        'input_mlro_signoff': 'Encik Faizal bin Abdullah, MLRO',
        'input_entity_category': 'E-money issuer',
    },
    'Malaysia (FIED) — Pawnbroker gold layering': {
        'input_reporting_institution': 'Penang Gold Pawnshop Sdn Bhd (Pawnbrokers Act + AMLA First Schedule)',
        'input_str_reference': 'STR-MY-PAWN-2026-04-0044',
        'input_prepared_by': 'Mr Tan Wei-Ming, Compliance Officer / Owner',
        'input_mlro_signoff': 'Mr Tan Wei-Ming (also owner-operator)',
        'input_entity_category': 'Pawnbroker',
    },
    'Australia (AUSTRAC SMR) — Tranche 2 real estate agent': {
        'input_reporting_institution': 'Crystal Bay Properties Pty Ltd (Tranche 2 real estate agent — registered with AUSTRAC 2026)',
        'input_str_reference': 'SMR-AU-T2REA-2026-05-0001',
        'input_prepared_by': 'Sophie Watanabe, Senior Sales Manager (acting AML/CTF CO)',
        'input_mlro_signoff': 'David Costa, Principal & AML/CTF Compliance Officer',
        'input_entity_category': 'Real estate agent (Tranche 2 — from 2026)',
    },
    'Australia (AUSTRAC SMR) — Tranche 2 accountant corporate-structuring': {
        'input_reporting_institution': 'Berriman Tax Advisory Pty Ltd (Tranche 2 accountant — registered with AUSTRAC 2026)',
        'input_str_reference': 'SMR-AU-T2ACT-2026-04-0008',
        'input_prepared_by': 'Michael Donovan, Tax Partner (engagement partner)',
        'input_mlro_signoff': 'Helena Rouvas, Managing Partner & AML/CTF Compliance Officer',
        'input_entity_category': 'Accountant / conveyancer (Tranche 2 — from 2026)',
    },
    'Australia (AUSTRAC SMR) — Tranche 2 precious metals dealer': {
        'input_reporting_institution': 'Sydney Bullion Exchange Pty Ltd (Tranche 2 precious metals dealer — registered with AUSTRAC March 2026)',
        'input_str_reference': 'SMR-AU-T2PMD-2026-05-0003',
        'input_prepared_by': 'Andrea Coleman, Store Manager (acting AML/CTF CO)',
        'input_mlro_signoff': 'Robert Sang, Managing Director & AML/CTF Compliance Officer',
        'input_entity_category': 'Precious metals dealer (Tranche 2 — from 2026)',
    },
}

# Direct filing-portal links per jurisdiction — appears as a button after the
# narrative is generated so analysts can jump straight to the filing system.
FILING_PORTALS = {
    "Singapore (STRO)": ("SONAR (Singapore Police Force)", "https://eservices.police.gov.sg/sonar"),
    "Hong Kong (JFIU)": ("STREAMS (JFIU)", "https://www.jfiu.gov.hk/en/str_what.html"),
    "Malaysia (FIED)": ("FINS (BNM AML/CFT portal)", "https://amlcft.bnm.gov.my/"),
    "Australia (AUSTRAC SMR)": ("AUSTRAC Online", "https://online.austrac.gov.au/"),
}

st.set_page_config(
    page_title="AML Agents - STR Reporting",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# Authentication — demo-grade login via streamlit-authenticator + local YAML.
# Sits at the top so unauthenticated users only see the login screen.
# ============================================================================
auth_config = load_config()
authenticator = stauth.Authenticate(
    auth_config["credentials"],
    auth_config["cookie"]["name"],
    auth_config["cookie"]["key"],
    auth_config["cookie"]["expiry_days"],
)

# Render login form. streamlit-authenticator updates st.session_state with
# 'authentication_status' (True / False / None), 'name', 'username'.
try:
    authenticator.login(location="main")
except Exception as login_err:
    st.error(f"Login error: {login_err}")

auth_status = st.session_state.get("authentication_status")

if not auth_status:
    # Login / signup view — short-circuit the rest of the app
    st.markdown(
        """
<div style="max-width: 520px; margin: 1rem auto 1.5rem auto; padding: 1.5rem 2rem;
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1e40af 100%);
            border-radius: 12px; color: #fff;">
    <h2 style="color: #fff; margin: 0;">AML Agents</h2>
    <p style="color: #cbd5e1; margin: 0.4rem 0 0 0; font-size: 0.92rem;">
        AI-drafted STR narratives for compliance teams. Sign in to continue.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    if auth_status is False:
        st.error("Username or password is incorrect.")
    elif auth_status is None:
        st.info(
            "**Demo credentials**: username `demo` · password `demo123`  \n"
            "Or create your own account below."
        )

    with st.expander("Create a new account", expanded=False):
        try:
            (
                email_new,
                username_new,
                name_new,
            ) = authenticator.register_user(
                location="main",
                pre_authorization=False,
                merge_username_email=False,
            )
            if email_new:
                save_config(auth_config)
                st.success(
                    f"Account created for **{name_new}** (username: `{username_new}`). "
                    "Sign in above with your new credentials."
                )
        except Exception as reg_err:
            st.error(str(reg_err))

    st.stop()

# From this point on the user is authenticated.
auth_username = st.session_state["username"]
auth_name = st.session_state.get("name", auth_username)

# Polish CSS — branded header, card layout, hide default Streamlit chrome
st.markdown(
    """
<style>
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stToolbar"] {display: none;}
    div[data-testid="stDecoration"] {display: none;}

    /* Tighten top padding */
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px;}

    /* Branded header */
    .brand-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1e40af 100%);
        padding: 1.75rem 2.25rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
    }
    .brand-left {
        flex: 1 1 auto;
        min-width: 0;
    }
    .brand-right {
        flex: 0 0 auto;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        align-items: flex-end;
        max-width: 280px;
    }
    .brand-header h1 {
        color: #ffffff !important;
        font-size: 1.6rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .brand-header .subtitle {
        color: #cbd5e1;
        margin: 0.4rem 0 0 0;
        font-size: 0.92rem;
        font-weight: 400;
    }
    .brand-header .badge {
        display: inline-block;
        background: rgba(255,255,255,0.12);
        color: #cbd5e1;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 500;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }
    /* Authority chips on the right of the header */
    .auth-chip {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 6px;
        padding: 0.45rem 0.7rem;
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        white-space: nowrap;
        backdrop-filter: blur(4px);
    }
    .auth-chip .auth-abbr {
        color: #ffffff;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.02em;
    }
    .auth-chip .auth-name {
        color: #cbd5e1;
        font-size: 0.7rem;
        font-weight: 400;
    }
    /* Stack header on narrow screens */
    @media (max-width: 900px) {
        .brand-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .brand-right {
            align-items: flex-start;
            max-width: 100%;
            margin-top: 0.5rem;
        }
    }

    /* Section labels above bordered containers */
    .section-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #475569;
        margin: 0.4rem 0 0.5rem 0.1rem;
    }

    /* Output area */
    .output-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #1e40af;
        margin: 1.5rem 0 0.5rem 0.1rem;
    }

    /* Buttons */
    .stButton button {
        font-weight: 500;
        border-radius: 6px;
    }
    .stButton button[kind="primary"] {
        height: 2.75rem;
        font-size: 0.95rem;
    }

    /* Sidebar tweaks */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* Make the collapsed-sidebar expand button highly visible.
       Streamlit's default chevron is small and easy to miss. */
    [data-testid="collapsedControl"] {
        background-color: #1e40af !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
        margin: 0.75rem !important;
        box-shadow: 0 2px 8px rgba(30, 64, 175, 0.35) !important;
        transition: all 0.15s ease-in-out !important;
        z-index: 999 !important;
    }
    [data-testid="collapsedControl"]:hover {
        background-color: #1e3a8a !important;
        transform: scale(1.08) !important;
        box-shadow: 0 4px 14px rgba(30, 64, 175, 0.5) !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="collapsedControl"] path {
        color: #ffffff !important;
        fill: #ffffff !important;
        stroke: #ffffff !important;
        width: 22px !important;
        height: 22px !important;
    }

    /* Sidebar's own collapse button (visible when sidebar is open) */
    [data-testid="stSidebarCollapseButton"] button {
        background-color: rgba(30, 64, 175, 0.1) !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: rgba(30, 64, 175, 0.2) !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state for form fields
for k in SAMPLE_CASE.keys():
    if f"input_{k}" not in st.session_state:
        st.session_state[f"input_{k}"] = ""
if "input_recommendation" not in st.session_state:
    st.session_state["input_recommendation"] = "File STR"

# Filing metadata — first-run defaults come from user profile in credentials.yaml
# (overrides env vars if present). Subsequent runs preserve whatever the user
# has typed in the form.
if "_profile_loaded_for" not in st.session_state or st.session_state["_profile_loaded_for"] != auth_username:
    profile = get_user_profile(auth_config, auth_username)
    profile_defaults = {
        "input_reporting_institution": profile["reporting_institution"]
            or os.getenv("DEFAULT_REPORTING_INSTITUTION", ""),
        "input_str_reference": "",
        "input_prepared_by": profile["analyst_name"]
            or os.getenv("DEFAULT_ANALYST_NAME", ""),
        "input_mlro_signoff": profile["mlro_name"]
            or os.getenv("DEFAULT_MLRO_NAME", ""),
        "input_entity_category": profile["entity_category"] or "— Select —",
    }
    for k, v in profile_defaults.items():
        st.session_state[k] = v
    st.session_state["_profile_loaded_for"] = auth_username

for k, v in FILING_METADATA_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "input_date_of_filing" not in st.session_state:
    st.session_state["input_date_of_filing"] = date.today()

# ============================================================================
# Sidebar — user identity, profile editor, logout. Rendered before the main
# column so the user has access to it even before scrolling the form.
# ============================================================================
with st.sidebar:
    # ---- Profile header — avatar + name ----
    avatar_path = get_user_avatar_path(auth_username)
    if avatar_path:
        st.image(str(avatar_path), width=88)
    else:
        # Initial-letter avatar placeholder
        initial = (auth_name or auth_username or "?")[0].upper()
        st.markdown(
            f"""
<div style="width: 88px; height: 88px; background: linear-gradient(135deg, #1e3a8a, #1e40af);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            color: white; font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem;
            box-shadow: 0 2px 8px rgba(30, 64, 175, 0.25);">{initial}</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f"**{auth_name}**  \n<small style='color: #64748b;'>`{auth_username}`</small>",
                unsafe_allow_html=True)

    # Avatar upload
    avatar_upload = st.file_uploader(
        "Upload profile photo",
        type=["png", "jpg", "jpeg"],
        key="avatar_upload",
        label_visibility="visible",
        help="JPG or PNG, square ~200×200 px works best.",
    )
    if avatar_upload is not None:
        # Streamlit returns the same UploadedFile across reruns until cleared,
        # so guard with a session marker to avoid re-saving on every rerun.
        marker_key = f"_avatar_saved_{avatar_upload.name}_{avatar_upload.size}"
        if not st.session_state.get(marker_key):
            ext = avatar_upload.name.rsplit(".", 1)[-1] if "." in avatar_upload.name else "png"
            save_avatar(auth_username, avatar_upload.getvalue(), ext)
            st.session_state[marker_key] = True
            st.success("Profile photo updated.")
            st.rerun()

    try:
        authenticator.logout("Sign out", location="sidebar", use_container_width=True)
    except Exception as logout_err:
        st.error(f"Logout error: {logout_err}")

    st.markdown("---")
    st.markdown("### Profile defaults")
    st.caption("Auto-fill the Filing metadata fields on every case.")

    profile_now = get_user_profile(auth_config, auth_username)
    new_inst = st.text_input(
        "Reporting Institution",
        value=profile_now["reporting_institution"],
        key="profile_inst",
    )
    new_analyst = st.text_input(
        "Your name + role",
        value=profile_now["analyst_name"],
        key="profile_analyst",
    )
    new_mlro = st.text_input(
        "MLRO name",
        value=profile_now["mlro_name"],
        key="profile_mlro",
    )

    if st.button("Save profile", use_container_width=True):
        update_user_profile(
            auth_config,
            auth_username,
            reporting_institution=new_inst,
            analyst_name=new_analyst,
            mlro_name=new_mlro,
        )
        save_config(auth_config)
        # Force re-load on next rerun so Filing metadata picks up new defaults
        st.session_state.pop("_profile_loaded_for", None)
        st.success("Profile saved. New defaults active on next case.")

    # ---- Pre-flight system check — run before each ICP demo ----
    st.markdown("---")
    with st.expander("Pre-flight check", expanded=False):
        st.caption(
            "Run before each demo meeting to confirm everything's wired up."
        )
        if st.button("Run system check", use_container_width=True, key="preflight_btn"):
            checks: list[tuple[str, bool, str]] = []

            # Anthropic API key
            anth_key = os.getenv("ANTHROPIC_API_KEY", "")
            checks.append((
                "Anthropic API key",
                anth_key.startswith("sk-ant-") and len(anth_key) > 50,
                f"set ({len(anth_key)} chars)" if anth_key else "missing",
            ))

            # OpenSanctions key
            os_key = os.getenv("OPENSANCTIONS_API_KEY", "")
            checks.append((
                "OpenSanctions API key",
                len(os_key) >= 16,
                f"set ({len(os_key)} chars)" if os_key else "missing",
            ))

            # All 4 rubrics present
            for jur, path in RUBRICS.items():
                if path is None:
                    checks.append((f"Rubric: {jur}", False, "no path configured"))
                    continue
                ok = path.exists() and path.stat().st_size > 1000
                size = path.stat().st_size if path.exists() else 0
                checks.append((
                    f"Rubric: {jur}",
                    ok,
                    f"{size:,} bytes" if size else "missing",
                ))

            # All 4 guidance docs
            for jur, path in GUIDANCE.items():
                if path is None or not path.exists():
                    checks.append((f"Guidance: {jur}", False, "missing"))
                else:
                    checks.append((
                        f"Guidance: {jur}",
                        path.stat().st_size > 500,
                        f"{path.stat().st_size:,} bytes",
                    ))

            # Sample library has 6 per jurisdiction
            from lib.connectors import CONNECTORS as _C
            for jur in RUBRICS.keys():
                samples = SAMPLE_LIBRARY.get(jur, {})
                checks.append((
                    f"Samples: {jur}",
                    len(samples) >= 4,
                    f"{len(samples)} samples loaded",
                ))

            # Connectors loaded
            checks.append((
                "Connectors catalogue",
                len(_C) >= 100,
                f"{len(_C)} platforms loaded",
            ))

            # Render results
            n_pass = sum(1 for _, ok, _ in checks if ok)
            n_fail = len(checks) - n_pass
            if n_fail == 0:
                st.success(f"All {len(checks)} checks passed — ready to demo")
            else:
                st.warning(f"{n_pass} passed, {n_fail} failed")
            for label, ok, detail in checks:
                icon = "✓" if ok else "✗"
                color = "#059669" if ok else "#dc2626"
                st.markdown(
                    f'<div style="font-size: 0.82rem; color: {color};">'
                    f'<strong>{icon}</strong> {label} — <small>{detail}</small></div>',
                    unsafe_allow_html=True,
                )

# Initialize jurisdiction + model in session_state so the toolbar (rendered after
# the header) can drive the header content via st.session_state lookups.
if "jurisdiction" not in st.session_state:
    st.session_state["jurisdiction"] = list(RUBRICS.keys())[0]
if "model" not in st.session_state:
    st.session_state["model"] = "claude-sonnet-4-6"
jurisdiction = st.session_state["jurisdiction"]
model = st.session_state["model"]

# Branded header — jurisdiction-aware, with authority chips on the right
authorities = JURISDICTION_AUTHORITIES.get(jurisdiction, [])
auth_chips_html = "".join(
    f'<div class="auth-chip"><span class="auth-abbr">{a["abbr"]}</span>'
    f'<span class="auth-name">{a["name"]}</span></div>'
    for a in authorities
)
jur_label = JURISDICTION_LABEL.get(jurisdiction, jurisdiction)

st.markdown(
    f"""
<div class="brand-header">
    <div class="brand-left">
        <span class="badge">v0 · {jur_label}</span>
        <h1>AML Agents - STR Reporting</h1>
        <p class="subtitle">AI-drafted suspicious transaction reports. Analyst-supplied facts only — never fabricated. Per-sentence audit trail.</p>
    </div>
    <div class="brand-right">
        {auth_chips_html}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Top toolbar — jurisdiction, model, and quick actions, always visible in the
# main column. Replaces the sidebar so the controls can never be hidden.
st.markdown('<div class="section-label">Configuration</div>', unsafe_allow_html=True)
with st.container(border=True):
    tool_col1, tool_col2, tool_col3, tool_col4, tool_col5 = st.columns(
        [2, 2, 3, 1, 1], gap="medium"
    )
    with tool_col1:
        st.selectbox(
            "Jurisdiction",
            list(RUBRICS.keys()),
            key="jurisdiction",
            help="Drives the rubric, filing guidance, authority chips, and entity categories.",
        )
    with tool_col2:
        st.selectbox(
            "Model",
            ["claude-sonnet-4-6", "claude-opus-4-7"],
            key="model",
            help="Sonnet for cost-efficient drafts. Opus for complex cases.",
        )
    with tool_col3:
        # Sample picker — filtered by current jurisdiction
        current_jur_for_samples = st.session_state.get(
            "jurisdiction", list(RUBRICS.keys())[0]
        )
        available_samples = list(
            SAMPLE_LIBRARY.get(current_jur_for_samples, {}).keys()
        )
        if not available_samples:
            available_samples = ["(no samples for this jurisdiction)"]
        # Reset stale selection if jurisdiction changed
        if st.session_state.get("sample_choice") not in available_samples:
            st.session_state["sample_choice"] = available_samples[0]
        st.selectbox(
            "Sample case",
            available_samples,
            key="sample_choice",
            help="Pick the typology that matches your demo audience. Then click Load.",
        )
    with tool_col4:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("Load", use_container_width=True):
            current_jur = st.session_state["jurisdiction"]
            sample_name = st.session_state.get("sample_choice")
            mapping = SAMPLE_LIBRARY.get(current_jur, {}).get(sample_name)
            if mapping:
                case_key, filing_key = mapping
                sample = SAMPLE_CASES.get(case_key, SAMPLE_CASES["Singapore (STRO)"])
                sample_filing = SAMPLE_FILING_METADATAS.get(
                    filing_key, SAMPLE_FILING_METADATAS["Singapore (STRO)"]
                )
                for k, v in sample.items():
                    st.session_state[f"input_{k}"] = v
                st.session_state["input_recommendation"] = "File STR"
                for k, v in sample_filing.items():
                    st.session_state[k] = v
                st.session_state["input_date_of_filing"] = date.today()
                st.rerun()
    with tool_col5:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True):
            for k in SAMPLE_CASE.keys():
                st.session_state[f"input_{k}"] = ""
            for k, v in FILING_METADATA_DEFAULTS.items():
                st.session_state[k] = v
            st.session_state["input_date_of_filing"] = date.today()
            st.rerun()

# After widgets render, re-read in case the user changed the dropdown this run
jurisdiction = st.session_state["jurisdiction"]
model = st.session_state["model"]

# ============================================================================
# Top-level tabs — Draft STR / Connectors / Obligation register / Horizon scanning
# ============================================================================
tab_draft, tab_connectors, tab_obligations, tab_horizon, tab_news = st.tabs(
    [
        "Draft STR",
        "Connectors",
        "Obligation register",
        "Horizon scanning",
        "Jurisdictional news",
    ]
)

with tab_draft:
    # Getting started — for ICPs trying the demo solo. Auto-collapsed for
    # regular users so it doesn't get in the way of normal workflow.
    with st.expander("New here? 5-step demo flow", expanded=False):
        st.markdown(
            """
1. **Pick a jurisdiction** in the toolbar above (Singapore / Hong Kong / Malaysia / Australia)
2. **Click *Load*** to populate the form with a sample case for that jurisdiction
3. **Optional**: drag a sample PDF or KYC image into *Supporting documents* — Claude will read it
4. **Click *Generate STR narrative*** — narrative appears in 5–15 seconds with `[A]` / `[I]` tags per sentence
5. **Click *File this STR via [portal]*** to jump to the regulator's filing system

Authority chips on the right of the header show which regulators apply to your jurisdiction. The **Filing guidance** expander below shows legal basis, threshold, timing, tipping-off rules. The **Filing metadata** section captures the institution + STR reference + sign-off details that go into the narrative header.

Switch tabs at the top to explore **Connectors** (161 platforms), **Obligation register** (regulatory deadlines), **Horizon scanning** (regulatory updates), and **Jurisdictional news** (industry coverage).
            """
        )

    # Jurisdiction guidance panel — collapsible, jurisdiction-aware
    guidance_path = GUIDANCE.get(jurisdiction)
    if guidance_path and guidance_path.exists():
        with st.expander(f"Filing guidance — {jurisdiction}", expanded=False):
            st.markdown(guidance_path.read_text())

    # Filing metadata — case header fields (reporting entity, STR ref, sign-off)
    st.markdown('<div class="section-label">Filing metadata</div>', unsafe_allow_html=True)
    with st.container(border=True):
        # Entity category dropdown — driven by selected jurisdiction
        categories = ENTITY_CATEGORIES.get(jurisdiction, ["— Select —"])
        # If session state holds a category not valid for the new jurisdiction, reset
        current_cat = st.session_state.get("input_entity_category", "— Select —")
        if current_cat not in categories:
            st.session_state["input_entity_category"] = "— Select —"

        st.selectbox(
            "Reporting Entity Category",
            categories,
            key="input_entity_category",
            help=(
                "Pick the category that matches your institution's licensing under "
                "the selected jurisdiction. Drives sectoral-notice context in the narrative."
            ),
        )

        meta_col1, meta_col2 = st.columns(2, gap="large")
        with meta_col1:
            st.text_input(
                "Reporting Institution",
                key="input_reporting_institution",
                placeholder="e.g. ACME Bank Singapore Pte Ltd (MAS-licensed)",
                help="Set DEFAULT_REPORTING_INSTITUTION in .env to pre-fill across cases.",
            )
            st.text_input(
                "STR Reference",
                key="input_str_reference",
                placeholder="e.g. STR-2026-04-0042",
            )
            st.date_input(
                "Date of Filing",
                key="input_date_of_filing",
            )
        with meta_col2:
            st.text_input(
                "Prepared by (analyst)",
                key="input_prepared_by",
                placeholder="e.g. Lim Wei Ling, Senior Compliance Analyst",
                help="Set DEFAULT_ANALYST_NAME in .env to pre-fill.",
            )
            st.text_input(
                "MLRO Sign-off",
                key="input_mlro_signoff",
                placeholder="e.g. Tan Boon Heng, MLRO",
                help="Set DEFAULT_MLRO_NAME in .env to pre-fill.",
            )

    # Input form
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="section-label">Subject</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.text_input(
                "Customer name",
                key="input_customer_name",
                placeholder="e.g. ACME Trading Pte Ltd",
            )
            st.text_input(
                "Customer ID / Account",
                key="input_customer_id",
                placeholder="e.g. A123456789",
            )

            # Sanctions / PEP / watchlist screening — manual button + auto-screen toggle
            current_name = st.session_state.get("input_customer_name", "")
            screen_btn_col, screen_auto_col = st.columns([1, 1])
            with screen_btn_col:
                screen = st.button(
                    "Screen against sanctions / PEP lists",
                    use_container_width=True,
                    disabled=len(current_name.strip()) < 3,
                    help="Searches OpenSanctions (UN, OFAC, EU, UK HMT, MAS, AUSTRAC, and 200+ other lists, plus PEPs).",
                )
            with screen_auto_col:
                auto_screen = st.toggle(
                    "Auto-screen on type",
                    value=st.session_state.get("auto_screen_enabled", False),
                    key="auto_screen_enabled",
                    help=(
                        "Automatically screen as you finish typing the customer name. "
                        "Triggers once name has 5+ characters AND has changed materially. "
                        "Cached for 30 min so repeated queries are free."
                    ),
                )

            # Auto-screen: trigger when name has changed materially since last screen
            last_screened = st.session_state.get("screening_query", "")
            name_clean = current_name.strip()
            meaningful_change = (
                name_clean != last_screened
                and len(name_clean) >= 5
                and abs(len(name_clean) - len(last_screened)) >= 3
            )

            if screen or (auto_screen and meaningful_change):
                with st.spinner("Searching OpenSanctions…"):
                    result = search_sanctions(current_name)
                st.session_state["screening_result"] = result
                st.session_state["screening_query"] = current_name

            # Show screening results if they match the current name
            if (
                "screening_result" in st.session_state
                and st.session_state.get("screening_query") == current_name
                and current_name.strip()
            ):
                sr = st.session_state["screening_result"]
                if sr.get("api_key_required"):
                    st.warning(
                        "**OpenSanctions API key required.** "
                        "Register free at [opensanctions.org/account/login](https://www.opensanctions.org/account/login), "
                        "copy your API key, then add this line to `~/dev/amlagents/.env`:  \n"
                        "`OPENSANCTIONS_API_KEY=your-key-here`  \n"
                        "Then restart the app."
                    )
                elif "error" in sr:
                    st.warning(f"Screening service unavailable: {sr['error']}")
                elif sr["total"] == 0:
                    st.success(
                        f"No matches found in OpenSanctions for '{current_name}'. "
                        "Searched 200+ sanctions, PEP, and watchlist sources."
                    )
                else:
                    hits = [summarize_entity(r) for r in sr["results"]]
                    top_score = max(h["score"] for h in hits)
                    top_class = classify_match(top_score)

                    if top_class == "high":
                        st.error(
                            f"**HIGH-CONFIDENCE MATCH** — {len(hits)} result(s), "
                            f"top score {top_score:.2f}. Review before proceeding."
                        )
                    elif top_class == "medium":
                        st.warning(
                            f"**Possible match** — {len(hits)} result(s), "
                            f"top score {top_score:.2f}. Likely worth investigating."
                        )
                    else:
                        st.info(
                            f"{len(hits)} low-confidence match(es), top score "
                            f"{top_score:.2f}. Likely false positives but review."
                        )

                    for h in hits:
                        klass = classify_match(h["score"])
                        risk_label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}[klass]
                        target_label = "SANCTIONED" if h["target"] else "PEP / RCA / other"
                        expander_title = (
                            f"[{risk_label}]  {h['caption']}  ·  "
                            f"score {h['score']:.2f}  ·  {h['schema']}  ·  {target_label}"
                        )
                        with st.expander(expander_title, expanded=(klass == "high")):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Match score:** {h['score']:.2f}")
                                st.markdown(
                                    f"**OpenSanctions match flag:** {'Yes' if h['match'] else 'No'}"
                                )
                                st.markdown(
                                    f"**Sanctions target:** {'Yes (currently sanctioned)' if h['target'] else 'No'}"
                                )
                            with col_b:
                                st.markdown(f"**Country:** {h['country']}")
                                st.markdown(f"**Topics:** {h['topics']}")
                            st.markdown(f"**Datasets:** {h['datasets']}")
                            if h["url"]:
                                st.markdown(f"[View full record on OpenSanctions →]({h['url']})")

            st.text_area(
                "KYC summary",
                key="input_customer_kyc",
                placeholder="Occupation, source of funds, expected activity, onboarding risk rating",
                height=110,
            )

            # Supporting documents upload — KYC, statements, source-of-funds, ID
            st.markdown(
                '<div style="font-size: 0.78rem; font-weight: 600; color: #475569; '
                'margin: 0.6rem 0 0.3rem 0;">Supporting documents (optional)</div>',
                unsafe_allow_html=True,
            )
            uploaded_docs = st.file_uploader(
                "Attach ID cards, bank statements, KYC letters, source-of-funds documents, screenshots",
                accept_multiple_files=True,
                type=["pdf", "png", "jpg", "jpeg", "docx", "txt", "eml", "csv", "xlsx"],
                key="input_supporting_docs",
                label_visibility="collapsed",
                help="v0: document names included in narrative context. v1: full content extraction via Claude vision/PDF.",
            )
            if uploaded_docs:
                for doc in uploaded_docs:
                    st.caption(f"Attached: {doc.name} ({doc.size:,} bytes)")

        st.markdown('<div class="section-label">Triggering activity</div>', unsafe_allow_html=True)
        with st.container(border=True):
            # Alert source dropdown — TrustSphere Risk Index featured first
            from lib.connectors import CONNECTORS as _ALL_CONNECTORS
            _alert_source_options = ["TrustSphere Risk Index", "Internal transaction monitoring"] + [
                c.name for c in _ALL_CONNECTORS
                if c.category in (
                    "Transaction monitoring",
                    "Transaction monitoring & case management",
                    "Transaction monitoring (enterprise)",
                    "Transaction monitoring & contextual decisioning",
                    "Transaction monitoring & fraud",
                )
                and c.name != "TrustSphere Risk Index"
            ] + ["Other / external referral"]

            if st.session_state.get("input_alert_source") not in _alert_source_options:
                st.session_state["input_alert_source"] = _alert_source_options[0]

            st.selectbox(
                "Alert source",
                _alert_source_options,
                key="input_alert_source",
                help="Which connected platform raised this alert. TrustSphere Risk Index is the featured composite signal.",
            )

            # TrustSphere Risk Index — score slider with band badge
            ts_col1, ts_col2 = st.columns([2, 1])
            with ts_col1:
                ts_score_val = st.slider(
                    "TrustSphere Risk Index score (0–100)",
                    min_value=0,
                    max_value=100,
                    value=st.session_state.get("input_ts_risk_score", 0),
                    key="input_ts_risk_score",
                    help="Composite risk score from TrustSphere Risk Index. 0–39 Low, 40–69 Medium, 70–100 High.",
                )
            with ts_col2:
                _band = "Low" if ts_score_val < 40 else ("Medium" if ts_score_val < 70 else "High")
                _band_color = {"Low": "#059669", "Medium": "#d97706", "High": "#dc2626"}[_band]
                st.markdown(
                    f'<div style="margin-top: 1.85rem; text-align: center;">'
                    f'<span style="background: {_band_color}; color: white; padding: 0.4rem 0.9rem; '
                    f'border-radius: 6px; font-weight: 600; font-size: 0.85rem;">'
                    f'{ts_score_val} — {_band}</span></div>',
                    unsafe_allow_html=True,
                )

            st.text_area(
                "Transactions",
                key="input_transactions",
                placeholder="One per line:  date | amount | currency | counterparty | channel",
                height=130,
            )
            st.text_input(
                "Alert reason",
                key="input_alert_reason",
                placeholder="What flagged the case?",
            )
            st.text_area(
                "Red flag indicators",
                key="input_red_flags",
                placeholder="Specific indicia observed — map to FATF / STRO typology",
                height=100,
            )

    with col2:
        st.markdown('<div class="section-label">Analyst investigation</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.text_area(
                "Investigation notes",
                key="input_analyst_notes",
                placeholder=(
                    "What you reviewed, found, confirmed, could not verify. "
                    "Customer's explanation if obtained, and your assessment of plausibility."
                ),
                height=320,
            )

            # Adverse media findings — separate input so the model treats them
            # as analyst-stated facts ([A]) tied to a verifiable source.
            st.text_area(
                "Adverse media findings (optional)",
                key="input_adverse_media",
                placeholder=(
                    "Document any adverse media hits — source publication, date, headline, "
                    "URL. e.g. 'Sin Chew Daily 2026-03-22: customer named in junket-licensing "
                    "investigation. URL: ...'"
                ),
                height=110,
                help=(
                    "Production roadmap: integrated adverse-media API (ComplyAdvantage, "
                    "Refinitiv, Dow Jones). For v0, paste findings manually."
                ),
            )

            # Adverse media supporting documents (article PDFs, screenshots)
            st.markdown(
                '<div style="font-size: 0.78rem; font-weight: 600; color: #475569; '
                'margin: 0.4rem 0 0.3rem 0;">Adverse media documents (optional)</div>',
                unsafe_allow_html=True,
            )
            adverse_docs = st.file_uploader(
                "Attach adverse media articles, court filings, regulator press releases, etc.",
                accept_multiple_files=True,
                type=["pdf", "png", "jpg", "jpeg", "html", "txt"],
                key="input_adverse_docs",
                label_visibility="collapsed",
            )
            if adverse_docs:
                for doc in adverse_docs:
                    st.caption(f"Attached: {doc.name} ({doc.size:,} bytes)")

            st.selectbox(
                "Recommended action",
                ["File STR", "No further action", "Enhanced monitoring", "Account closure"],
                key="input_recommendation",
            )

    # Generate button
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    generate = st.button("Generate STR narrative", type="primary", use_container_width=True)

    if generate:
        customer_name = st.session_state["input_customer_name"]
        customer_id = st.session_state["input_customer_id"]
        customer_kyc = st.session_state["input_customer_kyc"]
        transactions = st.session_state["input_transactions"]
        alert_reason = st.session_state["input_alert_reason"]
        red_flags = st.session_state["input_red_flags"]
        analyst_notes = st.session_state["input_analyst_notes"]
        recommendation = st.session_state["input_recommendation"]
        reporting_institution = st.session_state["input_reporting_institution"]
        entity_category = st.session_state["input_entity_category"]
        str_reference = st.session_state["input_str_reference"]
        prepared_by = st.session_state["input_prepared_by"]
        mlro_signoff = st.session_state["input_mlro_signoff"]
        date_of_filing = st.session_state["input_date_of_filing"]
        alert_source = st.session_state.get("input_alert_source", "Internal transaction monitoring")
        ts_risk_score = st.session_state.get("input_ts_risk_score", 0)
        ts_risk_band = "Low" if ts_risk_score < 40 else ("Medium" if ts_risk_score < 70 else "High")
        adverse_media = st.session_state.get("input_adverse_media", "")
        # Document lists for prompt context AND multi-modal content blocks
        supporting_files = st.session_state.get("input_supporting_docs") or []
        adverse_files = st.session_state.get("input_adverse_docs") or []
        supporting_docs_list = (
            ", ".join(d.name for d in supporting_files) or "[none attached]"
        )
        adverse_docs_list = (
            ", ".join(d.name for d in adverse_files) or "[none attached]"
        )

        # ============================================================
        # Build multi-modal content blocks: Claude reads PDFs / images natively.
        # ============================================================
        import base64 as _b64

        def _file_to_block(uploaded_file, label: str):
            """Convert a Streamlit UploadedFile to an Anthropic content block.

            Returns None if the file type is unsupported.
            Supported: PDF (document block), images (image block), text (text block).
            """
            try:
                data = uploaded_file.getvalue()
            except Exception:
                return None
            name = uploaded_file.name
            mime = (uploaded_file.type or "").lower()
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

            # PDF — Anthropic native PDF support
            if mime == "application/pdf" or ext == "pdf":
                return {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": _b64.b64encode(data).decode("ascii"),
                    },
                    "title": f"{label}: {name}",
                }
            # Images
            if mime.startswith("image/") or ext in ("png", "jpg", "jpeg", "gif", "webp"):
                # Normalize media type
                if ext in ("jpg", "jpeg"):
                    media_type = "image/jpeg"
                elif ext == "png":
                    media_type = "image/png"
                elif ext == "gif":
                    media_type = "image/gif"
                elif ext == "webp":
                    media_type = "image/webp"
                else:
                    media_type = mime or "image/png"
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": _b64.b64encode(data).decode("ascii"),
                    },
                }
            # Plain text — pass content directly
            if mime.startswith("text/") or ext in ("txt", "csv", "eml"):
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
                if text.strip():
                    snippet = text[:5000]  # cap per-doc text size
                    return {
                        "type": "text",
                        "text": f"\n\n[{label}: {name}]\n{snippet}\n",
                    }
            # Unsupported type — skip
            return None

        # Cap total docs to keep cost reasonable. Skipped docs noted in prompt.
        MAX_DOCS = 6
        document_blocks = []
        skipped_docs: list[str] = []
        for f in supporting_files[:MAX_DOCS]:
            b = _file_to_block(f, "Customer document")
            if b is None:
                skipped_docs.append(f.name)
            else:
                document_blocks.append(b)
        for f in adverse_files[: max(0, MAX_DOCS - len(document_blocks))]:
            b = _file_to_block(f, "Adverse-media document")
            if b is None:
                skipped_docs.append(f.name)
            else:
                document_blocks.append(b)
        if len(supporting_files) + len(adverse_files) > MAX_DOCS:
            overflow = supporting_files[MAX_DOCS:] + adverse_files[
                max(0, MAX_DOCS - len(supporting_files)):
            ]
            for f in overflow:
                skipped_docs.append(f"{f.name} (over MAX_DOCS={MAX_DOCS} limit)")

        skipped_note = (
            f"\n\n[Documents skipped — unsupported type or over per-case limit]: "
            f"{', '.join(skipped_docs)}"
            if skipped_docs else ""
        )
        if entity_category == "— Select —":
            entity_category = "[not provided]"

        rubric_path = RUBRICS[jurisdiction]

        if rubric_path is None or not rubric_path.exists():
            st.error(f"Rubric for {jurisdiction} not yet implemented. v0 supports Singapore (STRO) only.")
        elif not (customer_name or analyst_notes or transactions):
            st.warning("Provide at least one of: customer name, transactions, or analyst notes.")
        elif not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY not set. Edit ~/dev/amlagents/.env and restart the app.")
        else:
            rubric = rubric_path.read_text()
            user_input = f"""[FILING METADATA]
    Reporting Institution: {reporting_institution or '[not provided]'}
    Reporting Entity Category: {entity_category}
    STR Reference: {str_reference or '[not provided]'}
    Date of Filing: {date_of_filing.strftime('%Y-%m-%d') if date_of_filing else '[not provided]'}
    Prepared by: {prepared_by or '[not provided]'}
    MLRO Sign-off: {mlro_signoff or '[not provided]'}

    [SUBJECT]
    Name: {customer_name or '[not provided]'}
    ID: {customer_id or '[not provided]'}
    KYC: {customer_kyc or '[not provided]'}

    [TRANSACTIONS]
    {transactions or '[not provided]'}

    [ALERT]
    Source: {alert_source}
    TrustSphere Risk Index: {ts_risk_score}/100 ({ts_risk_band})
    Reason: {alert_reason or '[not provided]'}
    Red flags: {red_flags or '[not provided]'}

    [ANALYST NOTES]
    {analyst_notes or '[not provided]'}

    [ADVERSE MEDIA]
    {adverse_media or '[none documented by analyst]'}

    [SUPPORTING DOCUMENTS REVIEWED]
    Customer documents: {supporting_docs_list}
    Adverse-media documents: {adverse_docs_list}
    {skipped_note}

    [RECOMMENDATION]
    {recommendation}

    Draft the STR narrative following the rubric. Use only facts stated in the inputs and any uploaded documents. Never fabricate.

    For uploaded documents (PDFs, images, text): extract specific facts that support the narrative — transaction amounts, dates, named parties, addresses, signatures, watermarks, source-of-wealth declarations. Tag any fact extracted from a document as `[A]` (analyst-supplied via the document) and identify the source document by name."""

            client = Anthropic()

            # Build the user message: text input + any document/image content blocks.
            # Anthropic accepts a list of content blocks for multi-modal input.
            user_content_blocks = [{"type": "text", "text": user_input}]
            user_content_blocks.extend(document_blocks)

            spinner_msg = (
                f"Drafting narrative + analysing {len(document_blocks)} document(s)…"
                if document_blocks
                else "Drafting narrative…"
            )

            # Stream the response so the analyst sees text appear progressively
            # rather than waiting 5–15 seconds for a complete response.
            st.markdown('<div class="output-label">Generated narrative</div>', unsafe_allow_html=True)
            narrative_container = st.container(border=True)
            narrative = ""

            with st.spinner(spinner_msg):
                with client.messages.stream(
                    model=model,
                    max_tokens=2000,
                    system=[
                        {
                            "type": "text",
                            "text": rubric,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_content_blocks}],
                ) as stream:
                    placeholder = narrative_container.empty()
                    for text_chunk in stream.text_stream:
                        narrative += text_chunk
                        placeholder.markdown(narrative + "▌")  # caret indicator
                    placeholder.markdown(narrative)  # final render without caret
                    response = stream.get_final_message()

            # Direct filing-portal link — high-impact UX so analysts jump straight
            # to the FIU's filing system after reviewing the draft narrative.
            portal_name, portal_url = FILING_PORTALS.get(jurisdiction, ("FIU portal", "#"))
            st.markdown(
                f'<div style="margin-top: 1rem; margin-bottom: 0.5rem;">'
                f'<a href="{portal_url}" target="_blank" '
                f'style="display: block; background: #1e40af; color: white; '
                f'padding: 0.85rem 1.5rem; border-radius: 8px; text-decoration: none; '
                f'font-weight: 600; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
                f'File this STR via {portal_name} →'
                f'</a></div>',
                unsafe_allow_html=True,
            )
            st.caption(
                f"Opens the {portal_name} filing system in a new tab. "
                "You'll need your institution's credentials to authenticate."
            )

            # ==============================================================
            # Consortium (beta) — cross-institution STR intelligence sharing
            # ==============================================================
            st.markdown(
                '<div class="output-label" style="margin-top: 1.5rem;">Consortium (beta)</div>',
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                # Compute consortium fingerprint for the current case
                _tags = extract_tags(red_flags, analyst_notes, alert_reason, adverse_media)
                _amount_band = amount_band(transactions)

                _lookup = consortium_lookup(
                    subject_name=customer_name,
                    subject_id=customer_id,
                    jurisdiction=jurisdiction,
                    entity_category=entity_category if entity_category != "[not provided]" else "",
                    typology_tags=_tags,
                    institution=reporting_institution,
                )

                cons_col1, cons_col2 = st.columns([2, 1])
                with cons_col1:
                    st.markdown(
                        f"**Consortium hash for this STR:** `{_lookup['subject_hash']}`  \n"
                        f"<small style='color: #64748b;'>"
                        f"Anonymous hash of subject identifiers — same subject filed by another "
                        f"institution would generate the same hash without revealing the original "
                        f"name or ID."
                        f"</small>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"**Detected typology tags:** "
                        f"{', '.join(f'`{t}`' for t in _tags) if _tags else '<i>none extracted</i>'}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Amount band:** `{_amount_band}`")

                with cons_col2:
                    cs = _lookup["score"]
                    cs_color = "#059669" if cs == 0 else ("#d97706" if cs < 50 else "#dc2626")
                    cs_label = "No prior matches" if cs == 0 else (
                        "Some pattern overlap" if cs < 50 else "Multi-institution pattern detected"
                    )
                    st.markdown(
                        f'<div style="text-align: center; padding-top: 0.5rem;">'
                        f'<div style="font-size: 0.7rem; font-weight: 600; color: #475569; '
                        f'text-transform: uppercase; letter-spacing: 0.05em;">Consortium score</div>'
                        f'<div style="font-size: 2.5rem; font-weight: 700; color: {cs_color};">'
                        f'{cs}/100</div>'
                        f'<div style="font-size: 0.78rem; color: {cs_color}; font-weight: 500;">'
                        f'{cs_label}</div></div>',
                        unsafe_allow_html=True,
                    )

                if _lookup["breakdown"]:
                    with st.expander("Score breakdown", expanded=cs > 0):
                        for b in _lookup["breakdown"]:
                            st.markdown(f"- {b}")
                        st.caption(
                            "v0 placeholder scoring. Tomorrow's session: refine the algorithm "
                            "with your methodology. Production deployment requires backend API "
                            "+ legal framework (US Patriot Act 314(b), AMLA s.66B, etc.)."
                        )

                if _lookup["own_filings_for_this_subject"] > 0:
                    st.info(
                        f"You have previously filed {_lookup['own_filings_for_this_subject']} "
                        f"STR(s) for this subject hash. Consider whether this is a continuation "
                        f"or a new pattern."
                    )

                if st.button(
                    "Submit this STR to the consortium",
                    type="secondary",
                    use_container_width=True,
                    help=(
                        "Logs the anonymized fingerprint (hashed subject + tags + jurisdiction + "
                        "amount band) to the consortium. Original narrative is never shared."
                    ),
                ):
                    submitted = consortium_submit(
                        subject_name=customer_name,
                        subject_id=customer_id,
                        institution=reporting_institution,
                        jurisdiction=jurisdiction,
                        entity_category=entity_category if entity_category != "[not provided]" else "",
                        alert_source=alert_source,
                        typology_tags=_tags,
                        amount_band_value=_amount_band,
                        risk_score=ts_risk_score,
                        str_reference=str_reference,
                    )
                    st.success(
                        f"Submitted to consortium as `{submitted.id}` — "
                        f"hash `{submitted.subject_hash_value}` logged."
                    )

            # Email forward — generates a mailto link with pre-filled subject + body.
            # Note: browsers cannot auto-attach the PDF via mailto; user must
            # download the PDF and drag-and-drop into their email client.
            from urllib.parse import quote as _urlquote
            _subject = f"STR draft for review — {str_reference or 'Untitled'} — {customer_name or 'Subject'}"
            _body = (
                f"Please review the attached STR draft for filing readiness.\n\n"
                f"Reporting Institution: {reporting_institution or 'N/A'}\n"
                f"Subject: {customer_name or 'N/A'}\n"
                f"STR Reference: {str_reference or 'N/A'}\n"
                f"Jurisdiction: {jurisdiction}\n"
                f"Recommended action: {recommendation}\n\n"
                f"Note: Please save the PDF locally and attach to this email "
                f"(browsers cannot auto-attach via mailto).\n\n"
                f"-- Drafted via AML Agents"
            )
            mailto_url = f"mailto:?subject={_urlquote(_subject)}&body={_urlquote(_body)}"
            st.markdown(
                f'<div style="margin-top: 0.75rem; margin-bottom: 0.5rem;">'
                f'<a href="{mailto_url}" style="display: block; background: #475569; '
                f'color: white; padding: 0.7rem 1.2rem; border-radius: 6px; '
                f'text-decoration: none; font-weight: 500; text-align: center;">'
                f'Email this STR (opens your mail client) →</a></div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "**Important**: most regulators (STRO, JFIU, FIED, AUSTRAC) do **not** accept STRs "
                "by email — formal filing must use the official portal above. Email forward is for "
                "internal review only (e.g. send to your MLRO before filing)."
            )

            # Download buttons — three formats
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
            with col_a:
                st.download_button(
                    "Download .txt",
                    data=narrative,
                    file_name=f"STR_{customer_id or 'draft'}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with col_b:
                st.download_button(
                    "Download .md",
                    data=narrative,
                    file_name=f"STR_{customer_id or 'draft'}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col_c:
                pdf_bytes = narrative_to_pdf(
                    narrative,
                    str_reference or f"STR-{date_of_filing}",
                    reporting_institution,
                    jurisdiction,
                )
                st.download_button(
                    "Download .pdf",
                    data=pdf_bytes,
                    file_name=f"STR_{customer_id or 'draft'}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            usage = response.usage
            cache_read = getattr(usage, "cache_read_input_tokens", 0)
            cache_write = getattr(usage, "cache_creation_input_tokens", 0)
            st.caption(
                f"Tokens — input {usage.input_tokens:,} · output {usage.output_tokens:,} · "
                f"cache read {cache_read:,} · cache write {cache_write:,}"
            )


# ============================================================================
# Connectors tab — integration roadmap. Each connector populates specific STR
# form sections when wired up (KYC → Subject, alerts → Triggering activity,
# screening hits → Sanctions screening, etc.). Status reflects build state.
# ============================================================================
with tab_connectors:
    st.markdown(
        '<div class="section-label">Integration roadmap</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "**161 connectors** to leading AML / TM / KYC / Sanctions screening / blockchain "
        "platforms. Connectors don't just integrate — they **populate the STR**: KYC data into "
        "Subject, alerts into Triggering activity, screening hits into Sanctions panel, KYT "
        "scores into Risk Index. Use **search** below or expand a category."
    )

    def _render_connector_card(c, badge_color: str) -> None:
        populates_html = (
            "<div style='font-size: 0.72rem; color: #1e40af; margin-top: 0.4rem;'>"
            "<strong>Populates:</strong> " + " · ".join(c.populates) + "</div>"
            if c.populates else ""
        )
        st.markdown(
            f"""
<div style="border-left: 3px solid {badge_color}; padding: 0.6rem 0.9rem;
            margin-bottom: 0.5rem; background: #f8fafc; border-radius: 4px;">
    <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <div style="font-weight: 600; color: #0f172a;">
            <a href="{c.homepage}" target="_blank" style="color: #1e40af; text-decoration: none;">
                {c.name}
            </a>
        </div>
        <span style="background: {badge_color}; color: white;
                     padding: 0.12rem 0.5rem; border-radius: 4px; font-size: 0.65rem;
                     font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
                     white-space: nowrap; margin-left: 0.5rem;">{c.status}</span>
    </div>
    <div style="font-size: 0.74rem; color: #64748b; margin-top: 0.2rem;">
        {c.integration_type}
    </div>
    <div style="font-size: 0.82rem; color: #475569; margin-top: 0.4rem;">
        {c.description}
    </div>
    {populates_html}
</div>
            """,
            unsafe_allow_html=True,
        )

    # Search + status filter row
    cn_search_col, cn_status_col = st.columns([3, 2])
    with cn_search_col:
        cn_search = st.text_input(
            "Search connectors (name, category, description)",
            key="connector_search",
            placeholder="e.g. Hawk, sanctions, Sumsub, Singapore...",
        )
    with cn_status_col:
        cn_filter = st.selectbox(
            "Filter by status",
            ["All statuses"] + CONNECTOR_STATUSES,
            key="connector_status_filter",
        )

    # If search is active, show flat filtered list
    if cn_search.strip():
        results = connectors_search(cn_search)
        if cn_filter != "All statuses":
            results = [c for c in results if c.status == cn_filter]
        if not results:
            st.info(f"No connectors match search '{cn_search}'.")
        else:
            st.caption(f"Found {len(results)} match(es) for '{cn_search}'")
            cols = st.columns(2)
            for i, c in enumerate(results):
                with cols[i % 2]:
                    _render_connector_card(c, CONNECTOR_STATUS_COLOURS.get(c.status, "#64748b"))
    else:
        # No search — show collapsible categories
        grouped = connectors_by_category()

        # Apply status filter inside categories
        if cn_filter != "All statuses":
            grouped = {
                cat: [c for c in conns if c.status == cn_filter]
                for cat, conns in grouped.items()
            }
            grouped = {k: v for k, v in grouped.items() if v}

        if not grouped:
            st.info("No connectors match this filter.")
        else:
            for cat, conns in grouped.items():
                live_count = sum(1 for c in conns if c.status == "Live")
                indev_count = sum(1 for c in conns if c.status in ("In development", "Beta"))
                # Auto-expand categories with Live or In-dev work
                expanded_default = (live_count > 0) or (indev_count > 0)
                summary = f"{cat} — {len(conns)} connector{'s' if len(conns) != 1 else ''}"
                if live_count > 0:
                    summary += f" · {live_count} Live"
                if indev_count > 0:
                    summary += f" · {indev_count} In dev"
                with st.expander(summary, expanded=expanded_default):
                    cols = st.columns(2)
                    for i, c in enumerate(conns):
                        with cols[i % 2]:
                            _render_connector_card(
                                c, CONNECTOR_STATUS_COLOURS.get(c.status, "#64748b")
                            )

    st.caption(
        "Roadmap priorities tracked against ICP demand. If a platform you use isn't on the "
        "roadmap or you'd like to bump priority, contact us — most modern AML / TM / KYC "
        "vendors have REST APIs or webhook delivery, and a connector typically takes 1-2 "
        "weeks per integration."
    )


# ============================================================================
# Obligation register tab — track regulatory obligations per institution
# ============================================================================
with tab_obligations:
    st.markdown(
        '<div class="section-label">Regulatory obligation register</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Track regulatory obligations across all jurisdictions in one place — annual filings, "
        "thematic reviews, statute deadlines, sectoral notice attestations. Persistent across "
        "sessions. Filter by jurisdiction or status."
    )

    # Filter controls
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        ob_jur_filter = st.selectbox(
            "Filter by jurisdiction",
            ["All jurisdictions"] + list(RUBRICS.keys()),
            key="ob_jur_filter",
        )
    with filter_col2:
        ob_status_filter = st.selectbox(
            "Filter by status",
            ["All statuses"] + STATUSES,
            key="ob_status_filter",
        )

    # Add new obligation
    with st.expander("Add a new obligation", expanded=False):
        with st.form("add_obligation_form", clear_on_submit=True):
            new_title = st.text_input("Title", placeholder="e.g. MAS Notice 626 annual attestation")
            new_description = st.text_area("Description", height=80)
            ob_col1, ob_col2 = st.columns(2)
            with ob_col1:
                new_jurisdiction = st.selectbox("Jurisdiction", list(RUBRICS.keys()))
                new_statute = st.text_input(
                    "Statute / notice reference", placeholder="e.g. MAS Notice 626 §10"
                )
                new_due = st.date_input("Due date")
            with ob_col2:
                new_status = st.selectbox("Status", STATUSES)
                new_owner = st.text_input("Owner", placeholder="e.g. MLRO / Head of Compliance")
                new_notes = st.text_input("Notes (optional)")
            submitted = st.form_submit_button("Add obligation", type="primary")
            if submitted and new_title:
                add_obligation(
                    title=new_title,
                    description=new_description,
                    jurisdiction=new_jurisdiction,
                    statute_or_notice=new_statute,
                    due_date=new_due.isoformat() if new_due else "",
                    status=new_status,
                    owner=new_owner,
                    notes=new_notes,
                )
                st.success(f"Added: {new_title}")
                st.rerun()

    # Render filtered list
    obligations = load_obligations()
    if ob_jur_filter != "All jurisdictions":
        obligations = [o for o in obligations if o.jurisdiction == ob_jur_filter]
    if ob_status_filter != "All statuses":
        obligations = [o for o in obligations if o.status == ob_status_filter]

    if not obligations:
        st.info("No obligations match your filter. Add one above to start tracking.")
    else:
        for o in obligations:
            status_color = {
                "Open": "#64748b",
                "In progress": "#1e40af",
                "Closed": "#059669",
                "Overdue": "#dc2626",
            }.get(o.status, "#64748b")
            with st.container(border=True):
                top_row = st.columns([5, 1, 1])
                with top_row[0]:
                    st.markdown(
                        f"**{o.title}** &nbsp; "
                        f'<span style="color: {status_color}; font-size: 0.75rem; '
                        f'font-weight: 600; text-transform: uppercase;">{o.status}</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"{o.jurisdiction}  ·  Due: {o.due_date or '—'}  ·  Owner: {o.owner or '—'}"
                    )
                    if o.statute_or_notice:
                        st.caption(f"Reference: {o.statute_or_notice}")
                    if o.description:
                        st.markdown(f"<small>{o.description}</small>", unsafe_allow_html=True)
                    if o.notes:
                        st.caption(f"Notes: {o.notes}")
                with top_row[1]:
                    new_ob_status = st.selectbox(
                        "Status",
                        STATUSES,
                        index=STATUSES.index(o.status) if o.status in STATUSES else 0,
                        key=f"ob_status_{o.id}",
                        label_visibility="collapsed",
                    )
                    if new_ob_status != o.status:
                        update_obligation(o.id, status=new_ob_status)
                        st.rerun()
                with top_row[2]:
                    if st.button("Delete", key=f"ob_del_{o.id}", use_container_width=True):
                        delete_obligation(o.id)
                        st.rerun()

    # Tracked regulator directory — reference for sourcing new obligations
    render_regulator_directory(key_prefix="obligations")


# ============================================================================
# Horizon scanning tab — recent regulatory updates per jurisdiction
# ============================================================================
with tab_horizon:
    st.markdown(
        '<div class="section-label">Regulatory horizon scanning</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Curated feed of recent regulatory updates across all four jurisdictions. "
        "Filter by jurisdiction. Items are colour-coded by impact level."
    )

    h_col1, h_col2, h_col3, h_col4 = st.columns([2, 2, 1, 1])
    with h_col1:
        horizon_jur = st.selectbox(
            "Filter by jurisdiction",
            ["All jurisdictions"] + list(RUBRICS.keys()),
            key="horizon_jur_filter",
        )
    with h_col2:
        horizon_cat = st.selectbox(
            "Filter by category",
            ["All categories", "Regulatory", "Enforcement", "Industry", "Typology", "Sanctions"],
            key="horizon_cat_filter",
        )
    with h_col3:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        include_live = st.toggle(
            "Live feeds",
            value=True,
            key="horizon_include_live",
            help="Fetch from regulator RSS feeds (cached 30 min). Toggle off for curated only.",
        )
    with h_col4:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        force_refresh = st.button(
            "Refresh",
            use_container_width=True,
            help="Force-refresh live RSS feeds (bypasses 30-min cache).",
        )

    items, feed_statuses = all_items_for_jurisdiction(
        None if horizon_jur == "All jurisdictions" else horizon_jur,
        include_live=include_live,
        force_refresh=force_refresh,
    )
    if horizon_cat != "All categories":
        items = [i for i in items if i.category == horizon_cat]

    # Show feed-fetch status for transparency
    if include_live and feed_statuses:
        ok_count = sum(
            1 for v in feed_statuses.values()
            if v.startswith("OK") or v.startswith("cached")
        )
        err_count = sum(1 for v in feed_statuses.values() if v.startswith("error"))
        if err_count == 0:
            st.caption(f"Live feeds: {ok_count} responding · cache TTL 30 min")
        else:
            with st.expander(
                f"Live feed status — {ok_count} OK, {err_count} unavailable",
                expanded=False,
            ):
                for k, v in feed_statuses.items():
                    icon = "OK" if (v.startswith("OK") or v.startswith("cached")) else "FAIL"
                    st.markdown(f"- **{icon}** {k}: `{v}`")
                st.caption(
                    "Some regulator RSS URLs change without notice. Curated items still load. "
                    "Update URLs in `lib/horizon.py` if a feed is consistently down."
                )

    if not items:
        st.info("No items match your filter.")
    else:
        for item in items:
            impact_color = {
                "High": "#dc2626",
                "Medium": "#d97706",
                "Low": "#64748b",
            }.get(item.impact, "#64748b")
            with st.container(border=True):
                row = st.columns([4, 1])
                with row[0]:
                    st.markdown(
                        f"**{item.title}**  \n"
                        f'<small style="color: #64748b;">'
                        f"{item.date}  ·  {item.jurisdiction}  ·  {item.category}  ·  Source: {item.source}"
                        f"</small>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<small>{item.summary}</small>", unsafe_allow_html=True
                    )
                    st.markdown(
                        f'[Open source →]({item.url})',
                        unsafe_allow_html=True,
                    )
                with row[1]:
                    st.markdown(
                        f'<div style="text-align: right; padding-top: 0.4rem;">'
                        f'<span style="background: {impact_color}; color: white; '
                        f'padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.7rem; '
                        f'font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">'
                        f"{item.impact} impact</span></div>",
                        unsafe_allow_html=True,
                    )

    st.caption(
        "Curated to 2026-04-28. v0 uses a static catalogue; production roadmap pulls from "
        "regulator RSS feeds (MAS, HKMA, BNM, AUSTRAC) with LLM-assisted summarization."
    )

    # Tracked regulator directory — same set used by Obligations and News
    render_regulator_directory(key_prefix="horizon")


# ============================================================================
# Jurisdictional news tab — broader compliance/fintech/regtech news per country
# ============================================================================
with tab_news:
    st.markdown(
        '<div class="section-label">Jurisdictional news</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Industry news, market events, talent moves, M&A, fraud-trend coverage, and regulator "
        "announcements across the four jurisdictions. Distinct from horizon scanning (which "
        "tracks regulatory change). Filter by country and topic."
    )

    n_col1, n_col2, n_col3, n_col4 = st.columns([2, 2, 1, 1])
    with n_col1:
        news_jur = st.selectbox(
            "Filter by country",
            ["All jurisdictions"] + list(RUBRICS.keys()),
            key="news_jur_filter",
        )
    with n_col2:
        news_topic = st.selectbox(
            "Filter by topic",
            ["All topics"] + NEWS_TOPICS,
            key="news_topic_filter",
        )
    with n_col3:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        news_include_live = st.toggle(
            "Live feeds",
            value=True,
            key="news_include_live",
            help="Pull from industry RSS (FinExtra, ACAMS Today, CoinDesk, etc.) — cached 30 min.",
        )
    with n_col4:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        news_refresh = st.button(
            "Refresh",
            use_container_width=True,
            key="news_refresh_btn",
            help="Force-refresh live feeds (bypass 30-min cache).",
        )

    news_items, news_statuses = news_items_for(
        jurisdiction=news_jur,
        topic=news_topic,
        include_live=news_include_live,
        force_refresh=news_refresh,
    )

    if news_include_live and news_statuses:
        ok_count = sum(
            1 for v in news_statuses.values()
            if v.startswith("OK") or v.startswith("cached")
        )
        err_count = sum(1 for v in news_statuses.values() if v.startswith("error"))
        if err_count == 0:
            st.caption(f"Industry feeds: {ok_count} responding · cache TTL 30 min")
        else:
            with st.expander(
                f"Live feed status — {ok_count} OK, {err_count} unavailable",
                expanded=False,
            ):
                for k, v in news_statuses.items():
                    icon = "OK" if (v.startswith("OK") or v.startswith("cached")) else "FAIL"
                    st.markdown(f"- **{icon}** {k}: `{v}`")

    if not news_items:
        st.info("No news items match your filter.")
    else:
        for item in news_items:
            with st.container(border=True):
                row = st.columns([4, 1])
                with row[0]:
                    st.markdown(
                        f"**{item.title}**  \n"
                        f'<small style="color: #64748b;">'
                        f"{item.date}  ·  {item.jurisdiction}  ·  {item.topic}  ·  "
                        f"Source: {item.source}"
                        f"</small>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"<small>{item.summary}</small>", unsafe_allow_html=True)
                    st.markdown(
                        f'<a href="{item.url}" target="_blank" '
                        f'style="font-size: 0.82rem;">Open source →</a>',
                        unsafe_allow_html=True,
                    )
                with row[1]:
                    st.markdown(
                        f'<div style="text-align: right; padding-top: 0.4rem;">'
                        f'<span style="background: #1e40af; color: white; '
                        f'padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.7rem; '
                        f'font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">'
                        f"{item.topic.split(' / ')[0]}</span></div>",
                        unsafe_allow_html=True,
                    )

    st.caption(
        f"Curated to {time.strftime('%Y-%m-%d')}. v0 uses static + RSS-pulled feeds. "
        "Production roadmap: per-country news APIs, LinkedIn/Twitter signals, "
        "LLM-summarised industry intelligence."
    )

    # Tracked regulator directory — reference for sourcing news
    render_regulator_directory(key_prefix="news")
