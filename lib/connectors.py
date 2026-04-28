"""Connectors catalogue — third-party platforms that AML Agents can integrate with.

This is a structural catalogue, not active connections. For v0, all connectors
show "Available on request" — real integrations are commercial deals
negotiated per-customer (each vendor has their own API and pricing).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Connector:
    name: str
    category: str
    description: str
    homepage: str
    status: str = "On request"  # Live / Beta / In development / Roadmap Q3 2026 / Roadmap Q4 2026 / Roadmap 2027 / On request
    integration_type: str = "REST API"  # REST API / webhook / SFTP / file upload / OAuth


# Status sort order — Live first, then in-progress, then roadmap, then on-request
STATUS_ORDER = {
    "Live": 0,
    "Beta": 1,
    "In development": 2,
    "Roadmap Q3 2026": 3,
    "Roadmap Q4 2026": 4,
    "Roadmap 2027": 5,
    "On request": 6,
}

STATUS_COLOURS = {
    "Live": "#10b981",
    "Beta": "#06b6d4",
    "In development": "#3b82f6",
    "Roadmap Q3 2026": "#8b5cf6",
    "Roadmap Q4 2026": "#a855f7",
    "Roadmap 2027": "#94a3b8",
    "On request": "#64748b",
}


CONNECTORS: list[Connector] = [
    # ---- Live (working in v0) ----
    Connector(
        "TrustSphere Risk Index",
        "Risk scoring (proprietary)",
        "Composite financial-crime risk score combining sanctions, PEP, adverse media, "
        "transaction-pattern, and beneficial-owner signals into a single 0–100 risk band. "
        "Powered by TrustSphere Partners.",
        "https://trustsphere.partners/risk-index",
        status="Live",
        integration_type="Native (in-app)",
    ),
    Connector(
        "OpenSanctions",
        "Sanctions / PEP / watchlists (open data)",
        "Open-data aggregated sanctions, PEP, and watchlist sources. Wired into the Subject "
        "section's screening button.",
        "https://www.opensanctions.org",
        status="Live",
        integration_type="REST API (/match/default)",
    ),
    Connector(
        "Anthropic Claude API",
        "LLM (narrative generation)",
        "Native PDF and image processing; primary engine for STR narrative drafting and "
        "uploaded-document analysis.",
        "https://docs.anthropic.com",
        status="Live",
        integration_type="REST API",
    ),

    # ---- In development (Q2 2026 — pre-event) ----
    Connector(
        "Sumsub",
        "KYC / KYB / EDD",
        "Comprehensive identity verification. Wiring webhook ingestion of KYC events for "
        "automatic Subject pre-fill.",
        "https://sumsub.com",
        status="In development",
        integration_type="Webhook + REST",
    ),
    Connector(
        "ComplyAdvantage",
        "Sanctions / PEP / adverse media",
        "Sanctions, PEP, and adverse-media screening with continuous monitoring. Replaces "
        "OpenSanctions for paid-tier customers needing higher-volume screening.",
        "https://complyadvantage.com",
        status="In development",
        integration_type="REST API",
    ),

    # ---- Roadmap Q3 2026 (priority based on ICP demand) ----
    Connector(
        "Hawk AI",
        "Transaction monitoring",
        "AI-native AML transaction monitoring; popular in EU fintech and digital banks. "
        "Connector to ingest alert payloads via webhook and pre-fill Subject + Triggering activity.",
        "https://hawk.ai",
        status="Roadmap Q3 2026",
        integration_type="Webhook (alert ingestion)",
    ),
    Connector(
        "Unit21",
        "Transaction monitoring",
        "Modern TM and case management. Connector to pull alerts and post-back the "
        "drafted narrative to Unit21 case files.",
        "https://www.unit21.ai",
        status="Roadmap Q3 2026",
        integration_type="REST API (bidirectional)",
    ),
    Connector(
        "Sardine",
        "Transaction monitoring & fraud",
        "Real-time fraud + AML monitoring; popular with crypto exchanges and neobanks.",
        "https://www.sardine.ai",
        status="Roadmap Q3 2026",
        integration_type="Webhook + REST",
    ),
    Connector(
        "Chainalysis",
        "Crypto KYT (know-your-transaction)",
        "Blockchain analytics for VASP TM. Connector to pull KYT scores into the Subject "
        "section automatically when a wallet address is provided.",
        "https://www.chainalysis.com",
        status="Roadmap Q3 2026",
        integration_type="REST API",
    ),
    Connector(
        "TRM Labs",
        "Crypto KYT / investigations",
        "Blockchain intelligence for compliance and law-enforcement use.",
        "https://www.trmlabs.com",
        status="Roadmap Q3 2026",
        integration_type="REST API",
    ),
    Connector(
        "Elliptic",
        "Crypto KYT / sanctions",
        "Blockchain analytics with strong sanctions and exchange-risk data.",
        "https://www.elliptic.co",
        status="Roadmap Q3 2026",
        integration_type="REST API",
    ),

    # ---- Roadmap Q4 2026 ----
    Connector(
        "Hummingbird",
        "Transaction monitoring & case management",
        "Compliance workflow with case-management primitives. Bidirectional connector to "
        "post draft narratives back into Hummingbird cases.",
        "https://www.hummingbird.co",
        status="Roadmap Q4 2026",
        integration_type="REST API (bidirectional)",
    ),
    Connector(
        "Quantexa",
        "Transaction monitoring & contextual decisioning",
        "Entity-resolution and network analytics; deployed at HSBC, StanChart, etc.",
        "https://www.quantexa.com",
        status="Roadmap Q4 2026",
        integration_type="REST API",
    ),
    Connector(
        "Lucinity",
        "Transaction monitoring",
        "AI-native AML platform with explainability focus.",
        "https://www.lucinity.com",
        status="Roadmap Q4 2026",
        integration_type="REST API",
    ),
    Connector(
        "Onfido (Entrust)",
        "KYC / identity verification",
        "Biometric and document-based KYC; acquired by Entrust 2024.",
        "https://onfido.com",
        status="Roadmap Q4 2026",
        integration_type="Webhook + REST",
    ),
    Connector(
        "Persona",
        "KYC / KYB / EDD",
        "Configurable identity platform popular with US fintech.",
        "https://withpersona.com",
        status="Roadmap Q4 2026",
        integration_type="Webhook + REST",
    ),
    Connector(
        "Alloy",
        "KYC orchestration / decisioning",
        "Identity decision platform orchestrating multiple KYC vendors.",
        "https://www.alloy.com",
        status="Roadmap Q4 2026",
        integration_type="REST API",
    ),
    Connector(
        "Refinitiv World-Check (LSEG)",
        "Sanctions / PEP / adverse media",
        "Industry-standard global PEP and sanctions data. Enterprise-tier replacement for "
        "OpenSanctions where customers already have a World-Check licence.",
        "https://www.lseg.com/en/risk-intelligence/screening-and-monitoring",
        status="Roadmap Q4 2026",
        integration_type="REST API",
    ),
    Connector(
        "Dow Jones Risk & Compliance",
        "Sanctions / PEP / adverse media",
        "Curated risk and compliance data; enterprise-grade.",
        "https://www.dowjones.com/professional/risk/",
        status="Roadmap Q4 2026",
        integration_type="REST API",
    ),
    Connector(
        "Snowflake",
        "Data warehouse",
        "Pull customer / transaction / KYC data directly from a Snowflake warehouse to "
        "pre-fill case forms.",
        "https://www.snowflake.com",
        status="Roadmap Q4 2026",
        integration_type="JDBC / REST",
    ),
    Connector(
        "Databricks",
        "Data lakehouse",
        "Pull data from a Databricks lakehouse for STR drafting and feature derivation.",
        "https://www.databricks.com",
        status="Roadmap Q4 2026",
        integration_type="JDBC / REST",
    ),

    # ---- Roadmap 2027 ----
    Connector(
        "Featurespace (Visa)",
        "Transaction monitoring",
        "ARIC adaptive behavioural-analytics platform; acquired by Visa 2024.",
        "https://www.featurespace.com",
        status="Roadmap 2027",
        integration_type="Webhook",
    ),
    Connector(
        "Cable",
        "Compliance assurance & TM testing",
        "Continuous compliance testing and assurance for TM rule effectiveness.",
        "https://cable.tech",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "Resistant AI",
        "Document fraud & TM",
        "AI-driven document fraud detection.",
        "https://www.resistant.ai",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "Napier",
        "Transaction monitoring",
        "AML compliance platform serving Tier-1 banks.",
        "https://www.napier.ai",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "ThetaRay",
        "Transaction monitoring",
        "Cross-border AML detection using unsupervised ML.",
        "https://www.thetaray.com",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "SAS Anti-Money Laundering",
        "Transaction monitoring (enterprise)",
        "Established enterprise AML platform.",
        "https://www.sas.com/en_us/software/anti-money-laundering.html",
        status="Roadmap 2027",
        integration_type="SFTP / REST",
    ),
    Connector(
        "NICE Actimize",
        "Transaction monitoring (enterprise)",
        "Comprehensive financial-crime suite.",
        "https://www.niceactimize.com",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "Oracle Financial Services AML",
        "Transaction monitoring (enterprise)",
        "Enterprise FCCM suite within Oracle's banking stack.",
        "https://www.oracle.com/financial-services/financial-crime/",
        status="Roadmap 2027",
        integration_type="REST API / JDBC",
    ),
    Connector(
        "IBM Safer Payments",
        "Transaction monitoring (enterprise)",
        "Real-time fraud and AML monitoring.",
        "https://www.ibm.com/products/safer-payments",
        status="Roadmap 2027",
        integration_type="REST API",
    ),
    Connector(
        "Salesforce Financial Services Cloud",
        "CRM",
        "Pull customer KYC, RM notes, and adverse-media flags from Salesforce.",
        "https://www.salesforce.com/financial-services/",
        status="Roadmap 2027",
        integration_type="REST API",
    ),

    # ---- On request (build if a customer needs it) ----
    Connector(
        "Trulioo",
        "KYC / KYB",
        "Global identity verification with broad APAC coverage.",
        "https://www.trulioo.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Veriff",
        "KYC / identity verification",
        "Identity verification with strong fraud prevention.",
        "https://www.veriff.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Jumio",
        "KYC / identity verification",
        "Established KYC vendor with broad enterprise deployments.",
        "https://www.jumio.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "ComplyCube",
        "KYC / AML",
        "All-in-one KYC and AML compliance platform.",
        "https://www.complycube.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Moody's BvD (Orbis / Compliance Catalyst)",
        "Corporate intelligence / UBO",
        "Beneficial-ownership and corporate-structure intelligence.",
        "https://www.moodys.com/web/en/us/capabilities/compliance.html",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Sayari",
        "Corporate intelligence / supply-chain risk",
        "Open-source corporate-network and counterparty risk data.",
        "https://sayari.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Castellum.AI",
        "Sanctions / PEP",
        "Real-time global sanctions and PEP data with API-first delivery.",
        "https://www.castellum.ai",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Kharon RiskWatcher",
        "Sanctions / supply-chain risk",
        "OFAC/EU sanctions risk research and screening.",
        "https://www.kharon.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "Verafin (Nasdaq)",
        "Case management / SAR filing",
        "End-to-end FCC suite for credit unions and community banks.",
        "https://www.verafin.com",
        status="On request",
        integration_type="REST API",
    ),
    Connector(
        "ACAMS Risk Assessment",
        "AML risk assessment",
        "Methodology-based AML enterprise-wide risk assessment.",
        "https://www.acams.org",
        status="On request",
        integration_type="File upload",
    ),
]


def by_category() -> dict[str, list[Connector]]:
    """Group connectors by their category for UI rendering."""
    grouped: dict[str, list[Connector]] = {}
    for c in CONNECTORS:
        grouped.setdefault(c.category, []).append(c)
    return grouped


def by_status() -> dict[str, list[Connector]]:
    """Group connectors by their integration status, ordered by STATUS_ORDER."""
    grouped: dict[str, list[Connector]] = {}
    for c in CONNECTORS:
        grouped.setdefault(c.status, []).append(c)
    # Order by STATUS_ORDER
    ordered: dict[str, list[Connector]] = {}
    for status in sorted(grouped.keys(), key=lambda s: STATUS_ORDER.get(s, 99)):
        ordered[status] = sorted(grouped[status], key=lambda c: c.name.lower())
    return ordered


ALL_STATUSES = list(STATUS_ORDER.keys())
