import os
from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

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

st.set_page_config(
    page_title="AML Agents — STR Drafter",
    layout="wide",
    initial_sidebar_state="expanded",
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

# Sidebar
with st.sidebar:
    st.markdown("#### Configuration")
    jurisdiction = st.selectbox("Jurisdiction", list(RUBRICS.keys()))
    model = st.selectbox(
        "Model",
        ["claude-sonnet-4-6", "claude-opus-4-7"],
        index=0,
        help="Sonnet for cost-efficient drafts. Opus for complex multi-jurisdiction cases.",
    )

    st.markdown("---")
    st.markdown("#### Quick actions")
    if st.button("Load sample case", use_container_width=True):
        for k, v in SAMPLE_CASE.items():
            st.session_state[f"input_{k}"] = v
        st.session_state["input_recommendation"] = "File STR"
        st.rerun()

    if st.button("Clear form", use_container_width=True):
        for k in SAMPLE_CASE.keys():
            st.session_state[f"input_{k}"] = ""
        st.rerun()

    st.markdown("---")
    st.markdown("#### Jurisdiction coverage")
    st.markdown(
        "- Singapore STRO &nbsp;✓  \n"
        "- Hong Kong JFIU &nbsp;<small>v0.1</small>  \n"
        "- Malaysia FIED &nbsp;<small>v0.2</small>  \n"
        "- Australia AUSTRAC &nbsp;<small>v0.2</small>",
        unsafe_allow_html=True,
    )

# Branded header
st.markdown(
    """
<div class="brand-header">
    <span class="badge">v0 · Singapore</span>
    <h1>AML Agents — STR Narrative Drafter</h1>
    <p class="subtitle">AI-drafted suspicious transaction reports. Analyst-supplied facts only — never fabricated. Per-sentence audit trail.</p>
</div>
""",
    unsafe_allow_html=True,
)

# Jurisdiction guidance panel — collapsible, jurisdiction-aware
guidance_path = GUIDANCE.get(jurisdiction)
if guidance_path and guidance_path.exists():
    with st.expander(f"Filing guidance — {jurisdiction}", expanded=False):
        st.markdown(guidance_path.read_text())

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

    rubric_path = RUBRICS[jurisdiction]

    if rubric_path is None or not rubric_path.exists():
        st.error(f"Rubric for {jurisdiction} not yet implemented. v0 supports Singapore (STRO) only.")
    elif not (customer_name or analyst_notes or transactions):
        st.warning("Provide at least one of: customer name, transactions, or analyst notes.")
    elif not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY not set. Edit ~/dev/amlagents/.env and restart the app.")
    else:
        rubric = rubric_path.read_text()
        user_input = f"""[SUBJECT]
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
