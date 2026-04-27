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
    status: str = "Available on request"


CONNECTORS: list[Connector] = [
    # Transaction monitoring
    Connector(
        "Hawk AI",
        "Transaction monitoring",
        "AI-native AML transaction monitoring; popular in EU fintech and digital banks.",
        "https://hawk.ai",
    ),
    Connector(
        "Unit21",
        "Transaction monitoring",
        "Modern TM and case management; widely deployed at US fintechs and crypto exchanges.",
        "https://www.unit21.ai",
    ),
    Connector(
        "Hummingbird",
        "Transaction monitoring & case management",
        "Compliance workflow platform with strong SAR/STR drafting and case-management primitives.",
        "https://www.hummingbird.co",
    ),
    Connector(
        "Quantexa",
        "Transaction monitoring & contextual decisioning",
        "Entity-resolution and network analytics; deployed at major banks (HSBC, Standard Chartered).",
        "https://www.quantexa.com",
    ),
    Connector(
        "Featurespace (Visa)",
        "Transaction monitoring",
        "ARIC adaptive behavioural-analytics platform; acquired by Visa 2024.",
        "https://www.featurespace.com",
    ),
    Connector(
        "Sardine",
        "Transaction monitoring & fraud",
        "Real-time fraud + AML monitoring; popular with crypto exchanges and neobanks.",
        "https://www.sardine.ai",
    ),
    Connector(
        "Lucinity",
        "Transaction monitoring",
        "AI-native AML platform with explainability focus.",
        "https://www.lucinity.com",
    ),
    Connector(
        "Cable",
        "Compliance assurance & TM testing",
        "Continuous compliance testing and assurance for TM rule effectiveness.",
        "https://cable.tech",
    ),
    Connector(
        "Resistant AI",
        "Document fraud & TM",
        "AI-driven document fraud detection and transaction monitoring.",
        "https://www.resistant.ai",
    ),
    Connector(
        "Napier",
        "Transaction monitoring",
        "AML compliance platform serving Tier-1 banks and large fintechs.",
        "https://www.napier.ai",
    ),
    Connector(
        "ThetaRay",
        "Transaction monitoring",
        "Cross-border AML detection using unsupervised ML; popular for correspondent banking.",
        "https://www.thetaray.com",
    ),
    Connector(
        "SAS Anti-Money Laundering",
        "Transaction monitoring (enterprise)",
        "Established enterprise AML platform; deployed at major Tier-1 banks globally.",
        "https://www.sas.com/en_us/software/anti-money-laundering.html",
    ),
    Connector(
        "NICE Actimize",
        "Transaction monitoring (enterprise)",
        "Comprehensive financial-crime suite including AML, fraud, and case management.",
        "https://www.niceactimize.com",
    ),
    Connector(
        "Oracle Financial Services AML",
        "Transaction monitoring (enterprise)",
        "Enterprise FCCM suite within Oracle's banking technology stack.",
        "https://www.oracle.com/financial-services/financial-crime/",
    ),
    Connector(
        "IBM Safer Payments",
        "Transaction monitoring (enterprise)",
        "Real-time fraud and AML monitoring; large-bank deployments.",
        "https://www.ibm.com/products/safer-payments",
    ),

    # KYC / KYB / EDD
    Connector(
        "Sumsub",
        "KYC / KYB / EDD",
        "Comprehensive identity verification; popular with fintech and crypto.",
        "https://sumsub.com",
    ),
    Connector(
        "Onfido (Entrust)",
        "KYC / identity verification",
        "Biometric and document-based KYC; acquired by Entrust 2024.",
        "https://onfido.com",
    ),
    Connector(
        "Trulioo",
        "KYC / KYB",
        "Global identity verification with broad coverage including APAC markets.",
        "https://www.trulioo.com",
    ),
    Connector(
        "Veriff",
        "KYC / identity verification",
        "Identity verification with strong fraud prevention.",
        "https://www.veriff.com",
    ),
    Connector(
        "Jumio",
        "KYC / identity verification",
        "Established KYC vendor with broad enterprise deployments.",
        "https://www.jumio.com",
    ),
    Connector(
        "Persona",
        "KYC / KYB / EDD",
        "Configurable identity platform popular with US fintech.",
        "https://withpersona.com",
    ),
    Connector(
        "Alloy",
        "KYC orchestration / decisioning",
        "Identity decision platform; orchestrates multiple KYC vendors.",
        "https://www.alloy.com",
    ),
    Connector(
        "ComplyCube",
        "KYC / AML",
        "All-in-one KYC and AML compliance platform.",
        "https://www.complycube.com",
    ),

    # Sanctions / PEP / adverse media
    Connector(
        "ComplyAdvantage",
        "Sanctions / PEP / adverse media",
        "Sanctions, PEP, and adverse media screening with continuous monitoring.",
        "https://complyadvantage.com",
    ),
    Connector(
        "Refinitiv World-Check (LSEG)",
        "Sanctions / PEP / adverse media",
        "Industry-standard global PEP and sanctions data; enterprise pricing.",
        "https://www.lseg.com/en/risk-intelligence/screening-and-monitoring",
    ),
    Connector(
        "Dow Jones Risk & Compliance",
        "Sanctions / PEP / adverse media",
        "Curated risk and compliance data; enterprise-grade.",
        "https://www.dowjones.com/professional/risk/",
    ),
    Connector(
        "Moody's BvD (Orbis / Compliance Catalyst)",
        "Corporate intelligence / UBO",
        "Beneficial-ownership and corporate-structure intelligence.",
        "https://www.moodys.com/web/en/us/capabilities/compliance.html",
    ),
    Connector(
        "Sayari",
        "Corporate intelligence / supply-chain risk",
        "Open-source corporate-network and counterparty risk data.",
        "https://sayari.com",
    ),
    Connector(
        "Castellum.AI",
        "Sanctions / PEP",
        "Real-time global sanctions and PEP data with API-first delivery.",
        "https://www.castellum.ai",
    ),
    Connector(
        "Kharon RiskWatcher",
        "Sanctions / supply-chain risk",
        "OFAC/EU sanctions risk research and screening.",
        "https://www.kharon.com",
    ),
    Connector(
        "OpenSanctions",
        "Sanctions / PEP / watchlists (open data)",
        "Open-data aggregated sanctions, PEP, and watchlist sources. Already wired into AML Agents.",
        "https://www.opensanctions.org",
        status="Connected (in-app screening)",
    ),

    # Case management / SAR filing
    Connector(
        "Verafin (Nasdaq)",
        "Case management / SAR filing",
        "End-to-end financial-crime suite for credit unions and community banks; Nasdaq-owned.",
        "https://www.verafin.com",
    ),
    Connector(
        "ACAMS Risk Assessment",
        "AML risk assessment",
        "Methodology-based AML enterprise-wide risk assessment platform.",
        "https://www.acams.org",
    ),

    # Crypto / KYT
    Connector(
        "Chainalysis",
        "Crypto KYT (know-your-transaction)",
        "Industry-leading blockchain analytics for VASP transaction monitoring.",
        "https://www.chainalysis.com",
    ),
    Connector(
        "TRM Labs",
        "Crypto KYT / investigations",
        "Blockchain intelligence for compliance and law-enforcement use.",
        "https://www.trmlabs.com",
    ),
    Connector(
        "Elliptic",
        "Crypto KYT / sanctions",
        "Blockchain analytics with strong sanctions and exchange-risk data.",
        "https://www.elliptic.co",
    ),

    # Core banking / data warehouse
    Connector(
        "Snowflake",
        "Data warehouse",
        "Pull customer, transaction, and KYC data from a Snowflake warehouse for STR drafting.",
        "https://www.snowflake.com",
    ),
    Connector(
        "Databricks",
        "Data lakehouse",
        "Pull data from a Databricks lakehouse for STR drafting and feature derivation.",
        "https://www.databricks.com",
    ),
    Connector(
        "Salesforce Financial Services Cloud",
        "CRM",
        "Pull customer KYC, relationship-manager notes, and adverse-media flags.",
        "https://www.salesforce.com/financial-services/",
    ),
]


def by_category() -> dict[str, list[Connector]]:
    """Group connectors by their category for UI rendering."""
    grouped: dict[str, list[Connector]] = {}
    for c in CONNECTORS:
        grouped.setdefault(c.category, []).append(c)
    return grouped
