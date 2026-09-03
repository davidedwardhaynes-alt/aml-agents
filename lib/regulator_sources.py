"""Credible-regulator source catalogue for AML Agents.

Ingested 2026-09-02 from the user's "Regulatory Sources May 2026.xlsx"
(303 sources across 31 jurisdictions). Each entry is a (display_name,
url) tuple grouped by jurisdiction so the daily-briefing script can
inject them as citation context into the podcast prompt, and so a
future feed-discovery pass can auto-add the ones with discoverable
RSS/press-release listings to lib/news.py.

Coverage by jurisdiction (roughly, TLD-inferred):
    Australia 18 · Bangladesh 7 · Bhutan 1 · Brunei 1 · Cambodia 5
    China 26 · Hong Kong 17 · India 19 · Indonesia 7 · International 67
    Japan 13 · Laos 2 · Macau 4 · Malaysia 6 · Maldives 2
    Mongolia 4 · Myanmar 2 · Nepal 2 · New Zealand 8 · North Korea 1
    Pakistan 6 · Papua New Guinea 2 · Philippines 9 · Singapore 10
    South Korea 21 · Sri Lanka 3 · Taiwan 9 · Thailand 14
    United Kingdom 4 · United States 5 · Vietnam 8

Note: this is the RAW catalogue of authoritative source URLs. It is
NOT yet the ingestion list — the daily news pipeline (lib/news.py)
ingests a curated subset that has been confirmed to expose RSS feeds
or LLM-scrapable press-release listings. Use `unconvered_sources()`
to see which catalogue entries are still pending ingestion.
"""

from __future__ import annotations

import re
from typing import Iterable

REGULATOR_SOURCES: dict[str, list[tuple[str, str]]] = {
    'Australia': [
        ('AUSTRAC', 'https://www.austrac.gov.au'),
        ('Australian Communications and Media Authority', 'https://www.acma.gov.au'),
        ('Australian Competition and Consumer Commission', 'https://www.accc.gov.au'),
        ('Australian Federal Police', 'https://www.afp.gov.au'),
        ('Australian Financial Complaints Authority', 'https://www.afca.org.au'),
        ('Australian Financial Security Authority', 'https://www.afsa.gov.au'),
        ('Australian Prudential Regulation Authority', 'https://www.apra.gov.au'),
        ('Australian Sanctions Office', 'https://www.dfat.gov.au/international-relations/security/sanctions'),
        ('Australian Securities Exchange', 'https://www.asx.com.au'),
        ('Australian Securities and Investments Commission', 'https://www.asic.gov.au'),
        ('Clean Energy Regulator', 'https://www.cleanenergyregulator.gov.au'),
        ('Council of Financial Regulators', 'https://www.cfr.gov.au'),
        ('Department of Foreign Affairs and Trade', 'https://www.dfat.gov.au'),
        ('Department of Home Affairs', 'https://www.homeaffairs.gov.au'),
        ('Financial Services Council', 'https://www.fsc.org.au'),
        ('Office of the Australian Information Commissioner', 'https://www.oaic.gov.au'),
        ('Reserve Bank of Australia', 'https://www.rba.gov.au'),
        ('The Treasury', 'https://treasury.gov.au'),
    ],
    'Bangladesh': [
        ('Anti-Corruption Commission', 'https://www.acc.org.bd'),
        ('Bangladesh Bank', 'https://www.bb.org.bd'),
        ('Bangladesh Financial Intelligence Unit', 'https://www.bfiu.org.bd'),
        ('Bangladesh Investment Development Authority', 'https://www.bida.gov.bd'),
        ('Bangladesh Securities and Exchange Commission', 'https://www.sec.gov.bd'),
        ('Chittagong Stock Exchange', 'https://www.cse.com.bd'),
        ('Insurance Development and Regulatory Authority', 'https://www.idra.org.bd'),
    ],
    'Bhutan': [
        ('Royal Monetary Authority of Bhutan', 'https://www.rma.org.bt'),
    ],
    'Brunei': [
        ('Autoriti Monetari Brunei Darussalam', 'https://www.ambd.gov.bn'),
    ],
    'Cambodia': [
        ('Cambodia Association of Securities Firms', 'https://www.casf.org.kh'),
        ('Credit Guarantee Corporation of Cambodia', 'https://www.cgcc.com.kh'),
        ('National Bank of Cambodia', 'https://www.nbc.gov.kh'),
        ('Non-Bank Financial Services Authority', 'https://www.nbfsa.gov.kh'),
        ('Securities and Exchange Regulator of Cambodia', 'https://www.serc.gov.kh'),
    ],
    'China': [
        ('Asset Management Association of China', 'https://www.amac.org.cn'),
        ('China Anti-Money Laundering Monitoring and Analysis Center', 'http://www.pbccrc.org.cn'),
        ('China Banking and Insurance Regulatory Commission', 'http://www.cbirc.gov.cn'),
        ('China Financial Futures Exchange', 'http://www.cffex.com.cn'),
        ('China Securities Regulatory Commission', 'http://www.csrc.gov.cn'),
        ('Cyberspace Administration of China', 'https://www.cac.gov.cn'),
        ('Dalian Commodity Exchange', 'http://www.dce.com.cn'),
        ('Guangzhou Futures Exchange', 'http://www.gfex.com.cn'),
        ('Ministry of Commerce', 'http://www.mofcom.gov.cn'),
        ("Ministry of Finance of the People\\'s Republic of China", 'http://www.mof.gov.cn'),
        ('Ministry of Industry and Information Technology', 'https://www.miit.gov.cn'),
        ('Ministry of Public Security', 'http://www.mps.gov.cn'),
        ('National Association of Financial Market Institutional Investors', 'https://www.nafmii.org.cn'),
        ('National Audit Office', 'http://www.audit.gov.cn'),
        ('National Development and Reform Commission', 'https://www.ndrc.gov.cn'),
        ('National Financial Regulatory Administration', 'https://www.nfra.gov.cn'),
        ("People\\'s Bank of China", 'http://www.pbc.gov.cn'),
        ('Shanghai Futures Exchange', 'http://www.shfe.com.cn'),
        ('Shanghai International Energy Exchange', 'https://www.ine.cn'),
        ('Shanghai Stock Exchange', 'http://www.sse.com.cn'),
        ('Shenzhen Stock Exchange', 'http://www.szse.cn'),
        ('State Administration of Foreign Exchange', 'http://www.safe.gov.cn'),
        ('State Council', 'https://www.gov.cn'),
        ("Supreme People\\'s Court", 'https://www.court.gov.cn'),
        ("Supreme People\\'s Procuratorate", 'https://www.spp.gov.cn'),
        ('Zhengzhou Commodity Exchange', 'http://www.czce.com.cn'),
    ],
    'Hong Kong': [
        ('Accounting and Financial Reporting Council', 'https://www.afrc.org.hk'),
        ('Financial Services Development Council', 'https://www.fsdc.org.hk'),
        ('Financial Services and the Treasury Bureau', 'https://www.fstb.gov.hk'),
        ('Hong Kong Association of Banks', 'https://www.hkab.org.hk'),
        ('Hong Kong Deposit Protection Board', 'https://www.dps.org.hk'),
        ('Hong Kong Exchanges and Clearing Limited', 'https://www.hkex.com.hk'),
        ('Hong Kong Institute of Certified Public Accountants', 'https://www.hkicpa.org.hk'),
        ('Hong Kong Investment Corporation', 'https://www.hkic.org.hk'),
        ('Hong Kong Monetary Authority', 'https://www.hkma.gov.hk'),
        ('Hong Kong Mortgage Corporation', 'https://www.hkmc.com.hk'),
        ('Hong Kong Police Force', 'https://www.police.gov.hk'),
        ('Independent Commission Against Corruption', 'https://www.icac.org.hk'),
        ('Inland Revenue Department', 'https://www.ird.gov.hk'),
        ('Insurance Authority', 'https://www.ia.org.hk'),
        ('Mandatory Provident Fund Schemes Authority', 'https://www.mpfa.org.hk'),
        ('Office of the Privacy Commissioner for Personal Data', 'https://www.pcpd.org.hk'),
        ('Securities and Futures Commission', 'https://www.sfc.hk'),
    ],
    'India': [
        ('Central Board of Direct Taxes', 'https://incometaxindia.gov.in'),
        ('Central Bureau of Investigation', 'https://cbi.gov.in'),
        ('Central Information Commission', 'https://cic.gov.in'),
        ('Central Vigilance Commission', 'https://cvc.gov.in'),
        ('Competition Commission of India', 'https://www.cci.gov.in'),
        ('Department of Financial Services', 'https://financialservices.gov.in'),
        ('Directorate of Revenue Intelligence', 'https://dri.nic.in'),
        ('Enforcement Directorate', 'https://www.enforcementdirectorate.gov.in'),
        ('Financial Intelligence Unit-India', 'https://fiuindia.gov.in'),
        ('Insurance Regulatory and Development Authority of India', 'https://www.irdai.gov.in'),
        ('International Financial Services Centres Authority', 'https://www.ifsca.gov.in'),
        ('Ministry of Corporate Affairs', 'https://www.mca.gov.in'),
        ('Ministry of Finance', 'https://www.finmin.nic.in'),
        ('National Payments Corporation of India', 'https://www.npci.org.in'),
        ('Pension Fund Regulatory and Development Authority', 'https://www.pfrda.org.in'),
        ('Reserve Bank of India', 'https://www.rbi.org.in'),
        ('Securities and Exchange Board of India', 'https://www.sebi.gov.in'),
        ('Serious Fraud Investigation Office', 'https://sfio.nic.in'),
        ('Unique Identification Authority of India', 'https://uidai.gov.in'),
    ],
    'Indonesia': [
        ('Bank Indonesia', 'https://www.bi.go.id'),
        ('Corruption Eradication Commission', 'https://www.kpk.go.id'),
        ('Directorate General of Customs and Excise', 'https://www.beacukai.go.id'),
        ('Financial Services Authority (Otoritas Jasa Keuangan)', 'https://www.ojk.go.id'),
        ('Indonesian Financial Transaction Reports and Analysis Center', 'https://www.ppatk.go.id'),
        ('Ministry of Communication and Digital', 'https://www.komdigi.go.id'),
        ('National Cyber and Crypto Agency', 'https://www.bssn.go.id'),
    ],
    'International': [
        ('ASEAN Secretariat', 'https://asean.org'),
        ('ASEANAPOL', 'https://www.aseanapol.org'),
        ('Alliance for Financial Inclusion', 'https://www.afi-global.org'),
        ('Asia/Pacific Group on Money Laundering', 'https://www.apgml.org'),
        ('Asset Recovery Interagency Network – Asia Pacific', 'https://www.arin-ap.org'),
        ('Association of Chartered Certified Accountants', 'https://www.accaglobal.com'),
        ('Association of Mutual Funds of India', 'https://www.amfiindia.com'),
        ('Bank for International Settlements', 'https://www.bis.org'),
        ('Basel Committee on Banking Supervision', 'https://www.bis.org/bcbs'),
        ('Bombay Stock Exchange', 'https://www.bseindia.com'),
        ('Bursa Malaysia', 'https://www.bursamalaysia.com'),
        ('Committee on Payments and Market Infrastructures', 'https://www.bis.org/cpmi'),
        ('European Banking Authority', 'https://www.eba.europa.eu'),
        ('European Securities and Markets Authority', 'https://www.esma.europa.eu'),
        ('Financial Action Task Force', 'https://www.fatf-gafi.org'),
        ('Financial Action Task Force on Money Laundering (Asia/Pacific Group)', 'https://www.apgml.org'),
        ('Financial Centres for Sustainability', 'https://www.fc4s.org'),
        ('Financial Stability Board', 'https://www.fsb.org'),
        ('Global Digital Finance', 'https://www.globaldigitalfinance.org'),
        ('Global Finance & Technology Network', 'https://www.gftn.org'),
        ('Global Finance and Technology Network', 'https://www.gftn.org'),
        ('Global Financial Innovation Network', 'https://www.thegfin.com'),
        ('Global Financial Literacy Excellence Center', 'https://gflec.org'),
        ('Global Financial Markets Association', 'https://www.gfma.org'),
        ('Global Legal Entity Identifier Foundation', 'https://www.gleif.org'),
        ('Group of Twenty', 'https://www.g20.org'),
        ('Guangzhou Emissions Exchange', 'https://www.cnemission.com'),
        ('INTERPOL Asia and South Pacific', 'https://www.interpol.int/Who-we-are/Where-we-work/Asia-and-the-South-Pacific'),
        ('International Accounting Standards Board', 'https://www.ifrs.org'),
        ('International Anti-Corruption Academy', 'https://www.iaca.int'),
        ('International Association for Trusted Blockchain Applications', 'https://www.inatba.org'),
        ('International Association of Deposit Insurers', 'https://www.iadi.org'),
        ('International Association of Insurance Supervisors', 'https://www.iaisweb.org'),
        ('International Banking Federation', 'https://www.ibfed.org'),
        ('International Capital Market Association', 'https://www.icmagroup.org'),
        ('International Corporate Governance Network', 'https://www.icgn.org'),
        ('International Council of Securities Associations', 'https://www.icsa.global'),
        ('International Federation of Accountants', 'https://www.ifac.org'),
        ('International Financial Reporting Standards Foundation', 'https://www.ifrs.org'),
        ('International Forum of Independent Audit Regulators', 'https://www.ifiar.org'),
        ('International Monetary Fund', 'https://www.imf.org'),
        ('International Network for Small and Medium Sized Enterprises', 'https://www.international-sme.org'),
        ('International Network on Financial Education', 'https://www.oecd.org/financial/education'),
        ('International Organization of Pension Supervisors', 'https://www.iopsweb.org'),
        ('International Organization of Securities Commissions', 'https://www.iosco.org'),
        ('International Securities Lending Association', 'https://www.islaemea.org'),
        ('International Swaps and Derivatives Association', 'https://www.isda.org'),
        ('Islamic Financial Services Board', 'https://www.ifsb.org'),
        ('Multi Commodity Exchange of India', 'https://www.mcxindia.com'),
        ('Nasdaq', 'https://www.nasdaq.com'),
        ('National Commodity & Derivatives Exchange Limited', 'https://www.ncdex.com'),
        ('National Stock Exchange of India', 'https://www.nseindia.com'),
        ('Network for Greening the Financial System', 'https://www.ngfs.net'),
        ('Organisation for Economic Co-operation and Development', 'https://www.oecd.org'),
        ('Pacific Transnational Crime Network', 'https://www.pacifictransnationalcrimenetwork.org'),
        ('Public Company Accounting Oversight Board', 'https://pcaobus.org'),
        ('Singapore Exchange', 'https://www.sgx.com'),
        ('Singapore Exchange Regulation', 'https://www.sgx.com/regulation'),
        ('Sustainable Banking and Finance Network', 'https://www.sbfnetwork.org'),
        ('The Egmont Group of Financial Intelligence Units', 'https://egmontgroup.org'),
        ('The Institute of Chartered Accountants of India', 'https://www.icai.org'),
        ('United Nations Conference on Trade and Development', 'https://unctad.org'),
        ('United Nations Environment Programme Finance Initiative', 'https://www.unepfi.org'),
        ('United Nations Office on Drugs and Crime', 'https://www.unodc.org'),
        ('Wolfsberg Group', 'https://www.wolfsberg-principles.com'),
        ('World Bank Group', 'https://www.worldbank.org'),
        ('World Federation of Exchanges', 'https://www.world-exchanges.org'),
    ],
    'Japan': [
        ('Bank of Japan', 'https://www.boj.or.jp'),
        ('Consumer Affairs Agency', 'https://www.caa.go.jp'),
        ('Financial Services Agency', 'https://www.fsa.go.jp'),
        ('Japan Exchange Group', 'https://www.jpx.co.jp'),
        ('Japan Financial Intelligence Center', 'https://www.npa.go.jp/sosikihanzai/jafic'),
        ('Japan Securities Dealers Association', 'https://www.jsda.or.jp'),
        ('Japan Virtual Currency Exchange Association', 'https://jvcea.or.jp'),
        ('Ministry of Internal Affairs and Communications', 'https://www.soumu.go.jp'),
        ('National Police Agency', 'https://www.npa.go.jp'),
        ('Osaka Exchange', 'https://www.jpx.co.jp/english/markets/derivatives'),
        ('Personal Information Protection Commission', 'https://www.ppc.go.jp'),
        ('Tokyo Commodity Exchange', 'https://www.tocom.or.jp'),
        ('Tokyo Stock Exchange', 'https://www.jpx.co.jp/english/markets/equities'),
    ],
    'Laos': [
        ('Bank of the Lao P.D.R.', 'https://www.bol.gov.la'),
        ('Securities and Exchange Commission Office', 'https://www.seco.gov.la'),
    ],
    'Macau': [
        ('Chongwa (Macao) Financial Asset Exchange', 'https://www.moex.com.mo'),
        ('Macao International Carbon Emission Exchange', 'https://www.mcax.mo'),
        ('Monetary Authority of Macao', 'https://www.amcm.gov.mo'),
        ('Personal Data Protection Bureau', 'https://www.gpdp.gov.mo'),
    ],
    'Malaysia': [
        ('Bank Negara Malaysia', 'https://www.bnm.gov.my'),
        ('Department of Personal Data Protection', 'https://www.pdp.gov.my'),
        ('Financial Intelligence Unit Malaysia', 'https://www.bnm.gov.my/financial-intelligence'),
        ('Malaysian Anti-Corruption Commission', 'https://www.sprm.gov.my'),
        ('Ministry of Digital', 'https://www.digital.gov.my'),
        ('Securities Commission Malaysia', 'https://www.sc.com.my'),
    ],
    'Maldives': [
        ('Capital Market Development Authority', 'https://www.cmda.gov.mv'),
        ('Maldives Monetary Authority', 'https://www.mma.gov.mv'),
    ],
    'Mongolia': [
        ('Bank of Mongolia', 'https://www.mongolbank.mn'),
        ('Financial Intelligence Unit Mongolia', 'https://www.fiu.mn'),
        ('Financial Regulatory Commission', 'https://www.frc.mn'),
        ('Independent Authority Against Corruption', 'https://www.iaac.mn'),
    ],
    'Myanmar': [
        ('Central Bank of Myanmar', 'https://www.cbm.gov.mm'),
        ('Securities and Exchange Commission of Myanmar', 'https://www.secmyanmar.gov.mm'),
    ],
    'Nepal': [
        ('Nepal Rastra Bank', 'https://www.nrb.org.np'),
        ('Securities Board of Nepal', 'https://www.sebon.gov.np'),
    ],
    'New Zealand': [
        ('Commerce Commission New Zealand', 'https://comcom.govt.nz'),
        ('External Reporting Board', 'https://www.xrb.govt.nz'),
        ('Financial Intelligence Unit New Zealand', 'https://www.police.govt.nz/advice/businesses-and-organisations/fiu'),
        ('Financial Markets Authority', 'https://www.fma.govt.nz'),
        ('Ministry of Business, Innovation and Employment', 'https://www.mbie.govt.nz'),
        ('Office of the Privacy Commissioner', 'https://www.privacy.org.nz'),
        ('Reserve Bank of New Zealand', 'https://www.rbnz.govt.nz'),
        ('Serious Fraud Office', 'https://www.sfo.govt.nz'),
    ],
    'North Korea': [
        ("Central Bank of the Democratic People\\'s Republic of Korea", 'http://www.cbk.gov.kp'),
    ],
    'PNG': [
        ('Bank of Papua New Guinea', 'https://www.bankpng.gov.pg'),
        ('Securities Commission of Papua New Guinea', 'https://www.scpng.gov.pg'),
    ],
    'Pakistan': [
        ('Federal Board of Revenue', 'https://www.fbr.gov.pk'),
        ('Financial Monitoring Unit', 'https://www.fmu.gov.pk'),
        ('National Accountability Bureau', 'https://nab.gov.pk'),
        ('National Counter Terrorism Authority', 'https://www.nacta.gov.pk'),
        ('Securities and Exchange Commission of Pakistan', 'https://www.secp.gov.pk'),
        ('State Bank of Pakistan', 'https://www.sbp.org.pk'),
    ],
    'Philippines': [
        ('Anti-Money Laundering Council', 'https://www.amlc.gov.ph'),
        ('Bangko Sentral ng Pilipinas', 'https://www.bsp.gov.ph'),
        ('Bureau of Internal Revenue', 'https://www.bir.gov.ph'),
        ('Cybercrime Investigation and Coordinating Center', 'https://www.cicc.gov.ph'),
        ('Insurance Commission', 'https://www.insurance.gov.ph'),
        ('National Privacy Commission', 'https://www.privacy.gov.ph'),
        ('Office of the Ombudsman', 'https://www.ombudsman.gov.ph'),
        ('Philippine Stock Exchange', 'https://www.pse.com.ph'),
        ('Securities and Exchange Commission', 'https://www.sec.gov.ph'),
    ],
    'Singapore': [
        ('Accounting and Corporate Regulatory Authority', 'https://www.acra.gov.sg'),
        ('Competition and Consumer Commission of Singapore', 'https://www.cccs.gov.sg'),
        ('Corrupt Practices Investigation Bureau', 'https://www.cpib.gov.sg'),
        ('Government Technology Agency', 'https://www.tech.gov.sg'),
        ('Infocomm Media Development Authority', 'https://www.imda.gov.sg'),
        ('Ministry of Law', 'https://www.mlaw.gov.sg'),
        ('Monetary Authority of Singapore', 'https://www.mas.gov.sg'),
        ('Personal Data Protection Commission', 'https://www.pdpc.gov.sg'),
        ('Singapore Police Force', 'https://www.police.gov.sg'),
        ('Suspicious Transaction Reporting Office', 'https://www.police.gov.sg/Who-We-Are/Organisational-Structure/Specialist-Staff-Departments/Commercial-Affairs-Department/Suspicious-Transaction-Reporting-Office'),
    ],
    'South Korea': [
        ('Anti-Corruption & Civil Rights Commission', 'https://www.acrc.go.kr'),
        ('Bank of Korea', 'https://www.bok.or.kr'),
        ('Digital Asset Exchange Alliance', 'https://www.daxa.or.kr'),
        ('Financial Security Institute', 'https://www.fsec.or.kr'),
        ('Financial Services Commission', 'https://www.fsc.go.kr'),
        ('Financial Supervisory Service', 'https://www.fss.or.kr'),
        ('Korea Accounting Standards Board', 'https://www.kasb.or.kr'),
        ('Korea Asset Management Corporation', 'https://www.kamco.or.kr'),
        ('Korea Capital Market Institute', 'https://www.kcmi.re.kr'),
        ('Korea Credit Information Services', 'https://www.kcredit.or.kr'),
        ('Korea Customs Service', 'https://www.customs.go.kr'),
        ('Korea Exchange', 'https://www.krx.co.kr'),
        ('Korea Federation of Banks', 'https://www.kfb.or.kr'),
        ('Korea Financial Intelligence Unit', 'https://www.kofiu.go.kr'),
        ('Korea Financial Investment Association', 'https://www.kofia.or.kr'),
        ('Korea Internet & Security Agency', 'https://www.kisa.or.kr'),
        ('Korea Securities Depository', 'https://www.ksd.or.kr'),
        ('Ministry of Economy and Finance', 'https://www.moef.go.kr'),
        ('National Police Agency', 'https://www.police.go.kr'),
        ('National Tax Service', 'https://www.nts.go.kr'),
        ('Personal Information Protection Commission', 'https://www.pipc.go.kr'),
    ],
    'Sri Lanka': [
        ('Central Bank of Sri Lanka', 'https://www.cbsl.gov.lk'),
        ('Colombo Stock Exchange', 'https://www.cse.lk'),
        ('Securities and Exchange Commission of Sri Lanka', 'https://www.sec.gov.lk'),
    ],
    'Taiwan': [
        ('Agency Against Corruption', 'https://www.moj.gov.tw'),
        ('Central Bank of the Republic of China (Taiwan)', 'https://www.cbc.gov.tw'),
        ('Financial Supervisory Commission', 'https://www.fsc.gov.tw'),
        ('Ministry of Economic Affairs', 'https://www.moea.gov.tw'),
        ('Ministry of Finance - Taiwan', 'https://www.mof.gov.tw'),
        ('Taiwan Depository and Clearing Corporation', 'https://www.tdcc.com.tw'),
        ('Taiwan Financial Intelligence Center', 'https://www.mjib.gov.tw/en'),
        ('Taiwan Futures Exchange', 'https://www.taifex.com.tw'),
        ('Taiwan High Prosecutors Office', 'https://www.tph.moj.gov.tw'),
    ],
    'Thailand': [
        ('Anti-Money Laundering Office', 'https://www.amlo.go.th'),
        ('Association of Thai Securities Companies', 'https://www.asco.or.th'),
        ('Bank of Thailand', 'https://www.bot.or.th'),
        ('Central Investigation Bureau', 'https://cib.go.th'),
        ('Cyber Crime Investigation Bureau', 'https://ccib.go.th'),
        ('Department of Special Investigation', 'https://www.dsi.go.th'),
        ('Electronic Transactions Development Agency', 'https://www.etda.or.th'),
        ('National Anti-Corruption Commission', 'https://www.nacc.go.th'),
        ('Office of Insurance Commission', 'https://www.oic.or.th'),
        ('Personal Data Protection Committee', 'https://www.pdpc.or.th'),
        ('Revenue Department', 'https://www.rd.go.th'),
        ('Securities and Exchange Commission', 'https://www.sec.or.th'),
        ('Stock Exchange of Thailand', 'https://www.set.or.th'),
        ("Thailand\\'s Board of Investment", 'https://www.boi.go.th'),
    ],
    'United Kingdom': [
        ('Bank of England', 'https://www.bankofengland.co.uk'),
        ('Financial Conduct Authority', 'https://www.fca.org.uk'),
        ('Foreign, Commonwealth and Development Office', 'https://www.gov.uk/government/organisations/foreign-commonwealth-development-office'),
        ('Prudential Regulation Authority', 'https://www.bankofengland.co.uk/prudential-regulation'),
    ],
    'United States': [
        ('Commodity Futures Trading Commission', 'https://www.cftc.gov'),
        ('Department of Justice', 'https://www.justice.gov'),
        ('Financial Crimes Enforcement Network', 'https://www.fincen.gov'),
        ('Office of Foreign Assets Control', 'https://ofac.treasury.gov'),
        ('Securities and Exchange Commission', 'https://www.sec.gov'),
    ],
    'Vietnam': [
        ('Anti-Money Laundering Department (State Bank of Vietnam)', 'https://www.sbv.gov.vn/webcenter/portal/en/home/sbv/aml'),
        ('Authority of Information Security', 'https://ais.gov.vn'),
        ('Government Inspectorate of Vietnam', 'https://www.giv.gov.vn'),
        ('Ministry of Finance', 'https://www.mof.gov.vn'),
        ('Ministry of Public Security', 'https://mps.gov.vn'),
        ('Ministry of Science and Technology', 'https://www.most.gov.vn'),
        ('State Bank of Vietnam', 'https://www.sbv.gov.vn'),
        ('State Securities Commission of Vietnam', 'https://www.ssc.gov.vn'),
    ],
}


def all_sources() -> list[tuple[str, str, str]]:
    """Return flat list of (jurisdiction, name, url) for every source."""
    out: list[tuple[str, str, str]] = []
    for jur, entries in REGULATOR_SOURCES.items():
        for name, url in entries:
            out.append((jur, name, url))
    return out


def sources_for(jurisdiction: str) -> list[tuple[str, str]]:
    """Return the (name, url) sources for a given jurisdiction, or []
    if the jurisdiction isn't in the catalogue."""
    return list(REGULATOR_SOURCES.get(jurisdiction, []))


def domains_for(jurisdiction: str) -> list[str]:
    """Return the bare hostnames (e.g. 'www.mas.gov.sg') for a
    jurisdiction — useful for cross-checking coverage against the RSS
    feeds ingested in lib/news.py."""
    hosts: list[str] = []
    for _name, url in REGULATOR_SOURCES.get(jurisdiction, []):
        host = re.sub(r'^https?://', '', url).split('/')[0]
        hosts.append(host.lower())
    return hosts


def uncovered_sources(covered_hosts: Iterable[str]) -> list[tuple[str, str, str]]:
    """Return (jurisdiction, name, url) triples for every catalogue
    entry whose hostname is NOT in the caller-supplied covered_hosts.
    Used by scripts/discover_regulator_feeds.py to work through the
    ingestion backlog."""
    covered = {h.lower().lstrip('.') for h in covered_hosts}
    out: list[tuple[str, str, str]] = []
    for jur, name, url in all_sources():
        host = re.sub(r'^https?://', '', url).split('/')[0].lower()
        # A source is "covered" if its host or any suffix matches.
        matched = any(host == c or host.endswith('.' + c) for c in covered)
        if not matched:
            out.append((jur, name, url))
    return out
