"""Connector-derived risk signals — the structured "why this was flagged" payload.

Each sample case ships with a curated list of risk signals that would, in production,
be sourced from the 161 connectors (BioCatch, Chainalysis, ThreatMetrix, ComplyAdvantage,
SAS, NICE Actimize, Hawk AI, Featurespace, Sift, Plaid, Trulioo, etc.).

The signals serve three purposes:
  1. UI — render as a "Risk signals from connectors" card list in the Draft STR tab,
     showing the analyst exactly what each upstream system flagged.
  2. LLM prompt — fed into the narrative-generation prompt so the drafted STR can
     cite "BioCatch flagged a 92% mouse-dynamics deviation" rather than vaguely say
     "the customer's behaviour was unusual".
  3. Demo storytelling — concretely demonstrates how the connector ecosystem feeds
     into a single STR narrative, which is the company's core pitch.

Each signal mirrors how the connector would actually report in production: precise
numeric findings + the AML implication. Severity is a 3-band classification.

Adding a new sample case? Add a new dict entry keyed by the case label that the form
loads. If a case has no entry here the UI gracefully shows nothing.
"""

from __future__ import annotations  # Python 3.9 compat

from dataclasses import dataclass, field
from typing import Literal


Severity = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True)
class ConnectorSignal:
    """A single risk signal as it would arrive from one of the 161 connectors."""

    connector: str          # "BioCatch", "Chainalysis", "ComplyAdvantage", ...
    category: str           # one of CATEGORIES from lib.connectors
    signal: str             # the raw observation, e.g. "Mouse-dynamics deviation 87%"
    implication: str        # AML/CTF implication, e.g. "Possible remote takeover"
    severity: Severity = "MEDIUM"
    confidence: int = 80    # 0-100 — connector's own confidence in the finding
    timestamp: str = ""     # ISO-ish, e.g. "2026-04-15 14:32 SGT"


def severity_emoji(s: Severity) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(s, "⚪")


def severity_color(s: Severity) -> str:
    return {"HIGH": "#FF3B30", "MEDIUM": "#FF9500", "LOW": "#FFCC00"}.get(s, "#86868B")


# ---------------------------------------------------------------------------
# Sample case → list of signals.
# Keys must match the SAMPLE_CASE labels used by the form (case_key in app.py).
# ---------------------------------------------------------------------------

SIGNALS_BY_CASE: dict[str, list[ConnectorSignal]] = {

    # =====================================================================
    # SINGAPORE (STRO) — ACME Trading: trade-based ML, fintech wholesale
    # =====================================================================
    "Singapore (STRO)": [
        ConnectorSignal(
            connector="ComplyAdvantage",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Counterparty Mohammed A. (UAE individual) matched against UN "
                "Consolidated Sanctions List — entry added 2026-02-11, name and "
                "DOB match score 94%."
            ),
            implication=(
                "Direct sanctions exposure. MAS Notice 626 §6.1 requires immediate "
                "freeze of suspected sanctioned-party transactions and STRO filing "
                "irrespective of monetary threshold."
            ),
            severity="HIGH",
            confidence=94,
            timestamp="2026-04-16 09:14 SGT",
        ),
        ConnectorSignal(
            connector="TrustSphere Risk Index",
            category="Risk Orchestration",
            signal=(
                "Customer composite risk score moved from 32 (Medium-Low) at "
                "onboarding to 87 (High) over 72h — driven by 3x volume spike + "
                "new high-risk-jurisdiction counterparties + sanctions hit."
            ),
            implication=(
                "Step-change in customer risk profile demands EDD refresh and "
                "MLRO review per the bank's risk-rating policy."
            ),
            severity="HIGH",
            confidence=92,
            timestamp="2026-04-17 16:45 SGT",
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Transaction monitoring rule TBM-014 fired: 3 outbound wires within "
                "72h totalling SGD 1.25M, each individually below the SGD 500k "
                "internal review threshold (structuring score: 0.91)."
            ),
            implication=(
                "Classic structuring / smurfing pattern. STRO's 2024 Trade-Based "
                "ML typology bulletin lists this as the #1 indicator for "
                "wholesale-banking misuse."
            ),
            severity="HIGH",
            confidence=91,
            timestamp="2026-04-17 17:02 SGT",
        ),
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "Beneficiary 'HK-XYZ Ltd' identified as a Hong Kong shell "
                "company — no employees, no website, registered address shared "
                "with 47 other entities. Incorporated 2025-11-22, six weeks "
                "before first inbound payment."
            ),
            implication=(
                "Newly-incorporated shell counterparty inconsistent with "
                "declared 'new supplier deals'. Suggests a controlled funnel "
                "rather than a genuine commercial relationship."
            ),
            severity="HIGH",
            confidence=88,
        ),
        ConnectorSignal(
            connector="ThreatMetrix",
            category="Behavioral & Device Intelligence",
            signal=(
                "Three of the four payment instructions originated from a "
                "session using a residential VPN exit node in Dubai — first time "
                "this customer has authenticated from outside Singapore in 18 "
                "months of activity."
            ),
            implication=(
                "Account-takeover risk and/or third-party operational control. "
                "Adds weight to the 'inability to explain transactions' finding "
                "from RM outreach."
            ),
            severity="MEDIUM",
            confidence=84,
            timestamp="2026-04-15 22:09 SGT",
        ),
    ],

    # =====================================================================
    # HONG KONG (JFIU) — Golden Harbor: jewelry / TBML
    # =====================================================================
    "Hong Kong (JFIU)": [
        ConnectorSignal(
            connector="ComplyAdvantage",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Counterparty Mohammad Rezaie matched against OFAC SDN List "
                "(SDGT designation, entry 2024-07) — name + Iranian-residency "
                "match score 96%."
            ),
            implication=(
                "OFAC-sanctioned counterparty with Iran nexus. AMLO §25A "
                "filing obligation triggered; consent-from-JFIU required before "
                "any payout."
            ),
            severity="HIGH",
            confidence=96,
            timestamp="2026-04-13 11:08 HKT",
        ),
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "Hidden BO discovery: Mr Chan Wai-Lung (51%) holds via BVI "
                "nominee 'Eastwood Capital Ltd' — undisclosed at onboarding. "
                "Mr Chan named in two earlier HK casino-junket investigations "
                "(2022, 2024)."
            ),
            implication=(
                "Material breach of CDD obligations (HKMA SPM CG-5). The "
                "concealed BO is the controlling mind of the suspected "
                "layering ring."
            ),
            severity="HIGH",
            confidence=91,
        ),
        ConnectorSignal(
            connector="Featurespace ARIC",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Trade-based ML scenario score 0.94 — invoiced jewelry prices "
                "21% above LBMA reference for comparable lots; cash-component "
                "ratio (28%) inconsistent with B2B precious-stones peers."
            ),
            implication=(
                "Classic over-invoicing TBML. JFIU's 2025 typology guidance "
                "highlights jewelry trade as the #2 TBML vector in HK after "
                "electronics."
            ),
            severity="HIGH",
            confidence=94,
            timestamp="2026-04-14 15:22 HKT",
        ),
        ConnectorSignal(
            connector="HKMA Peer-Bank Intel (informal)",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Mainland counterparty 'Shenzhen Lihua Trading Co.' flagged "
                "by 4 of 11 HKMA AI-FCC member banks in the past 90 days for "
                "TBML-typology activity."
            ),
            implication=(
                "Cross-bank consensus signal materially raises the suspicion "
                "threshold per the HKAB Guidance on Information Sharing in "
                "Financial Crime."
            ),
            severity="MEDIUM",
            confidence=82,
        ),
        ConnectorSignal(
            connector="Dow Jones Adverse Media",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "HK Free Press article 2026-03-28 names 'Golden Harbor Holdings' "
                "in casino-junket linked layering ring. Article cites two anonymous "
                "ICAC sources."
            ),
            implication=(
                "Adverse-media confirmation of the underlying typology. STRO/JFIU "
                "filing now defensible on EITHER independent source."
            ),
            severity="HIGH",
            confidence=86,
        ),
    ],

    # =====================================================================
    # HK — VASP darknet flow (Cheung Ka-Wai)
    # =====================================================================
    "Hong Kong (JFIU) — VASP darknet flow": [
        ConnectorSignal(
            connector="Chainalysis KYT",
            category="Crypto AML & Blockchain Analytics",
            signal=(
                "Inbound wallet bc1q...t8x: 100% of the 2.45 BTC traces within "
                "2 hops to Hydra-successor darknet market 'Mega' (cluster "
                "exposure score 0.98). Wallet 3Mq2...wRn: 87% darknet exposure "
                "via the same cluster."
            ),
            implication=(
                "Knowing receipt of crypto with darknet provenance is an SFC "
                "VASP Code §11 STR trigger and a JFIU §25A predicate-offence "
                "indicator."
            ),
            severity="HIGH",
            confidence=98,
            timestamp="2026-04-08 20:31 HKT",
        ),
        ConnectorSignal(
            connector="TRM Labs",
            category="Crypto AML & Blockchain Analytics",
            signal=(
                "Independent verification — same wallets show 92% combined "
                "darknet/sanctioned-mixer exposure. TRM risk score 'Severe'."
            ),
            implication=(
                "Two independent KYT vendors agreeing on darknet provenance "
                "removes the 'tooling-error' defence."
            ),
            severity="HIGH",
            confidence=96,
        ),
        ConnectorSignal(
            connector="BioCatch",
            category="Behavioral & Device Intelligence",
            signal=(
                "Session behavioural profile during the 2026-04-11 BTC-to-HKD "
                "conversion deviated 87% from the customer's 6-month baseline "
                "(typing cadence, session-length, device-orientation). Score: "
                "Coached/Scripted-Activity 0.79."
            ),
            implication=(
                "Suggests third-party operational control — consistent with the "
                "knowing-layering-agent assessment from RM outreach."
            ),
            severity="MEDIUM",
            confidence=79,
            timestamp="2026-04-11 14:06 HKT",
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Withdrawal pattern matches typology TPL-VASP-07 ('crypto "
                "cash-out via third-party bank rails'): inbound BTC → same-day "
                "HKD conversion → outbound to ≥2 unrelated bank accounts."
            ),
            implication=(
                "Direct match to SFC/HKMA 2025 'crypto cash-out' typology "
                "bulletin. Industry-recognised pattern strengthens the STR."
            ),
            severity="HIGH",
            confidence=93,
        ),
        ConnectorSignal(
            connector="ThreatMetrix",
            category="Behavioral & Device Intelligence",
            signal=(
                "Withdrawal-instruction sessions originated from a Mongolian "
                "residential proxy not previously used by this customer. Device "
                "fingerprint matches three other unrelated customers flagged in "
                "the past 60 days."
            ),
            implication=(
                "Cross-customer device reuse implies a coordinated mule-recruitment "
                "ring, not isolated illicit activity."
            ),
            severity="HIGH",
            confidence=88,
        ),
    ],

    # =====================================================================
    # HK — Casino-junket bank layering (Pearl Maritime)
    # =====================================================================
    "Hong Kong (JFIU) — Casino-junket bank layering": [
        ConnectorSignal(
            connector="HKMA Peer-Bank Intel (informal)",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Macau counterparties 'Macau Sky Tourism Ltd' and 'Macau Star "
                "Resort Travel Co' flagged by 7 of 11 AI-FCC member banks as "
                "Macau-junket-affiliated layering vehicles."
            ),
            implication=(
                "Multi-bank consensus on junket affiliation removes any "
                "ambiguity. JFIU consent application defensible on this alone."
            ),
            severity="HIGH",
            confidence=89,
        ),
        ConnectorSignal(
            connector="Featurespace ARIC",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Round-trip-transfer detection: 4.5M HKD outbound 2026-04-16 → "
                "same amount inbound 2026-04-17 via different counterparty in "
                "the same Shenzhen postcode. Round-trip score 0.96."
            ),
            implication=(
                "Round-tripping is a tier-1 layering indicator. JFIU's 2024 "
                "typology bulletin explicitly cites this exact pattern for "
                "marine-equipment shell companies."
            ),
            severity="HIGH",
            confidence=96,
            timestamp="2026-04-17 09:18 HKT",
        ),
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "Pearl Maritime's three director-related shell companies "
                "('Pearl Marine Logistics Ltd', 'East Pearl Equipment Ltd', "
                "'Pearl Trans-Pacific Ltd') incorporated within 90 days of each "
                "other in mid-2024, all sharing the same registered-agent address."
            ),
            implication=(
                "Layering-vehicle proliferation pattern. EDD failed to detect "
                "the related-party network at onboarding."
            ),
            severity="MEDIUM",
            confidence=85,
        ),
        ConnectorSignal(
            connector="Dow Jones Adverse Media",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Mr Wong Tin-Lok (75% BO) named in Macau ICAC 2025 enforcement "
                "filing as a person-of-interest in an active junket-laundering "
                "investigation. Filing public 2026-02-14."
            ),
            implication=(
                "Director under active enforcement scrutiny in adjacent "
                "jurisdiction is a definitive STR trigger under HKMA SPM AML-3."
            ),
            severity="HIGH",
            confidence=92,
        ),
    ],

    # =====================================================================
    # SG — DPT cash-out via Tornado Cash (Vanessa Tan)
    # =====================================================================
    "Singapore (STRO) — DPT cash-out": [
        ConnectorSignal(
            connector="Chainalysis KYT",
            category="Crypto AML & Blockchain Analytics",
            signal=(
                "100% of inbound 2.8 BTC traces to Tornado Cash output within "
                "2 hops. Mixer-exposure cluster score 0.99 — highest band."
            ),
            implication=(
                "Tornado Cash is OFAC-designated (SDN, August 2022). Knowing "
                "receipt of mixer-output funds is a per-se MAS PSN02 STR "
                "trigger and a sanctions issue."
            ),
            severity="HIGH",
            confidence=99,
            timestamp="2026-04-09 14:18 SGT",
        ),
        ConnectorSignal(
            connector="TRM Labs",
            category="Crypto AML & Blockchain Analytics",
            signal=(
                "Independent re-trace: same wallet shows 96% Tornado-Cash + "
                "12% Hydra-successor exposure within 3 hops."
            ),
            implication=(
                "Two-vendor agreement removes any 'tooling-error' defence. "
                "Source of crypto unambiguously illicit."
            ),
            severity="HIGH",
            confidence=96,
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Withdrawal pattern matches typology TPL-DPT-04 (DPT cash-out "
                "via third-party bank rails): inbound BTC → same-day SGD "
                "conversion → outbound to bank account in different name."
            ),
            implication=(
                "Direct match to MAS 2025 typology bulletin on DPT cash-out "
                "for darknet/scam proceeds. Pattern recognition strengthens STR."
            ),
            severity="HIGH",
            confidence=93,
        ),
        ConnectorSignal(
            connector="ThreatMetrix",
            category="Behavioral & Device Intelligence",
            signal=(
                "BTC-deposit and SGD-withdrawal sessions originated from a "
                "Mongolian residential proxy not previously used by this "
                "customer. Device fingerprint shared with 4 unrelated "
                "high-risk customers in the past 30 days."
            ),
            implication=(
                "Device-fingerprint reuse indicates a coordinated mule-network "
                "operation — not isolated illicit activity."
            ),
            severity="HIGH",
            confidence=87,
        ),
    ],

    # =====================================================================
    # SG — Real estate DNFBP / Sentosa Cove SPV (Crescent Bay)
    # =====================================================================
    "Singapore (STRO) — Real estate DNFBP": [
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "BVI-Cayman SPV chain mapped: Crescent Bay (SG) → Eastwood "
                "Holdings (BVI) → Beachfront Trust (Cayman) → UBO Mr Wei. "
                "All three layers incorporated within 60 days of each other "
                "in early 2026 — pure transaction-vehicle pattern, no "
                "operating substance."
            ),
            implication=(
                "Three-layer offshore wrapper introduced solely for this "
                "transaction. Tier-1 indicator under FATF DNFBP risk guide "
                "for high-value real estate."
            ),
            severity="HIGH",
            confidence=94,
        ),
        ConnectorSignal(
            connector="Dow Jones Adverse Media",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "UBO Mr Wei Jianzhong: Caixin (PRC) article 2025-05-14 names "
                "him in connection with state-owned enterprise irregularities "
                "at Hebei Iron & Steel Group. Article cites two anonymous "
                "Central Commission for Discipline Inspection sources."
            ),
            implication=(
                "Adverse-media confirmation of UBO risk profile. SoF claim "
                "('family manufacturing wealth') becomes implausible given "
                "named SOE-corruption nexus."
            ),
            severity="HIGH",
            confidence=88,
        ),
        ConnectorSignal(
            connector="TrustSphere Risk Index",
            category="Risk Orchestration",
            signal=(
                "Composite SPV risk score 91/100 (Severe). Drivers: BVI/"
                "Cayman wrapper + adverse-media UBO hit + price 22% above "
                "URA caveat comparables + offshore-only funding."
            ),
            implication=(
                "Multi-factor red-flag stack. CEA-licensed real estate agent "
                "is in DNFBP STR scope under MAS supervision."
            ),
            severity="HIGH",
            confidence=91,
        ),
        ConnectorSignal(
            connector="URA Caveat / RealLink",
            category="Specialized Solutions",
            signal=(
                "Purchase price SGD 28M is 22% above the median of the past "
                "8 closed comparable sales in the same Sentosa Cove "
                "development (last 12 months)."
            ),
            implication=(
                "Materially over-market price is a classic over-valuation "
                "indicator for real-estate-based laundering."
            ),
            severity="MEDIUM",
            confidence=86,
        ),
    ],

    # =====================================================================
    # SG — Lawyer trust account misuse (Apex Legal LLC)
    # =====================================================================
    "Singapore (STRO) — Lawyer trust account misuse": [
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "BVI destination 'Greenfield Capital Ltd' has no operating "
                "history, no employees, and shares its registered agent with "
                "31 other shells implicated in 4 prior STR filings across "
                "the SG legal sector."
            ),
            implication=(
                "Pure pass-through shell. No commercial nexus to declared SG "
                "commodity-broking business."
            ),
            severity="HIGH",
            confidence=90,
        ),
        ConnectorSignal(
            connector="Dow Jones Adverse Media",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Goldcrest UBO Mr Tan Boon-Hwa: Straits Times 2026-02-08 "
                "article names him in alleged commodity-fraud syndicate "
                "investigation by SPF Commercial Affairs Department."
            ),
            implication=(
                "Adverse-media + alleged predicate-offence link makes the "
                "trust-account flow defensibly suspicious under Law Society "
                "AML/CFT Practice Direction."
            ),
            severity="HIGH",
            confidence=89,
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Trust-account pattern: 99% pass-through (in/out within 24h, "
                "minimal retention) with no underlying matter file. Matches "
                "FATF DNFBP layering typology TPL-LEG-02."
            ),
            implication=(
                "Legal-sector trust-account abuse is a known FATF mutual-"
                "evaluation finding for SG. STRO STR obligation crystallises."
            ),
            severity="HIGH",
            confidence=92,
        ),
    ],

    # =====================================================================
    # SG — PSMD gold cash conversion (Liu Wenfeng)
    # =====================================================================
    "Singapore (STRO) — PSMD gold cash conversion": [
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Structuring rule fired: 3 cash purchases of SGD 8,500 / "
                "8,200 / 9,800 — all just below the SGD 10,000 cash-CDD "
                "trigger. Structuring score 0.97."
            ),
            implication=(
                "Classic just-below-threshold structuring. STRO 2024 PSMD "
                "typology bulletin lists this as the #1 red flag for "
                "precious-metals dealers."
            ),
            severity="HIGH",
            confidence=97,
            timestamp="2026-04-13 15:42 SGT",
        ),
        ConnectorSignal(
            connector="ID-Pal",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "Day 2 visit: customer presented a different passport with "
                "different name from Day 1. Document-mismatch confidence "
                "98%. Junior staff did not enforce CDD escalation."
            ),
            implication=(
                "Multi-identity activity is a definitive STR trigger under "
                "MAS Notice PSMD-N01 §6.4. Internal-control failure also "
                "warranting escalation."
            ),
            severity="HIGH",
            confidence=98,
        ),
        ConnectorSignal(
            connector="TrustSphere Risk Index",
            category="Risk Orchestration",
            signal=(
                "Customer composite score 89/100 (Severe). Drivers: "
                "structuring + multi-identity + cash-band uniformity "
                "(all 100-dollar notes from same bank-band wrappers) + "
                "immediate onward sale to unaffiliated jeweller."
            ),
            implication=(
                "All four drivers map directly to FATF/STRO typology for "
                "proceeds-of-crime cash being layered via gold."
            ),
            severity="HIGH",
            confidence=91,
        ),
    ],

    # =====================================================================
    # SG — Capital markets OTC wash trading (Helios / Aleksandr V.)
    # =====================================================================
    "Singapore (STRO) — Capital markets OTC wash trading": [
        ConnectorSignal(
            connector="ComplyAdvantage",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Customer Mr Aleksandr V. matched against DFAT-list-adjacent "
                "Russia-Ukraine sanctions watchlist — 78% confidence. Not on "
                "primary OFAC SDN but in the secondary-targeting indicator "
                "list as of 2025-09."
            ),
            implication=(
                "Russia-nexus customer with sanctions-adjacent profile in "
                "OTC fixed-income at a CMS licensee. MAS Notice 314 EDD "
                "obligation engaged."
            ),
            severity="HIGH",
            confidence=78,
        ),
        ConnectorSignal(
            connector="Featurespace ARIC",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Wash-trading detection: paired buy/sell of identical bond "
                "ISINs between Counterparty A and B at <0.3% price spread, "
                "repeated 4 times across 6 days. Wash-trading score 0.96."
            ),
            implication=(
                "Round-trip OTC trades with no economic substance. Classic "
                "layering via capital-markets infrastructure. MAS Notice "
                "314 + SFA market-misconduct provisions both engaged."
            ),
            severity="HIGH",
            confidence=96,
        ),
        ConnectorSignal(
            connector="Sayari",
            category="Identity, eKYC, KYB & Onboarding",
            signal=(
                "Counterparties A and B share the same Cayman administrator "
                "and the same beneficial-controller (UBO match 91%) — "
                "ostensibly independent counterparties are in fact related."
            ),
            implication=(
                "The 'two-counterparty wash' is in fact one party trading "
                "with itself. Removes any 'arm's-length trading' defence."
            ),
            severity="HIGH",
            confidence=91,
        ),
    ],

    # =====================================================================
    # HK — Virtual bank mule cluster (ZA Bank ML detection)
    # =====================================================================
    "Hong Kong (JFIU) — Virtual bank mule cluster": [
        ConnectorSignal(
            connector="In-house ML mule-detection model",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Cluster ZA-2026-Q2-CL-118 identified via in-house mule-"
                "detection model — precision 94%, recall 88% on backtest. "
                "7 accounts share device-fingerprint family + onboarding "
                "referrer chain + balanced in/out flow."
            ),
            implication=(
                "ML-precision-94% mule cluster is a definitive STR signal "
                "under HKMA virtual-bank AML expectations."
            ),
            severity="HIGH",
            confidence=94,
        ),
        ConnectorSignal(
            connector="ThreatMetrix",
            category="Behavioral & Device Intelligence",
            signal=(
                "Device fingerprint family analysis: all 7 accounts run on "
                "3 device IDs sharing iOS version, carrier, locale, accelero"
                "meter signature. Likely device farm — cluster confidence 0.96."
            ),
            implication=(
                "Device-farm operation — single operator controlling "
                "ostensibly separate accounts. Industry-recognised mule pattern."
            ),
            severity="HIGH",
            confidence=96,
        ),
        ConnectorSignal(
            connector="HKAB Inter-Bank Intel-Sharing",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Cross-checking inbound senders: 32 of the 41 unrelated "
                "retail senders have themselves filed scam-victim concerns "
                "(romance-scam / fake investment platform) at their primary "
                "banks. Coverage: 9 different HK banks."
            ),
            implication=(
                "Multi-bank consensus that the inbound funds are scam "
                "proceeds. JFIU consent application defensible on this "
                "alone."
            ),
            severity="HIGH",
            confidence=91,
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Outbound destinations are 6 higher-tier mule accounts that "
                "subsequently transfer to crypto exchanges or offshore. "
                "Pattern matches JFIU 2026-03 typology bulletin on SVF / "
                "e-wallet mule recruitment via job-scam ads."
            ),
            implication=(
                "Two-tier mule architecture. Cluster is the bottom-tier "
                "collection layer; outbound destinations are the layering "
                "vehicles."
            ),
            severity="HIGH",
            confidence=88,
        ),
    ],

    # =====================================================================
    # MY — Digital asset exchange / scam mule (Hafiz)
    # =====================================================================
    "Malaysia (FIED) — Digital asset exchange": [
        ConnectorSignal(
            connector="Sumsub KYT",
            category="Crypto AML & Blockchain Analytics",
            signal=(
                "All four outbound Tron wallets (TWb...mq3, TWb...nx7, "
                "TWb...kl9, TWb...ze4) flagged 'high risk — known scam-"
                "syndicate clusters'. Cluster exposure scores 0.91 to 0.97."
            ),
            implication=(
                "Outbound destinations are scam-controlled. SC Malaysia "
                "Recognized Markets Guidelines + AMLA s.14 STR obligation."
            ),
            severity="HIGH",
            confidence=95,
            timestamp="2026-04-16 11:14 MYT",
        ),
        ConnectorSignal(
            connector="Hawk AI",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Velocity rule fired: MYR 145k single-day inbound (8x "
                "declared monthly income) → same-day 100% conversion to "
                "USDT → split-withdrawal to 4 wallets within 24h. "
                "Pattern-match score 0.93 to BNM 2026-04 typology bulletin."
            ),
            implication=(
                "Direct match to BNM's documented investment-scam mule "
                "typology. Customer is mule-victim, not the originator."
            ),
            severity="HIGH",
            confidence=93,
        ),
        ConnectorSignal(
            connector="Maybank Inter-Bank Intel (informal)",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Upstream: the MYR 145k inbound to the customer's Maybank "
                "account arrived from 17 unrelated retail senders within "
                "the prior 48 hours. Several of those senders have filed "
                "scam-loss reports."
            ),
            implication=(
                "Confirms the customer is the cash-out leg of an active "
                "investment-scam syndicate. Coordinate with Maybank on "
                "victim outreach."
            ),
            severity="HIGH",
            confidence=89,
        ),
    ],

    # =====================================================================
    # MY — E-money issuer wallet mule (Sarah binti Ahmad Faizal)
    # =====================================================================
    "Malaysia (FIED) — E-money issuer wallet mule": [
        ConnectorSignal(
            connector="In-house TM rules",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Velocity rule VEL-EMI-12 fired: wallet sees MYR 30k+/week "
                "vs declared monthly income MYR 1,500 — 100x ratio. Tier "
                "upgrade triggered within 1 week of onboarding (atypical)."
            ),
            implication=(
                "Velocity-vs-profile gap of 100x is a definitive mule "
                "indicator under BNM AML/CFT Sectoral Guidelines for EMIs."
            ),
            severity="HIGH",
            confidence=95,
        ),
        ConnectorSignal(
            connector="Cross-bank fraud intel-sharing",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Inbound senders span 7+ MY banks; cross-checking with the "
                "interbank fraud-sharing database returned 18 hits — all "
                "self-filed scam-victim cases ranging from job-scams to "
                "investment-scams."
            ),
            implication=(
                "Inbound funds confirmed scam proceeds. Customer is bottom-"
                "tier mule in a job-scam network."
            ),
            severity="HIGH",
            confidence=92,
        ),
        ConnectorSignal(
            connector="BioCatch",
            category="Behavioral & Device Intelligence",
            signal=(
                "Session behavioural profile during outbound transfers "
                "showed 'coached/scripted' indicators (typing cadence "
                "abnormal for 22-year-old student demographic, paste-from-"
                "clipboard heavy for recipient details). Score 0.84."
            ),
            implication=(
                "Customer is being remotely directed during transfers — "
                "consistent with her self-report of a 'Telegram task' "
                "arrangement."
            ),
            severity="MEDIUM",
            confidence=84,
        ),
    ],

    # =====================================================================
    # MALAYSIA (FIED) — generic high-risk SME corporate (placeholder structure)
    # =====================================================================
    "Malaysia (FIED)": [
        ConnectorSignal(
            connector="ComplyAdvantage",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Customer matched a domestic PEP (Selangor state assemblyman, "
                "spouse) at 92% confidence; not declared at onboarding."
            ),
            implication=(
                "AMLA §16 enhanced-CDD failure. BNM AML/CFT Sector 1 §11 "
                "requires senior-management approval and ongoing EDD."
            ),
            severity="HIGH",
            confidence=92,
        ),
        ConnectorSignal(
            connector="TrustSphere Risk Index",
            category="Risk Orchestration",
            signal=(
                "Composite score moved from 38 to 81 over 60 days, driven by "
                "high-risk-jurisdiction inflows and PEP discovery."
            ),
            implication=(
                "Step-change risk profile demands EDD refresh and MLRO review."
            ),
            severity="HIGH",
            confidence=88,
        ),
        ConnectorSignal(
            connector="NICE Actimize",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Velocity rule fired: 4x expected monthly turnover in 14 days, "
                "with 6 new counterparties first-seen in the past 21 days."
            ),
            implication=(
                "Velocity + new-counterparty combination scores as Layering "
                "Stage 2 under the Wolfsberg 2024 typology framework."
            ),
            severity="HIGH",
            confidence=90,
        ),
    ],

    # =====================================================================
    # AUSTRALIA (AUSTRAC SMR) — generic
    # =====================================================================
    "Australia (AUSTRAC SMR)": [
        ConnectorSignal(
            connector="ComplyAdvantage",
            category="AML Data, Screening & Regulatory Intelligence",
            signal=(
                "Beneficial owner matched to Australian DFAT consolidated list "
                "(Russia/Ukraine sanctions tranche, 2025-09 update) at 89% "
                "confidence."
            ),
            implication=(
                "AML/CTF Act §41 SMR obligation triggered. Designated-person "
                "freeze obligation under Autonomous Sanctions Act §16."
            ),
            severity="HIGH",
            confidence=89,
        ),
        ConnectorSignal(
            connector="Featurespace ARIC",
            category="Enterprise FRAML & Decisioning Platforms",
            signal=(
                "Cuckoo-smurfing pattern detected: 14 inbound deposits each "
                "below AUD 10,000 from unrelated personal accounts within 48h, "
                "consolidated and outbound to a single overseas wire."
            ),
            implication=(
                "AUSTRAC's 2024 cuckoo-smurfing typology guidance lists this "
                "as the #1 TR indicator for remittance and FX dealer sectors."
            ),
            severity="HIGH",
            confidence=95,
        ),
        ConnectorSignal(
            connector="BioCatch",
            category="Behavioral & Device Intelligence",
            signal=(
                "All 14 inbound-depositor sessions used the same device "
                "fingerprint (Android emulator signature) — depositors are "
                "purportedly different individuals."
            ),
            implication=(
                "Single operator controlling ostensibly separate accounts — "
                "unambiguous mule-network indicator. AUSTRAC RegTech advisory "
                "AML-2024-3."
            ),
            severity="HIGH",
            confidence=94,
        ),
    ],
}


def signals_for(case_key: str) -> list[ConnectorSignal]:
    """Return signals for a case key, or empty list if none defined."""
    return SIGNALS_BY_CASE.get(case_key, [])


def signals_as_prompt_text(signals: list[ConnectorSignal]) -> str:
    """Render signals as a compact text block for the LLM narrative prompt.

    The block is meant to be appended to the existing prompt under a clear
    heading so the model can cite individual connector findings in the audit
    trail without inventing details.
    """
    if not signals:
        return ""
    lines = ["RISK SIGNALS FROM CONNECTORS (cite by connector name where relevant):"]
    for s in signals:
        ts = f" [{s.timestamp}]" if s.timestamp else ""
        lines.append(
            f"- [{s.severity}] {s.connector} ({s.category}){ts}: {s.signal} "
            f"→ Implication: {s.implication} (confidence {s.confidence}%)"
        )
    return "\n".join(lines)
