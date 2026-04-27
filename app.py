import os
from datetime import date
from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from lib.sanctions import classify_match, search_sanctions, summarize_entity

# override=True ensures .env changes are picked up on every Streamlit rerun
# (without needing a full server restart). Critical for API key updates.
load_dotenv(override=True)

ROOT = Path(__file__).parent
RUBRICS = {
    "Singapore (STRO)": ROOT / "rubrics" / "strostr.md",
    "Hong Kong (JFIU)": None,
    "Malaysia (FIED)": None,
    "Australia (AUSTRAC SMR)": None,
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
        "Authorized institution — restricted licence bank / DTC",
        "Licensed corporation (SFC) — Types 1–12",
        "Authorized insurer",
        "Insurance broker / agent",
        "Money service operator (MSO)",
        "Stored value facility (SVF)",
        "Trust or company service provider (TCSP)",
        "Virtual asset service provider (VASP)",
        "Solicitor / law firm (DNFBP)",
        "Accountant (DNFBP)",
        "Estate agent (DNFBP)",
        "Precious metals / stones dealer (DNFBP)",
    ],
    "Malaysia (FIED)": [
        "— Select —",
        "Licensed bank / Islamic bank",
        "Investment bank",
        "Development financial institution (DFI)",
        "Money services business (MSB)",
        "Insurance / takaful operator",
        "Insurance broker",
        "Capital market intermediary (SC-licensed)",
        "E-money issuer",
        "Digital asset exchange (DAE)",
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
        "Authorised deposit-taking institution (ADI)",
        "Insurer / life insurance provider",
        "Designated remittance service",
        "Gambling service provider — casino / wagering / bookmaker",
        "Bullion dealer",
        "Digital currency exchange (DCE)",
        "Securities / derivatives dealer",
        "Solicitor (Tranche 2 — from 2026)",
        "Accountant / conveyancer (Tranche 2 — from 2026)",
        "Real estate agent (Tranche 2 — from 2026)",
        "Precious metals dealer (Tranche 2 — from 2026)",
    ],
}

SAMPLE_CASE = {
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
}

# Filing metadata defaults — per-institution values pulled from env vars so the
# user doesn't retype their institution and MLRO name on every case.
FILING_METADATA_DEFAULTS = {
    "input_reporting_institution": os.getenv("DEFAULT_REPORTING_INSTITUTION", ""),
    "input_str_reference": "",
    "input_prepared_by": os.getenv("DEFAULT_ANALYST_NAME", ""),
    "input_mlro_signoff": os.getenv("DEFAULT_MLRO_NAME", ""),
    "input_entity_category": "— Select —",
}

SAMPLE_FILING_METADATA = {
    "input_reporting_institution": "Demo Bank Singapore Pte Ltd (MAS-licensed bank)",
    "input_str_reference": "STR-2026-04-0042",
    "input_prepared_by": "Lim Wei Ling, Senior Compliance Analyst",
    "input_mlro_signoff": "Tan Boon Heng, MLRO",
    "input_entity_category": "Bank (full / wholesale / merchant)",
}

st.set_page_config(
    page_title="AML Agents — STR Drafter",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

# Filing metadata — pre-fill from env-var defaults if available
for k, v in FILING_METADATA_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "input_date_of_filing" not in st.session_state:
    st.session_state["input_date_of_filing"] = date.today()

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
    tool_col1, tool_col2, tool_col3, tool_col4 = st.columns([2, 2, 1, 1], gap="medium")
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
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("Load sample case", use_container_width=True):
            for k, v in SAMPLE_CASE.items():
                st.session_state[f"input_{k}"] = v
            st.session_state["input_recommendation"] = "File STR"
            for k, v in SAMPLE_FILING_METADATA.items():
                st.session_state[k] = v
            st.session_state["input_date_of_filing"] = date.today()
            st.rerun()
    with tool_col4:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("Clear form", use_container_width=True):
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

        col_a, col_b, col_c = st.columns([1, 1, 3])
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

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_write = getattr(usage, "cache_creation_input_tokens", 0)
        st.caption(
            f"Tokens — input {usage.input_tokens:,} · output {usage.output_tokens:,} · "
            f"cache read {cache_read:,} · cache write {cache_write:,}"
        )
