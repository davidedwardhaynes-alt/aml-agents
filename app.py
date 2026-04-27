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

st.set_page_config(page_title="AML Agents — STR Drafter", layout="wide")

st.sidebar.title("Configuration")
jurisdiction = st.sidebar.selectbox("Jurisdiction", list(RUBRICS.keys()))
model = st.sidebar.selectbox(
    "Model",
    ["claude-sonnet-4-6", "claude-opus-4-7"],
    index=0,
)
st.sidebar.caption("Sonnet for cost. Opus for complex multi-jurisdiction cases.")
st.sidebar.markdown("---")
st.sidebar.caption(
    "v0: STRO only. JFIU / FIED / AUSTRAC ship as rubric files in v0.1."
)

st.title("AML Agents — STR Narrative Drafter")
st.caption(
    "AI-drafted suspicious transaction report narratives. "
    "Analyst-supplied facts only — never fabricated. Human stays in the loop."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Subject")
    customer_name = st.text_input("Customer name")
    customer_id = st.text_input("Customer ID / Account number")
    customer_kyc = st.text_area(
        "KYC summary (occupation, source of funds, expected activity)",
        height=110,
    )

    st.subheader("Triggering activity")
    transactions = st.text_area(
        "Transactions (one per line: date | amount | currency | counterparty | channel)",
        height=130,
    )
    alert_reason = st.text_input("Alert / triage reason")
    red_flags = st.text_area("Red flag indicators observed", height=100)

with col2:
    st.subheader("Analyst investigation")
    analyst_notes = st.text_area(
        "Investigation notes — what you reviewed, found, confirmed, could not verify",
        height=320,
    )
    recommendation = st.selectbox(
        "Recommended action",
        ["File STR", "No further action", "Enhanced monitoring", "Account closure"],
    )

if st.button("Generate narrative", type="primary"):
    rubric_path = RUBRICS[jurisdiction]

    if rubric_path is None or not rubric_path.exists():
        st.error(
            f"Rubric for {jurisdiction} is not yet implemented. "
            "v0 supports Singapore (STRO) only."
        )
    elif not (customer_name or analyst_notes or transactions):
        st.warning(
            "Provide at least one of: customer name, transactions, or analyst notes."
        )
    elif not os.getenv("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and paste your key. "
            "Get one at https://console.anthropic.com"
        )
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

Draft the STR narrative following the rubric above. Use only facts stated in the inputs. Never fabricate."""

        client = Anthropic()

        with st.spinner("Drafting narrative..."):
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

        st.subheader("Generated narrative")
        st.markdown(narrative)

        usage = response.usage
        st.caption(
            f"Tokens — input: {usage.input_tokens} | "
            f"output: {usage.output_tokens} | "
            f"cache read: {getattr(usage, 'cache_read_input_tokens', 0)} | "
            f"cache write: {getattr(usage, 'cache_creation_input_tokens', 0)}"
        )

        st.download_button(
            "Download narrative",
            data=narrative,
            file_name=f"STR_narrative_{customer_id or 'draft'}.txt",
            mime="text/plain",
        )
