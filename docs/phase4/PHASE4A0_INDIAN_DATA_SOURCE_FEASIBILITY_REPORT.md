# PROPVAL AI — PHASE 4A-0: INDIAN REAL ESTATE DATA SOURCE FEASIBILITY AUDIT

**Audit Date:** November 3, 2026  
**Auditor Profile:** Senior Real Estate Data Architect, Indian Property Registration Research Analyst, Data Governance Specialist & Fintech Data Engineer  
**Status:** Complete Feasibility Audit (No Code Modified / Strictly Research & Architecture)

---

## 1. Executive Summary

PropVal AI is an enterprise automated valuation model (AVM) and property intelligence platform built on React 19, FastAPI, PostgreSQL 16 / PostGIS, Alembic, CatBoost ML, and conformal uncertainty prediction. A core architectural gate requires at least **1,000 verified empirical deed transactions** with exact registration identifiers, monetary consideration, timestamps, property classification, and spatial coordinates before models can be trained and calibrated for a specific micro-market.

This feasibility audit investigates the technical, legal, and operational viability of acquiring genuine empirical property transaction and deed records across India. 

### Key Findings
1. **The "Open API" Fallacy:** No state registration department in India (including Kaveri 2.0 in Karnataka, IGR Maharashtra, TNREGINET in Tamil Nadu, or IGRS Telangana) operates an open, public-facing REST API for automated bulk transaction deed extraction. All public citizen portals are designed exclusively for manual single-record searches protected by CAPTCHAs, OTPs, Aadhaar/virtual ID verification, and per-search search-fee payments.
2. **Legal & Compliance Boundaries:** Direct automated scraping or attempting to bypass portal CAPTCHA/session tokens violates portal Terms of Service, Section 43/66 of the Information Technology Act (2000), and creates non-compliance risks under the **Digital Personal Data Protection Act, 2023 (DPDP Act 2023)** regarding personally identifiable information (PII) of buyers, sellers, and witnesses in registered deeds.
3. **Institutional & Authorized Pathways:** Lawful bulk and automated deed transaction ingestion is viable exclusively through two authorized channels:
   - **Authorized State B2B / G2B Institutional Gateways:** E.g., Maharashtra IGR's authorized institutional data subscription / title verification API integration (accessible to financial institutions, banks, and authorized research/fintech entities), and Karnataka D-PAT / institutional land records framework.
   - **Licensed Commercial Real Estate Transaction Aggregators:** Specialized data providers (e.g., Zapkey, Propstack, CRE Matrix, Liases Foras) who maintain official B2B licensing, offline Sub-Registrar Office (SRO) data acquisition pipelines, index-II sanitization protocols, and structured APIs providing PII-cleansed deed metadata.
   - **Open Data Benchmarks (Guidance / Circle Rates):** Government open data portals (data.gov.in) provide macro-level guidance values and district-level statistics, but *not* granular deed-level actual transaction prices.
4. **Recommended Initial Pilot:** A dual-track pilot combining:
   - **Primary Track (Micro-Market Deed Transactions):** An authorized B2B data licensing evaluation with an accredited property transaction provider (such as Zapkey or Propstack) targeting **Bengaluru Urban (Karnataka)** and **Mumbai Suburban / Pune (Maharashtra)** to acquire an initial cohort of 2,500–5,000 structured, geocoded, PII-stripped historical registered deed transactions.
   - **Secondary Track (Macro & Baseline Rates):** Official ingestion of published Government Guidance/Ready Reckoner circle rate schedules from Karnataka Kaveri and Maharashtra IGR open datasets to establish baseline valuation floors.

---

## 2. State-Wise Data Source Inventory

### 2.1 Karnataka — Kaveri 2.0
* **Official Portal:** [https://kaveri.karnataka.gov.in](https://kaveri.karnataka.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Department of Stamps and Registration, Government of Karnataka.
* **Available Public Services:** Property valuation guidance rate search, registered deed search (Index-II), Encumbrance Certificate (EC) generation, Certified Copy (CC) requests.
* **Technical Accessibility Tier:** **Class D / E** (Manual citizen portal access; no public REST API; OTP/CAPTCHA gated).
* **Automated Data Access Feasibility:** 
  - Citizen portal uses encrypted payload handshakes and per-query CAPTCHA.
  - Integration for private tech platforms is only permitted via formal MoU under the Karnataka Centre for e-Governance (CeG) / Bhoomi / Kaveri API gateway for registered banks and licensed NBFCs.
* **Geographical Coverage:** All 31 districts of Karnataka, with highest fidelity in BBMP / BDA (Bengaluru Urban and Rural).
* **Update Frequency:** Real-time for registration; public index updated on deed stamp clearance.

### 2.2 Maharashtra — Inspector General of Registration (IGR)
* **Official Portal:** [https://igrmaharashtra.gov.in](https://igrmaharashtra.gov.in) & e-Search portal [https://esearchigr.maharashtra.gov.in](https://esearchigr.maharashtra.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Registration & Stamps Department, Government of Maharashtra.
* **Available Public Services:** e-Search (free and paid search of Index-II data), Ready Reckoner (ASR) rates, e-Step-in, e-Registration of Leave & License / Sale deeds.
* **Technical Accessibility Tier:** **Class C & D** (Manual citizen e-Search; authorized institutional subscription available for banks/institutions).
* **Automated Data Access Feasibility:**
  - IGR Maharashtra operates one of the most mature digitized index repositories in India.
  - Manual access requires paid registration on e-Search (fees per year/search).
  - Formal institutional tie-ups (IGR Institutional Search API) exist for scheduled commercial banks and authorized legal search firms, requiring formal enterprise security audits and government undertakings.
* **Geographical Coverage:** Full state (Mumbai City, Mumbai Suburban, Pune, Thane, Nagpur, etc.).
* **Update Frequency:** Daily deed index sync.

### 2.3 Andhra Pradesh — Registration & Land Records (IGRS AP & Meebhoomi)
* **Official Portal:** [https://registration.ap.gov.in](https://registration.ap.gov.in) and [https://meebhoomi.ap.gov.in](https://meebhoomi.ap.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Registration and Stamps Department, Government of Andhra Pradesh.
* **Available Public Services:** Market value search, certified copy inspection, Encumbrance search, Adangal/1-B land records.
* **Technical Accessibility Tier:** **Class D / E** (Manual access; citizen OTP gated; Webland/Meebhoomi services restricted).
* **Automated Data Access Feasibility:** 
  - No public API for automated deed harvesting.
  - Land records APIs are integrated through Andhra Pradesh e-Pragati portal, strictly gated to state departments and empanelled fintechs via APOnline.
* **Geographical Coverage:** Statewide (Visakhapatnam, Vijayawada, Guntur, Tirupati, etc.).
* **Update Frequency:** Daily transaction indexing.

### 2.4 Tamil Nadu — TNREGINET
* **Official Portal:** [https://tnreginet.gov.in](https://tnreginet.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Commercial Taxes and Registration Department, Government of Tamil Nadu.
* **Available Public Services:** Guideline value search, EC search, Document status, registered deed copy application.
* **Technical Accessibility Tier:** **Class D / E** (Manual access; rate-limited; CAPTCHA on deed lookup).
* **Automated Data Access Feasibility:**
  - Strict bot detection, dynamic session cookies, and CAPTCHA challenge-response on search forms.
  - No public API. Institutional access is governed via TNeGA (Tamil Nadu e-Governance Agency) for state initiatives and empanelled financial institutions.
* **Geographical Coverage:** Chennai, Kanchipuram, Chengalpattu, Coimbatore, and all 38 districts.
* **Update Frequency:** Regular (continuous deed indexing).

### 2.5 Telangana — Registration and Stamps Department (IGRS Telangana / Dharani)
* **Official Portal:** [https://registration.telangana.gov.in](https://registration.telangana.gov.in) & [https://dharani.telangana.gov.in](https://dharani.telangana.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Registration and Stamps Department / Revenue Department, Government of Telangana.
* **Available Public Services:** Market value assistance, EC search, Registered deed details (Prohibited properties search, agricultural land record portal Dharani).
* **Technical Accessibility Tier:** **Class D / E** (Citizen portal with mobile OTP verification; no public REST API).
* **Automated Data Access Feasibility:**
  - Automated queries without human authentication are blocked.
  - Official T-Hub / ITE&C department data exchanges require institutional sandbox empanelment.
* **Geographical Coverage:** Greater Hyderabad Municipal Corporation (GHMC), Rangareddy, Medchal-Malkajgiri, and broader Telangana.
* **Update Frequency:** Real-time deed processing.

### 2.6 Delhi — Revenue Department / DORIS
* **Official Portal:** [https://esearch.delhigovt.nic.in](https://esearch.delhigovt.nic.in) & [https://revenue.delhi.gov.in](https://revenue.delhi.gov.in) *(Accessed: November 2026)*
* **Responsible Department:** Revenue Department, Government of NCT of Delhi.
* **Available Public Services:** Delhi Online Registration Information System (DORIS), Circle rate lookup, deed search.
* **Technical Accessibility Tier:** **Class D / E** (Manual web search; sporadic uptime; NIC CAPTCHA protection).
* **Automated Data Access Feasibility:** No public automated API. Circle rates are published as static notifications and PDF tables.
* **Geographical Coverage:** 11 Revenue Districts of Delhi.
* **Update Frequency:** Static circle rates; daily deed processing.

---

## 3. Alternative Institutional, Open & Commercial Sources

| Category | Source Name | Description & URL | Accessibility Model | Viability for PropVal AI |
| :--- | :--- | :--- | :--- | :--- |
| **Open Government Data** | Open Government Data (OGD) Platform India | [https://data.gov.in](https://data.gov.in) *(Accessed: Nov 2026)* | **Class B** (Public bulk download / Open API with API key) | High for guidance values and macro trends; **Zero** for deed-level micro transaction prices. |
| **Central Valuation / Housing** | RBI / NHB RESIDEX | [https://residex.nhb.org.in](https://residex.nhb.org.in) *(Accessed: Nov 2026)* | **Class E** (Quarterly published index / Macro city indices) | Useful as a benchmark macro trend feature; no deed-level training data. |
| **Commercial Real Estate Intelligence** | Zapkey Technologies | [https://www.zapkey.com](https://www.zapkey.com) *(Accessed: Nov 2026)* | **Class C** (Commercial B2B API / Bulk Data Feed) | **Highest.** Specialized in digitized, geocoded registered Index-II transactions (Maharashtra, Bengaluru, etc.). |
| **Commercial Real Estate Intelligence** | Propstack / CRE Matrix | [https://www.propstack.com](https://www.propstack.com) / [https://crematrix.com](https://crematrix.com) *(Accessed: Nov 2026)* | **Class C** (Enterprise B2B Subscription / Custom Feeds) | High for commercial, residential high-rises, and institutional project registrations. |
| **Mortgage / Banking Data** | CERSAI (Central Registry of Securitisation Asset Reconstruction and Security Interest) | [https://www.cersai.org.in](https://www.cersai.org.in) *(Accessed: Nov 2026)* | **Class C / F** (Regulated entity access only; strict statutory clearance) | Highly restricted; only accessible to regulated lending entities (banks/NBFCs). Not viable for general tech evaluation. |

---

## 4. Data Field Feasibility Matrix

The following table assesses the empirical availability of required valuation fields across key Indian data sources:

| Target Field | Kaveri 2.0 (Karnataka) | IGR Maharashtra | TNREGINET (Tamil Nadu) | Licensed Data Provider (e.g. Zapkey/Propstack) | Open Data (data.gov.in / NHB) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Transaction Identifier** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Registration Number** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Registration Date** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Transaction Amount (Consideration Value)** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Guidance / Ready Reckoner Value** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | PARTIALLY AVAILABLE (Aggregated) |
| **Property Type (Flat, Plot, Commercial)** | PARTIALLY AVAILABLE | AVAILABLE | PARTIALLY AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **State** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE |
| **District** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE |
| **Sub-District / SRO Office** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Village / Locality / Sector** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Survey Number / Plot Number** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Land Area (Extent in Sq Ft / Sq M)** | AVAILABLE (Plots) | AVAILABLE (Plots) | AVAILABLE (Plots) | AVAILABLE | NOT AVAILABLE |
| **Built-up Area / Carpet Area** | PARTIALLY AVAILABLE (often Super Built-up) | AVAILABLE (Carpet / Built-up noted in Index-II) | PARTIALLY AVAILABLE | AVAILABLE (Standardized carpet & super built-up) | NOT AVAILABLE |
| **Property Classification / Use** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Geographic Coordinates (Lat/Long)** | NOT AVAILABLE (Textual address only) | NOT AVAILABLE (Textual address only) | NOT AVAILABLE (Textual address only) | AVAILABLE (Geocoded via master project spatial database) | NOT AVAILABLE |
| **Source Reference & Deed Type** | AVAILABLE (Sale, Gift, Mortgage, etc.) | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |
| **Verification / Stamp Clearance Status** | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | NOT AVAILABLE |

### Field Availability Classification Summary:
* **Government SRO Portals (Kaveri, IGR, TNREGINET):** Registration identifiers, deed dates, reported consideration amounts, stamp duty, SRO office, survey numbers, and legal property descriptions are **AVAILABLE** in raw documents. However, **Geographic Coordinates are NOT AVAILABLE** directly in the registration records—they are stored solely as textual schedules of boundaries and revenue identifiers. Geocoding requires entity matching with municipal and spatial cadastral layers.
* **Licensed Commercial Providers:** Have pre-engineered GIS geocoding pipelines mapping registered deed survey/flat numbers to verified polygon coordinates, making Lat/Long **AVAILABLE**.
* **Open Government Data:** Strictly aggregated or macro-level; individual deed fields are **NOT AVAILABLE**.

---

## 5. Technical Accessibility & Anti-Scraping Audit

| Source | Official Portal URL | Technical Access Classification | API Availability | Auth / Security Controls | Commercial Usage Rights |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Karnataka Kaveri 2.0** | `kaveri.karnataka.gov.in` | **Class D** (Manual citizen portal) | No public API. B2B via CeG for empanelled banks. | Session cookies, per-action CAPTCHA, SMS OTP for citizen accounts. | Citizen inspection only. Scraping explicitly prohibited by IT terms. |
| **Maharashtra IGR** | `igrmaharashtra.gov.in` | **Class C & D** (Manual e-Search + Institutional API) | Official Institutional API exists for licensed entities. | User registration, per-search fee payment, IP whitelisting for institutional API. | Commercial use permitted via formal institutional license agreement. |
| **Tamil Nadu TNREGINET** | `tnreginet.gov.in` | **Class D** (Manual citizen portal) | No public API. TNeGA gateway for state entities. | Image CAPTCHA, strict request throttling, citizen login. | Terms restrict automated extraction and redistribution. |
| **Telangana IGRS** | `registration.telangana.gov.in` | **Class D** (Manual citizen portal) | No public API. | Mobile OTP verification, Cloudflare / WAF protections. | Inspection only. Automated queries blocked. |
| **Delhi DORIS** | `esearch.delhigovt.nic.in` | **Class D** (Manual citizen portal) | No public API. | NIC CAPTCHA, manual form submission. | General inspection; no automated bulk license. |
| **India OGD (Data.gov.in)** | `data.gov.in` | **Class A & B** (Documented REST API & CSV download) | Fully documented Open API with API Key. | Registered API token; per-minute rate limits. | Permitted under National Data Sharing and Accessibility Policy (NDSAP). |
| **Zapkey / Propstack** | Commercial B2B Gateways | **Class A & C** (Documented REST API / S3 Data Feed) | Dedicated REST JSON API & bulk parquet/CSV delivery. | API Key / OAuth 2.0 Bearer tokens, IP whitelisting. | Fully authorized under commercial data licensing contract. |

> [!CAUTION]
> **Technical Access Warning:** Attempting automated headless browser scraping (e.g., Selenium, Playwright, Puppeteer) against Kaveri 2.0 or TNREGINET violates portal Terms of Service and triggers Web Application Firewall (WAF) IP bans. It is strictly excluded from PropVal AI architecture.

---

## 6. Legal, Governance & Privacy Review

### 6.1 Digital Personal Data Protection Act, 2023 (DPDP Act 2023)
* **Status & Relevance:** Passed by Parliament and notified in the Gazette of India; enforcement framework applies to digital processing of personal data.
* **Risk in Property Deeds:** Registered deeds contain direct Personally Identifiable Information (PII), including:
  - Full names of buyer, seller, confirming parties, and witnesses.
  - Residential addresses and contact numbers.
  - PAN cards, Aadhaar numbers (or masked Aadhaar), and passport photographs attached to deed index copies.
* **Governance Requirement for PropVal AI:**
  - **De-Identification & Anonymization:** PropVal AI's property valuation engine requires property attributes (location, area, age, amenities, floor) and transaction economics (date, price, stamp duty, guidance rate). **It does not require and must never ingest party personal identifiers.**
  - **In-flight PII Masking:** Any acquisition pipeline must sanitize buyer/seller names, identity card numbers, and signatures prior to loading records into PropVal AI's PostgreSQL transaction tables.
  - **Purpose Limitation:** Under Section 6 of the DPDP Act, data must only be processed for the lawful purpose explicitly stated.

### 6.2 IT Act (2000) & Terms of Use Restrictions
* Bypassing security controls, CAPTCHAs, or token expirations on state portals is a violation under Section 43 (Damage to computer system / unauthorized access) and Section 66 of the Information Technology Act, 2000.
* Lawful compliance requires either **authorized institutional API integration agreements** or **procurement from legally licensed commercial aggregators** whose collection methods and licensing agreements indemnify downstream software platforms.

### 6.3 Commercial Usage & Data Intellectual Property
* Data published on government portals under citizen lookup services is licensed solely for individual verification of encumbrances and title.
* Commercial redistribution or monetized automated valuation based on raw government web page extraction without an institutional license is actionable under copyright and breach of terms.
* Open Data under NDSAP (data.gov.in) permits commercial use, but does not contain individual transaction deeds.

---

## 7. Source Prioritization Matrix

Each potential source is scored on a scale of 1 to 10 across key architectural dimensions:
* **Authenticity (15%):** Legal deed verification and government-backed record reliability.
* **Availability & Access (15%):** Ease of lawful automated or scheduled integration without technical blockage.
* **API Maturity (15%):** Availability of documented, predictable machine-to-machine interfaces.
* **Licensing Clarity (15%):** Clear commercial usage rights and compliance with DPDP Act.
* **Spatial & Field Depth (20%):** Completeness of micro-market attributes (built-up area, carpet area, lat/long).
* **Cost & Feasibility (20%):** Feasibility within early-stage pilot budgets and resource constraints.

| Candidate Source | Authenticity (15%) | Availability (15%) | API Maturity (15%) | Licensing Clarity (15%) | Field & Spatial Depth (20%) | Cost Feasibility (20%) | Weighted Score (100%) | Priority Rank |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Zapkey / Propstack (B2B Data Provider)** | 9.5 | 9.0 | 9.5 | 9.5 | 9.0 | 7.0 | **8.85** | **1 (Recommended Pilot)** |
| **Maharashtra IGR (Authorized Institutional Access)** | 10.0 | 6.5 | 7.5 | 8.5 | 7.5 | 6.5 | **7.70** | **2 (Recommended G2B)** |
| **Karnataka Kaveri 2.0 (Official CeG MoU)** | 10.0 | 5.0 | 6.0 | 8.0 | 7.0 | 6.0 | **6.90** | **3 (Strategic Long-term)** |
| **Open Government Data (data.gov.in)** | 9.0 | 9.0 | 8.5 | 10.0 | 3.0 | 10.0 | **6.45** | **4 (Baseline Rates Only)** |
| **Telangana IGRS / Dharani (Govt Direct)** | 9.5 | 4.0 | 4.0 | 7.0 | 6.5 | 7.0 | **6.15** | **5** |
| **Tamil Nadu TNREGINET (Govt Direct)** | 9.5 | 3.5 | 3.0 | 6.0 | 6.0 | 7.0 | **5.65** | **6** |
| **Delhi DORIS (Govt Direct)** | 8.5 | 3.0 | 2.0 | 5.5 | 5.0 | 7.0 | **4.95** | **7** |

---

## 8. Recommended Pilot Strategy for PropVal AI

### 8.1 Recommended Target Micro-Markets
1. **Bengaluru Urban (Karnataka):** Whitefield, Bellandur, Electronic City, and HSR Layout corridors.
2. **Mumbai Suburban / Pune (Maharashtra):** Andheri-Bandra corridor (Mumbai) or Hinjewadi / Wakad corridor (Pune).

### 8.2 Recommended Source Architecture (Two-Track Approach)

```
+--------------------------------------------------------------------------------------------------------+
|                                    PROPVAL AI DATA ACQUISITION PILOT                                    |
+--------------------------------------------------------------------------------------------------------+
                                                    |
             +--------------------------------------+--------------------------------------+
             |                                                                             |
             v                                                                             v
+---------------------------------------------+               +---------------------------------------------+
|    TRACK 1: EMPIRICAL TRANSACTION DEEDS     |               |    TRACK 2: STATUTORY GUIDANCE BASELINES    |
| (Target: 2,500 - 5,000 Verified Records)    |               |         (Macro Rate Calibration)            |
+---------------------------------------------+               +---------------------------------------------+
| Source: Licensed B2B Transaction Provider   |               | Source: Maharashtra Ready Reckoner /        |
|         (e.g., Zapkey / Propstack feed)     |               |         Karnataka Kaveri Guidance Tables    |
| Delivery: Authorized B2B REST API / S3 CSV  |               | Delivery: Open Data / Department Tables     |
| Attributes:                                 |               | Attributes:                                 |
|  - Registered deed date & number            |               |  - SRO unit rates (per sq m / sq ft)        |
|  - Actual transacted consideration value    |               |  - Ward / survey number base values         |
|  - Verified carpet / built-up area          |               |  - Property classification multipliers      |
|  - PII-Stripped (No buyer/seller identity)  |               |                                             |
|  - Lat / Long spatial point coordinates     |               |                                             |
+---------------------------------------------+               +---------------------------------------------+
             |                                                                             |
             +--------------------------------------+--------------------------------------+
                                                    |
                                                    v
+--------------------------------------------------------------------------------------------------------+
|                          PROPVAL AI INGESTION & DATA VALIDATION PIPELINE                               |
|                                                                                                        |
|  1. In-flight PII Audit & Purge Gate                                                                   |
|  2. Schema Mapping into `TransactionRecord` ORM entity                                                 |
|  3. PostGIS Spatial Point Projection (EPSG:4326)                                                       |
|  4. Outlier & Data Quality Filters (e.g., nominal consideration vs guidance rate check)                |
|  5. Minimum 1,000 Deed ML Readiness Gate Enforcement                                                   |
+--------------------------------------------------------------------------------------------------------+
```

### 8.3 Justification for Track 1 & Track 2
* **Compliance with PropVal AI ML Readiness Gate:** The CatBoost ML model requires $\ge 1,000$ verified empirical deeds with real market clearing prices. Public citizen portals cannot lawfully or technically yield 1,000 deeds programmatically without breaching security controls. A commercial B2B evaluation bundle yields high-fidelity, geocoded, legally compliant data with zero anti-scraping litigation risk.
* **Instant Geographic Alignment:** Commercial feeds already bridge the gap between Indian revenue records (Survey No./Gat No.) and spatial coordinates (Latitude/Longitude), which are mandatory for PostGIS queries in PropVal AI.
* **DPDP Act Zero-Liability:** Reputable vendors deliver PII-sanitized index data, ensuring PropVal AI never stores or processes protected citizen personal data.

---

## 9. Estimated Integration Complexity

| Pipeline Component | Estimated Engineering Effort | Technical Dependencies | Risk Level |
| :--- | :--- | :--- | :--- |
| **PII Sanitizer & Ingestion Filter** | 3-5 Engineering Days | Python regular expressions, spaCy / PII detection rules | Low |
| **PostGIS Spatial Loader** | 2-3 Engineering Days | SQLAlchemy GeoAlchemy2, PostGIS extension, spatial indexing | Low |
| **B2B API / S3 Feed Adapter** | 4-6 Engineering Days | HTTP client / AWS S3 client, schema mapping to PropVal AI models | Low |
| **Outlier & Consideration Sanity Checks** | 3-4 Engineering Days | Guidance rate boundary ratio checks, IQR outlier filtering | Medium |
| **G2B Institutional MoU (If pursuing direct)** | 3-6 Months Administrative Lead Time | Legal vetting, state e-Governance agency security audit | High (Administrative) |

---

## 10. Recommended Next Actions

1. **Procure Sample B2B Evaluation Cohort:** Engage with an authorized transaction aggregator (e.g., Zapkey or Propstack) to obtain a sample evaluation dataset (1,000 to 2,000 anonymized records) for Bengaluru Urban (Whitefield/Bellandur) or Mumbai Suburban (Andheri/Bandra).
2. **Design Ingestion Schema Mapping:** Map vendor payload fields directly to the existing PropVal AI database models without altering core application logic.
3. **Formalize DPDP Data Hygiene Policy:** Draft an internal data governance standard verifying that all ingested transactions are strictly anonymized and devoid of citizen identity markers before entering the PostGIS repository.
4. **Benchmark Model Training in Pilot Zone:** Once the sample dataset is loaded and passes the 1,000-deed ML readiness gate, execute the existing CatBoost training pipeline and evaluate conformal uncertainty intervals on authentic Indian transactions.

---

*Report prepared strictly in accordance with PropVal AI Phase 4A-0 Research & Feasibility Guidelines. No code altered. No unauthorized requests executed.*

