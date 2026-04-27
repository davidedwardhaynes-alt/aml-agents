import io
import os
import re
from datetime import date
from pathlib import Path

import markdown as md_pkg
import streamlit as st
import streamlit_authenticator as stauth
from anthropic import Anthropic
from dotenv import load_dotenv
from fpdf import FPDF

from auth.users import (
    get_user_profile,
    load_config,
    save_config,
    update_user_profile,
)
from lib.sanctions import classify_match, search_sanctions, summarize_entity

# override=True ensures .env changes are picked up on every Streamlit rerun
# (without needing a full server restart). Critical for API key updates.
load_dotenv(override=True)


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
    page_title="AML Agents — STR Drafter",
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
    st.markdown(f"### Signed in as")
    st.markdown(f"**{auth_name}**  \n`{auth_username}`")

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
        <h1>AML Agents — STR Narrative Drafter</h1>
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

        # Sanctions / PEP / watchlist screening
        current_name = st.session_state.get("input_customer_name", "")
        screen_btn_col, _ = st.columns([1, 1])
        with screen_btn_col:
            screen = st.button(
                "Screen against sanctions / PEP lists",
                use_container_width=True,
                disabled=len(current_name.strip()) < 3,
                help="Searches OpenSanctions (UN, OFAC, EU, UK HMT, MAS, AUSTRAC, and 200+ other lists, plus PEPs).",
            )

        if screen:
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

    st.markdown('<div class="section-label">Triggering activity</div>', unsafe_allow_html=True)
    with st.container(border=True):
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
            height=380,
        )
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
Reason: {alert_reason or '[not provided]'}
Red flags: {red_flags or '[not provided]'}

[ANALYST NOTES]
{analyst_notes or '[not provided]'}

[RECOMMENDATION]
{recommendation}

Draft the STR narrative following the rubric. Use only facts stated in the inputs. Never fabricate."""

        client = Anthropic()

        with st.spinner("Drafting narrative…"):
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                system=[
                    {
                        "type": "text",
                        "text": rubric,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_input}],
            )

        narrative = response.content[0].text

        st.markdown('<div class="output-label">Generated narrative</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(narrative)

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
