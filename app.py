from __future__ import annotations  # Python 3.9 PEP 604 compat (X | Y union syntax)

import io
import json
import os
import re
import time
import datetime as dt
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
from lib.subscriptions import (
    TIMEZONES as SUB_TIMEZONES,
    add_subscription,
    find_by_email as find_subs_by_email,
    unsubscribe as unsubscribe_token,
)
from lib.tasks import (
    TASK_STATUSES,
    add_task,
    delete_task,
    relink_seed_tasks_to_obligations,
    task_progress,
    tasks_for,
    update_task,
)
from lib.digest import build_digest as build_digest_payload
from lib.podcast import (
    latest_podcast as latest_podcast_meta,
    recent_podcasts as recent_podcasts_meta,
)
from lib.podcast_feed import feed_summary as podcast_feed_summary
from lib.video import (
    latest_video as latest_video_meta,
    recent_videos as recent_videos_meta,
)
from lib.obligations import (  # noqa: I001 — keep grouped for diff cleanliness
    reseed_obligations,
    STATUSES,
    add_obligation,
    delete_obligation,
    load_obligations,
    update_obligation,
)
from lib.sanctions import classify_match, search_sanctions, summarize_entity
from lib.connector_signals import (
    signals_for as connector_signals_for,
    signals_as_prompt_text,
    severity_color,
)

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
    "Philippines (AMLC)": ROOT / "rubrics" / "amlcstr.md",
    "Indonesia (PPATK)": ROOT / "rubrics" / "ppatkstr.md",
    "Japan (JAFIC)": ROOT / "rubrics" / "jaficstr.md",
    "Korea (KoFIU)": ROOT / "rubrics" / "kofiustr.md",
    "Australia (AUSTRAC SMR)": ROOT / "rubrics" / "austracsmr.md",
    "New Zealand (FIU NZ)": ROOT / "rubrics" / "nzfiustr.md",
}
GUIDANCE = {
    "Singapore (STRO)": ROOT / "guidance" / "sg-stro.md",
    "Hong Kong (JFIU)": ROOT / "guidance" / "hk-jfiu.md",
    "Malaysia (FIED)": ROOT / "guidance" / "my-fied.md",
    "Philippines (AMLC)": ROOT / "guidance" / "ph-amlc.md",
    "Indonesia (PPATK)": ROOT / "guidance" / "id-ppatk.md",
    "Japan (JAFIC)": ROOT / "guidance" / "jp-jafic.md",
    "Korea (KoFIU)": ROOT / "guidance" / "kr-kofiu.md",
    "Australia (AUSTRAC SMR)": ROOT / "guidance" / "au-austrac.md",
    "New Zealand (FIU NZ)": ROOT / "guidance" / "nz-fiu.md",
}
JURISDICTION_LABEL = {
    "Singapore (STRO)": "Singapore",
    "Hong Kong (JFIU)": "Hong Kong",
    "Malaysia (FIED)": "Malaysia",
    "Philippines (AMLC)": "Philippines",
    "Indonesia (PPATK)": "Indonesia",
    "Japan (JAFIC)": "Japan",
    "Korea (KoFIU)": "Korea",
    "Australia (AUSTRAC SMR)": "Australia",
    "New Zealand (FIU NZ)": "New Zealand",
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
    "Philippines (AMLC)": [
        {"abbr": "AMLC", "name": "Anti-Money Laundering Council"},
        {"abbr": "BSP", "name": "Bangko Sentral ng Pilipinas"},
        {"abbr": "SEC", "name": "Securities and Exchange Commission"},
    ],
    "Indonesia (PPATK)": [
        {"abbr": "PPATK", "name": "Pusat Pelaporan dan Analisis Transaksi Keuangan"},
        {"abbr": "OJK", "name": "Otoritas Jasa Keuangan"},
        {"abbr": "BI", "name": "Bank Indonesia"},
    ],
    "Japan (JAFIC)": [
        {"abbr": "JAFIC", "name": "Japan Financial Intelligence Center"},
        {"abbr": "FSA", "name": "Financial Services Agency"},
        {"abbr": "BOJ", "name": "Bank of Japan"},
    ],
    "Korea (KoFIU)": [
        {"abbr": "KoFIU", "name": "Korea Financial Intelligence Unit"},
        {"abbr": "FSC", "name": "Financial Services Commission"},
        {"abbr": "FSS", "name": "Financial Supervisory Service"},
    ],
    "Australia (AUSTRAC SMR)": [
        {"abbr": "AUSTRAC", "name": "AUS Transaction Reports & Analysis Centre"},
    ],
    "New Zealand (FIU NZ)": [
        {"abbr": "FIU NZ", "name": "Financial Intelligence Unit (NZ Police)"},
        {"abbr": "RBNZ", "name": "Reserve Bank of New Zealand"},
        {"abbr": "FMA", "name": "Financial Markets Authority"},
        {"abbr": "DIA", "name": "Department of Internal Affairs"},
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
    "Philippines (AMLC)": [
        "— Select —",
        "Universal / commercial bank (UKB / KB) — BSP-supervised",
        "Thrift bank — BSP-supervised",
        "Rural / cooperative bank — BSP-supervised",
        "Non-stock savings and loan association (NSSLA)",
        "Quasi-bank / financing company — BSP-supervised",
        "Money service business (MSB) — remittance / money changer",
        "Electronic money issuer (EMI) — BSP-licensed (e.g. GCash, Maya)",
        "Virtual asset service provider (VASP) — BSP-licensed",
        "Pawnshop — BSP-supervised",
        "Foreign exchange dealer",
        "Securities broker-dealer / investment house — SEC-supervised",
        "Mutual fund / investment company — SEC-supervised",
        "Lending / financing company — SEC-supervised",
        "Life insurance company — IC-supervised",
        "Non-life insurance company — IC-supervised",
        "Pre-need company — IC-supervised",
        "Casino — PAGCOR / IRR / POGO-licensed",
        "Real estate broker / developer (DNFBP)",
        "Jewellery / precious metals / stones dealer (DNFBP)",
        "Lawyer / accountant (DNFBP, where carrying out specified transactions)",
    ],
    "Indonesia (PPATK)": [
        "— Select —",
        "Bank Umum (commercial bank) — OJK-supervised",
        "Bank Umum Syariah (Sharia commercial bank) — OJK-supervised",
        "Bank Perekonomian Rakyat (BPR / BPRS — rural bank) — OJK-supervised",
        "Insurer / reinsurer — OJK-supervised",
        "Securities company / investment manager — OJK-supervised",
        "Fintech P2P lending platform — OJK-supervised",
        "Multifinance / consumer finance — OJK-supervised",
        "Pension fund (Dana Pensiun) — OJK-supervised",
        "Custodian bank — OJK-supervised",
        "E-money issuer / payment service provider — BI-supervised",
        "Money remitter (KUPVA Bukan Bank) — BI-supervised",
        "Crypto-asset trader (Pedagang Aset Kripto) — Bappebti-registered",
        "Notary (Notaris) — PPATK direct",
        "Advocate (Advokat) — PPATK direct",
        "Public accountant (Akuntan Publik) — PPATK direct",
        "Real-estate agent (Agen Properti) — PPATK direct",
        "Precious metals / stones dealer — PPATK direct",
        "Automotive dealer — PPATK direct",
    ],
    "Japan (JAFIC)": [
        "— Select —",
        "City bank (megabank — Mitsubishi UFJ, Mizuho, Sumitomo Mitsui, Resona)",
        "Regional bank — first-tier (e.g. Bank of Yokohama, Chiba Bank)",
        "Regional bank — second-tier (Daini-chigin)",
        "Shinkin bank (cooperative regional bank)",
        "Shinyo kumiai (credit cooperative)",
        "Securities firm — Type I FIBO (e.g. Nomura, Daiwa, SMBC Nikko)",
        "Investment management firm — Type II FIBO",
        "Life insurer (Seimei Hoken)",
        "Non-life insurer (Songai Hoken)",
        "Money lender (Shōhi-sha kinyū / consumer finance)",
        "Crypto-asset exchange service provider (Anshō Kōkan-gyōsha — FSA-registered)",
        "Funds-transfer service provider (Shikin Idō-gyōsha)",
        "Prepaid payment-instrument issuer (above threshold)",
        "Real estate agent — METI-supervised",
        "Dealer in precious metals / stones (Kikinzoku-shōnin)",
        "Attorney (Bengoshi) — DNFBP captured activities",
        "Judicial scrivener (Shihō shoshi) — DNFBP",
        "Certified public accountant (Kōnin kaikei-shi) — DNFBP",
        "Tax accountant (Zeirishi) — DNFBP",
        "Trust / corporate-service provider (TCSP)",
    ],
    "Korea (KoFIU)": [
        "— Select —",
        "Commercial bank (시중은행 — KB, Shinhan, Hana, Woori, NH)",
        "Foreign-bank branch (Korea office)",
        "Special bank (특수은행 — IBK, KEB Hana, KDB)",
        "Mutual savings bank (저축은행)",
        "Securities firm (증권회사)",
        "Asset management company (자산운용회사)",
        "Investment trust company",
        "Life insurer (생명보험)",
        "Non-life insurer (손해보험)",
        "Credit-card / capital company (여신전문금융회사)",
        "E-money issuer / electronic-payment service provider (전자지급결제대행업)",
        "Virtual asset service provider (가상자산사업자 — FTRA-registered, e.g. Upbit, Bithumb, Coinone, Korbit)",
        "Casino — Kangwon Land / Paradise / Grand Korea Leisure",
        "Notary (한정 captured activities)",
        "Lawyer (한정 captured activities)",
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
    "New Zealand (FIU NZ)": [
        "— Select —",
        "Registered bank (RBNZ-supervised — ANZ, ASB, BNZ, Westpac, Kiwibank)",
        "Non-bank deposit taker (NBDT) — RBNZ-supervised",
        "Life insurer — RBNZ-supervised",
        "Issuer / fund manager — FMA-supervised",
        "Derivatives issuer — FMA-supervised",
        "Financial advice provider — FMA-supervised",
        "Custodian / DIMS provider — FMA-supervised",
        "Equity crowdfunding / P2P lending service — FMA-supervised",
        "Casino (DIA-supervised — SkyCity, Christchurch, Dunedin, Hamilton, Queenstown)",
        "Money remitter / currency exchange — DIA-supervised",
        "Lawyer / conveyancer (DNFBP — DIA-supervised)",
        "Accountant (DNFBP — DIA-supervised, captured activities)",
        "Real estate agent (DNFBP — DIA-supervised)",
        "Dealer in high-value goods (DHVG — cash ≥ NZD 10,000)",
        "Trust / corporate service provider (TCSP) — DIA-supervised",
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
    "Philippines (AMLC)": {
        "EMI mule — BCM investment-scam layering": (
            "Philippines (AMLC)", "Philippines (AMLC)",
        ),
        "Casino — POGO chip-walking + cross-property redemption": (
            "Philippines (AMLC) — POGO casino chip-walking",
            "Philippines (AMLC) — POGO casino chip-walking",
        ),
    },
    "Indonesia (PPATK)": {
        "Bank Umum — KKN procurement-corruption layering": (
            "Indonesia (PPATK)", "Indonesia (PPATK)",
        ),
        "Pedagang Aset Kripto — BCM investment-scam mule": (
            "Indonesia (PPATK) — Crypto Pedagang Aset Kripto mule",
            "Indonesia (PPATK) — Crypto Pedagang Aset Kripto mule",
        ),
    },
    "Japan (JAFIC)": {
        "City bank — tokushu sagi mule layering": (
            "Japan (JAFIC)", "Japan (JAFIC)",
        ),
        "Crypto exchange (CAESP) — JPY-to-USDT layering": (
            "Japan (JAFIC) — CAESP USDT layering",
            "Japan (JAFIC) — CAESP USDT layering",
        ),
        "Real estate (METI-supervised) — Tokyo cash buyer": (
            "Japan (JAFIC) — Real estate cash buyer",
            "Japan (JAFIC) — Real estate cash buyer",
        ),
        "Funds-transfer (Shikin Idō) — DPRK sanctions corridor": (
            "Japan (JAFIC) — Shikin Ido DPRK corridor",
            "Japan (JAFIC) — Shikin Ido DPRK corridor",
        ),
    },
    "Korea (KoFIU)": {
        "Commercial bank — voice phishing mule + VASP layering": (
            "Korea (KoFIU)", "Korea (KoFIU)",
        ),
        "VASP (Upbit/Bithumb-class) — DPRK Lazarus layering": (
            "Korea (KoFIU) — VASP DPRK Lazarus",
            "Korea (KoFIU) — VASP DPRK Lazarus",
        ),
        "Casino (Kangwon Land / Paradise) — chip-walking": (
            "Korea (KoFIU) — Casino chip-walking",
            "Korea (KoFIU) — Casino chip-walking",
        ),
        "E-money (KakaoPay / NaverPay) — illegal pyramid layering": (
            "Korea (KoFIU) — E-money illegal pyramid",
            "Korea (KoFIU) — E-money illegal pyramid",
        ),
    },
    "New Zealand (FIU NZ)": {
        "Real estate (DIA-DNFBP) — Auckland cash buyer": (
            "New Zealand (FIU NZ)", "New Zealand (FIU NZ)",
        ),
        "Registered bank (RBNZ) — investment-scam victim mule": (
            "New Zealand (FIU NZ) — Bank investment-scam mule",
            "New Zealand (FIU NZ) — Bank investment-scam mule",
        ),
        "Casino (DIA-supervised SkyCity) — chip-walking layering": (
            "New Zealand (FIU NZ) — SkyCity chip-walking",
            "New Zealand (FIU NZ) — SkyCity chip-walking",
        ),
        "Lawyer / conveyancer (DIA-DNFBP) — trust account misuse": (
            "New Zealand (FIU NZ) — Lawyer trust account",
            "New Zealand (FIU NZ) — Lawyer trust account",
        ),
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

    # ===== Philippines (AMLC) =====
    "Philippines (AMLC)": {
        "customer_name": "Maria Theresa Santos",
        "customer_id": "BSP-EMI-PH-2026-04-CUST-3128",
        "customer_kyc": (
            "Filipino-resident retail customer of a BSP-licensed EMI (e.g. GCash / Maya). "
            "Declared occupation: BPO call-centre agent. Declared monthly income: PHP 28,000. "
            "Account opened 2024-08; first 18 months activity consistent with payroll deposit, "
            "P2P transfers to family in Visayas region, occasional small e-commerce purchases. "
            "Risk rating: Low at onboarding, no PEP / sanctions hit."
        ),
        "transactions": (
            "2026-04-08 | PHP 95,000 inbound | InstaPay from 'Investment Recovery Specialist Inc' (unverified counterparty)\n"
            "2026-04-09 | PHP 92,000 outbound | InstaPay to crypto on-ramp (BSP-licensed VASP)\n"
            "2026-04-10 | PHP 110,000 inbound | InstaPay from same 'Investment Recovery Specialist Inc'\n"
            "2026-04-10 | PHP 108,000 outbound | InstaPay to second BSP-licensed VASP wallet\n"
            "2026-04-12 | PHP 145,000 inbound | InstaPay from 'Investment Recovery Specialist Inc'\n"
            "2026-04-12 | PHP 142,000 outbound | InstaPay to GCash wallet of unrelated retail customer"
        ),
        "alert_reason": (
            "Inbound flow ~10x declared monthly income within 5 days; consistent in-then-out "
            "pattern with retention <1% per leg; counterparty matches AMLC investment-scam mule "
            "typology (BCM Resolution 2025-series)."
        ),
        "red_flags": (
            "Pattern matches AMLC published typology for Business-Email-Compromise / "
            "Investment-Scam mule activity: rapid in-and-out, near-pass-through retention, "
            "consistent counterparty name suggestive of advance-fee fraud, layering through "
            "two VASPs and a P2P recipient. Customer's declared profile (BPO agent, PHP 28k "
            "monthly) is grossly inconsistent with PHP 350k flows in 5 days. Counterparty "
            "'Investment Recovery Specialist Inc' is unregistered with SEC and matches the "
            "naming pattern in AMLC's 2025 BCM-victim mule advisory."
        ),
        "analyst_notes": (
            "EDD initiated 2026-04-13 by EMI's compliance team. Customer outreach via "
            "in-app secure message: customer stated the transfers were 'helping a friend "
            "recover money she lost to investors' but could not name the friend, the "
            "platform, or the original investment vehicle. Customer not aware that her "
            "wallet may be used in a layering chain (typical mule-victim profile). Tipping-"
            "off considerations under AMLA s.9(c)(2) shaped the wording of the EDD request — "
            "no reference to STR or AMLC was made. AMLC Resolution series on BCM-investment "
            "scams applies; Recommend STR + temporary EMI wallet hold per BSP Circular 1108 "
            "freeze provisions + customer financial-literacy referral. Cross-flag the two "
            "VASP recipient wallets to peer institutions via AMLC information-sharing."
        ),
    },
    "Philippines (AMLC) — POGO casino chip-walking": {
        "customer_name": "Mr Liu Wei",
        "customer_id": "POGO-PH-2026-04-CUST-7218",
        "customer_kyc": (
            "PRC national, Hong Kong-resident, regular guest at a PAGCOR-licensed integrated "
            "resort in Entertainment City, Manila. Declared occupation: 'business consultant'. "
            "Source-of-funds declared: 'business proceeds and personal savings'. KYC: PRC "
            "passport, HK ID. Casino enrolled customer at junket-promoter referral level. "
            "Prior visits 2025: average chip purchase USD 80,000 per visit; play patterns "
            "consistent with declared profile."
        ),
        "transactions": (
            "2026-04-12 (Visit 1, IRR-A) | USD 320,000 chip purchase | cash + USD wire from HK | minimal play (~30 min)\n"
            "2026-04-12 (Visit 1, IRR-A) | USD 305,000 chip redemption | requested manager's cheque payable to HK-incorporated trading company\n"
            "2026-04-13 (Visit 2, IRR-B same operator) | USD 280,000 chip purchase | cash | minimal play\n"
            "2026-04-13 (Visit 2, IRR-B) | USD 270,000 chip redemption | wire to BVI account\n"
            "2026-04-14 (Visit 3, IRR-A) | USD 350,000 chip purchase | wire from HK | minimal play\n"
            "2026-04-14 (Visit 3, IRR-A) | USD 340,000 chip redemption | wire to Cambodia account\n"
            "Total: USD 950,000 cycled through 72 hours; 95% retention loss on play of <2%."
        ),
        "alert_reason": (
            "Classic chip-walking / cross-property redemption pattern; minimal play with "
            "<3% loss; redemption proceeds payable to multiple offshore third parties; "
            "patterns inconsistent with prior 2025 visit profile."
        ),
        "red_flags": (
            "Three-visit pattern over 72 hours showing consistent chip-walk: large purchase, "
            "minimal play, near-full redemption to a different offshore third party each "
            "time. Cross-property redemption via two IRRs operated by the same parent group — "
            "matches AMLC and PAGCOR-published casino layering typology. Redemption "
            "destinations (HK trading company, BVI, Cambodia) suggestive of layering through "
            "multiple jurisdictions. No business or personal connection between the customer "
            "and any of the three redemption beneficiaries declared. Junket-promoter referral "
            "tier known to be associated with cross-border layering activity per AMLC "
            "intelligence shared with PAGCOR licensees."
        ),
        "analyst_notes": (
            "Surveillance and AML compliance teams at both IRR-A and IRR-B coordinated review "
            "on 2026-04-15 once the cross-property pattern surfaced via the operator's "
            "consolidated player-tracking system. EDD requested: source-of-funds documentation "
            "for the three chip-purchase deposits and business rationale for each of the three "
            "third-party redemption beneficiaries. Customer declined to provide source-of-funds "
            "documentation, citing 'commercial confidentiality'. AMLC casino reporting "
            "obligations under the Casino IRR apply; the Casino is an independent reporting "
            "entity to AMLC. Recommend STR + customer no-future-service tagging at both IRRs + "
            "junket-promoter relationship review + AMLC Resolution series filing of the "
            "redemption-beneficiary names for inter-licensee circulation. Tipping-off "
            "compliance under AMLA s.9(c)(2) maintained throughout."
        ),
    },

    # ===== Indonesia (PPATK) =====
    "Indonesia (PPATK)": {
        "customer_name": "Bapak Andi Wijaya",
        "customer_id": "OJK-BU-ID-2026-04-CUST-9914",
        "customer_kyc": (
            "Indonesian national, Jakarta-resident retail customer of a tier-1 Bank Umum. "
            "Declared occupation: civil servant (PNS) at a regional government office in "
            "South Sulawesi. Declared monthly salary: IDR 12,000,000. Account opened "
            "2023-03; activity through end-2025 consistent with salary deposit, regular "
            "household and family transfers, modest savings. Risk rating: Medium (PEP-"
            "adjacent — local government official with procurement signing authority); "
            "EDD review last completed Q2 2025."
        ),
        "transactions": (
            "2026-04-05 | IDR 1,250,000,000 inbound | BI-FAST from PT Karya Mandiri (construction company) | reference 'consulting fee'\n"
            "2026-04-06 | IDR 380,000,000 outbound | BI-FAST to private brokerage account (customer's spouse, also OJK-licensed)\n"
            "2026-04-07 | IDR 410,000,000 outbound | BI-FAST to OVO wallet (customer's adult child)\n"
            "2026-04-08 | IDR 215,000,000 outbound | wire to Singapore-based investment account (customer's individual offshore account)\n"
            "2026-04-10 | IDR 240,000,000 outbound | property-developer escrow account (Jakarta)\n"
            "Total: IDR 1.245bn dispersed within 5 days against declared profile of IDR 12m/month salary."
        ),
        "alert_reason": (
            "Inbound flow ~100x declared monthly income within 5 days; counterparty PT Karya "
            "Mandiri is a regional construction contractor with awarded contracts at the "
            "customer's signing-authority office; fan-out layering pattern matches PPATK "
            "Tipologi KKN (corruption-proceeds layering)."
        ),
        "red_flags": (
            "Inbound IDR 1.25bn from PT Karya Mandiri — public procurement records show "
            "this contractor was awarded tender T-2026-038 by the customer's office on "
            "2026-03-28. Reference 'consulting fee' is implausible given customer's role "
            "as awarding authority (conflict-of-interest at minimum, gratification offence "
            "at worst per UU Tipikor 1999 / 2001). Subsequent fan-out layering across spouse, "
            "child, offshore investment account, and a property escrow — classic UU TPPU "
            "Article 2 corruption-proceeds layering pattern documented in PPATK Tipologi KKN. "
            "Customer's PEP-adjacent risk rating triggered the bank's transaction-monitoring "
            "rule for procurement-counterparty inflows; EDD threshold breached on the "
            "first inbound."
        ),
        "analyst_notes": (
            "Bank's compliance function escalated to *Pejabat Penanggung Jawab APU-PPT* on "
            "2026-04-09 after BI-FAST monitoring rule fired on Day 1. EDD initiated: "
            "documentation requested for the consulting engagement underlying PT Karya "
            "Mandiri's IDR 1.25bn payment, including signed engagement letter, scope of "
            "work, deliverables. Customer produced a brief unsigned MoU dated 2026-03-15 "
            "(post-tender award) and could not articulate deliverables when asked. "
            "Tipping-off compliance under UU TPPU 2010 Article 12 maintained — EDD "
            "communication did not reference LTKM or PPATK. UU TPPU 2010 Article 2 "
            "predicate offence(s): corruption / KKN. Parallel KPK interest highly likely "
            "given the public-procurement nexus. Recommend LTKM filing to PPATK via GRIPS + "
            "internal hold on remaining customer funds + flag spouse and adult-child "
            "accounts for connected-party EDD + escalate to bank's Group Head of FCC for "
            "consideration of formal customer-relationship termination subject to UU TPPU "
            "tipping-off restrictions. PPATK ordinarily channels KKN cases to KPK via "
            "PPATK-direct disclosure rather than the bank disclosing to KPK."
        ),
    },
    "Indonesia (PPATK) — Crypto Pedagang Aset Kripto mule": {
        "customer_name": "Ms Siti Nurhaliza",
        "customer_id": "BAPPEBTI-PAK-ID-2026-04-CUST-4072",
        "customer_kyc": (
            "Indonesian national, Surabaya-resident retail customer of a Bappebti-registered "
            "crypto-asset trader (Pedagang Aset Kripto — PAK). Declared occupation: online "
            "marketplace seller. Declared monthly turnover: IDR 18,000,000. Account opened "
            "2025-11; previous activity consistent with small Tokocrypto / Indodax buys "
            "(~IDR 2-5m / month). Risk rating: Low at onboarding, no PEP, no sanctions hit."
        ),
        "transactions": (
            "2026-04-15 | IDR 480,000,000 inbound | OVO wallet from 'Asuransi Konsultan Pemulihan' (unverified counterparty)\n"
            "2026-04-15 | IDR 470,000,000 USDT purchase | on-ramp via Pedagang Aset Kripto\n"
            "2026-04-15 | 31,000 USDT outbound | TRC-20 to external wallet (Cambodia exchange-cluster KYT hit)\n"
            "2026-04-17 | IDR 520,000,000 inbound | DANA wallet from same 'Asuransi Konsultan Pemulihan'\n"
            "2026-04-17 | IDR 510,000,000 USDT purchase | on-ramp via Pedagang Aset Kripto\n"
            "2026-04-17 | 33,500 USDT outbound | TRC-20 to second Cambodia-cluster wallet\n"
            "Total: IDR 1bn in / out via crypto on-ramp + off-ramp in 3 days; <1% retention."
        ),
        "alert_reason": (
            "Inbound flow ~55x declared monthly turnover within 3 days; near-pass-through "
            "retention; off-ramp destination wallets KYT-tagged to Cambodia-cluster "
            "investment-scam off-ramp ring; counterparty matches PPATK Tipologi BCM "
            "investment-scam mule pattern."
        ),
        "red_flags": (
            "Pattern matches PPATK Tipologi BCM investment-scam mule profile: rapid "
            "in-then-out via PAK, near-zero retention, off-ramp destinations matching KYT "
            "vendor tags for Cambodia-based scam-cluster wallets (KYT vendor: Chainalysis "
            "+ TRM Labs cross-confirmation). Counterparty 'Asuransi Konsultan Pemulihan' "
            "(literally 'Insurance Recovery Consultant') unregistered with OJK; naming "
            "pattern matches PPATK 2026 advisory on advance-fee / recovery-scam mule "
            "recruitment via OJK-unregulated 'asuransi' branded entities. Customer's "
            "declared profile (online marketplace seller, IDR 18m/month) grossly "
            "inconsistent with IDR 1bn in 3 days. Two separate e-wallet on-ramp channels "
            "(OVO, DANA) used for same flow — consistent with mule cross-channel layering."
        ),
        "analyst_notes": (
            "PAK's compliance function flagged via the Chainalysis KYT alert on the first "
            "TRC-20 outbound (Cambodia-cluster KYT score 87). EDD initiated 2026-04-18: "
            "customer unable to explain source of inbound flows, named 'Asuransi Konsultan "
            "Pemulihan' but could not produce contracts, invoices, or contact details. "
            "Customer appeared confused — typical mule-victim profile (recruitment via "
            "Telegram / WhatsApp 'easy money' messaging). Tipping-off compliance under "
            "UU TPPU 2010 Article 12 maintained throughout EDD. UU TPPU 2010 Article 2 "
            "predicate offences: fraud + cybercrime + transnational money laundering. "
            "Recommend LTKM to PPATK via GRIPS + customer wallet hold + customer "
            "financial-literacy referral + flag the two Cambodia-cluster destination "
            "wallets to peer PAKs via Bappebti and PPATK information-sharing channels. "
            "Cross-flag OVO / DANA wallet IDs that funded the on-ramps for connected-party "
            "EDD by the originating e-money issuers under PBI 23/6/PBI/2021 obligations."
        ),
    },

    # ===== Japan (JAFIC) =====
    "Japan (JAFIC)": {
        "customer_name": "Mr Tanaka Hiroshi",
        "customer_id": "FSA-CB-JP-2026-04-CUST-58217",
        "customer_kyc": (
            "Japanese national, Tokyo-resident retail customer of a city bank "
            "(megabank — Mitsubishi UFJ-class). Declared occupation: retired "
            "company employee. Declared monthly pension income: JPY 280,000. "
            "Account opened 2018; activity through end-2025 consistent with "
            "pension deposit, household payments, and modest term-deposit "
            "rotations. Risk rating: Standard (no PEP, no foreign-resident "
            "trigger). Honnin Tokutei Jikō Kakunin (identity verification) "
            "via My Number Card on file."
        ),
        "transactions": (
            "2026-04-12 | inbound JPY 4,200,000 cash | over-counter deposit at branch | customer stated 'savings'\n"
            "2026-04-12 | outbound JPY 4,150,000 | Zengin wire to 'recovery support firm' (unverified counterparty) | customer counter to teller queries\n"
            "2026-04-15 | inbound JPY 3,800,000 cash | over-counter deposit (different branch) | customer stated 'savings'\n"
            "2026-04-15 | outbound JPY 3,750,000 | Zengin wire to a second 'consulting firm' counterparty\n"
            "2026-04-19 | inbound JPY 5,100,000 cash | over-counter deposit (third branch) | customer agitated, declined to detail purpose\n"
            "2026-04-19 | outbound JPY 5,050,000 | Zengin wire to a third counterparty"
        ),
        "alert_reason": (
            "Inbound cash 50x declared monthly pension across 7 days; rapid in-and-out "
            "with Zengin transfers to three unrelated 'recovery / consulting' firm "
            "counterparties; customer cycling across branches; pattern matches the "
            "JAFIC tokushu sagi (specialised fraud) mule-victim typology."
        ),
        "red_flags": (
            "Pattern matches JAFIC's *tokushu sagi* / *ore-ore* refund-scam mule-victim "
            "typology — elderly customer recruited by phone caller posing as 'tax-refund "
            "specialist' or 'It's me' relative needing emergency funds; customer is the "
            "victim, not the bad actor. Branch-rotation strongly suggestive of caller "
            "coaching to evade single-branch pattern recognition. Counterparty firms — "
            "'recovery support', 'consulting' — match published JAFIC reference cases. "
            "Customer's distressed demeanour and inability to explain the purpose of "
            "transfers is a typical victim-recognition red flag."
        ),
        "analyst_notes": (
            "Bank's transaction-monitoring rule fired on the second cash-deposit-then-"
            "Zengin-transfer cycle. Branch staff escalated to MLRO function on 2026-04-15. "
            "Customer outreach 2026-04-19 (after third cycle): customer initially evasive, "
            "eventually disclosed receiving phone calls from a person claiming to be a "
            "'tax bureau official' arranging a refund that required upfront payment of "
            "'processing fees'. Customer was not aware these were fraud transfers. "
            "Tipping-off compliance under APTCP Article 8(3) maintained — no reference "
            "to STR or JAFIC in initial customer communications. After customer "
            "recognition, branch initiated a victim-protection conversation in "
            "coordination with police. APTCP Act Article 8 STR obligation applies. "
            "Recommend STR + temporary account hold + customer-protection coordination "
            "with NPA *tokushu sagi* prevention unit + flag the three counterparty "
            "Zengin destination accounts to JBA inter-bank intelligence channel. "
            "JAFIC published reference cases on tokushu sagi mule-victim layering."
        ),
    },

    # ===== Korea (KoFIU) =====
    "Korea (KoFIU)": {
        "customer_name": "Ms Kim Min-ji",
        "customer_id": "FSC-CB-KR-2026-04-CUST-71803",
        "customer_kyc": (
            "Korean national, Seoul-resident retail customer of a tier-1 commercial "
            "bank (Shinhan / KB-class). Declared occupation: office worker. Declared "
            "monthly salary: KRW 3,800,000. Account opened 2022; activity through "
            "end-2025 consistent with salary deposit, household payments, KakaoPay / "
            "NaverPay e-wallet top-ups. Risk rating: Standard. Goegaek Hwakin "
            "(customer verification) via RRN + Driver Licence on file."
        ),
        "transactions": (
            "2026-04-08 | inbound KRW 18,000,000 | KFTC retail wire from 'Investment Recovery Center Inc' (unverified) | reference 'compensation refund'\n"
            "2026-04-08 | outbound KRW 17,800,000 | KRW-USDT on-ramp via Upbit (FTRA-registered VASP)\n"
            "2026-04-09 | outbound 12,800 USDT | TRC-20 to external wallet (Cambodia-cluster KYT score 91)\n"
            "2026-04-11 | inbound KRW 22,000,000 | KFTC retail wire from same 'Investment Recovery Center Inc'\n"
            "2026-04-11 | outbound KRW 21,750,000 | KRW-USDT on-ramp via Bithumb (FTRA-registered VASP)\n"
            "2026-04-11 | outbound 15,800 USDT | TRC-20 to second Cambodia-cluster wallet"
        ),
        "alert_reason": (
            "Inbound flow ~10x declared monthly salary in 4 days; near-pass-through "
            "retention; KRW-to-USDT on-ramp at two different FTRA-registered VASPs; "
            "destination wallets KYT-tagged to Cambodia-cluster scam-off-ramp ring; "
            "matches KoFIU voice-phishing-victim mule typology."
        ),
        "red_flags": (
            "Pattern matches KoFIU published *Sangye Sarye* (suspicious-pattern case) "
            "for voice-phishing (*boishu pishing*) victim mule activity: rapid in-and-"
            "out via VASP, near-zero retention, destinations tagged to Cambodia "
            "scam-cluster off-ramp wallets (Chainalysis + TRM Labs cross-confirmation). "
            "Counterparty 'Investment Recovery Center Inc' unregistered with FSC; naming "
            "pattern matches recent KoFIU advisory on advance-fee / recovery-scam mule "
            "recruitment. Customer's declared profile (office worker, KRW 3.8m / month) "
            "grossly inconsistent with KRW 40m in 4 days. Use of two separate "
            "FTRA-registered VASPs (Upbit + Bithumb) consistent with mule cross-"
            "platform layering pattern."
        ),
        "analyst_notes": (
            "Bank's transaction-monitoring rule fired on the first VASP on-ramp on "
            "2026-04-08. KoFIU's 2024 *Sangye Sarye* case set #2024-07 (Cambodia-"
            "cluster voice-phishing layering) flagged a near-identical fact pattern. "
            "Bank's *Junseo Tamdang Imja* (Compliance Officer) initiated EDD on "
            "2026-04-09: customer described receiving phone calls from someone "
            "claiming to be a 'prosecutor' investigating an alleged identity-theft "
            "case requiring 'temporary fund relocation for safekeeping'. Customer "
            "was unaware of being a victim of voice-phishing fraud. Tipping-off "
            "compliance under FTRA Article 12 maintained. FTRA Article 4 STR "
            "obligation applies; predicate offence: voice phishing under the "
            "Special Act on Voice Phishing + transnational money laundering. "
            "Recommend STR to KoFIU + temporary account hold + customer-protection "
            "coordination with FSS investor-protection bureau and Korean National "
            "Police Agency cyber bureau + flag the two destination wallet IDs to "
            "Upbit + Bithumb for cross-VASP travel-rule data exchange + parallel "
            "engagement with the Special Act on Voice Phishing rapid-freeze "
            "framework. Cambodia-cluster off-ramp wallets cross-flagged to KoFIU "
            "for international-cooperation channels with Cambodia FIU."
        ),
    },

    # ===== New Zealand (FIU NZ) =====
    "New Zealand (FIU NZ)": {
        "customer_name": "Pacific Sunrise Holdings Ltd",
        "customer_id": "DIA-RE-NZ-2026-04-CUST-2104",
        "customer_kyc": (
            "NZ-incorporated company, registered Auckland, beneficial owner declared "
            "as Mr Wei Liu (Chinese national, no NZ residency, Hong Kong primary "
            "address). Declared business activity: 'investment company'. NZBN obtained "
            "2026-02. Account-equivalent relationship is with a DIA-supervised "
            "Auckland real-estate agency (the reporting entity). Standard CDD under "
            "AML/CFT Act s.14 conducted at engagement; EDD under s.22 triggered at "
            "purchase price + cross-border-funds source."
        ),
        "transactions": (
            "2026-04-08 | Buyer-side purchase agreement signed | Mosman-style Remuera waterfront residence | NZD 9,800,000\n"
            "2026-04-12 | Initial deposit NZD 980,000 | wire from HK-based 'family office' account (not in customer's name) | source-of-funds documentation requested\n"
            "2026-04-15 | Settlement scheduled | balance NZD 8,820,000 to settle via solicitor's trust account\n"
            "2026-04-15 | EDD documentation requested but not produced | customer counsel cited 'commercial confidentiality of source-of-wealth'\n"
            "2026-04-18 | PTR (NZD 1,000+ international wire) filed for 980k deposit; SAR consideration triggered"
        ),
        "alert_reason": (
            "Auckland waterfront purchase 18% above CoreLogic comparable; deposit wire "
            "from non-customer-name 'family office' in Hong Kong; UBO chain has "
            "undocumented 'family wealth from agriculture' source-of-wealth claim; "
            "EDD source-of-funds documentation declined. Pattern matches FIU NZ "
            "Auckland real-estate cash-buyer typology."
        ),
        "red_flags": (
            "Customer is a NZ shell company incorporated 2 months before purchase, "
            "with foreign-resident UBO. Deposit funded from a third-party HK 'family "
            "office' account, not the customer's or the UBO's named account. UBO's "
            "declared source of wealth — 'family wealth from agriculture' — produced "
            "no supporting documentation (bank statements, tax records, sale-of-"
            "business records). Purchase price 18% above recent CoreLogic comparable "
            "for Remuera waterfront properties. Customer counsel's invocation of "
            "'commercial confidentiality' for source-of-wealth is a recognised "
            "FIU NZ red-flag indicator under the Auckland real-estate-cash-buyer "
            "typology. Pattern matches FIU NZ 2025 *Quarterly Typology Report* on "
            "high-value-property layering via NZ-incorporated shell."
        ),
        "analyst_notes": (
            "Real-estate agency is DIA-supervised under the AML/CFT Act 2009. "
            "Standard CDD on the customer (NZ-incorporated company with foreign UBO) "
            "triggered s.22 EDD given the high-value-property + cross-border-funds "
            "+ recent-incorporation profile. EDD documentation requests met with "
            "non-cooperation. Solicitor (also a DIA-supervised reporting entity) "
            "received the trust-account settlement instructions and identified "
            "parallel red flags under their own AML/CFT programme. PTR filed for "
            "the 980k deposit (international wire ≥ NZD 1,000 threshold). "
            "Tipping-off compliance under s.46 maintained throughout — customer "
            "communications referenced only standard CDD requirements. Crimes Act "
            "s.243 money-laundering offence and Tax Administration Act tax-evasion "
            "offence are the most likely predicate offence anchors. Recommend SAR "
            "to FIU NZ via goAML within the 3-working-day window + suspension of "
            "the agency's involvement in the transaction (subject to commercial "
            "and contractual considerations) + flag the HK 'family office' "
            "originator account to the agency's correspondent bank for inter-"
            "institution intelligence. Coordinated SAR with the customer's "
            "solicitor expected. FIU NZ's *Quarterly Typology Reports* reference "
            "this pattern in the Auckland-Queenstown high-value-property series."
        ),
    },

    # ===================================================================
    # Japan (JAFIC) — additional 3 sample cases
    # ===================================================================
    "Japan (JAFIC) — CAESP USDT layering": {
        "customer_name": "Mr Sato Kenji",
        "customer_id": "FSA-CAESP-JP-2026-04-CUST-91204",
        "customer_kyc": (
            "Japanese national, Osaka-resident retail customer of an "
            "FSA-registered Crypto-Asset Exchange Service Provider "
            "(*Anshō Kōkan-gyōsha*) — bitFlyer-class. Declared occupation: "
            "self-employed e-commerce seller. Declared monthly income: "
            "JPY 600,000. Account opened 2024 with CAESP-tier-2 KYC "
            "(My Number Card + selfie liveness). Risk rating: Standard. "
            "Expected profile: retail crypto trading, sub-JPY 2m monthly."
        ),
        "transactions": (
            "2026-04-12 | inbound JPY 8,400,000 | Zengin wire from 'consulting fees' counterparty (unverified) | retail JPY deposit\n"
            "2026-04-12 | converted JPY 8,300,000 to 56,200 USDT (TRC-20) | spot order book\n"
            "2026-04-13 | outbound 56,000 USDT | TRC-20 to external wallet TKb...x9q (KYT score 87, mixer-cluster tagged)\n"
            "2026-04-15 | inbound JPY 9,200,000 | second Zengin wire from same counterparty\n"
            "2026-04-15 | converted JPY 9,100,000 to 61,500 USDT\n"
            "2026-04-15 | outbound 61,200 USDT | TRC-20 to second mixer-cluster wallet"
        ),
        "alert_reason": (
            "Inbound flow 14× declared monthly income; rapid JPY-to-USDT conversion "
            "with near-zero retention; destination wallets KYT-tagged to mixer-"
            "cluster ring. Pattern matches FSA Crypto-Asset Exchange AML/CFT "
            "Guideline tokushu sagi crypto-cash-out typology."
        ),
        "red_flags": (
            "Pattern matches FSA's 2024 published reference case on tokushu sagi "
            "(specialised fraud) crypto-cash-out: rapid Zengin in, JPY-to-USDT, "
            "TRC-20 out to mixer-cluster wallets. Counterparty 'consulting fees' "
            "naming pattern matches JAFIC Sankō Jirei tokushu sagi recruiter "
            "indicia. Customer's declared profile (e-commerce, JPY 600k/month) "
            "grossly inconsistent with JPY 17.6m in 4 days. KYT scores 87 on "
            "both destination wallets (Chainalysis + TRM cross-confirmation) "
            "indicate Hydra-successor mixer cluster."
        ),
        "analyst_notes": (
            "CAESP's TM rule fired on the second JPY-to-USDT conversion cycle. "
            "Customer outreach 2026-04-15 (after second cycle): customer evasive, "
            "claimed JPY transfers were 'consulting fees from a referred client'. "
            "EDD documentation declined under 'commercial confidentiality'. "
            "Tipping-off compliance under APTCP Article 8(3) maintained throughout. "
            "FSA Crypto-Asset Exchange Service Provider AML/CFT Guidelines apply "
            "in addition to APTCP Article 8 STR. Recommend STR to JAFIC + temporary "
            "account freeze + flag the two TRC-20 destination wallets to JVCEA "
            "industry-association cross-VASP intelligence channel + parallel "
            "engagement with NPA Cyber Bureau on the mixer-cluster destination "
            "addresses. Cross-flag the originating Zengin counterparty to JBA "
            "intelligence."
        ),
    },

    "Japan (JAFIC) — Real estate cash buyer": {
        "customer_name": "Tokyo Heritage Trading Co Ltd (株式会社東京遺産通商)",
        "customer_id": "METI-RE-JP-2026-CUST-1843",
        "customer_kyc": (
            "Japan-incorporated trading company, registered Tokyo Minato-ku "
            "(Hōjin Bangō: 8013301042371). Beneficial owner declared as Mr "
            "Aleksandr V., Russian national, no Japanese residency. Declared "
            "business activity: 'commodity trading'. Account-equivalent "
            "relationship is with a METI-supervised real-estate agency in "
            "Tokyo. CDD performed at engagement; EDD requested at the "
            "purchase-price + foreign-UBO + cross-border-funds trigger."
        ),
        "transactions": (
            "2026-04-08 | Buyer-side purchase agreement signed | Minato-ku Roppongi luxury condominium | JPY 480,000,000 (~4.8 oku-en)\n"
            "2026-04-12 | Initial deposit JPY 48,000,000 | wire from Cyprus-based 'family office' account (not in customer's name)\n"
            "2026-04-15 | Settlement scheduled | balance JPY 432,000,000 via shihō shoshi escrow\n"
            "2026-04-16 | EDD source-of-wealth documentation declined | customer counsel cited 'commercial confidentiality'"
        ),
        "alert_reason": (
            "Roppongi luxury-condo purchase 22% above recent comparable transactions; "
            "deposit wire from non-customer-name Cyprus 'family office'; UBO chain "
            "has Russian-domiciled prior business with sanctions-adjacent profile. "
            "Pattern matches JAFIC published reference case on real-estate "
            "high-value-property layering by foreign UBO."
        ),
        "red_flags": (
            "Customer is a Japanese shell company incorporated 4 months before the "
            "purchase, with foreign-resident UBO. Deposit funded from a third-party "
            "Cyprus 'family office' account, not the customer's or the UBO's named "
            "account. UBO Mr Aleksandr V. previously domiciled in Russia until "
            "2023; declared source of wealth ('commodity trading from family business') "
            "produced no supporting documentation. Purchase price 22% above recent "
            "Minato Roppongi comparables. METI 2024 real-estate AML guidelines list "
            "all of these as red-flag indicators. Sanctions-screening of the Cyprus "
            "originator account flagged 'partial match' with EU-listed sanctioned "
            "intermediary; warrants escalation."
        ),
        "analyst_notes": (
            "Real-estate agency is METI-supervised under APTCP Article 2. EDD trigger "
            "at the high-value + foreign-UBO + cross-border-funds combination. EDD "
            "documentation requests met with non-cooperation. Shihō shoshi (judicial "
            "scrivener) handling the escrow has filed parallel concerns under their "
            "own APTCP obligations. Tipping-off compliance under Article 8(3) "
            "maintained — customer communications referenced only standard CDD "
            "requirements. Sotaihō predicate offences (organised-crime layering and "
            "tax evasion) and FEFTA cross-border notification both apply. Recommend "
            "STR to JAFIC + suspension of agency involvement (subject to commercial "
            "considerations) + flag the Cyprus 'family office' originator to the "
            "agency's correspondent bank for MOF-FEFTA notification + coordinated "
            "STR with the shihō shoshi. Sanctions desk escalation to METI parallel "
            "track. Pattern matches JAFIC reference cases on Tokyo high-value-"
            "property layering by foreign UBO."
        ),
    },

    "Japan (JAFIC) — Shikin Ido DPRK corridor": {
        "customer_name": "Pacific Trade Solutions GK",
        "customer_id": "FSA-SI-JP-2026-CUST-3902",
        "customer_kyc": (
            "Japan-registered Goudou Gaisha (合同会社), incorporated 2024 Q3, "
            "registered Yokohama. Beneficial owner declared as Mr Kim T., "
            "naturalised Japanese citizen of Korean ethnic origin (Zainichi). "
            "Declared business: 'Pacific commodity exports'. Reporting "
            "institution is an FSA-licensed Funds-Transfer Service Provider "
            "(*Shikin Idō-gyōsha*). CDD onboarding April 2025, no flags."
        ),
        "transactions": (
            "2026-04-10 | inbound JPY 28,000,000 | aggregated from 6 separate Tokyo retail counterparties (each ~JPY 4.5m)\n"
            "2026-04-11 | outbound JPY 27,800,000 | Shikin Idō wire to a Dalian (PRC) trading company beneficiary | reference 'commodity prepayment'\n"
            "2026-04-15 | inbound JPY 31,000,000 | aggregated from 7 Tokyo retail counterparties\n"
            "2026-04-15 | outbound JPY 30,800,000 | Shikin Idō wire to second Dalian trading company\n"
            "2026-04-19 | inbound JPY 22,500,000 | aggregated from 5 retail counterparties\n"
            "2026-04-19 | outbound JPY 22,400,000 | Shikin Idō wire to a Vladivostok (Russia) trading company | reference 'oil products advance'"
        ),
        "alert_reason": (
            "Repeating aggregation-then-outbound pattern with PRC and Russia "
            "beneficiaries; aggregation counterparties are all Tokyo retail "
            "individuals; reference fields identical 'commodity prepayment' / "
            "'oil products advance'. Pattern matches JAFIC + UN Panel of Experts "
            "DPRK sanctions-evasion typology — Zainichi-network remittance via "
            "Dalian/Vladivostok front companies."
        ),
        "red_flags": (
            "Aggregation-then-outbound pattern with international destinations is "
            "high-risk under FATF Recommendation 16. Beneficiary trading companies "
            "in Dalian and Vladivostok are well-documented in UN Panel of Experts "
            "reports as DPRK sanctions-evasion conduits. Aggregation counterparties "
            "(13 retail individuals across 9 days) appear coordinated — same "
            "transfer-amount tier, same reference language, same window. Customer's "
            "declared 'Pacific commodity exports' is inconsistent with the volume, "
            "velocity, and the specific Dalian-Vladivostok corridor. Mr Kim T.'s "
            "Zainichi ethnic-Korean profile is itself not a red flag, but combined "
            "with the corridor and counterparty profile is consistent with "
            "JAFIC-published DPRK-sanctions-evasion typology."
        ),
        "analyst_notes": (
            "TM fired on the third aggregation-then-outbound cycle. EDD requested "
            "2026-04-19. Customer counsel asserted commercial confidentiality and "
            "declined to produce trade documentation. Tipping-off compliance under "
            "Article 8(3) maintained. Recommend immediate STR to JAFIC + immediate "
            "outbound-transaction freeze + parallel notification to MOF/Customs "
            "under FEFTA's North Korea sanctions framework + parallel notification "
            "to NPA Public Security Bureau (organised-crime division). UN "
            "Resolution 1718/2270 sanctions framework potentially applicable; if "
            "any beneficiary entity is on the UN consolidated list, asset-freeze "
            "obligations under Foreign Exchange and Foreign Trade Act apply "
            "immediately and override commercial considerations. Coordinate "
            "via JAFIC for international-cooperation channels with PRC and Russia "
            "FIU equivalents. Sotaihō organised-crime predicate and Public "
            "Intimidation Crimes Financing Act predicate both potentially apply."
        ),
    },

    # ===================================================================
    # Korea (KoFIU) — additional 3 sample cases
    # ===================================================================
    "Korea (KoFIU) — VASP DPRK Lazarus": {
        "customer_name": "Mr Park Jung-Soo",
        "customer_id": "FTRA-VASP-KR-2026-CUST-44519",
        "customer_kyc": (
            "Korean national, Seoul-resident, customer of an FTRA-registered "
            "tier-1 VASP (Upbit / Bithumb-class). Declared occupation: "
            "self-employed software developer. Declared monthly income KRW "
            "8,000,000. Account opened 2023; uses Real-Name Verification "
            "Account (Sushin Hwakin Gyejwa) at NH Bank. Risk rating: Medium."
        ),
        "transactions": (
            "2026-04-08 | inbound 4.2 BTC (~KRW 380,000,000) | external wallet bc1q...m4n (Chainalysis tag: 'Lazarus Group cluster')\n"
            "2026-04-08 | converted 4.2 BTC to KRW 378,000,000 | spot order book\n"
            "2026-04-09 | outbound KRW 376,000,000 | KFTC wire to NH Bank account in customer's name\n"
            "2026-04-09 | outbound KRW 200,000,000 | structured KRW withdrawals to four third-party Korean accounts (KRW 50m each)\n"
            "2026-04-12 | inbound 3.8 BTC | second external wallet (KYT score 95; flagged North Korea exposure)\n"
            "2026-04-12 | similar conversion + structured withdrawal pattern"
        ),
        "alert_reason": (
            "Inbound BTC tagged by Chainalysis and TRM Labs as 'Lazarus Group "
            "cluster' (DPRK state-sponsored cybercrime); structured withdrawal "
            "to multiple third-party KRW accounts; pattern matches KoFIU + FSC "
            "2025 advisory on DPRK-Lazarus crypto-laundering."
        ),
        "red_flags": (
            "Inbound wallets tagged by both Chainalysis and TRM Labs as Lazarus "
            "Group cluster — DPRK state-sponsored APT group well-documented in "
            "UN Panel of Experts reports. Lazarus crypto-theft proceeds typically "
            "laundered through East Asian VASPs (Korea, Japan, Singapore) before "
            "off-ramp. Customer's structured KRW withdrawal pattern (KRW 50m "
            "tranches just under the KRW 100m KFTC scrutiny threshold) is "
            "classic Lazarus-cohort layering. Customer profile (software "
            "developer) ostensibly plausible for crypto holding but the volume "
            "(KRW 800m+ in a week) is grossly inconsistent. KoFIU advisory "
            "issued Q4 2025 specifically addresses this typology."
        ),
        "analyst_notes": (
            "VASP's KYT auto-flagged the first inbound wallet within 90 seconds "
            "of confirmation. Junseo Tamdang Imja escalated immediately. NIS "
            "(National Intelligence Service) and KoFIU coordination protocol "
            "engaged given DPRK nexus. Tipping-off under FTRA Article 12 "
            "maintained. FTRA Article 4 STR obligation crystallised on KYT "
            "alert; immediate filing required (not 30-day window). Asset freeze "
            "under domestic sanctions regulation activated on the NH Bank "
            "downstream account. Recommend STR + immediate freeze + FSC notification "
            "+ NIS coordination + cross-VASP travel-rule data exchange to flag "
            "the four KRW destination accounts to peer Korean banks. Korean "
            "Bar Association referral if any of the third-party recipient "
            "accounts belongs to a 변호사 (lawyer). UN Resolution 1718/2270 "
            "sanctions framework applies; do not engage with customer outside "
            "of NIS-coordinated channels."
        ),
    },

    "Korea (KoFIU) — Casino chip-walking": {
        "customer_name": "Mr Lee Han-Suk",
        "customer_id": "FTRA-CASINO-KR-2026-CUST-12087",
        "customer_kyc": (
            "Korean national, Seoul-resident, regular customer of Kangwon "
            "Land casino (the only foreigner-and-Korean casino in Korea; "
            "FTRA-registered). Declared occupation: senior corporate "
            "executive. Declared annual income KRW 200,000,000. Customer "
            "in 'high-roller' tier; risk rating: High at onboarding."
        ),
        "transactions": (
            "2026-04-08 | cash buy-in KRW 150,000,000 | over-counter at cage\n"
            "2026-04-08 | minimal table play (~10% of buy-in) | departed with KRW 135,000,000 in chips\n"
            "2026-04-09 | re-entered casino | attempted to redeem KRW 135,000,000 chips for cash\n"
            "2026-04-09 | also visited Paradise Walker Hill (Seoul) — chips stamped from Kangwon Land redeemed for KRW 50,000,000 cash + KRW 85,000,000 cashier's cheque\n"
            "2026-04-12 | repeat cycle: KRW 200,000,000 buy-in at Kangwon Land, minimal play, redemption split across Paradise + Grand Korea Leisure properties"
        ),
        "alert_reason": (
            "Classic chip-walking: large cash buy-in, minimal play, redemption "
            "across multiple FTRA-registered casinos. Pattern designed to "
            "convert cash to casino-issued cashier's cheques without genuine "
            "gambling, evading the cash-source explanation."
        ),
        "red_flags": (
            "Buy-in to play ratio of ~10% is the signature chip-walking indicator. "
            "Cross-property redemption (Kangwon Land chips redeemed at Paradise / "
            "Grand Korea Leisure) is a layering technique to break the audit "
            "trail. Cashier's-cheque redemption is the laundering objective: a "
            "casino-issued instrument with no source-of-funds question. KoFIU's "
            "2024 published Sangye Sarye case set explicitly addresses this "
            "pattern. Customer's declared KRW 200m annual income inconsistent "
            "with KRW 350m+ across two days. Chip-walking is also a recognised "
            "predicate-offence indicator under the Concealment of Criminal "
            "Proceeds Act (Article 3 — concealment via gambling instruments)."
        ),
        "analyst_notes": (
            "Kangwon Land's TM fired on the second cycle. Cross-property "
            "intelligence shared via FTRA-mandated casino-industry information-"
            "sharing channel. EDD requested 2026-04-13; customer claimed "
            "'switching strategies' but produced no source-of-funds for the "
            "buy-in cash. Tipping-off under FTRA Article 12 maintained. "
            "Recommend coordinated STR to KoFIU + cross-casino freeze on the "
            "customer's player accounts at all three properties + FIU "
            "intelligence-sharing with the customer's bank for KRW 100m+ "
            "deposit pattern review. KoFIU + FSC Casino-Sector AML Guidelines "
            "apply. Article 9 safe-harbour invoked. Coordinate with Korean "
            "National Police Agency (Casino Crimes Unit) on potential predicate "
            "offence — illegal gambling proceeds layering or tax evasion."
        ),
    },

    "Korea (KoFIU) — E-money illegal pyramid": {
        "customer_name": "Ms Choi Soo-Yeon",
        "customer_id": "FTRA-EMI-KR-2026-CUST-78231",
        "customer_kyc": (
            "Korean national, Busan-resident, e-wallet customer of a major "
            "FSC-licensed e-money issuer (KakaoPay / NaverPay / Toss-class; "
            "FTRA Bogo Gigwan). Declared occupation: small-business owner. "
            "Declared monthly income KRW 5,000,000. Account opened 2024."
        ),
        "transactions": (
            "2026-04-08 | inbound KRW 320,000,000 | aggregated across 47 micro-deposits from 47 unique senders (each KRW 4.5–8m)\n"
            "2026-04-08 | outbound KRW 318,000,000 | bulk withdrawal to single bank account (Hana Bank) in customer's name\n"
            "2026-04-12 | repeat: KRW 410,000,000 inbound from 62 micro-senders, bulk withdrawal\n"
            "2026-04-15 | repeat: KRW 380,000,000 inbound from 55 micro-senders, bulk withdrawal\n"
            "Most senders' e-wallet KYC profiles share a common 'investment opportunity' onboarding code"
        ),
        "alert_reason": (
            "Aggregation pattern from many small senders into a single beneficiary "
            "with bulk withdrawal — classic illegal-pyramid (*bul-beob piramideu*) "
            "operator-tier layering. Senders share a common onboarding code "
            "indicating coordinated recruitment."
        ),
        "red_flags": (
            "Pattern matches KoFIU 2025 advisory on illegal-pyramid scheme "
            "operator-tier layering — operator collects from recruits via "
            "e-wallet (low scrutiny), then bulk-withdraws to a clean bank "
            "account. Senders' shared onboarding-code field is a strong "
            "indicator of coordinated MLM recruitment, which under Korean "
            "law (Door-to-Door Sales Act and Multi-Level Marketing Act) is "
            "criminal where the scheme has no genuine product. Customer's "
            "declared KRW 5m monthly income inconsistent with KRW 1.1bn+ in "
            "a week. EMI customer-service tickets reveal complaints from "
            "two senders alleging being unable to recruit further, "
            "consistent with the typical pyramid-collapse stage."
        ),
        "analyst_notes": (
            "EMI's TM fired on the second aggregation cycle. Sender-graph "
            "analysis showed a recruitment tree consistent with multi-level "
            "marketing pyramid. Customer outreach 2026-04-15: customer "
            "claimed 'investment club organising' but produced no documents. "
            "EDD declined. Tipping-off under FTRA Article 12 maintained. "
            "Recommend STR to KoFIU + immediate e-wallet freeze + Hana "
            "Bank cross-flag for KRW 1.1bn deposit review + FSC investor-"
            "protection bureau notification + Korean National Police Agency "
            "(Economic Crimes Unit) referral for illegal-pyramid prosecution. "
            "Under FTRA Article 5-2's e-money provisions, victim "
            "identification protocols apply to the recruited senders — many "
            "of whom are also victims, not perpetrators. Coordinated approach "
            "via the FSC's special pyramid-scheme rapid-response framework."
        ),
    },

    # ===================================================================
    # New Zealand (FIU NZ) — additional 3 sample cases
    # ===================================================================
    "New Zealand (FIU NZ) — Bank investment-scam mule": {
        "customer_name": "Mrs Margaret Wilson",
        "customer_id": "RBNZ-NZ-2026-CUST-58420",
        "customer_kyc": (
            "New Zealand citizen, Auckland-resident, retired (age 68). "
            "Customer of an RBNZ-supervised registered bank (ANZ / ASB / "
            "BNZ / Westpac / Kiwibank-class) for over 20 years. Income "
            "primarily NZ Superannuation + modest dividend income. "
            "Account profile through Q1 2026: routine pension deposit, "
            "household payments. Risk rating: Low."
        ),
        "transactions": (
            "2026-04-08 | outbound NZD 180,000 | international wire to a Singapore-based 'investment platform' beneficiary (unverified)\n"
            "2026-04-12 | outbound NZD 220,000 | second wire to same Singapore beneficiary, reference 'top-up investment'\n"
            "2026-04-15 | outbound NZD 95,000 | third wire — different Singapore beneficiary, customer claimed 'platform recovery fee'\n"
            "Customer's source-of-funds: drained term deposit (NZD 320,000) + remortgage on principal residence (NZD 250,000)"
        ),
        "alert_reason": (
            "Three large international outbounds in 8 days, totalling NZD "
            "495,000, from a customer with no prior international-wire history. "
            "Funded by drained term deposit + remortgage. Beneficiary 'investment "
            "platform' unverifiable. Pattern matches FIU NZ Quarterly Typology "
            "Report on investment-scam victim mule activity (the customer is "
            "the victim, not the bad actor)."
        ),
        "red_flags": (
            "FIU NZ's 2025 Quarterly Typology Report documents this exact pattern: "
            "elderly New Zealander, contacted by phone or messaging-app "
            "purporting to offer 'high-yield investment opportunity' on a "
            "Singapore-based platform; customer drains savings + remortgages; "
            "subsequent transfers escalate as 'recovery fees' or 'platform "
            "tax' are demanded. Customer's pension-only income inconsistent "
            "with NZD 495,000 in 8 days. Remortgage of principal residence to "
            "fund foreign 'investment' is the signature investment-scam-victim "
            "indicator. Source: FIU NZ AML/CFT Q3 2025 Typology Report."
        ),
        "analyst_notes": (
            "Bank's TM fired on the second wire (which exceeded the customer's "
            "lifetime international-wire profile). Branch contact 2026-04-15 "
            "during the third wire request. Customer initially defensive — "
            "described the platform in terms suggestive of scam coaching "
            "('they said the bank wouldn't understand the opportunity'). "
            "Branch escalated to AML/CFT Compliance Officer; investor-"
            "protection conversation initiated in coordination with the SFO "
            "Financial Crime Unit. Tipping-off compliance under s.46 maintained. "
            "Recommend SAR + PTR (the international wires exceed NZD 1,000 "
            "threshold) + customer-protection conversation in coordination with "
            "Police FCG (Financial Crimes Group) + cross-flag the two Singapore "
            "beneficiary accounts to MAS / STRO via FIU-to-FIU information-"
            "sharing channel. Bank's wider customer base reviewed for similar "
            "pattern; two additional potential victims identified and surfaced. "
            "AML/CFT Act s.40 SAR obligation applies."
        ),
    },

    "New Zealand (FIU NZ) — SkyCity chip-walking": {
        "customer_name": "Mr Robert Tan",
        "customer_id": "DIA-CASINO-NZ-2026-CUST-7041",
        "customer_kyc": (
            "Singaporean citizen, Auckland-visiting customer of SkyCity "
            "Auckland (DIA-supervised under AML/CFT Act). High-roller tier. "
            "Declared occupation: 'investment manager'. CDD on file from "
            "2024 visit; EDD triggered at the high-value-cash-buy-in level."
        ),
        "transactions": (
            "2026-04-08 | cash buy-in NZD 250,000 | over-counter at SkyCity Auckland cage\n"
            "2026-04-08 | minimal table play (~12%) | departed with NZD 220,000 chips\n"
            "2026-04-09 | redeemed NZD 100,000 chips for cash; NZD 120,000 redeemed for SkyCity cashier's cheque\n"
            "2026-04-10 | flew to Queenstown; visited SkyCity Queenstown casino\n"
            "2026-04-10 | second cycle: NZD 200,000 buy-in, minimal play, NZD 175,000 redemption (cash + cheque mix)"
        ),
        "alert_reason": (
            "Cross-property chip-walking: large cash buy-in, minimal play, "
            "redemption mix of cash + cashier's cheque, repeated across "
            "multiple SkyCity properties. Foreign-resident high-roller "
            "indicia. Pattern matches FIU NZ Q1 2026 Auckland-Queenstown "
            "high-value-property typology variant."
        ),
        "red_flags": (
            "Buy-in-to-play ratio ~12% is the signature chip-walking pattern. "
            "Cross-property redemption (Auckland chips → Queenstown buy-in) "
            "is a layering technique. Cashier's-cheque redemption is the "
            "laundering objective: an instrument with no source-of-funds "
            "question. Foreign UBO (Singapore) raises the cross-border-"
            "layering profile. Casino's own EDD attempted source-of-wealth "
            "documentation but customer declined ('investment manager — "
            "professional discretion'). Pattern matches FIU NZ Q1 2026 "
            "thematic finding on SkyCity-Queenstown corridor abuse — "
            "mirror of the established Macau / NSW casino layering "
            "typologies but using NZ as the layering jurisdiction."
        ),
        "analyst_notes": (
            "SkyCity's TM fired on the second-property buy-in. Cross-property "
            "intelligence shared via DIA-supervised casino-industry channel. "
            "EDD documentation declined. Tipping-off under s.46 maintained. "
            "Recommend coordinated SAR to FIU NZ via goAML + PTR for any "
            "cash redemption ≥ NZD 10,000 + cross-property freeze on player "
            "account + FIU-to-FIU information sharing with MAS / STRO "
            "(Singapore beneficiary jurisdiction) + DIA notification of "
            "the typological finding for sectoral intelligence. AML/CFT Act "
            "s.40 SAR obligation applies. s.45 safe-harbour invoked. "
            "DIA Casino-Sector AML/CFT Guidelines specifically address this "
            "pattern; align operational response."
        ),
    },

    "New Zealand (FIU NZ) — Lawyer trust account": {
        "customer_name": "Pacific Edge Legal Trust Account (Wallace & Co Solicitors)",
        "customer_id": "DIA-LAW-NZ-2026-CUST-2901",
        "customer_kyc": (
            "Auckland-based law firm trust account, DIA-supervised reporting "
            "entity under the AML/CFT Act 2009. The 'customer' for AML "
            "purposes is the underlying client of the firm — Mr Aleksey K., "
            "Russian national, NZ residency since 2024. Firm conducting "
            "'commercial property and corporate-structuring' work for Mr "
            "Aleksey K. since January 2026. Standard CDD performed at "
            "engagement; EDD triggered at the cross-border-funds + Russian-"
            "national + corporate-structuring profile."
        ),
        "transactions": (
            "2026-04-08 | inbound NZD 1,200,000 | wire from Cyprus 'family office' to firm trust account, designated for 'commercial property purchase'\n"
            "2026-04-09 | outbound NZD 350,000 | from trust account to a NZ-incorporated shell (NZ Co A) controlled by Mr Aleksey K.\n"
            "2026-04-10 | outbound NZD 280,000 | to NZ-incorporated shell (NZ Co B) — newly incorporated 6 weeks earlier\n"
            "2026-04-12 | outbound NZD 400,000 | to a third NZ shell (NZ Co C) | reference 'capital injection'\n"
            "2026-04-15 | balance NZD 170,000 | client requested return to Cyprus 'family office' with no associated property purchase"
        ),
        "alert_reason": (
            "Trust-account pass-through with no clear commercial purpose: "
            "funds split across three newly-incorporated NZ shell companies, "
            "with residual returned to source. Pattern matches FATF DNFBP "
            "indicators for legal/professional involvement in layering."
        ),
        "red_flags": (
            "Classic 'lawyer-trust-account-as-layering-vehicle' typology. "
            "FATF Recommendation 22 contemplates exactly this risk; AML/CFT "
            "Act 2009 captures lawyers and conveyancers under DIA supervision "
            "to address it. Funds routed via Cyprus 'family office' (well-"
            "documented sanctions / opacity-jurisdiction concern), split "
            "across three NZ shell entities (NZ Co A/B/C) all newly "
            "incorporated and all controlled by the same UBO, then balance "
            "returned to source — no economic substance whatsoever. Mr "
            "Aleksey K.'s Russian-national profile + 2024 NZ-residency "
            "transition + Cyprus funds-source warrants enhanced sanctions "
            "screening. Originator account flagged 'partial match' against "
            "EU 11th-package sanctioned individual."
        ),
        "analyst_notes": (
            "Firm's AML/CFT Compliance Officer (s.56 nominee) escalated on "
            "the third outbound. EDD requested 2026-04-12; client counsel "
            "asserted 'commercial confidentiality and legal-professional "
            "privilege'. Firm's legal-ethics review concluded that AML/CFT "
            "Act s.40 SAR obligation overrides claimed privilege for the "
            "transactional facts (privilege does not extend to facts of "
            "transactions). Tipping-off under s.46 maintained. Recommend "
            "SAR to FIU NZ + immediate cessation of further trust-account "
            "transactions for this client + coordinated SAR with the "
            "Auckland branch of the firm's correspondent bank (BNZ) on the "
            "Cyprus originator account + EU sanctions desk parallel "
            "notification under the Russia Sanctions Regulations 2022. "
            "DIA Lawyer-Sector AML/CFT Guidelines specifically address "
            "trust-account-pass-through layering. NZ Law Society professional-"
            "conduct review will be triggered if the SAR is filed; firm "
            "partners briefed accordingly. Crimes Act ss.243-245 money-"
            "laundering offence and Tax Administration Act tax-evasion "
            "offence are the most likely predicate-offence anchors."
        ),
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
    "Philippines (AMLC)": ("AMLC Portal", "https://www.amlc.gov.ph/"),
    "Indonesia (PPATK)": ("GRIPS (PPATK reporting portal)", "https://www.ppatk.go.id/"),
    "Japan (JAFIC)": ("JAFIC online portal (NPA)", "https://www.npa.go.jp/sosikihanzai/jafic/"),
    "Korea (KoFIU)": ("KoFIU electronic reporting (FSC)", "https://www.kofiu.go.kr/"),
    "Australia (AUSTRAC SMR)": ("AUSTRAC Online", "https://online.austrac.gov.au/"),
    "New Zealand (FIU NZ)": ("goAML (FIU NZ Police)", "https://www.police.govt.nz/about-us/structure/teams-and-units/financial-intelligence-unit"),
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
<div style="max-width: 520px; margin: 1.5rem auto 1.75rem auto; padding: 2rem 2.25rem;
            background:
                radial-gradient(120% 180% at 0% 0%, rgba(0,113,227,0.10) 0%, rgba(0,113,227,0) 55%),
                radial-gradient(120% 180% at 100% 100%, rgba(94,92,230,0.10) 0%, rgba(94,92,230,0) 55%),
                rgba(255,255,255,0.85);
            backdrop-filter: saturate(180%) blur(20px);
            -webkit-backdrop-filter: saturate(180%) blur(20px);
            border: 1px solid rgba(0,0,0,0.06); border-radius: 18px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 8px 28px rgba(0,0,0,0.04);
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;">
    <h2 style="color: #1D1D1F; margin: 0; font-weight: 700; letter-spacing: -0.028em; font-size: 1.7rem;">AML Agents</h2>
    <p style="color: #6E6E73; margin: 0.55rem 0 0 0; font-size: 0.95rem; line-height: 1.45;">
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

# Polish CSS — Apple-style design system. Soft grey canvas, white surfaces with
# hairline borders, SF Pro typography, calm accent blue, segmented-control tabs.
st.markdown(
    """
<style>
    /* ---- Apple-style design tokens ---------------------------------------
       Palette:  canvas #F5F5F7 · surface #FFFFFF · hairline #D2D2D7
                 text  #1D1D1F · secondary #6E6E73 · tertiary #86868B
                 accent #0071E3 (Apple blue) · accent-hover #0077ED
       Type:    -apple-system / SF Pro stack, antialiased
       Radius:  14px cards · 10px inputs/buttons · 980px pills
       Shadow:  hairline + very soft drop (0 1px 2px / 0 4px 16px rgba(0,0,0,.04))
    ----------------------------------------------------------------------- */

    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stToolbar"] {display: none;}
    div[data-testid="stDecoration"] {display: none;}

    /* Global typography + canvas */
    html, body, [class*="css"], .stApp, .block-container {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                     "Helvetica Neue", "Inter", system-ui, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    .stApp { background: #F5F5F7; color: #1D1D1F; }
    .block-container {
        padding-top: 2.25rem;
        padding-bottom: 4rem;
        max-width: 1280px;
    }

    /* Headings — Apple Display tight tracking */
    h1, h2, h3, h4 {
        color: #1D1D1F;
        letter-spacing: -0.022em;
        font-weight: 600;
    }
    h1 { letter-spacing: -0.028em; font-weight: 700; }

    /* Branded header — frosted-glass hero with soft tint */
    .brand-header {
        background:
            radial-gradient(120% 180% at 0% 0%, rgba(0,113,227,0.10) 0%, rgba(0,113,227,0) 55%),
            radial-gradient(120% 180% at 100% 100%, rgba(94,92,230,0.10) 0%, rgba(94,92,230,0) 55%),
            rgba(255,255,255,0.78);
        backdrop-filter: saturate(180%) blur(20px);
        -webkit-backdrop-filter: saturate(180%) blur(20px);
        border: 1px solid rgba(0,0,0,0.06);
        padding: 2rem 2.25rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 8px 28px rgba(0,0,0,0.04);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.75rem;
    }
    .brand-left {
        flex: 1 1 auto;
        min-width: 0;
    }
    .brand-right {
        flex: 0 0 auto;
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        align-items: flex-end;
        max-width: 280px;
    }
    .brand-header h1 {
        color: #1D1D1F !important;
        font-size: 1.85rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.028em;
        line-height: 1.15;
    }
    .brand-header .subtitle {
        color: #6E6E73;
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
        font-weight: 400;
        line-height: 1.45;
    }
    .brand-header .badge {
        display: inline-block;
        background: rgba(0,113,227,0.10);
        color: #0071E3;
        padding: 0.25rem 0.7rem;
        border-radius: 980px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }
    /* Authority chips on the right of the header */
    .auth-chip {
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        display: flex;
        align-items: baseline;
        gap: 0.55rem;
        white-space: nowrap;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        backdrop-filter: blur(6px);
    }
    .auth-chip .auth-abbr {
        color: #1D1D1F;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: -0.01em;
    }
    .auth-chip .auth-name {
        color: #6E6E73;
        font-size: 0.72rem;
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
        letter-spacing: 0.08em;
        color: #6E6E73;
        margin: 1.1rem 0 0.55rem 0.15rem;
    }

    /* Output area — accent blue label */
    .output-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #0071E3;
        margin: 1.75rem 0 0.55rem 0.15rem;
    }

    /* Bordered containers (st.container(border=True)) — soft cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #E5E5EA !important;
        border-radius: 14px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 4px 16px rgba(0,0,0,0.03);
    }

    /* Buttons — Apple primary pill + subtle secondary */
    .stButton button, .stDownloadButton button, .stFormSubmitButton button {
        font-weight: 500;
        border-radius: 980px;
        border: 1px solid rgba(0,0,0,0.10);
        background: #FFFFFF;
        color: #1D1D1F;
        padding: 0.4rem 1.1rem;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {
        background: #FAFAFC;
        border-color: rgba(0,0,0,0.18);
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
        background: #0071E3;
        color: #FFFFFF !important;
        border-color: #0071E3;
        height: 2.85rem;
        font-size: 0.95rem;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,113,227,0.20), 0 4px 14px rgba(0,113,227,0.18);
    }
    .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
        background: #0077ED;
        border-color: #0077ED;
        box-shadow: 0 2px 4px rgba(0,113,227,0.25), 0 6px 18px rgba(0,113,227,0.22);
    }

    /* Inputs — white surface, hairline border, blue focus ring */
    .stTextInput input, .stTextArea textarea, .stDateInput input,
    .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border: 1px solid #D2D2D7 !important;
        border-radius: 10px !important;
        color: #1D1D1F !important;
        font-size: 0.92rem !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus,
    .stNumberInput input:focus {
        border-color: #0071E3 !important;
        box-shadow: 0 0 0 3px rgba(0,113,227,0.18) !important;
        outline: none !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stMultiSelect label, .stDateInput label, .stNumberInput label,
    .stRadio label, .stCheckbox label, .stFileUploader label {
        font-weight: 500 !important;
        color: #1D1D1F !important;
        font-size: 0.88rem !important;
    }

    /* Tabs — Apple segmented control */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #EBEBF0;
        padding: 4px;
        border-radius: 12px;
        border: none;
    }
    .stTabs [data-baseweb="tab"] {
        height: 36px;
        padding: 0 16px;
        background: transparent;
        border: none;
        border-radius: 8px;
        color: #1D1D1F;
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255,255,255,0.5);
        color: #1D1D1F;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #1D1D1F !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.04);
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* Expanders — clean cards */
    .streamlit-expanderHeader, [data-testid="stExpander"] summary {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        color: #1D1D1F !important;
    }
    [data-testid="stExpander"] {
        border: 1px solid #E5E5EA !important;
        border-radius: 12px !important;
        background: #FFFFFF;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    /* Alerts — softer Apple-style banners */
    div[data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    /* Code blocks */
    code, pre {
        font-family: "SF Mono", "JetBrains Mono", "Menlo", monospace !important;
        background: #F5F5F7;
        border-radius: 6px;
    }

    /* Dataframe / table polish */
    .stDataFrame, .stTable {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E5E5EA;
    }

    /* Sidebar — frosted panel */
    section[data-testid="stSidebar"] {
        background: rgba(245,245,247,0.85);
        backdrop-filter: saturate(180%) blur(20px);
        border-right: 1px solid #E5E5EA;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* Sidebar collapse / expand controls — pill-shaped, Apple blue accent */
    [data-testid="collapsedControl"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D2D2D7 !important;
        border-radius: 980px !important;
        padding: 0.45rem !important;
        margin: 0.75rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.06) !important;
        transition: all 0.15s ease !important;
        z-index: 999 !important;
    }
    [data-testid="collapsedControl"]:hover {
        background-color: #FAFAFC !important;
        transform: scale(1.06) !important;
        box-shadow: 0 2px 4px rgba(0,113,227,0.20), 0 6px 18px rgba(0,113,227,0.18) !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="collapsedControl"] path {
        color: #0071E3 !important;
        fill: #0071E3 !important;
        stroke: #0071E3 !important;
        width: 20px !important;
        height: 20px !important;
    }
    [data-testid="stSidebarCollapseButton"] button {
        background-color: rgba(0,113,227,0.08) !important;
        border-radius: 980px !important;
        color: #0071E3 !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: rgba(0,113,227,0.14) !important;
    }

    /* Links — Apple blue */
    a, a:visited { color: #0071E3; text-decoration: none; }
    a:hover { color: #0077ED; text-decoration: underline; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E5EA;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    [data-testid="stMetricLabel"] { color: #6E6E73; font-weight: 500; }
    [data-testid="stMetricValue"] { color: #1D1D1F; font-weight: 600; letter-spacing: -0.02em; }

    /* Radio / checkbox accent */
    .stRadio [role="radiogroup"] label[data-baseweb="radio"] > div:first-child,
    .stCheckbox label[data-baseweb="checkbox"] > div:first-child {
        border-color: #D2D2D7;
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
<div style="width: 88px; height: 88px;
            background: linear-gradient(135deg, #0071E3 0%, #5E5CE6 100%);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            color: white; font-size: 2.1rem; font-weight: 600; margin-bottom: 0.6rem;
            letter-spacing: -0.02em;
            box-shadow: 0 1px 2px rgba(0,113,227,0.25), 0 6px 18px rgba(0,113,227,0.20);
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;">
    {initial}
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f"**{auth_name}**  \n<small style='color: #6E6E73;'>`{auth_username}`</small>",
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
                # Track the active case so the Connector-signals section
                # and the LLM prompt know which signals to render/inject.
                st.session_state["_active_case_key"] = case_key
                st.rerun()
    with tool_col5:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True):
            for k in SAMPLE_CASE.keys():
                st.session_state[f"input_{k}"] = ""
            for k, v in FILING_METADATA_DEFAULTS.items():
                st.session_state[k] = v
            st.session_state["input_date_of_filing"] = date.today()
            st.session_state["_active_case_key"] = None
            st.rerun()

# After widgets render, re-read in case the user changed the dropdown this run
jurisdiction = st.session_state["jurisdiction"]
model = st.session_state["model"]

# ============================================================================
# Top-level tabs — Draft STR / Connectors / Obligation register / Horizon scanning
# ============================================================================
(
    tab_draft,
    tab_connectors,
    tab_integration,
    tab_obligations,
    tab_horizon,
    tab_news,
) = st.tabs(
    [
        "Draft STR",
        "Connectors",
        "Integration guide",
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

    # ============================================================
    # Connector signals — the structured "why this was flagged" payload
    # surfaced from the 161 connectors. Pre-populated when a sample
    # case is loaded; included in the LLM prompt so the drafted
    # narrative can cite individual connector findings.
    # ============================================================
    _active_case = st.session_state.get("_active_case_key")
    _connector_signals = connector_signals_for(_active_case) if _active_case else []
    if _connector_signals:
        st.markdown(
            '<div class="section-label">Risk signals from connectors</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.caption(
                f"{len(_connector_signals)} signal(s) populated by upstream connectors. "
                "Each item is fed into the narrative prompt so the drafted STR can "
                "cite the connector by name."
            )
            for s in _connector_signals:
                color = severity_color(s.severity)
                ts_html = (
                    f'<span style="color:#86868B; font-size:0.72rem;">{s.timestamp}</span>'
                    if s.timestamp else ""
                )
                st.markdown(
                    f"""
<div style="background: #FFFFFF; border: 1px solid #E5E5EA; border-left: 4px solid {color};
            border-radius: 12px; padding: 0.85rem 1rem; margin-bottom: 0.6rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
    <div style="display:flex; justify-content:space-between; align-items:baseline; gap:0.75rem;
                flex-wrap:wrap; margin-bottom:0.35rem;">
        <div>
            <span style="font-weight:600; color:#1D1D1F; font-size:0.95rem;
                         letter-spacing:-0.01em;">{s.connector}</span>
            <span style="color:#86868B; font-size:0.78rem; margin-left:0.45rem;">
                · {s.category}</span>
        </div>
        <div style="display:flex; gap:0.45rem; align-items:center;">
            <span style="background:{color}; color:white; font-size:0.66rem; font-weight:600;
                         letter-spacing:0.04em; padding:0.16rem 0.52rem; border-radius:980px;">
                {s.severity}
            </span>
            <span style="color:#6E6E73; font-size:0.72rem;">{s.confidence}% conf</span>
            {ts_html}
        </div>
    </div>
    <div style="color:#1D1D1F; font-size:0.88rem; line-height:1.45; margin-bottom:0.35rem;">
        {s.signal}
    </div>
    <div style="color:#6E6E73; font-size:0.82rem; line-height:1.45;">
        <span style="font-weight:500; color:#0071E3;">Implication:</span> {s.implication}
    </div>
</div>
""",
                    unsafe_allow_html=True,
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

    {signals_as_prompt_text(connector_signals_for(st.session_state.get("_active_case_key", "")))}

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
            response = None
            generation_error: str | None = None

            try:
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
            except Exception as gen_err:
                err_type = type(gen_err).__name__
                err_text = str(gen_err)[:300]
                generation_error = f"{err_type}: {err_text}"

                # Common-error friendly messages
                if "401" in err_text or "authentication" in err_text.lower():
                    st.error(
                        "**Authentication failed.** Your Anthropic API key was rejected. "
                        "Check `~/dev/amlagents/.env` and run `~/dev/amlagents/fix-key.sh` "
                        "to update it from your clipboard."
                    )
                elif "429" in err_text or "rate" in err_text.lower():
                    st.error(
                        "**Rate limit hit.** Wait a moment and try again. If this happens "
                        "frequently, your Anthropic account may need a higher tier."
                    )
                elif "529" in err_text or "overloaded" in err_text.lower():
                    st.error(
                        "**Anthropic API is temporarily overloaded.** Try again in a few seconds."
                    )
                elif "billing" in err_text.lower() or "quota" in err_text.lower():
                    st.error(
                        "**Billing issue.** Add credits to your Anthropic account at "
                        "https://console.anthropic.com/settings/billing"
                    )
                else:
                    st.error(f"**Generation error.** {generation_error}")

                # If we got partial output, keep it for the user to copy/save
                if narrative:
                    st.warning(
                        f"Partial narrative captured ({len(narrative)} chars). "
                        "You can still copy and download below."
                    )

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

            # Skip token usage display + downstream actions if generation errored
            if generation_error or response is None:
                st.stop()  # halt this rerun's downstream rendering

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
# Integration guide tab — how to plug an external alerting / KYT / KYC system
# (Feedzai, Darwinium, Hawk AI, Chainalysis, ComplyAdvantage, Sumsub, ...)
# into AML Agents. Practitioner-facing user guide; covers webhook contract,
# auth, payload mapping, sample requests, and rollout sequencing.
# ============================================================================
with tab_integration:
    st.markdown(
        '<div class="section-label">Integration guide — feed your alerts into AML Agents</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Connect your existing alerting, KYT, KYC, or case-management platform so its "
        "alerts flow into AML Agents and pre-populate STR drafts. The pattern is the same "
        "for any of the 161 connectors: a webhook endpoint, an API key, and a JSON payload "
        "mapped to AML Agents fields. Follow the steps below — most banks complete a working "
        "integration in 1–2 weeks."
    )

    # ----------------------------------------------------------------------
    # Step 1 — choose the integration pattern
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 1 · Pick the integration pattern")
        st.markdown(
            "AML Agents supports three patterns. Pick the one that matches how your upstream "
            "platform delivers events."
        )
        pat_col1, pat_col2, pat_col3 = st.columns(3)
        with pat_col1:
            st.markdown(
                "**A · Webhook push (recommended)**\n\n"
                "Your platform POSTs each alert to AML Agents in real time. Lowest latency. "
                "Used by Feedzai, Hawk AI, Darwinium, Sift, Featurespace ARIC, Sumsub, "
                "BioCatch, Unit21, and most modern platforms."
            )
        with pat_col2:
            st.markdown(
                "**B · API pull (poll)**\n\n"
                "AML Agents periodically calls your platform's REST API for new alerts. "
                "Used when the upstream system can't push — e.g. some on-prem SAS or NICE "
                "Actimize deployments. Default poll interval: 60 seconds."
            )
        with pat_col3:
            st.markdown(
                "**C · File drop (SFTP / S3)**\n\n"
                "Your platform writes a CSV / JSONL file to an SFTP or S3 location; AML "
                "Agents picks it up. Used by legacy core-banking AML modules and some "
                "TBML monitoring vendors. End-of-day batch only."
            )

    # ----------------------------------------------------------------------
    # Step 2 — webhook endpoint + auth
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 2 · Get your webhook URL and API key")
        st.markdown(
            "Each AML Agents tenant gets a unique webhook URL and a long-lived API key. "
            "In v0 these are issued on request — Settings → Connectors → Generate "
            "credentials. In production they self-serve from the admin console."
        )
        st.code(
            "Webhook URL\n"
            "  https://api.amlagents.ai/v1/ingest/<tenant-id>/<connector-slug>\n\n"
            "Auth header (every request)\n"
            "  Authorization: Bearer <tenant-api-key>\n\n"
            "Optional signature header (recommended)\n"
            "  X-AmlAgents-Signature: hmac-sha256(<tenant-secret>, raw_body)",
            language="text",
        )
        st.caption(
            "The connector-slug names which upstream system is sending — feedzai, "
            "darwinium, hawk-ai, chainalysis-kyt, complyadvantage, sumsub, etc. AML "
            "Agents uses this to apply the right field-mapping profile (Step 4)."
        )

    # ----------------------------------------------------------------------
    # Step 3 — sample request
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 3 · Send a test alert")
        st.markdown(
            "Wire up the simplest possible payload first. AML Agents will accept it, "
            "echo back a normalised representation, and surface it in the Draft STR tab "
            "as a pre-populated case ready for the analyst to review."
        )
        ex_col1, ex_col2 = st.columns(2)
        with ex_col1:
            st.markdown("**curl**")
            st.code(
                """curl -X POST \\
  https://api.amlagents.ai/v1/ingest/acme-bank/feedzai \\
  -H "Authorization: Bearer $AMLAGENTS_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "alert_id": "FZ-2026-00482719",
    "alert_time": "2026-04-29T14:32:11+08:00",
    "score": 0.91,
    "rule": "TBM-014 structuring",
    "customer": {
      "id": "A123456789",
      "name": "ACME Trading Pte Ltd"
    },
    "transactions": [
      {"date": "2026-04-15", "amount": 480000, "ccy": "SGD",
       "counterparty": "HK-XYZ Ltd"}
    ],
    "raw_alert_url": "https://acme.feedzai.com/alerts/482719"
  }'""",
                language="bash",
            )
        with ex_col2:
            st.markdown("**Python**")
            st.code(
                """import os, requests, hmac, hashlib, json

api_key = os.environ["AMLAGENTS_API_KEY"]
secret  = os.environ["AMLAGENTS_SIGNING_SECRET"]
url = "https://api.amlagents.ai/v1/ingest/acme-bank/feedzai"

payload = {
    "alert_id": "FZ-2026-00482719",
    "alert_time": "2026-04-29T14:32:11+08:00",
    "score": 0.91,
    "rule": "TBM-014 structuring",
    "customer": {
        "id": "A123456789",
        "name": "ACME Trading Pte Ltd",
    },
    "transactions": [
        {"date": "2026-04-15", "amount": 480000,
         "ccy": "SGD", "counterparty": "HK-XYZ Ltd"},
    ],
    "raw_alert_url": "https://acme.feedzai.com/alerts/482719",
}
body = json.dumps(payload).encode()
sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

r = requests.post(
    url,
    data=body,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-AmlAgents-Signature": sig,
    },
    timeout=10,
)
r.raise_for_status()
print(r.json())""",
                language="python",
            )
        st.markdown("**Successful response**")
        st.code(
            """{
  "ok": true,
  "case_id": "case_01HXYZ...",
  "tenant": "acme-bank",
  "connector": "feedzai",
  "status": "ingested",
  "case_url": "https://app.amlagents.ai/cases/case_01HXYZ...",
  "echo": {
    "subject_name": "ACME Trading Pte Ltd",
    "subject_id": "A123456789",
    "transactions_count": 1,
    "alert_score": 0.91
  }
}""",
            language="json",
        )
        st.caption(
            "Errors return a structured JSON body with `error.code` and `error.message`. "
            "Common codes: `auth.invalid_key`, `payload.unknown_connector`, "
            "`payload.schema_mismatch`, `quota.exceeded`. Retries should be idempotent on "
            "`alert_id` — AML Agents deduplicates within a 24-hour window."
        )

    # ----------------------------------------------------------------------
    # Step 4 — payload mapping (the table)
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 4 · Map your payload to AML Agents fields")
        st.markdown(
            "AML Agents normalises every connector's payload into the same internal case "
            "schema. The table below shows the canonical fields and which keys each major "
            "connector supplies. AML Agents ships built-in mapping profiles for the "
            "platforms below; for any of the 161 connectors not listed, send the raw JSON "
            "and AML Agents' Haiku-based extractor proposes a mapping you can approve."
        )
        st.markdown(
            "| AML Agents field | Feedzai | Darwinium | Hawk AI | Chainalysis KYT | "
            "ComplyAdvantage | Sumsub |\n"
            "|---|---|---|---|---|---|---|\n"
            "| `subject.name` | `customer.name` | `actor.full_name` | `entity.legal_name` "
            "| `address.label` | `entity.name` | `applicant.info.fullName` |\n"
            "| `subject.id` | `customer.id` | `actor.persistent_id` | `entity.id` | "
            "`address.address` | `entity.id` | `applicant.id` |\n"
            "| `alert.score` | `score` | `risk.composite_score` | `alert.score` | "
            "`risk.score` | `match.score` | `review.reviewAnswer` |\n"
            "| `alert.rule` | `rule` | `signal.name` | `scenario_name` | "
            "`category` | `match_types[]` | `review.rejectLabels[]` |\n"
            "| `alert.timestamp` | `alert_time` | `event_time` | `created_at` | "
            "`timestamp` | `created_at` | `createdAt` |\n"
            "| `transactions[]` | `transactions[]` | `events[]` | `transactions[]` | "
            "`transfers[]` | _(N/A — counterparty platform)_ | _(N/A — KYC platform)_ |\n"
            "| `raw_alert_url` | `dashboard_url` | `case_url` | `link` | "
            "`investigation_url` | `entity_url` | `applicantId` (compose) |"
        )
        st.caption(
            "Custom mappings: any field not in the canonical schema is preserved under "
            "`metadata.<connector_slug>.*` so nothing is lost. The drafted STR narrative "
            "automatically references custom fields where they're material to the analysis."
        )

    # ----------------------------------------------------------------------
    # Step 5 — what happens after ingestion
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 5 · What AML Agents does with your alert")
        st.markdown(
            "1. **Deduplicate** against the prior 24h window using `alert_id` and "
            "`subject.id`.\n"
            "2. **Enrich** with TrustSphere Risk Index, sanctions/PEP screening "
            "(OpenSanctions or your contracted ComplyAdvantage), and adverse-media check "
            "if licensed.\n"
            "3. **Render** the alert as a pre-populated Draft STR case. The analyst opens "
            "it from the inbox at `/cases/<id>`.\n"
            "4. **Cite** your platform by name in the drafted narrative — e.g. "
            "*\"Feedzai rule TBM-014 fired on 2026-04-15 with score 0.91...\"*. The same "
            "is true for all 161 connectors.\n"
            "5. **Post-back (optional)** the final STRO/JFIU/FIED/AUSTRAC reference number "
            "to your platform's case file once filed, closing the loop."
        )

    # ----------------------------------------------------------------------
    # Step 6 — rollout sequencing
    # ----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### Step 6 · Recommended rollout sequencing")
        st.markdown(
            "**Week 1** — sandbox connection. Wire up the webhook with test data. Confirm "
            "auth, signature verification, and field mapping work end-to-end. Agree the "
            "deduplication window with your operations team.\n\n"
            "**Week 2** — shadow mode. Production alerts flow to AML Agents in parallel "
            "with your existing case-management tool; analysts continue to use the "
            "incumbent system but spot-check AML Agents' draft narratives. Track the "
            "narrative-quality gap.\n\n"
            "**Week 3 — pilot cohort.** A small group of analysts uses AML Agents as the "
            "primary drafter for a defined customer segment (typically retail FX or "
            "remittance). Measure time-to-file and MLRO QA scores.\n\n"
            "**Week 4+ — staged production.** Roll out to broader segments. Decommission "
            "duplicated case-management for ingested alerts where AML Agents is the "
            "system of record. Connect post-back so AML Agents updates your incumbent "
            "platform with the STR reference number."
        )

    # ----------------------------------------------------------------------
    # FAQ
    # ----------------------------------------------------------------------
    with st.expander("FAQ — common integration questions", expanded=False):
        st.markdown(
            "**Q · What if our platform isn't in the 161-connector catalogue?**  \n"
            "Send the raw JSON to the generic ingestion endpoint "
            "`/v1/ingest/<tenant-id>/custom`. AML Agents' Haiku extractor proposes a "
            "mapping; an admin approves it once and it's persisted as a tenant-specific "
            "profile.\n\n"
            "**Q · Can we encrypt customer PII before sending?**  \n"
            "Yes — opt in to the `payload.envelope_encryption` mode at tenant setup. "
            "AML Agents holds a tenant-specific KMS key (BYOK supported on AWS, Azure, "
            "GCP) and decrypts on ingestion. The decrypted payload never leaves the "
            "tenant's container.\n\n"
            "**Q · How does AML Agents handle PII residency?**  \n"
            "Production deployment supports Singapore, Hong Kong, Frankfurt, Sydney and "
            "US-East regions. Pick the region where your data should reside; alerts are "
            "ingested, processed and persisted within the chosen region. Cross-region "
            "replication is opt-in.\n\n"
            "**Q · How does the post-back to our case-management tool work?**  \n"
            "Your platform exposes a webhook URL of its own; AML Agents POSTs the STR "
            "filing reference, timestamp, and PDF link as soon as the analyst submits. "
            "Most case-management tools (Unit21, Hummingbird, Salesforce-FSC, in-house "
            "JIRA-based workflows) accept this.\n\n"
            "**Q · What about SLAs?**  \n"
            "v0 SLA: ingestion ack within 2 seconds, draft STR rendered within 30 seconds. "
            "Production paid tier: 99.9% monthly uptime, 1-second ack, 15-second draft "
            "rendering.\n\n"
            "**Q · How is this priced?**  \n"
            "Per ingested alert + per drafted STR. Volume tiers from 5,000 alerts / "
            "month upwards. Talk to TrustSphere Partners (David Edward Haynes) for a "
            "scoped quote — david@trustsphere.partners."
        )

    st.caption(
        "Need a worked example for your specific platform? Pick the connector in the "
        "Connectors tab and request the integration kit — TrustSphere ships a tenant-"
        "specific Postman collection, signature-verification snippet, and field-mapping "
        "profile."
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
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])
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
    with filter_col3:
        ob_priority_filter = st.selectbox(
            "Filter by priority",
            ["All priorities", "Critical", "High", "Standard", "Low"],
            key="ob_priority_filter",
            help="Critical / High = legacy obligations from the last 12 months that are commonly missed.",
        )
    with filter_col4:
        st.markdown("<div style='height:1.85rem;'></div>", unsafe_allow_html=True)
        if st.button(
            "Reset to seed",
            key="ob_reseed",
            help=(
                "Discard the current persisted obligations and rewrite the "
                "seed list — useful when seed prose has been updated and "
                "the running container has stale data on its writable disk."
            ),
            use_container_width=True,
        ):
            reseed_obligations()
            st.success("Reseeded the obligation register from lib/obligations.py")
            st.rerun()

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

    # Resolve any seed task placeholders to real obligation_ids on first
    # render of the session. Idempotent + cheap.
    if not st.session_state.get("_tasks_seed_linked"):
        relink_seed_tasks_to_obligations(obligations)
        st.session_state["_tasks_seed_linked"] = True
    if ob_jur_filter != "All jurisdictions":
        obligations = [o for o in obligations if o.jurisdiction == ob_jur_filter]
    if ob_status_filter != "All statuses":
        obligations = [o for o in obligations if o.status == ob_status_filter]
    if ob_priority_filter != "All priorities":
        obligations = [
            o for o in obligations
            if (getattr(o, "priority", "Standard") or "Standard") == ob_priority_filter
        ]

    # Sort: Overdue first, then Critical/High priority, then by due_date ascending.
    _priority_rank = {"Critical": 0, "High": 1, "Standard": 2, "Low": 3}
    _status_rank = {"Overdue": 0, "In progress": 1, "Open": 2, "Closed": 3}
    obligations.sort(key=lambda o: (
        _status_rank.get(o.status, 9),
        _priority_rank.get(getattr(o, "priority", "Standard") or "Standard", 9),
        o.due_date or "9999-12-31",
    ))

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
            # Priority styling: Critical = red, High = amber, Standard = grey
            _priority = getattr(o, "priority", "Standard") or "Standard"
            _priority_styles = {
                "Critical": ("#FFE5E5", "#C92A2A"),
                "High": ("#FFF4E5", "#B45309"),
                "Standard": (None, None),
                "Low": ("#F1F5F9", "#475569"),
            }
            _bg, _fg = _priority_styles.get(_priority, (None, None))
            _priority_badge = (
                f'<span style="background:{_bg}; color:{_fg}; '
                f'padding: 2px 10px; border-radius: 980px; font-size: 0.72rem; '
                f'font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;'
                f' margin-left: 0.6rem;">⚠ {_priority}</span>'
                if _bg
                else ""
            )
            with st.container(border=True):
                top_row = st.columns([5, 1, 1])
                with top_row[0]:
                    st.markdown(
                        f"**{o.title}** &nbsp; "
                        f'<span style="color: {status_color}; font-size: 0.75rem; '
                        f'font-weight: 600; text-transform: uppercase;">{o.status}</span>'
                        f"{_priority_badge}",
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

                # ----------------------------------------------------------
                # Expandable detail panel — full text, deadline calculation,
                # evidence, source link, plus the four new fields:
                # entities_impacted, penalties, common_mistakes, priority.
                # ----------------------------------------------------------
                _entities_impacted = getattr(o, "entities_impacted", "")
                _penalties = getattr(o, "penalties", "")
                _common_mistakes = getattr(o, "common_mistakes", "")
                _has_detail = bool(
                    getattr(o, "full_text", "")
                    or getattr(o, "deadline_explanation", "")
                    or getattr(o, "evidence", "")
                    or getattr(o, "source_url", "")
                    or _entities_impacted
                    or _penalties
                    or _common_mistakes
                )
                if _has_detail:
                    with st.expander("Show details", expanded=False):
                        if o.full_text:
                            st.markdown(
                                "<div class='output-label' style='margin-top:0;'>"
                                "What this obligation requires</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(o.full_text)
                        if _entities_impacted:
                            st.markdown(
                                "<div class='output-label'>Which entities this impacts</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(_entities_impacted)
                        if o.deadline_explanation:
                            st.markdown(
                                "<div class='output-label'>Deadline</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"**{o.due_date or '—'}** &nbsp; · &nbsp; "
                                f"{o.deadline_explanation}"
                            )
                        if _penalties:
                            st.markdown(
                                "<div class='output-label' "
                                "style='color:#C92A2A;'>"
                                "Penalties / enforcement if not met</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(_penalties)
                        if _common_mistakes:
                            st.markdown(
                                "<div class='output-label' "
                                "style='color:#B45309;'>"
                                "Common mistakes — pre-flight checklist</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(_common_mistakes)
                        if o.evidence:
                            st.markdown(
                                "<div class='output-label'>Evidence on examination</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(o.evidence)
                        if o.source_url:
                            st.markdown(
                                f"<div style='margin-top:0.8rem; font-size:0.78rem;'>"
                                f"<a href='{o.source_url}' target='_blank' "
                                f"rel='noopener noreferrer'>View source →</a>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                # ----------------------------------------------------------
                # Programme tracker — sub-tasks tied to this obligation.
                # Lets compliance / AML / fraud teams break the obligation
                # into owned, dated, status-tracked work items with a
                # meeting / checkpoint cadence note.
                # ----------------------------------------------------------
                _ob_tasks = tasks_for(o.id)
                _done_n, _total_n, _pct = task_progress(o.id)
                _progress_label = (
                    f"({_done_n}/{_total_n})"
                    if _total_n
                    else "(no tasks yet)"
                )
                with st.expander(
                    f"📋  Tasks {_progress_label}",
                    expanded=False,
                ):
                    if _total_n:
                        # Progress bar
                        st.progress(_pct / 100.0, text=f"{_pct:.0f}% complete")

                    # List existing tasks
                    for t in _ob_tasks:
                        _t_status_color = {
                            "Not started": "#6E6E73",
                            "In progress": "#0071E3",
                            "Blocked": "#C92A2A",
                            "Done": "#1B5E20",
                        }.get(t.status, "#6E6E73")
                        with st.container(border=True):
                            t_row = st.columns([5, 2, 1])
                            with t_row[0]:
                                st.markdown(
                                    f"**{t.title}** &nbsp; "
                                    f'<span style="color:{_t_status_color}; '
                                    f'font-size:0.7rem; font-weight:600; '
                                    f'text-transform:uppercase; letter-spacing:0.04em;">'
                                    f'{t.status}</span>',
                                    unsafe_allow_html=True,
                                )
                                meta_parts = []
                                if t.owner:
                                    meta_parts.append(f"Owner: {t.owner}")
                                if t.due_date:
                                    try:
                                        d = dt.date.fromisoformat(t.due_date)
                                        days = (d - dt.date.today()).days
                                        if days < 0:
                                            chip = f"Overdue {-days}d"
                                            chip_bg = "#FFE5E5"; chip_fg = "#C92A2A"
                                        elif days == 0:
                                            chip = "Due today"
                                            chip_bg = "#FFF4E5"; chip_fg = "#B45309"
                                        elif days <= 7:
                                            chip = f"Due in {days}d"
                                            chip_bg = "#FFF4E5"; chip_fg = "#B45309"
                                        else:
                                            chip = f"Due {t.due_date}"
                                            chip_bg = "rgba(0,113,227,0.10)"
                                            chip_fg = "#0071E3"
                                        meta_parts.append(
                                            f'<span style="background:{chip_bg};'
                                            f'color:{chip_fg};padding:1px 8px;'
                                            f'border-radius:980px;font-size:0.7rem;'
                                            f'font-weight:600;">{chip}</span>'
                                        )
                                    except Exception:
                                        meta_parts.append(f"Due: {t.due_date}")
                                if t.meeting_cadence:
                                    meta_parts.append(f"Cadence: {t.meeting_cadence}")
                                if meta_parts:
                                    st.markdown(
                                        "<small>"
                                        + " &nbsp; · &nbsp; ".join(meta_parts)
                                        + "</small>",
                                        unsafe_allow_html=True,
                                    )
                                if t.description:
                                    st.markdown(
                                        f"<small style='color:#6E6E73;'>"
                                        f"{t.description}</small>",
                                        unsafe_allow_html=True,
                                    )
                                if t.notes:
                                    st.caption(f"Notes: {t.notes}")
                            with t_row[1]:
                                new_t_status = st.selectbox(
                                    "Status",
                                    TASK_STATUSES,
                                    index=TASK_STATUSES.index(t.status)
                                        if t.status in TASK_STATUSES else 0,
                                    key=f"t_status_{t.id}",
                                    label_visibility="collapsed",
                                )
                                if new_t_status != t.status:
                                    update_task(t.id, status=new_t_status)
                                    st.rerun()
                            with t_row[2]:
                                if st.button(
                                    "✕",
                                    key=f"t_del_{t.id}",
                                    use_container_width=True,
                                    help="Delete this task",
                                ):
                                    delete_task(t.id)
                                    st.rerun()

                    # Add-task form
                    with st.form(f"add_task_{o.id}", clear_on_submit=True):
                        st.markdown(
                            "<div style='font-size:0.78rem;font-weight:600;"
                            "color:#1D1D1F;margin-top:0.4rem;'>Add a task</div>",
                            unsafe_allow_html=True,
                        )
                        nt_c1, nt_c2 = st.columns(2)
                        with nt_c1:
                            nt_title = st.text_input(
                                "Task title",
                                placeholder="e.g. Close FY2024 prior-year findings",
                                key=f"nt_title_{o.id}",
                            )
                            nt_owner = st.text_input(
                                "Owner",
                                placeholder="e.g. MLRO, Head of FCC, AML/CTF Compliance Officer",
                                key=f"nt_owner_{o.id}",
                            )
                            nt_due = st.date_input(
                                "Due date",
                                key=f"nt_due_{o.id}",
                            )
                        with nt_c2:
                            nt_desc = st.text_area(
                                "Description (optional)",
                                key=f"nt_desc_{o.id}",
                                height=80,
                            )
                            nt_status = st.selectbox(
                                "Status",
                                TASK_STATUSES,
                                key=f"nt_status_{o.id}",
                            )
                            nt_cadence = st.text_input(
                                "Meeting / cadence (optional)",
                                placeholder="e.g. Audit Committee 15 Dec 2025",
                                key=f"nt_cadence_{o.id}",
                            )
                        if st.form_submit_button(
                            "Add task",
                            type="primary",
                        ):
                            if nt_title:
                                add_task(
                                    obligation_id=o.id,
                                    title=nt_title,
                                    description=nt_desc,
                                    owner=nt_owner,
                                    due_date=nt_due.isoformat() if nt_due else "",
                                    status=nt_status,
                                    meeting_cadence=nt_cadence,
                                )
                                st.rerun()
                            else:
                                st.warning("Task title is required.")

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
            value=False,
            key="horizon_include_live",
            help=(
                "Fetch from regulator RSS feeds (cached 30 min). Default OFF so the tab "
                "renders instantly with curated items. Toggle on to pull live updates."
            ),
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
        "announcements across the six jurisdictions. Distinct from horizon scanning (which "
        "tracks regulatory change). Filter by country and topic."
    )

    # ----------------------------------------------------------------------
    # 📬 Daily briefing — subscribe to a 7am email digest, audio podcast,
    # or short video roll-up of news + obligations + horizon scanning.
    # Email is generated server-side; podcast/video are generated daily by
    # the cron and link is included in the email + on the home tab.
    # ----------------------------------------------------------------------
    with st.expander(
        "📬  Daily briefing — subscribe to the 7am roll-up",
        expanded=False,
    ):
        st.markdown(
            "Get a curated digest of the latest news, obligations falling due, "
            "and horizon-scanning items delivered to you every morning at "
            "**07:00 in your local timezone**. Pick the channel — short email, "
            "audio podcast, or video — and we'll generate it from the same "
            "feeds you see in the app."
        )
        with st.form("daily_briefing_subscribe", clear_on_submit=False):
            db_col1, db_col2 = st.columns(2)
            with db_col1:
                db_email = st.text_input(
                    "Email address",
                    placeholder="you@yourbank.com",
                    key="db_email",
                    help=(
                        "We send the email + podcast/video link to this address "
                        "every morning. Unsubscribe at any time via the footer "
                        "link in the email."
                    ),
                )
                db_tz_label = st.selectbox(
                    "Your timezone (delivery hour anchor)",
                    [label for label, _iana in SUB_TIMEZONES],
                    index=0,  # default: Singapore
                    key="db_tz",
                    help="Digest is delivered at 07:00 in this timezone.",
                )
                db_tz = next(
                    iana
                    for label, iana in SUB_TIMEZONES
                    if label == db_tz_label
                )
            with db_col2:
                db_jur = st.multiselect(
                    "Jurisdictions (leave empty for all 6)",
                    list(RUBRICS.keys()),
                    default=[],
                    key="db_jurisdictions",
                )
                db_topics = st.multiselect(
                    "News topics (leave empty for all)",
                    NEWS_TOPICS,
                    default=[],
                    key="db_topics",
                )

            st.markdown(
                "<div style='font-size:0.85rem; font-weight:500; "
                "color:#1D1D1F; margin-top:0.4rem;'>Channels</div>",
                unsafe_allow_html=True,
            )
            db_chan_col1, db_chan_col2, db_chan_col3 = st.columns(3)
            with db_chan_col1:
                db_email_on = st.checkbox(
                    "📧  Email digest",
                    value=True,
                    key="db_email_on",
                    help="HTML email — usually under 60s to read.",
                )
            with db_chan_col2:
                db_podcast_on = st.checkbox(
                    "🎙  Audio podcast",
                    value=False,
                    key="db_podcast_on",
                    help=(
                        "3–5 minute MP3 generated by Claude + TTS each morning. "
                        "Link in the email; also published as a private podcast feed."
                    ),
                )
            with db_chan_col3:
                db_video_on = st.checkbox(
                    "🎬  Video briefing",
                    value=False,
                    key="db_video_on",
                    help=(
                        "Short MP4 with the day's headlines as captioned slides "
                        "plus the same voiceover. Link in the email; uploadable "
                        "to your YouTube channel via OAuth (configure separately)."
                    ),
                )

            st.markdown(
                "<div style='font-size:0.85rem; font-weight:500; "
                "color:#1D1D1F; margin-top:0.6rem;'>Sections to include</div>",
                unsafe_allow_html=True,
            )
            db_inc_col1, db_inc_col2, db_inc_col3 = st.columns(3)
            with db_inc_col1:
                db_inc_news = st.checkbox(
                    "Jurisdictional news", value=True, key="db_inc_news"
                )
            with db_inc_col2:
                db_inc_oblig = st.checkbox(
                    "Obligations due (next 60d)", value=True, key="db_inc_oblig"
                )
            with db_inc_col3:
                db_inc_horizon = st.checkbox(
                    "Horizon scanning", value=True, key="db_inc_horizon"
                )

            db_submit = st.form_submit_button(
                "Subscribe me to the daily briefing",
                type="primary",
                use_container_width=False,
            )

            if db_submit:
                if not db_email or "@" not in db_email:
                    st.error("Please enter a valid email address.")
                elif not (db_email_on or db_podcast_on or db_video_on):
                    st.error("Pick at least one channel (email / podcast / video).")
                elif not (db_inc_news or db_inc_oblig or db_inc_horizon):
                    st.error("Pick at least one section to include.")
                else:
                    sub = add_subscription(
                        email=db_email,
                        timezone=db_tz,
                        jurisdictions=db_jur,
                        topics=db_topics,
                        include_news=db_inc_news,
                        include_obligations=db_inc_oblig,
                        include_horizon=db_inc_horizon,
                    )
                    # Persist the channel choices via session_state for the
                    # preview below; channel-format storage is wired later
                    # when the multi-channel sender is hooked up.
                    st.session_state["_db_last_sub_token"] = sub.unsubscribe_token
                    channels = []
                    if db_email_on:
                        channels.append("email")
                    if db_podcast_on:
                        channels.append("podcast")
                    if db_video_on:
                        channels.append("video")
                    st.success(
                        f"✓ Subscribed `{sub.email}` for the daily briefing — "
                        f"channels: {', '.join(channels)} · delivery 07:00 "
                        f"{sub.label_timezone()}. Preview the next email below."
                    )
                    st.rerun()

        # -- Preview pane: render the next digest for the most-recent
        # subscription so the user can sanity-check the content + style.
        token = st.session_state.get("_db_last_sub_token")
        if token:
            from lib.subscriptions import find_by_token  # local import
            sub = find_by_token(token)
            if sub:
                payload = build_digest_payload(sub)
                counts = payload.sections
                st.markdown(
                    "<div class='output-label'>Preview — what you'll receive tomorrow at 07:00</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Subject: **{payload.subject}**  ·  "
                    f"news ({counts['news']}) · obligations ({counts['obligations']}) · "
                    f"horizon ({counts['horizon']})"
                )
                with st.container(border=True):
                    st.components.v1.html(payload.html, height=720, scrolling=True)
                st.caption(
                    "💡 The audio podcast and video formats use the same content; "
                    "the cron generates them from this digest each morning. "
                    "Today's draft podcast script is also visible on the Home tab "
                    "once the daily-briefing GitHub Actions workflow has run."
                )

        # -- Unsubscribe section
        st.markdown(
            "<div class='output-label' style='margin-top:1.5rem;'>"
            "Already subscribed?</div>",
            unsafe_allow_html=True,
        )
        un_col1, un_col2 = st.columns([3, 1])
        with un_col1:
            db_lookup_email = st.text_input(
                "Look up by email",
                placeholder="you@yourbank.com",
                key="db_lookup_email",
                label_visibility="collapsed",
            )
        with un_col2:
            db_lookup_btn = st.button(
                "Find my subscriptions",
                key="db_lookup_btn",
                use_container_width=True,
            )
        if db_lookup_btn and db_lookup_email:
            existing = find_subs_by_email(db_lookup_email)
            if not existing:
                st.info("No active subscriptions for that email.")
            else:
                for s in existing:
                    e_col1, e_col2 = st.columns([4, 1])
                    with e_col1:
                        st.markdown(
                            f"**{s.email}**  ·  {s.label_timezone()}  ·  "
                            f"status: `{s.status}`  ·  "
                            f"jurisdictions: {', '.join(s.jurisdictions) or 'all 6'}  "
                        )
                    with e_col2:
                        if s.status == "active" and st.button(
                            "Unsubscribe", key=f"db_unsub_{s.id}",
                            use_container_width=True,
                        ):
                            unsubscribe_token(s.unsubscribe_token)
                            st.success(f"Unsubscribed {s.email}.")
                            st.rerun()

    # ----------------------------------------------------------------------
    # Today's briefing — audio podcast + video player. The cron at
    # data-briefing.yml writes data/podcasts/<date>.mp3 + data/videos/
    # <date>.mp4 each morning; this section finds the latest and plays it.
    # When the cron has not yet run (cold demo / fresh install), shows a
    # 'No briefing yet — runs nightly' state.
    # ----------------------------------------------------------------------
    pod = latest_podcast_meta()
    vid = latest_video_meta()
    if pod or vid:
        with st.expander(
            "🎙  Today's briefing — audio + video",
            expanded=False,
        ):
            tb_col1, tb_col2 = st.columns(2)
            with tb_col1:
                st.markdown(
                    "<div class='output-label' style='margin-top:0;'>"
                    "Audio podcast</div>",
                    unsafe_allow_html=True,
                )
                if pod and pod.mp3_path.exists():
                    st.markdown(f"**{pod.title}**")
                    # Read voice metadata from sidecar for badge labelling
                    _voice = ""
                    try:
                        _voice = json.loads(pod.sidecar_path.read_text()).get(
                            "voice", ""
                        ) or ""
                    except Exception:
                        pass
                    if pod.stub:
                        badge = (
                            "<span style='background:#FFF4E5;color:#B45309;"
                            "padding:2px 8px;border-radius:980px;font-size:11px;"
                            "font-weight:600;'>Silent stub — script generation failed</span>"
                        )
                    elif _voice.startswith("openai"):
                        badge = (
                            "<span style='background:rgba(0,113,227,0.10);"
                            "color:#0071E3;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, pod.duration_seconds // 60)} min  ·  OpenAI alloy</span>"
                        )
                    elif _voice.startswith("edge:dialogue"):
                        # Voice pair changed from Sonia → Libby on 2026-05-07.
                        # Render the badge using the actual stored voice tag
                        # so older sidecars still label correctly.
                        pair = _voice.split(":")[-1] if ":" in _voice else "Ryan + Libby"
                        badge = (
                            "<span style='background:rgba(52,199,89,0.12);"
                            "color:#1B5E20;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, pod.duration_seconds // 60)} min  ·  "
                            f"Two-host conversation ({pair}, free)</span>"
                        )
                    elif _voice.startswith("edge"):
                        badge = (
                            "<span style='background:rgba(52,199,89,0.12);"
                            "color:#1B5E20;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, pod.duration_seconds // 60)} min  ·  Edge Neural en-GB Ryan (free)</span>"
                        )
                    elif _voice.startswith("gtts"):
                        badge = (
                            "<span style='background:rgba(255,193,7,0.18);"
                            "color:#7C2D12;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, pod.duration_seconds // 60)} min  ·  gTTS en-UK (basic)</span>"
                        )
                    else:
                        badge = (
                            "<span style='background:rgba(0,113,227,0.10);"
                            "color:#0071E3;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, pod.duration_seconds // 60)} min</span>"
                        )
                    st.markdown(
                        f"<div style='font-size:0.78rem;color:#6E6E73;"
                        f"margin-bottom:0.6rem;'>{pod.date}  ·  "
                        f"{pod.script_chars:,} script chars  ·  {badge}</div>",
                        unsafe_allow_html=True,
                    )
                    try:
                        with open(pod.mp3_path, "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
                    except Exception as e:
                        st.warning(f"Audio file unreadable: {e}")
                else:
                    st.info(
                        "No podcast yet — the daily-briefing GitHub Actions "
                        "workflow runs at 22:30 UTC nightly. Trigger it "
                        "manually from the Actions tab to generate today's."
                    )
            with tb_col2:
                st.markdown(
                    "<div class='output-label' style='margin-top:0;'>"
                    "Video briefing</div>",
                    unsafe_allow_html=True,
                )
                if vid and vid.mp4_path.exists() and vid.mp4_path.stat().st_size > 0:
                    st.markdown(f"**{vid.title}**")
                    badge = (
                        "<span style='background:#FFF4E5;color:#B45309;"
                        "padding:2px 8px;border-radius:980px;font-size:11px;"
                        "font-weight:600;'>Stub — install ffmpeg in cron</span>"
                        if vid.stub
                        else (
                            "<span style='background:rgba(0,113,227,0.10);"
                            "color:#0071E3;padding:2px 8px;border-radius:980px;"
                            f"font-size:11px;font-weight:600;'>"
                            f"~{max(1, vid.duration_seconds // 60)} min  ·  "
                            f"{vid.n_slides} slides</span>"
                        )
                    )
                    st.markdown(
                        f"<div style='font-size:0.78rem;color:#6E6E73;"
                        f"margin-bottom:0.6rem;'>{vid.date}  ·  {badge}</div>",
                        unsafe_allow_html=True,
                    )
                    try:
                        with open(vid.mp4_path, "rb") as f:
                            st.video(f.read(), format="video/mp4")
                    except Exception as e:
                        st.warning(f"Video file unreadable: {e}")
                elif vid:
                    st.info(
                        "Video for today is empty — likely because FFmpeg was "
                        "not available in the cron container. Check the "
                        "daily-briefing workflow logs."
                    )
                else:
                    st.info(
                        "No video yet — runs nightly with the audio briefing."
                    )

            # Show today's script (transcript) in an expander so subscribers
            # can speed-read instead of listen if they prefer.
            if pod:
                with st.expander("Show transcript", expanded=False):
                    try:
                        meta = json.loads(pod.sidecar_path.read_text())
                        st.markdown(meta.get("script", "_(no script available)_"))
                    except Exception:
                        st.markdown("_(transcript unavailable)_")

            # ----------------------------------------------------------
            # Subscribe panel — RSS feed URL for podcast aggregators
            # (Apple Podcasts, Spotify, Wix Podcast Player, etc.) plus
            # one-click copy. The cron rebuilds feed.xml each morning.
            # ----------------------------------------------------------
            try:
                feed = podcast_feed_summary()
                if feed.get("url") and feed.get("items"):
                    st.markdown(
                        "<div class='output-label' style='margin-top:1.5rem;'>"
                        "Subscribe to the daily podcast</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"Apple Podcasts · Spotify · Pocket Casts · Overcast · "
                        f"Wix Podcast Player. {feed['items']} episodes, latest {feed['latest']}."
                    )
                    st.code(feed["url"], language=None)
                    st.caption(
                        "Paste this RSS feed URL into your podcast app's "
                        "'Add by URL' option. For trustsphere.ai's Podcast "
                        "tab, add a Wix RSS Podcast widget and point it at "
                        "this URL — new episodes appear automatically each "
                        "morning."
                    )
            except Exception:
                pass

            # ----------------------------------------------------------
            # Previous briefings — last 3 days under today's, so listeners
            # can catch up on what they missed. Each row pairs the audio
            # player with a video link (when the video MP4 has real
            # content) and a transcript expander.
            # ----------------------------------------------------------
            recent_pods = recent_podcasts_meta(n=4)
            recent_vids = recent_videos_meta(n=4)
            vids_by_date = {v.date: v for v in recent_vids}
            today_iso = dt.date.today().isoformat()
            # Skip today's entry (already rendered above) and take the next 3.
            prior = [p for p in recent_pods if p.date != today_iso][:3]

            if prior:
                st.markdown(
                    "<div class='output-label' style='margin-top:1.5rem;'>"
                    "Previous briefings</div>",
                    unsafe_allow_html=True,
                )
                for prev in prior:
                    with st.container(border=True):
                        prev_v = vids_by_date.get(prev.date)
                        prev_label = prev.title or f"AML Agents Briefing — {prev.date}"
                        st.markdown(
                            f"**{prev_label}**  &nbsp; "
                            f"<span style='font-size:0.72rem;color:#6E6E73;'>"
                            f"{prev.date}  ·  ~{max(1, prev.duration_seconds // 60)} min"
                            f"</span>",
                            unsafe_allow_html=True,
                        )
                        if prev.mp3_path.exists():
                            try:
                                with open(prev.mp3_path, "rb") as f:
                                    st.audio(f.read(), format="audio/mp3")
                            except Exception:
                                st.caption("(audio file unreadable)")
                        # Show a small transcript expander for each prior day
                        with st.expander("Show transcript", expanded=False):
                            try:
                                pmeta = json.loads(prev.sidecar_path.read_text())
                                st.markdown(
                                    pmeta.get("script", "_(no script available)_")
                                )
                            except Exception:
                                st.markdown("_(transcript unavailable)_")
                        # Link to the matching video MP4, when one was generated
                        # with real content (size > 0). Streamlit can't show
                        # multiple inline videos efficiently, so the prior-day
                        # videos are exposed as a download/open link.
                        if (
                            prev_v
                            and prev_v.mp4_path.exists()
                            and prev_v.mp4_path.stat().st_size > 0
                        ):
                            st.markdown(
                                f"<div style='font-size:0.78rem; margin-top:0.4rem;'>"
                                f"🎬 Video briefing for {prev.date} — "
                                f"<a href='https://github.com/davidedwardhaynes-alt/aml-agents/raw/main/data/videos/{prev.date}.mp4' "
                                f"target='_blank' rel='noopener noreferrer'>"
                                f"download MP4 →</a></div>",
                                unsafe_allow_html=True,
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
            value=False,
            key="news_include_live",
            help=(
                "Pull from industry RSS (FinExtra, ACAMS Today, CoinDesk, etc.) — cached 30 min. "
                "Default OFF so the tab renders instantly with curated + auto-generated articles. "
                "Toggle on to pull live RSS items (adds 1-3 sec network delay)."
            ),
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

    def _two_sentence_intro(text: str) -> str:
        """Trim summary to ~2 sentences for the feed view."""
        if not text:
            return ""
        # Split on period followed by space; take first 2 sentences max.
        parts = []
        chunks = text.replace("\n", " ").split(". ")
        for c in chunks[:2]:
            c = c.strip()
            if c and not c.endswith("."):
                c = c + "."
            if c:
                parts.append(c)
        return " ".join(parts) if parts else text[:300]

    if not news_items:
        st.info("No news items match your filter.")
    else:
        for idx, item in enumerate(news_items):
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
                    intro = _two_sentence_intro(item.summary)
                    st.markdown(f"<small>{intro}</small>", unsafe_allow_html=True)

                    # Every news item gets an expandable details panel.
                    # If full_article is populated (curated + LLM-generated
                    # items), show the full long-form analysis. Otherwise
                    # (live RSS items pulled on-demand) show the available
                    # summary text. In all cases a 'View source' link sits
                    # at the bottom of the expander.
                    with st.expander("Read more", expanded=False):
                        if item.full_article:
                            st.markdown(item.full_article)
                        else:
                            st.markdown(
                                "<small style='color:#6E6E73;'>"
                                "Live RSS item — full analysis not generated. "
                                "Summary below; the source link contains the "
                                "publisher's full text."
                                "</small>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(item.summary or "_(no summary available)_")
                        st.markdown(
                            f"<div style='margin-top:0.8rem; font-size:0.78rem; "
                            f"color:#6E6E73;'>"
                            f"Source: <a href=\"{item.url}\" target=\"_blank\" "
                            f"rel=\"noopener noreferrer\">{item.source}</a>"
                            f"  ·  {item.date}  ·  {item.jurisdiction}"
                            f"  ·  <a href=\"{item.url}\" target=\"_blank\" "
                            f"rel=\"noopener noreferrer\">View source →</a>"
                            f"</div>",
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
