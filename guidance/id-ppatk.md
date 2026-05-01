## Indonesia — STR (LTKM) Filing Guidance

### Legal basis
- **UU TPPU 2010** (Law No. 8 of 2010 on Prevention and Eradication of Money Laundering Crimes)
- **UU PPT 2013** (Law No. 9 of 2013 on Prevention and Eradication of Terrorism Financing)
- **PPATK Head Regulations** — particularly the *Peraturan Kepala PPATK* on customer due diligence, beneficial ownership, and the LTKM filing channel
- Sectoral rules:
  - **POJK 12/POJK.01/2017** (as amended) on AML/CFT for financial-services sector — applies to OJK-supervised commercial banks (*Bank Umum*), rural banks (*BPR / BPRS*), insurers, capital-market intermediaries, fintech P2P lenders, multifinance, pension funds
  - **PBI 23/6/PBI/2021** on Payment Service Providers (PSPs) — applies to e-money issuers, payment-system providers, switching, clearing, settlement
  - **Bappebti regulations** — apply to *Pedagang Aset Kripto* (crypto-asset traders) registered with the Commodity Futures Trading Regulatory Agency

### Who must file
**OJK-supervised financial sector** (*Pihak Pelapor* under POJK 12/2017):
- *Bank Umum* (commercial banks)
- *Bank Perekonomian Rakyat* (BPR) and *Bank Pembiayaan Rakyat Syariah* (BPRS) — rural banks, conventional and Sharia
- Insurers and reinsurers (life, general, Sharia)
- Securities companies (broker-dealers, investment managers)
- Fintech peer-to-peer lending platforms
- Multifinance and consumer-finance companies
- Pension funds (*dana pensiun*)
- Custodian banks

**BI-supervised payment sector**:
- E-money issuers (OVO, GoPay, DANA, ShopeePay, LinkAja, etc.)
- Payment-system providers (PSP) including switching, clearing, settlement
- Money remitters (KUPVA Bukan Bank)

**Bappebti-supervised**:
- Crypto-asset physical traders (*Pedagang Aset Kripto*) — Tokocrypto, Indodax, Pintu, etc.

**PPATK-direct (Profesi)**:
- Notaries (*notaris*)
- Advocates (*advokat*)
- Public accountants (*akuntan publik*)
- Real-estate agents (*agen properti*)
- Dealers in precious metals and stones (*pedagang logam mulia dan permata*)
- Automotive dealers (*pedagang kendaraan bermotor*)

### Threshold for filing
"Knows or has reasonable suspicion" (*mengetahui atau patut menduga*) under UU TPPU 2010 Article 23(1) that a transaction:
- deviates from the customer's profile, characteristics, or transaction pattern;
- is intended to avoid being reported under the Act;
- is funded by, or to be used for, an act of money laundering, terrorism financing, or one of the Article 2 predicate offences;
- the customer's identity or beneficial ownership cannot be verified.

### Timing
- File **within 3 working days** from the determination of suspicion (UU TPPU 2010 Article 23(2)).
- **Terrorism financing: file immediately** under UU PPT 2013.
- LTKT (cash transactions ≥ IDR 500,000,000 in a single working day) and LTKL (international funds transfers ≥ IDR 100,000,000) are filed separately. LTKM is filed in addition where suspicion exists.

### Filing channel
**GRIPS** (Gathering Reports & Information Processing System) — the PPATK reporting portal.

- Authentication: digital certificates issued by PPATK to *Pejabat Penanggung Jawab* (designated AML officer) and authorised data-entry officers.
- Electronic XML upload via API or portal.
- Each *Pihak Pelapor* must register with PPATK and obtain a unique reporting ID.

### Required content (LTKM-prescribed schema)
1. *Pihak Pelapor* identification — institution name, OJK / BI / PPATK code, sector, branch
2. *Pengguna Jasa* (customer) — full identity, NIK / NPWP, occupation, address, beneficial owner
3. Transaction(s) — date, channel (BI-FAST, RTGS, kliring, cash, e-wallet, crypto on-ramp), amount in IDR (and original currency)
4. Reasons for suspicion — narrative referencing UU TPPU 2010 Article 2 predicate offence(s)
5. Action taken by the reporting institution
6. Attachments (CDD documents, transaction records, screening output)

### Predicate offences (UU TPPU 2010 Article 2, abbreviated)
Corruption, bribery, narcotics, psychotropics, trafficking in persons, smuggling of migrant workers, unauthorised arms trade, terrorism, theft, embezzlement, fraud, currency forgery, gambling, prostitution, taxation crimes, banking crimes, capital-market crimes, insurance crimes, customs crimes, excise crimes, environmental crimes (illegal logging, illegal fishing, illegal mining), human trafficking, sexual exploitation of children, kidnapping, terrorism financing.

### Tipping-off
UU TPPU 2010 Article 12 prohibits *Pihak Pelapor* and its directors, commissioners, officials and employees from disclosing the existence of an LTKM to the *Pengguna Jasa* or to any unauthorised party. Customer-facing communications about EDD, transaction holds, or account closures must be drafted to comply.

### Penalties for non-filing
UU TPPU 2010 Article 12 prescribes administrative sanctions (fines, licence-related action) and Article 27 prescribes criminal penalties (imprisonment up to 5 years and/or fines up to IDR 1 billion) for officers found responsible for non-compliance with the LTKM obligation.

### Practical tips
- PPATK publishes regular *Tipologi* (typology) bulletins — incorporate the bulletin reference where the case fits (e.g. *Tipologi BCM* on investment-scam mule-victim layering; *Tipologi KKN* on corruption-proceeds layering).
- For e-wallet rapid-movement cases, cross-reference PBI 23/6/PBI/2021 and the OVO / GoPay / DANA wallet-pair pattern.
- Crypto-asset cases: cite Bappebti registration status of the *Pedagang Aset Kripto* and link to the on-ramp / off-ramp pattern.
- For corruption-related cases involving public officials, expect parallel KPK (Komisi Pemberantasan Korupsi) interest — coordinate disclosures via PPATK rather than directly to law enforcement.
