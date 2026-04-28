"""Comprehensive regulator and authoritative-source directory.

Organised by jurisdiction. Each entry includes:
  - name: short label
  - url: homepage / landing page
  - type: regulator category (FIU, central bank, securities, etc.)
  - rss_url: best-effort RSS endpoint where known; None if not exposed

For most regulators, RSS is not published or is non-standard. The directory
serves three product surfaces:
  - Horizon scanning — adds known-good RSS to the live-feed configuration
  - Obligation register — links from each obligation to its source authority
  - Jurisdictional news — additional RSS where available, plus reference list

Live-RSS subset is conservatively chosen — the UI handles fetch failures
gracefully but we shouldn't pollute the feed status panel with hundreds of
known-broken endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Regulator:
    name: str
    url: str
    type: str  # FIU / Central bank / Securities / Anti-corruption / etc.
    rss_url: str | None = None  # explicit RSS endpoint when known


# Jurisdictions ordered by product priority: 4 main markets, then APAC, then international, then UK/EU/US.
JURISDICTION_ORDER = [
    "Singapore",
    "Hong Kong",
    "Malaysia",
    "Australia",
    "Bangladesh",
    "Bhutan",
    "Brunei",
    "Cambodia",
    "China",
    "India",
    "Indonesia",
    "Japan",
    "Laos",
    "Macau",
    "Maldives",
    "Mongolia",
    "Myanmar",
    "Nepal",
    "New Zealand",
    "North Korea",
    "Pakistan",
    "Papua New Guinea",
    "Philippines",
    "South Korea",
    "Sri Lanka",
    "Taiwan",
    "Thailand",
    "Vietnam",
    "European Union",
    "United Kingdom",
    "United States",
    "International / Standard-setters",
    "ASEAN & Regional Networks",
]


REGULATORS: dict[str, list[Regulator]] = {
    "Singapore": [
        Regulator("ACRA — Accounting and Corporate Regulatory Authority", "https://www.acra.gov.sg", "Companies registry"),
        Regulator("CCCS — Competition and Consumer Commission", "https://www.cccs.gov.sg", "Competition"),
        Regulator("CPIB — Corrupt Practices Investigation Bureau", "https://www.cpib.gov.sg", "Anti-corruption"),
        Regulator("GFTN — Global Finance & Technology Network", "https://www.gftn.org", "Industry network"),
        Regulator("GovTech Singapore", "https://www.tech.gov.sg", "Government tech"),
        Regulator("IMDA — Infocomm Media Development Authority", "https://www.imda.gov.sg", "Telecoms / digital"),
        Regulator("MinLaw — Ministry of Law", "https://www.mlaw.gov.sg", "Legal"),
        Regulator("MAS — Monetary Authority of Singapore", "https://www.mas.gov.sg", "Central bank / financial supervisor", "https://www.mas.gov.sg/news/rss"),
        Regulator("PDPC — Personal Data Protection Commission", "https://www.pdpc.gov.sg", "Data protection"),
        Regulator("SGX — Singapore Exchange", "https://www.sgx.com", "Securities exchange"),
        Regulator("SGX Regulation", "https://www.sgx.com/regulation", "Securities exchange"),
        Regulator("Singapore Police Force", "https://www.police.gov.sg", "Law enforcement"),
        Regulator("STRO — Suspicious Transaction Reporting Office", "https://www.police.gov.sg/Who-We-Are/Organisational-Structure/Specialist-Staff-Departments/Commercial-Affairs-Department/Suspicious-Transaction-Reporting-Office", "FIU"),
    ],

    "Hong Kong": [
        Regulator("AFRC — Accounting and Financial Reporting Council", "https://www.afrc.org.hk", "Audit oversight"),
        Regulator("FSTB — Financial Services and the Treasury Bureau", "https://www.fstb.gov.hk", "Government — finance"),
        Regulator("FSDC — Financial Services Development Council", "https://www.fsdc.org.hk", "Industry development"),
        Regulator("HKAB — Hong Kong Association of Banks", "https://www.hkab.org.hk", "Industry association"),
        Regulator("DPS — Hong Kong Deposit Protection Scheme", "https://www.dps.org.hk", "Deposit insurance"),
        Regulator("HKEX — Hong Kong Exchanges and Clearing", "https://www.hkex.com.hk", "Securities exchange"),
        Regulator("HKICPA — Institute of Certified Public Accountants", "https://www.hkicpa.org.hk", "Audit profession"),
        Regulator("HKIC — Insurance Authority", "https://www.hkic.org.hk", "Industry"),
        Regulator("HKMA — Hong Kong Monetary Authority", "https://www.hkma.gov.hk", "Central bank / banking supervisor", "https://www.hkma.gov.hk/eng/rss/press-releases.xml"),
        Regulator("HKMC — Hong Kong Mortgage Corporation", "https://www.hkmc.com.hk", "Mortgage corp"),
        Regulator("Hong Kong Police Force", "https://www.police.gov.hk", "Law enforcement"),
        Regulator("ICAC — Independent Commission Against Corruption", "https://www.icac.org.hk", "Anti-corruption"),
        Regulator("IRD — Inland Revenue Department", "https://www.ird.gov.hk", "Tax"),
        Regulator("IA — Insurance Authority", "https://www.ia.org.hk", "Insurance supervisor"),
        Regulator("MPFA — Mandatory Provident Fund Schemes Authority", "https://www.mpfa.org.hk", "Pensions"),
        Regulator("PCPD — Privacy Commissioner for Personal Data", "https://www.pcpd.org.hk", "Data protection"),
        Regulator("SFC — Securities and Futures Commission", "https://www.sfc.hk", "Securities supervisor"),
    ],

    "Malaysia": [
        Regulator("BNM — Bank Negara Malaysia", "https://www.bnm.gov.my", "Central bank", "https://www.bnm.gov.my/rss-announcement"),
        Regulator("Bursa Malaysia", "https://www.bursamalaysia.com", "Securities exchange"),
        Regulator("Department of Personal Data Protection (PDP)", "https://www.pdp.gov.my", "Data protection"),
        Regulator("FIED — Financial Intelligence and Enforcement Department (BNM)", "https://www.bnm.gov.my/financial-intelligence", "FIU"),
        Regulator("MACC / SPRM — Malaysian Anti-Corruption Commission", "https://www.sprm.gov.my", "Anti-corruption"),
        Regulator("Ministry of Digital", "https://www.digital.gov.my", "Government — digital"),
        Regulator("SC Malaysia — Securities Commission", "https://www.sc.com.my", "Securities supervisor", "https://www.sc.com.my/api/rss/MediaRelease"),
    ],

    "Australia": [
        Regulator("Attorney-General's Department", "https://www.ag.gov.au", "Government — legal"),
        Regulator("ACMA — Australian Communications and Media Authority", "https://www.acma.gov.au", "Telecoms / media"),
        Regulator("ACCC — Australian Competition and Consumer Commission", "https://www.accc.gov.au", "Competition / consumer"),
        Regulator("AFP — Australian Federal Police", "https://www.afp.gov.au", "Law enforcement"),
        Regulator("AFCA — Australian Financial Complaints Authority", "https://www.afca.org.au", "Financial complaints"),
        Regulator("AFSA — Australian Financial Security Authority", "https://www.afsa.gov.au", "Insolvency / personal financial security"),
        Regulator("APRA — Australian Prudential Regulation Authority", "https://www.apra.gov.au", "Prudential supervisor", "https://www.apra.gov.au/news-and-publications/feed"),
        Regulator("DFAT — Sanctions", "https://www.dfat.gov.au/international-relations/security/sanctions", "Sanctions"),
        Regulator("ASIC — Australian Securities and Investments Commission", "https://www.asic.gov.au", "Securities supervisor", "https://asic.gov.au/about-asic/news-centre/find-a-media-release/feed/"),
        Regulator("ASX — Australian Securities Exchange", "https://www.asx.com.au", "Securities exchange"),
        Regulator("AUSTRAC — Australian Transaction Reports and Analysis Centre", "https://www.austrac.gov.au", "FIU", "https://www.austrac.gov.au/about-us/news-and-media/media-releases/feed"),
        Regulator("Clean Energy Regulator", "https://www.cleanenergyregulator.gov.au", "Energy"),
        Regulator("Council of Financial Regulators (CFR)", "https://www.cfr.gov.au", "Regulator coordination"),
        Regulator("DFAT — Foreign Affairs and Trade", "https://www.dfat.gov.au", "Foreign affairs"),
        Regulator("Home Affairs", "https://www.homeaffairs.gov.au", "Border / security"),
        Regulator("FSC — Financial Services Council", "https://www.fsc.org.au", "Industry association"),
        Regulator("OAIC — Office of the Australian Information Commissioner", "https://www.oaic.gov.au", "Data protection"),
        Regulator("RBA — Reserve Bank of Australia", "https://www.rba.gov.au", "Central bank"),
        Regulator("Australian Treasury", "https://treasury.gov.au", "Government — finance"),
    ],

    "Bangladesh": [
        Regulator("ACC — Anti-Corruption Commission", "https://www.acc.org.bd", "Anti-corruption"),
        Regulator("Bangladesh Bank", "https://www.bb.org.bd", "Central bank"),
        Regulator("BFIU — Bangladesh Financial Intelligence Unit", "https://www.bfiu.org.bd", "FIU"),
        Regulator("BIDA — Bangladesh Investment Development Authority", "https://www.bida.gov.bd", "Investment promotion"),
        Regulator("BSEC — Bangladesh Securities and Exchange Commission", "https://www.sec.gov.bd", "Securities supervisor"),
        Regulator("CSE — Chittagong Stock Exchange", "https://www.cse.com.bd", "Securities exchange"),
        Regulator("IDRA — Insurance Development and Regulatory Authority", "https://www.idra.org.bd", "Insurance supervisor"),
    ],

    "Bhutan": [
        Regulator("RMA — Royal Monetary Authority of Bhutan", "https://www.rma.org.bt", "Central bank"),
    ],

    "Brunei": [
        Regulator("AMBD — Autoriti Monetari Brunei Darussalam", "https://www.ambd.gov.bn", "Central bank"),
    ],

    "Cambodia": [
        Regulator("CASF — Cambodia Association of Securities Firms", "https://www.casf.org.kh", "Industry association"),
        Regulator("CGCC — Credit Guarantee Corporation of Cambodia", "https://www.cgcc.com.kh", "Credit guarantee"),
        Regulator("NBC — National Bank of Cambodia", "https://www.nbc.gov.kh", "Central bank"),
        Regulator("NBFSA — Non-Bank Financial Services Authority", "https://www.nbfsa.gov.kh", "Non-bank financial supervisor"),
        Regulator("SERC — Securities and Exchange Regulator of Cambodia", "https://www.serc.gov.kh", "Securities supervisor"),
    ],

    "China": [
        Regulator("AMAC — Asset Management Association of China", "https://www.amac.org.cn", "Industry association"),
        Regulator("CBIRC — Banking and Insurance Regulatory Commission", "http://www.cbirc.gov.cn", "Banking & insurance supervisor"),
        Regulator("CFFEX — China Financial Futures Exchange", "http://www.cffex.com.cn", "Futures exchange"),
        Regulator("CSRC — China Securities Regulatory Commission", "http://www.csrc.gov.cn", "Securities supervisor"),
        Regulator("DCE — Dalian Commodity Exchange", "http://www.dce.com.cn", "Commodities exchange"),
        Regulator("China Carbon Emission Trading", "https://www.cnemission.com", "Carbon market"),
        Regulator("GFEX — Guangzhou Futures Exchange", "http://www.gfex.com.cn", "Futures exchange"),
        Regulator("MOFCOM — Ministry of Commerce", "http://www.mofcom.gov.cn", "Government — commerce"),
        Regulator("MOF — Ministry of Finance", "http://www.mof.gov.cn", "Government — finance"),
        Regulator("MPS — Ministry of Public Security", "http://www.mps.gov.cn", "Law enforcement"),
        Regulator("NAFMII — National Association of Financial Market Institutional Investors", "https://www.nafmii.org.cn", "Industry association"),
        Regulator("National Audit Office", "http://www.audit.gov.cn", "Audit oversight"),
        Regulator("NDRC — National Development and Reform Commission", "https://www.ndrc.gov.cn", "Macro planning"),
        Regulator("NFRA — National Financial Regulatory Administration", "https://www.nfra.gov.cn", "Financial supervisor (succ. CBIRC)"),
        Regulator("PBoC — People's Bank of China", "http://www.pbc.gov.cn", "Central bank"),
        Regulator("SHFE — Shanghai Futures Exchange", "http://www.shfe.com.cn", "Commodities exchange"),
        Regulator("INE — Shanghai International Energy Exchange", "https://www.ine.cn", "Energy futures"),
        Regulator("SSE — Shanghai Stock Exchange", "http://www.sse.com.cn", "Securities exchange"),
        Regulator("SZSE — Shenzhen Stock Exchange", "http://www.szse.cn", "Securities exchange"),
        Regulator("SAFE — State Administration of Foreign Exchange", "http://www.safe.gov.cn", "FX regulator"),
        Regulator("State Council", "https://www.gov.cn", "Government"),
        Regulator("Supreme People's Court", "https://www.court.gov.cn", "Judiciary"),
        Regulator("Supreme People's Procuratorate", "https://www.spp.gov.cn", "Prosecution"),
        Regulator("ZCE — Zhengzhou Commodity Exchange", "http://www.czce.com.cn", "Commodities exchange"),
        Regulator("CAC — Cyberspace Administration", "https://www.cac.gov.cn", "Cybersecurity / data"),
        Regulator("MIIT — Ministry of Industry and Information Technology", "https://www.miit.gov.cn", "Industry / tech"),
        Regulator("PBoC Credit Reference Center", "http://www.pbccrc.org.cn", "Credit reporting"),
    ],

    "India": [
        Regulator("AMFI — Association of Mutual Funds in India", "https://www.amfiindia.com", "Industry association"),
        Regulator("BSE — Bombay Stock Exchange", "https://www.bseindia.com", "Securities exchange"),
        Regulator("Income Tax Department", "https://incometaxindia.gov.in", "Tax"),
        Regulator("CBI — Central Bureau of Investigation", "https://cbi.gov.in", "Law enforcement"),
        Regulator("CIC — Central Information Commission", "https://cic.gov.in", "Information rights"),
        Regulator("CCI — Competition Commission of India", "https://www.cci.gov.in", "Competition"),
        Regulator("Department of Financial Services", "https://financialservices.gov.in", "Government — finance"),
        Regulator("Enforcement Directorate", "https://www.enforcementdirectorate.gov.in", "Anti-money-laundering enforcement"),
        Regulator("FIU-IND — Financial Intelligence Unit", "https://fiuindia.gov.in", "FIU"),
        Regulator("IRDAI — Insurance Regulatory and Development Authority", "https://www.irdai.gov.in", "Insurance supervisor"),
        Regulator("IFSCA — International Financial Services Centres Authority", "https://www.ifsca.gov.in", "IFSC supervisor"),
        Regulator("MCA — Ministry of Corporate Affairs", "https://www.mca.gov.in", "Companies registry"),
        Regulator("Ministry of Finance", "https://www.finmin.nic.in", "Government — finance"),
        Regulator("MCX — Multi Commodity Exchange", "https://www.mcxindia.com", "Commodities exchange"),
        Regulator("NCDEX — National Commodity & Derivatives Exchange", "https://www.ncdex.com", "Derivatives exchange"),
        Regulator("NPCI — National Payments Corporation of India", "https://www.npci.org.in", "Payments"),
        Regulator("NSE — National Stock Exchange", "https://www.nseindia.com", "Securities exchange"),
        Regulator("PFRDA — Pension Fund Regulatory and Development Authority", "https://www.pfrda.org.in", "Pensions supervisor"),
        Regulator("RBI — Reserve Bank of India", "https://www.rbi.org.in", "Central bank"),
        Regulator("SEBI — Securities and Exchange Board of India", "https://www.sebi.gov.in", "Securities supervisor"),
        Regulator("SFIO — Serious Fraud Investigation Office", "https://sfio.nic.in", "Fraud investigation"),
        Regulator("ICAI — Institute of Chartered Accountants of India", "https://www.icai.org", "Audit profession"),
        Regulator("DRI — Directorate of Revenue Intelligence", "https://dri.nic.in", "Customs / revenue"),
        Regulator("UIDAI — Aadhaar Authority", "https://uidai.gov.in", "Identity"),
        Regulator("CVC — Central Vigilance Commission", "https://cvc.gov.in", "Anti-corruption"),
    ],

    "Indonesia": [
        Regulator("Bank Indonesia", "https://www.bi.go.id", "Central bank"),
        Regulator("KPK — Corruption Eradication Commission", "https://www.kpk.go.id", "Anti-corruption"),
        Regulator("OJK — Financial Services Authority", "https://www.ojk.go.id", "Financial supervisor"),
        Regulator("PPATK — Indonesian Financial Transaction Reports and Analysis Center", "https://www.ppatk.go.id", "FIU"),
        Regulator("KOMDIGI — Ministry of Communication and Digital", "https://www.komdigi.go.id", "Telecoms / digital"),
        Regulator("Indonesia Customs (Bea Cukai)", "https://www.beacukai.go.id", "Customs"),
        Regulator("BSSN — National Cyber and Crypto Agency", "https://www.bssn.go.id", "Cybersecurity"),
    ],

    "Japan": [
        Regulator("BOJ — Bank of Japan", "https://www.boj.or.jp", "Central bank"),
        Regulator("CAA — Consumer Affairs Agency", "https://www.caa.go.jp", "Consumer protection"),
        Regulator("FSA Japan — Financial Services Agency", "https://www.fsa.go.jp", "Financial supervisor"),
        Regulator("JPX — Japan Exchange Group", "https://www.jpx.co.jp", "Securities exchange"),
        Regulator("JAFIC — Japan Financial Intelligence Center", "https://www.npa.go.jp/sosikihanzai/jafic", "FIU"),
        Regulator("JSDA — Japan Securities Dealers Association", "https://www.jsda.or.jp", "Industry association"),
        Regulator("JVCEA — Japan Virtual and Crypto Assets Exchange Association", "https://jvcea.or.jp", "Industry — crypto"),
        Regulator("JPX Derivatives", "https://www.jpx.co.jp/english/markets/derivatives", "Derivatives exchange"),
        Regulator("PPC — Personal Information Protection Commission", "https://www.ppc.go.jp", "Data protection"),
        Regulator("TOCOM — Tokyo Commodity Exchange", "https://www.tocom.or.jp", "Commodities exchange"),
        Regulator("JPX Equities", "https://www.jpx.co.jp/english/markets/equities", "Securities exchange"),
        Regulator("NPA — National Police Agency", "https://www.npa.go.jp", "Law enforcement"),
        Regulator("Ministry of Internal Affairs and Communications", "https://www.soumu.go.jp", "Government — telecom"),
    ],

    "Laos": [
        Regulator("Bank of Lao PDR", "https://www.bol.gov.la", "Central bank"),
        Regulator("Lao Securities Commission Office", "https://www.seco.gov.la", "Securities supervisor"),
    ],

    "Macau": [
        Regulator("MOEX — Monetary Authority of Macao", "https://www.moex.com.mo", "Central bank"),
        Regulator("MCAX — Macao Chamber of Commerce", "https://www.mcax.mo", "Industry association"),
        Regulator("AMCM — Monetary Authority of Macao", "https://www.amcm.gov.mo", "Central bank"),
        Regulator("GPDP — Office for Personal Data Protection", "https://www.gpdp.gov.mo", "Data protection"),
    ],

    "Maldives": [
        Regulator("CMDA — Capital Market Development Authority", "https://www.cmda.gov.mv", "Securities supervisor"),
        Regulator("MMA — Maldives Monetary Authority", "https://www.mma.gov.mv", "Central bank"),
    ],

    "Mongolia": [
        Regulator("Bank of Mongolia", "https://www.mongolbank.mn", "Central bank"),
        Regulator("Mongolia FIU", "https://www.fiu.mn", "FIU"),
        Regulator("FRC — Financial Regulatory Commission", "https://www.frc.mn", "Financial supervisor"),
        Regulator("IAAC — Independent Authority Against Corruption", "https://www.iaac.mn", "Anti-corruption"),
    ],

    "Myanmar": [
        Regulator("CBM — Central Bank of Myanmar", "https://www.cbm.gov.mm", "Central bank"),
        Regulator("SECM — Securities and Exchange Commission of Myanmar", "https://www.secmyanmar.gov.mm", "Securities supervisor"),
    ],

    "Nepal": [
        Regulator("Nepal Rastra Bank", "https://www.nrb.org.np", "Central bank"),
        Regulator("SEBON — Securities Board of Nepal", "https://www.sebon.gov.np", "Securities supervisor"),
    ],

    "New Zealand": [
        Regulator("Commerce Commission", "https://comcom.govt.nz", "Competition"),
        Regulator("XRB — External Reporting Board", "https://www.xrb.govt.nz", "Financial reporting"),
        Regulator("NZ Police FIU", "https://www.police.govt.nz/advice/businesses-and-organisations/fiu", "FIU"),
        Regulator("FMA — Financial Markets Authority", "https://www.fma.govt.nz", "Financial supervisor"),
        Regulator("MBIE — Ministry of Business, Innovation and Employment", "https://www.mbie.govt.nz", "Government — business"),
        Regulator("Privacy Commissioner", "https://www.privacy.org.nz", "Data protection"),
        Regulator("RBNZ — Reserve Bank of New Zealand", "https://www.rbnz.govt.nz", "Central bank"),
        Regulator("SFO — Serious Fraud Office", "https://www.sfo.govt.nz", "Fraud investigation"),
    ],

    "North Korea": [
        Regulator("Central Bank of the DPRK", "http://www.cbk.gov.kp", "Central bank"),
    ],

    "Pakistan": [
        Regulator("FMU — Financial Monitoring Unit", "https://www.fmu.gov.pk", "FIU"),
        Regulator("NAB — National Accountability Bureau", "https://nab.gov.pk", "Anti-corruption"),
        Regulator("SECP — Securities and Exchange Commission of Pakistan", "https://www.secp.gov.pk", "Securities supervisor"),
        Regulator("SBP — State Bank of Pakistan", "https://www.sbp.org.pk", "Central bank"),
        Regulator("FBR — Federal Board of Revenue", "https://www.fbr.gov.pk", "Tax / customs"),
        Regulator("NACTA — National Counter Terrorism Authority", "https://www.nacta.gov.pk", "Counter-terrorism"),
    ],

    "Papua New Guinea": [
        Regulator("Bank of Papua New Guinea", "https://www.bankpng.gov.pg", "Central bank"),
        Regulator("SCPNG — Securities Commission", "https://www.scpng.gov.pg", "Securities supervisor"),
    ],

    "Philippines": [
        Regulator("AMLC — Anti-Money Laundering Council", "https://www.amlc.gov.ph", "FIU / supervisor"),
        Regulator("BSP — Bangko Sentral ng Pilipinas", "https://www.bsp.gov.ph", "Central bank"),
        Regulator("Insurance Commission", "https://www.insurance.gov.ph", "Insurance supervisor"),
        Regulator("National Privacy Commission", "https://www.privacy.gov.ph", "Data protection"),
        Regulator("Office of the Ombudsman", "https://www.ombudsman.gov.ph", "Anti-corruption"),
        Regulator("PSE — Philippine Stock Exchange", "https://www.pse.com.ph", "Securities exchange"),
        Regulator("SEC Philippines — Securities and Exchange Commission", "https://www.sec.gov.ph", "Securities supervisor"),
        Regulator("CICC — Cybercrime Investigation and Coordinating Center", "https://www.cicc.gov.ph", "Cybercrime"),
        Regulator("BIR — Bureau of Internal Revenue", "https://www.bir.gov.ph", "Tax"),
    ],

    "South Korea": [
        Regulator("ACRC — Anti-Corruption and Civil Rights Commission", "https://www.acrc.go.kr", "Anti-corruption"),
        Regulator("BoK — Bank of Korea", "https://www.bok.or.kr", "Central bank"),
        Regulator("DAXA — Digital Asset eXchange Alliance", "https://www.daxa.or.kr", "Industry — crypto"),
        Regulator("FSEC — Financial Security Institute", "https://www.fsec.or.kr", "Financial cybersecurity"),
        Regulator("FSC — Financial Services Commission", "https://www.fsc.go.kr", "Financial supervisor"),
        Regulator("FSS — Financial Supervisory Service", "https://www.fss.or.kr", "Financial supervisor"),
        Regulator("KASB — Korea Accounting Standards Board", "https://www.kasb.or.kr", "Accounting standards"),
        Regulator("KAMCO — Korea Asset Management Corporation", "https://www.kamco.or.kr", "Asset management"),
        Regulator("KCMI — Korea Capital Market Institute", "https://www.kcmi.re.kr", "Industry research"),
        Regulator("KCB — Korea Credit Bureau", "https://www.kcredit.or.kr", "Credit reporting"),
        Regulator("Korea Customs Service", "https://www.customs.go.kr", "Customs"),
        Regulator("KRX — Korea Exchange", "https://www.krx.co.kr", "Securities exchange"),
        Regulator("KFB — Korea Federation of Banks", "https://www.kfb.or.kr", "Industry association"),
        Regulator("KoFIU — Korea Financial Intelligence Unit", "https://www.kofiu.go.kr", "FIU"),
        Regulator("KOFIA — Korea Financial Investment Association", "https://www.kofia.or.kr", "Industry association"),
        Regulator("KSD — Korea Securities Depository", "https://www.ksd.or.kr", "Settlement / depository"),
        Regulator("MOEF — Ministry of Economy and Finance", "https://www.moef.go.kr", "Government — finance"),
        Regulator("Korean National Police Agency", "https://www.police.go.kr", "Law enforcement"),
        Regulator("National Tax Service", "https://www.nts.go.kr", "Tax"),
        Regulator("PIPC — Personal Information Protection Commission", "https://www.pipc.go.kr", "Data protection"),
        Regulator("KISA — Korea Internet & Security Agency", "https://www.kisa.or.kr", "Cybersecurity"),
    ],

    "Sri Lanka": [
        Regulator("CBSL — Central Bank of Sri Lanka", "https://www.cbsl.gov.lk", "Central bank"),
        Regulator("CSE — Colombo Stock Exchange", "https://www.cse.lk", "Securities exchange"),
        Regulator("SEC Sri Lanka", "https://www.sec.gov.lk", "Securities supervisor"),
    ],

    "Taiwan": [
        Regulator("Ministry of Justice", "https://www.moj.gov.tw", "Government — justice"),
        Regulator("CBC — Central Bank of the Republic of China (Taiwan)", "https://www.cbc.gov.tw", "Central bank"),
        Regulator("FSC Taiwan — Financial Supervisory Commission", "https://www.fsc.gov.tw", "Financial supervisor"),
        Regulator("MOEA — Ministry of Economic Affairs", "https://www.moea.gov.tw", "Government — economy"),
        Regulator("MOF — Ministry of Finance", "https://www.mof.gov.tw", "Government — finance"),
        Regulator("TDCC — Taiwan Depository and Clearing Corporation", "https://www.tdcc.com.tw", "Settlement / depository"),
        Regulator("MJIB — Ministry of Justice Investigation Bureau", "https://www.mjib.gov.tw/en", "Investigation / FIU"),
        Regulator("TAIFEX — Taiwan Futures Exchange", "https://www.taifex.com.tw", "Futures exchange"),
        Regulator("Taiwan High Prosecutors Office", "https://www.tph.moj.gov.tw", "Prosecution"),
    ],

    "Thailand": [
        Regulator("AMLO — Anti-Money Laundering Office", "https://www.amlo.go.th", "FIU"),
        Regulator("ASCO — Association of Securities Companies", "https://www.asco.or.th", "Industry association"),
        Regulator("BoT — Bank of Thailand", "https://www.bot.or.th", "Central bank"),
        Regulator("CIB — Central Investigation Bureau", "https://cib.go.th", "Law enforcement"),
        Regulator("DSI — Department of Special Investigation", "https://www.dsi.go.th", "Investigation"),
        Regulator("NACC — National Anti-Corruption Commission", "https://www.nacc.go.th", "Anti-corruption"),
        Regulator("OIC — Office of Insurance Commission", "https://www.oic.or.th", "Insurance supervisor"),
        Regulator("PDPC — Personal Data Protection Committee", "https://www.pdpc.or.th", "Data protection"),
        Regulator("Revenue Department", "https://www.rd.go.th", "Tax"),
        Regulator("SEC Thailand", "https://www.sec.or.th", "Securities supervisor"),
        Regulator("SET — Stock Exchange of Thailand", "https://www.set.or.th", "Securities exchange"),
        Regulator("BOI — Board of Investment", "https://www.boi.go.th", "Investment promotion"),
        Regulator("CCIB — Cyber Crime Investigation Bureau", "https://ccib.go.th", "Cybercrime"),
        Regulator("ETDA — Electronic Transactions Development Agency", "https://www.etda.or.th", "Digital — e-transactions"),
    ],

    "Vietnam": [
        Regulator("SBV AML Page", "https://www.sbv.gov.vn/webcenter/portal/en/home/sbv/aml", "AML page"),
        Regulator("Government Inspectorate of Vietnam", "https://www.giv.gov.vn", "Inspection / anti-corruption"),
        Regulator("MoF Vietnam — Ministry of Finance", "https://www.mof.gov.vn", "Government — finance"),
        Regulator("MOST — Ministry of Science and Technology", "https://www.most.gov.vn", "Science / tech"),
        Regulator("SBV — State Bank of Vietnam", "https://www.sbv.gov.vn", "Central bank"),
        Regulator("SSC — State Securities Commission", "https://www.ssc.gov.vn", "Securities supervisor"),
        Regulator("MPS — Ministry of Public Security", "https://mps.gov.vn", "Law enforcement"),
        Regulator("AIS — Authority of Information Security", "https://ais.gov.vn", "Cybersecurity"),
    ],

    "European Union": [
        Regulator("EBA — European Banking Authority", "https://www.eba.europa.eu", "Banking supervisor"),
        Regulator("ESMA — European Securities and Markets Authority", "https://www.esma.europa.eu", "Securities supervisor"),
    ],

    "United Kingdom": [
        Regulator("Bank of England", "https://www.bankofengland.co.uk", "Central bank"),
        Regulator("FCA — Financial Conduct Authority", "https://www.fca.org.uk", "Financial supervisor"),
        Regulator("FCDO — Foreign, Commonwealth & Development Office", "https://www.gov.uk/government/organisations/foreign-commonwealth-development-office", "Foreign affairs"),
        Regulator("PRA — Prudential Regulation Authority", "https://www.bankofengland.co.uk/prudential-regulation", "Prudential supervisor"),
    ],

    "United States": [
        Regulator("CFTC — Commodity Futures Trading Commission", "https://www.cftc.gov", "Derivatives supervisor"),
        Regulator("DOJ — Department of Justice", "https://www.justice.gov", "Law enforcement"),
        Regulator("Nasdaq", "https://www.nasdaq.com", "Securities exchange"),
        Regulator("PCAOB — Public Company Accounting Oversight Board", "https://pcaobus.org", "Audit oversight"),
        Regulator("SEC — Securities and Exchange Commission", "https://www.sec.gov", "Securities supervisor"),
        Regulator("FinCEN — Financial Crimes Enforcement Network", "https://www.fincen.gov", "FIU"),
        Regulator("OFAC — Office of Foreign Assets Control", "https://ofac.treasury.gov", "Sanctions"),
    ],

    "International / Standard-setters": [
        Regulator("AFI — Alliance for Financial Inclusion", "https://www.afi-global.org", "Financial inclusion network"),
        Regulator("ACCA Global", "https://www.accaglobal.com", "Audit profession"),
        Regulator("BIS — Bank for International Settlements", "https://www.bis.org", "International standards"),
        Regulator("BCBS — Basel Committee on Banking Supervision", "https://www.bis.org/bcbs", "Banking standards"),
        Regulator("CPMI — Committee on Payments and Market Infrastructures", "https://www.bis.org/cpmi", "Payments standards"),
        Regulator("FATF — Financial Action Task Force", "https://www.fatf-gafi.org", "AML/CTF standards"),
        Regulator("FC4S — Financial Centres for Sustainability", "https://www.fc4s.org", "Sustainability network"),
        Regulator("FSB — Financial Stability Board", "https://www.fsb.org", "Financial stability"),
        Regulator("GDF — Global Digital Finance", "https://www.globaldigitalfinance.org", "Digital finance"),
        Regulator("GFTN — Global Finance & Technology Network", "https://www.gftn.org", "Industry network"),
        Regulator("GFIN — Global Financial Innovation Network", "https://www.thegfin.com", "Innovation network"),
        Regulator("GFLEC — Global Financial Literacy Excellence Center", "https://gflec.org", "Financial education"),
        Regulator("GFMA — Global Financial Markets Association", "https://www.gfma.org", "Industry association"),
        Regulator("GLEIF — Global Legal Entity Identifier Foundation", "https://www.gleif.org", "Entity identification"),
        Regulator("G20", "https://www.g20.org", "Inter-governmental"),
        Regulator("IFRS Foundation", "https://www.ifrs.org", "Accounting standards"),
        Regulator("IACA — International Anti-Corruption Academy", "https://www.iaca.int", "Anti-corruption training"),
        Regulator("INATBA — International Association for Trusted Blockchain Applications", "https://www.inatba.org", "Blockchain standards"),
        Regulator("IADI — International Association of Deposit Insurers", "https://www.iadi.org", "Deposit insurance"),
        Regulator("IAIS — International Association of Insurance Supervisors", "https://www.iaisweb.org", "Insurance supervision"),
        Regulator("IBFed — International Banking Federation", "https://www.ibfed.org", "Industry association"),
        Regulator("ICMA — International Capital Market Association", "https://www.icmagroup.org", "Capital markets"),
        Regulator("ICGN — International Corporate Governance Network", "https://www.icgn.org", "Corporate governance"),
        Regulator("ICSA — International Council of Securities Associations", "https://www.icsa.global", "Securities industry"),
        Regulator("IFAC — International Federation of Accountants", "https://www.ifac.org", "Accounting profession"),
        Regulator("IFIAR — International Forum of Independent Audit Regulators", "https://www.ifiar.org", "Audit oversight"),
        Regulator("IMF — International Monetary Fund", "https://www.imf.org", "International finance"),
        Regulator("International SME", "https://www.international-sme.org", "SME network"),
        Regulator("OECD Financial Education", "https://www.oecd.org/financial/education", "Financial education"),
        Regulator("IOPS — International Organisation of Pension Supervisors", "https://www.iopsweb.org", "Pensions"),
        Regulator("IOSCO — International Organization of Securities Commissions", "https://www.iosco.org", "Securities standards"),
        Regulator("ISLA — International Securities Lending Association", "https://www.islaemea.org", "Securities lending"),
        Regulator("ISDA — International Swaps and Derivatives Association", "https://www.isda.org", "Derivatives industry"),
        Regulator("IFSB — Islamic Financial Services Board", "https://www.ifsb.org", "Islamic finance standards"),
        Regulator("NGFS — Network for Greening the Financial System", "https://www.ngfs.net", "Sustainable finance"),
        Regulator("OECD", "https://www.oecd.org", "Inter-governmental"),
        Regulator("SBFN — Sustainable Banking and Finance Network", "https://www.sbfnetwork.org", "Sustainable finance"),
        Regulator("Egmont Group", "https://egmontgroup.org", "FIU coordination"),
        Regulator("UNCTAD", "https://unctad.org", "Trade and development"),
        Regulator("UNEP FI — UN Environment Programme Finance Initiative", "https://www.unepfi.org", "Sustainable finance"),
        Regulator("UNODC — UN Office on Drugs and Crime", "https://www.unodc.org", "AML/CTF / drugs"),
        Regulator("Wolfsberg Group", "https://www.wolfsberg-principles.com", "Banking AML standards"),
        Regulator("World Bank", "https://www.worldbank.org", "Development finance"),
        Regulator("WFE — World Federation of Exchanges", "https://www.world-exchanges.org", "Exchanges association"),
    ],

    "ASEAN & Regional Networks": [
        Regulator("APG — Asia/Pacific Group on Money Laundering", "https://www.apgml.org", "FATF-style regional body"),
        Regulator("ARIN-AP — Asset Recovery Inter-Agency Network", "https://www.arin-ap.org", "Asset recovery"),
        Regulator("Pacific Transnational Crime Network", "https://www.pacifictransnationalcrimenetwork.org", "Law enforcement network"),
        Regulator("ASEAN Secretariat", "https://asean.org", "Inter-governmental"),
        Regulator("ASEANAPOL", "https://www.aseanapol.org", "Regional law enforcement"),
        Regulator("INTERPOL Asia & South Pacific", "https://www.interpol.int/Who-we-are/Where-we-work/Asia-and-the-South-Pacific", "International police"),
    ],
}


# RSS feeds with reasonably stable endpoints — these are added to live-pull config
KNOWN_RSS_FEEDS: list[tuple[str, str, str, str]] = [
    # (label, url, jurisdiction-tag, default-topic)
    ("FATF news", "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.rss", "All jurisdictions", "AML enforcement"),
    ("BIS news", "https://www.bis.org/list/press_releases/index.rss", "All jurisdictions", "Regulatory tech"),
    ("FSB news", "https://www.fsb.org/feed/", "All jurisdictions", "Regulatory tech"),
    ("OECD news", "https://www.oecd.org/news/news.xml", "All jurisdictions", "Regulatory tech"),
    ("IMF news", "https://www.imf.org/external/rss/en/news.aspx", "All jurisdictions", "Regulatory tech"),
    ("World Bank news", "https://www.worldbank.org/en/news/rss", "All jurisdictions", "Regulatory tech"),
    ("UNODC news", "https://www.unodc.org/unodc/index.rss", "All jurisdictions", "AML enforcement"),
    ("APG news", "https://www.apgml.org/news/index.aspx?type=rss", "All jurisdictions", "AML enforcement"),
    ("FCA UK", "https://www.fca.org.uk/news/rss.xml", "All jurisdictions", "Regulatory tech"),
    ("Bank of England", "https://www.bankofengland.co.uk/rss/news", "All jurisdictions", "Regulatory tech"),
    ("US SEC press releases", "https://www.sec.gov/news/pressreleases.rss", "All jurisdictions", "Regulatory tech"),
    ("FinCEN news", "https://www.fincen.gov/feed/news_release", "All jurisdictions", "AML enforcement"),
    ("CFTC press releases", "https://www.cftc.gov/PressRoom/PressReleases/rss", "All jurisdictions", "Regulatory tech"),
]


def all_jurisdictions() -> list[str]:
    """Jurisdictions in display order."""
    return JURISDICTION_ORDER


def regulators_for(jurisdiction: str) -> list[Regulator]:
    """Return regulators for a given jurisdiction (or empty list if unknown)."""
    return list(REGULATORS.get(jurisdiction, []))


def total_count() -> int:
    return sum(len(v) for v in REGULATORS.values())


def total_with_rss() -> int:
    return sum(1 for v in REGULATORS.values() for r in v if r.rss_url)


def search(query: str) -> list[tuple[str, Regulator]]:
    """Substring search across name + url + type. Returns (jurisdiction, regulator)."""
    q = (query or "").strip().lower()
    if not q:
        return []
    results: list[tuple[str, Regulator]] = []
    for jur in JURISDICTION_ORDER:
        for r in REGULATORS.get(jur, []):
            haystack = (r.name + " " + r.url + " " + r.type).lower()
            if q in haystack:
                results.append((jur, r))
    return results
