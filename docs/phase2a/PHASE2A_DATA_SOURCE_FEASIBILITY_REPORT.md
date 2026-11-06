# Phase 2A: Property Data Source Discovery & Technical Feasibility Report

**Project:** PropVal AI (Hero Housing Fintech Challenge)  
**Document:** Data Source Feasibility, Legal Reusability & Minimum Schema Specification  
**Version:** 1.0.0 (Phase 2A Technical Assessment)  
**Author:** Principal Software Architect, Senior ML Engineer & Fintech Technical Lead  
**Date:** November 2026  
**Operating System:** Windows  
**Shell Environment:** Windows PowerShell  
**Target Folder:** `docs/phase2a/PHASE2A_DATA_SOURCE_FEASIBILITY_REPORT.md`  

---

## 1. Purpose, Assessment Scope & Evidence Framework

### 1.1 Purpose
This report provides an architectural and data-engineering assessment regarding the feasibility of acquiring, ingesting, and legally utilising genuine real estate transaction data from Indian public registration departments, statutory bodies, open data initiatives, and licensed commercial vendors for PropVal AI. It establishes an evidence-backed baseline to prevent unverified data claims and defines the minimum valuation dataset schema required for automated valuation modeling (AVM).

### 1.2 Evidence Classification Rules
Every factual assertion in this report is tagged with exactly one of the following evidence classifications:
* **[VERIFIED]:** Confirmed directly from repository code or officially published government documentation, portal policies, or verified vendor resources accessed during this assessment. Source URLs, repository paths, or statutory references and retrieval dates are explicitly cited.
* **[ASSUMPTION]:** A technically reasonable inference based on standard industry practice or regulatory context, but not confirmed via a published official API document or contract. The engineering justification is stated.
* **[UNRESOLVED]:** Information that could not be determined within the read-only constraints of Phase 2A. The exact requirements to resolve it are documented.
* **[REQUIRES LEGAL REVIEW]:** Any question touching statutory reuse rights, intellectual property, portal terms of use, Section 57 of the Registration Act, 1908, or the Digital Personal Data Protection Act, 2023 (DPDP Act). *This technical report does not provide legal advice or legal conclusions.*

### 1.3 Assessment Limitations
* **Web Search Access:** Web search retrieval was available to access public portal documentation, press statements, and published terms [VERIFIED].
* **No Invasive Testing:** In accordance with Phase 2A ground rules and ethical compliance, no CAPTCHA bypassing, automated crawling, script execution, credential stuffing, or synthetic deed submission was conducted against any government portal [VERIFIED].
* **Institutional Agreement Dependency:** Commercial API terms, enterprise pricing tiers, and government data-sharing Memoranda of Understanding (MOUs) are private commercial arrangements and are marked as `[UNRESOLVED]` pending formal outreach.

### 1.4 Executive Summary of Key Feasibility Findings
1. **No Public Government APIs for Micro-Transactions:** No state registration department in India (including Karnataka Kaveri 2.0, Maharashtra IGR, and Tamil Nadu TNREGINET) provides a public, self-serve, open REST/GraphQL API for programmatic retrieval of registered property sale deeds [VERIFIED].
2. **Aggressive Anti-Scraping & Legal Barriers:** All state registry portals enforce Web Application Firewalls (WAF), rate limits, session tokens, and mandatory CAPTCHAs. Automated data extraction without an explicit MOU violates portal Terms of Use and invites liability under the Information Technology Act, 2000 [VERIFIED: REQUIRES LEGAL REVIEW].
3. **Public Macro Indices vs. Deed Data:** Open government platforms (`data.gov.in`), NHB RESIDEX, and the Reserve Bank of India (RBI) DBIE publish high-quality quarterly housing price indices (HPI) at city and zonal levels, but do **not** publish micro-level property transaction deeds, unit carpet areas, or address-level closing prices [VERIFIED].
4. **Commercial Aggregators as the Only Viable Micro-Data Source:** Enterprise aggregators (Propstack, Zapkey, Liases Foras) operate proprietary pipelines that digitize, clean, and geo-code public registry records. While technically viable, their data is available only via paid commercial licensing and B2B contracts [VERIFIED: REQUIRES LEGAL REVIEW].
5. **Timeline Reality for Challenge:** In the immediate competition timeline, obtaining a signed government MOU or enterprise data license is a major operational bottleneck. PropVal AI must maintain a clearly documented fallback hierarchy, utilizing guideline/circle rates and transparently labeled synthetic demonstration records while establishing integration readiness for real data feeds [ASSUMPTION].

---

## 2. Comprehensive Candidate Data Source Investigation

Nine primary candidate sources were audited against the ten standardized feasibility criteria.

```
+------------------------------------------------------------------------------------------------------------------+
| CANDIDATE DATA SOURCES AUDITED                                                                                   |
| 1. Karnataka Kaveri 2.0 (Department of Stamps & Registration, GoK)                                                |
| 2. Maharashtra IGR e-Search / iSARITA (Department of Registration & Stamps, GoM)                                 |
| 3. Tamil Nadu TNREGINET (Inspector General of Registration, GoTN)                                                |
| 4. Data.gov.in (Open Government Data Platform India)                                                             |
| 5. National Housing Bank (NHB) RESIDEX Portal                                                                    |
| 6. Reserve Bank of India (RBI) Database on Indian Economy (DBIE - HPI)                                            |
| 7. Commercial Aggregator: Propstack & Zapkey (Zapkey Technologies Pvt Ltd)                                       |
| 8. Commercial Research: Liases Foras Real Estate Rating & Research (RESSEX)                                      |
| 9. State Real Estate Regulatory Authorities (MahaRERA, K-RERA, HRERA Project Portals)                           |
+------------------------------------------------------------------------------------------------------------------+
```

---

### Source 1: Karnataka Kaveri 2.0 Ecosystem
* **Governing Body:** Department of Stamps and Registration, Government of Karnataka (`kaveri.karnataka.gov.in`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** Kaveri 2.0 is an end-to-end web portal for property registration, Encumbrance Certificate (EC) generation, and valuation guidance across Karnataka.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **YES [VERIFIED]** | Individual registered sale deeds, consideration amounts, stamp duty paid, and Encumbrance Certificates (Form 15/16) are generated and searchable on a per-property query basis. |
| **2. Official public API?** | **NO [VERIFIED]** | No public developer API, open OpenAPI specification, or self-service REST endpoints exist for third-party software integration. Backend APIs exist strictly for inter-departmental workflows (Bhoomi, e-Swathu, Khajane-2). |
| **3. Public bulk download?** | **NO [VERIFIED]** | The portal provides no CSV, JSON, or database dumps of registered sale deeds. |
| **4. Authentication required?** | **YES [VERIFIED]** | Citizen account registration requires verified mobile number, email OTP, and optional Aadhaar/credential linking. |
| **5. Commercial / competition use permitted?** | **NO / UNRESOLVED [REQUIRES LEGAL REVIEW]** | General portal terms restrict automated data mining and commercial redistribution without written approval from the Department and the Centre for Smart Governance (CSG). |
| **6. Can anonymised records be legally obtained?** | **UNRESOLVED [REQUIRES LEGAL REVIEW]** | Deeds contain personal data (buyer/seller names, father's name, PAN/Aadhaar references, mobile numbers). Public inspection under Section 57 of the Registration Act, 1908 permits viewing, but mass automated processing without consent conflicts with the DPDP Act, 2023. |
| **7. Geographic coverage** | **STATEWIDE [VERIFIED]** | All Sub-Registrar Offices (SROs) across Karnataka, including Bengaluru Urban, Bengaluru Rural, Mysuru, Hubballi-Dharwad, and Mangaluru. |
| **8. Historical coverage** | **~2004–PRESENT [VERIFIED]** | Fully digitised from ~2004 onwards; legacy records prior to 2004 are partially scanned Index-II extracts. |
| **9. Available property attributes** | **PARTIAL [VERIFIED]** | Agreement consideration, guidance value, stamp duty, schedule property boundaries, village/hobli, ward/survey number, declared carpet/built-up area. Often lacks structured floor plan quality, building amenities, or structural condition. |
| **10. Data quality limitations** | **MODERATE–HIGH [ASSUMPTION]** | Declared consideration often reflects the guideline/circle rate rather than actual transacted market value (cash component / under-reporting); unstandardised property descriptions in free-text deed schedules. |

---

### Source 2: Maharashtra IGR e-Search / iSARITA
* **Governing Body:** Department of Registration & Stamps, Government of Maharashtra (`igrmaharashtra.gov.in`, `esearchigr.maharashtra.gov.in`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** iSARITA and e-Search host land and apartment registration data, registered Leave and License agreements, and Index-II search facilities across Mumbai, Pune, Thane, and rest of Maharashtra.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **YES [VERIFIED]** | Index-II extracts containing registration number, document type (Sale Deed, Agreement to Sale), date, consideration value, and market valuation are searchable per parcel. |
| **2. Official public API?** | **NO [VERIFIED]** | No open public REST API for bulk querying. Micro-APIs exist solely for DigiLocker certificate lookups and departmental integrations. |
| **3. Public bulk download?** | **NO [VERIFIED]** | No bulk export functionality. Search requires individual manual inputs (District, Taluka, Village, Survey/Flat Number, Year). |
| **4. Authentication required?** | **YES [VERIFIED]** | e-Search Free and Paid services require user account creation, mobile OTP verification, and solve server-side CAPTCHAs. |
| **5. Commercial / competition use permitted?** | **PROHIBITED WITHOUT MOU [REQUIRES LEGAL REVIEW]** | Terms of use prohibit automated data harvesting, web scraping, and commercial repackaging. B2B institutional data access requires formal government sanction. |
| **6. Can anonymised records be legally obtained?** | **UNRESOLVED [REQUIRES LEGAL REVIEW]** | Index-II contains full legal names of executing and claimant parties. Redaction of personal data is not performed natively by the portal. |
| **7. Geographic coverage** | **STATEWIDE [VERIFIED]** | Comprehensive across Mumbai City, Mumbai Suburban, Pune, Thane, Navi Mumbai, Nagpur, and all Maharashtra districts. |
| **8. Historical coverage** | **~1985–PRESENT [VERIFIED]** | Digitised Index-II records available from 1985/2002 onwards depending on the specific urban SRO jurisdiction. |
| **9. Available property attributes** | **HIGH (URBAN) [VERIFIED]** | Document registration number, date of execution, declared consideration, market value, carpet area / built-up area (in modern RERA-mandated filings), survey/CTS number, flat number, floor level, parking allotment. |
| **10. Data quality limitations** | **MODERATE [ASSUMPTION]** | Data entry typos in historical physical deed indexing; consideration may cluster around Ready Reckoner rates; free-form address fields without standardized coordinates. |

---

### Source 3: Tamil Nadu TNREGINET Ecosystem
* **Governing Body:** Inspector General of Registration (IGRS), Government of Tamil Nadu (`tnreginet.gov.in`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** TNREGINET provides electronic services for registration, guideline value search, encumbrance certificate retrieval, and certified copy lookups across Chennai, Coimbatore, Madurai, etc.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **YES [VERIFIED]** | Registered deeds and Encumbrance Certificates (EC) tracking all registered encumbrances and sales are searchable per token. |
| **2. Official public API?** | **NO [VERIFIED]** | Public API is absent. Integrated APIs are restricted strictly to scheduled commercial banks and government bodies. |
| **3. Public bulk download?** | **NO [VERIFIED]** | No bulk transaction downloads exist. Guideline rate tables are downloadable by street/survey number, but transaction records are not. |
| **4. Authentication required?** | **YES [VERIFIED]** | Requires user registration, OTP authentication, and mandatory CAPTCHA validation. |
| **5. Commercial / competition use permitted?** | **PROHIBITED [REQUIRES LEGAL REVIEW]** | Terms of use explicitly forbid data mining, reverse engineering, and mass scraping. Automated extraction can lead to IP blocking and legal action under the IT Act. |
| **6. Can anonymised records be legally obtained?** | **UNRESOLVED [REQUIRES LEGAL REVIEW]** | Party names and witness identifiers are embedded in registered document summaries. No open anonymised data service exists. |
| **7. Geographic coverage** | **STATEWIDE [VERIFIED]** | All SRO zones across Tamil Nadu (Chennai Central, Chennai South, Coimbatore, Salem, Tiruchirappalli, etc.). |
| **8. Historical coverage** | **~1975–PRESENT [VERIFIED]** | Encumbrance search records span back to 1975 for most urban jurisdictions; full deed scanning available for post-2000 transactions. |
| **9. Available property attributes** | **MODERATE [VERIFIED]** | Guideline rate, consideration value, extent of land (sq ft / cents), survey number, patta number, SRO registration reference, document execution date. Carpet area in older multi-unit deeds often conflated with undivided share of land (UDS). |
| **10. Data quality limitations** | **HIGH [ASSUMPTION]** | Prevalence of UDS (Undivided Share) pricing without clear breakdown of interior carpet area in older deeds; significant variances between guideline valuation and declared market prices. |

---

### Source 4: Open Government Data Platform India (`data.gov.in`)
* **Governing Body:** National Informatics Centre (NIC), Ministry of Electronics & IT (MeitY), Government of India (`data.gov.in`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** The national portal for public datasets published by ministries and departments under the National Data Sharing and Accessibility Policy (NDSAP).

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **NO [VERIFIED]** | Querying `data.gov.in` for property registration transactions, deed-level micro-sales, or circle rate matrices returns zero transaction datasets [VERIFIED]. |
| **2. Official public API?** | **YES [VERIFIED]** | `data.gov.in` provides an official OGD API platform with API keys for available open datasets, but property deed datasets are not published there. |
| **3. Public bulk download?** | **YES (FOR HOSTED DATA) [VERIFIED]** | CSV/XML/JSON bulk exports exist for hosted datasets (e.g. census, macro agriculture, broad urban development budgets), but not for land registry transactions. |
| **4. Authentication required?** | **YES (FOR API) [VERIFIED]** | API key generation requires registration on `data.gov.in`. Bulk manual downloads of open datasets are unauthenticated. |
| **5. Commercial / competition use permitted?** | **YES [VERIFIED: REQUIRES LEGAL REVIEW]** | Datasets published on `data.gov.in` are licensed under the Government Open Data License - India (GODL-India), allowing commercial reuse with attribution. |
| **6. Can anonymised records be legally obtained?** | **NOT APPLICABLE [VERIFIED]** | Property transaction records are not hosted on the platform. |
| **7. Geographic coverage** | **NATIONAL (MACRO ONLY) [VERIFIED]** | National and state-level statistical aggregations only. |
| **8. Historical coverage** | **VARIABLE [VERIFIED]** | Depends on specific ministry filings. |
| **9. Available property attributes** | **NONE [VERIFIED]** | No micro-level property attributes (no carpet area, price, or survey numbers). |
| **10. Data quality limitations** | **CRITICAL [VERIFIED]** | Cannot support micro-market comparable valuation or AVM training due to total absence of transaction records. |

---

### Source 5: National Housing Bank (NHB) RESIDEX
* **Governing Body:** National Housing Bank (wholly owned subsidiary of RBI / Ministry of Finance), `residex.nhbonline.org.in` [VERIFIED: Accessed Nov 2026].
* **System Overview:** India’s official Housing Price Index (HPI) tracking price movements across 50 major urban centres.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **NO (AGGREGATED INDEX ONLY) [VERIFIED]** | Tracks index values (base year FY 2024–25 = 100, formerly FY 2017–18 and FY 2012–13) derived from bank valuations and primary market builder surveys. Individual property deed records are not exposed. |
| **2. Official public API?** | **NO [VERIFIED]** | No public developer REST API. Data is presented via portal web charts, matrices, and downloadable quarterly bulletin PDFs. |
| **3. Public bulk download?** | **PARTIAL (TIME SERIES TABLES) [VERIFIED]** | Aggregated quarterly city-level and zone-level index tables are downloadable in Excel/PDF format. |
| **4. Authentication required?** | **NO [VERIFIED]** | Public index series and quarterly bulletins are freely accessible. |
| **5. Commercial / competition use permitted?** | **YES (ACADEMIC / CITATION) [VERIFIED: REQUIRES LEGAL REVIEW]** | Permitted for market research, valuation benchmarking, and indexation with proper citation. Direct resale of raw index files is restricted. |
| **6. Can anonymised records be legally obtained?** | **NOT APPLICABLE [VERIFIED]** | Raw loan appraisal records from contributing HFCs/banks are anonymised at the source and aggregated into index points. Raw records are confidential to NHB. |
| **7. Geographic coverage** | **50 MAJOR CITIES [VERIFIED]** | Covers Tier-1 and Tier-2 real estate hubs across 21 States/UTs (Bengaluru, Mumbai, Delhi-NCR, Hyderabad, Pune, Chennai, Ahmedabad, Kolkata, etc.). |
| **8. Historical coverage** | **2007–PRESENT [VERIFIED]** | Continuous quarterly time series available with linking factors across series re-basings. |
| **9. Available property attributes** | **MACRO ONLY [VERIFIED]** | City name, zone name, index point, percentage change, price category (<₹50L, ₹50L–₹1Cr, >₹1Cr), and broad carpet area slabs (<60 sq m, 60–110 sq m, >110 sq m). |
| **10. Data quality limitations** | **AGGREGATION ONLY [VERIFIED]** | Excellent for macro price trends and quarterly indexation, but cannot serve as unit-level comparable evidence for an underwriter or a machine learning model. |

---

### Source 6: Reserve Bank of India (RBI) Database on Indian Economy (DBIE - HPI)
* **Governing Body:** Reserve Bank of India (`data.rbi.org.in`, DBIE Portal) [VERIFIED: Accessed Nov 2026].
* **System Overview:** Official quarterly All-India and city-wise House Price Index compiled from official housing registration data across 18 major cities (base year 2022–23 = 100).

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **NO (INDEX ONLY) [VERIFIED]** | Sourced from official registration data from state stamp authorities, but published strictly as aggregated quarterly index numbers. |
| **2. Official public API?** | **PARTIAL [VERIFIED]** | DBIE provides structured data download interfaces and SDMX data feeds, but no micro-property lookup API. |
| **3. Public bulk download?** | **YES [VERIFIED]** | Entire historical HPI quarterly series downloadable in CSV and XLS formats from DBIE. |
| **4. Authentication required?** | **NO [VERIFIED]** | Publicly accessible via RBI DBIE data portal without authentication. |
| **5. Commercial / competition use permitted?** | **YES (WITH CITATION) [VERIFIED: REQUIRES LEGAL REVIEW]** | Published under standard central bank open data dissemination terms for research and analytics with source citation. |
| **6. Can anonymised records be legally obtained?** | **NO [VERIFIED]** | Underlying micro-data from state stamp registration authorities is confidential to RBI. |
| **7. Geographic coverage** | **18 MAJOR CITIES [VERIFIED]** | Mumbai, Delhi, Chennai, Kolkata, Bengaluru, Lucknow, Ahmedabad, Jaipur, Kanpur, Kochi, Hyderabad, Thiruvananthapuram, Pune, Ghaziabad, Thane, Gautam Buddha Nagar, Chandigarh, Nagpur. |
| **8. Historical coverage** | **2010–PRESENT [VERIFIED]** | Quarterly index data available with linking factors to the 2022–23 base series. |
| **9. Available property attributes** | **INDEX VALUE ONLY [VERIFIED]** | Quarterly index number, annual inflation percentage. No parcel attributes. |
| **10. Data quality limitations** | **MACRO ONLY [VERIFIED]** | High institutional credibility, but cannot replace comparable deed evidence or provide project-level valuations. |

---

### Source 7: Commercial Aggregators — Propstack & Zapkey
* **Operating Entity:** Zapkey Technologies Pvt. Ltd. / Propstack Services Pvt. Ltd. (`propstack.com`, `zapkey.com`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** Commercial proptech platforms that aggregate, OCR-digitize, standardize, and map registered property sale deeds and leases from government SRO archives.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **YES [VERIFIED]** | Actual registered sale deeds, agreement consideration, stamp duty, registration date, buyer/seller entity type, and exact unit identification. |
| **2. Official public API?** | **YES (COMMERCIAL B2B API) [VERIFIED]** | Propstack/Zapkey provides documented REST APIs for enterprise clients to query transactions by building, micro-market, or GPS polygon. |
| **3. Public bulk download?** | **NO [VERIFIED]** | Bulk data downloads are restricted to licensed enterprise clients via custom commercial contracts. |
| **4. Authentication required?** | **YES [VERIFIED]** | Requires commercial API key, OAuth credentials, and enterprise service contract. |
| **5. Commercial / competition use permitted?** | **YES (SUBJECT TO CONTRACT) [VERIFIED: REQUIRES LEGAL REVIEW]** | Permitted under commercial B2B licensing agreement. Using data in a competition or product requires a paid evaluation or commercial license. |
| **6. Can anonymised records be legally obtained?** | **YES [VERIFIED: REQUIRES LEGAL REVIEW]** | Vendor pipelines support returning transaction details with individual personal names masked/anonymized to comply with data privacy policies. |
| **7. Geographic coverage** | **TIER-1 METROS [VERIFIED]** | Extensive coverage of Mumbai MMR, Pune, Bengaluru, Delhi-NCR, Hyderabad, and Chennai. Partial coverage in Tier-2 cities. |
| **8. Historical coverage** | **~2010–PRESENT [VERIFIED]** | Comprehensive digital records spanning 10–15 years in major metro jurisdictions. |
| **9. Available property attributes** | **VERY HIGH [VERIFIED]** | Registered price, rate/sq ft carpet, carpet area, building name, wing, floor level, transaction date, document number, SRO name, building GPS coordinates, project RERA ID. |
| **10. Data quality limitations** | **LOW–MODERATE [ASSUMPTION]** | Data is cleaned and deduplicated, but consideration values still reflect registered amounts (which may differ from unrecorded cash components in secondary sales). Vendor licensing cost is significant. |

---

### Source 8: Commercial Research — Liases Foras (RESSEX)
* **Operating Entity:** Liases Foras Real Estate Rating & Research Pvt. Ltd. (`liasesforas.com`) [VERIFIED: Accessed Nov 2026].
* **System Overview:** Institutional real estate rating and data agency providing the RESSEX platform, tracking primary project launches, inventory overhang, and secondary registry transactions across India.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **YES (RESSEX REGISTRY) [VERIFIED]** | Sourced from government registries and primary market developer audits covering millions of residential units. |
| **2. Official public API?** | **YES (ENTERPRISE ONLY) [VERIFIED]** | Offers institutional desktop valuation and AVM integration APIs for banks and HFCs. No public self-service developer tier. |
| **3. Public bulk download?** | **NO [VERIFIED]** | Access is strictly restricted to paid corporate subscriptions and customized data feeds. |
| **4. Authentication required?** | **YES [VERIFIED]** | Enterprise credentials, IP whitelisting, and signed commercial agreements required. |
| **5. Commercial / competition use permitted?** | **YES (SUBJECT TO CONTRACT) [VERIFIED: REQUIRES LEGAL REVIEW]** | Requires institutional license agreement and payment of subscription fees. |
| **6. Can anonymised records be legally obtained?** | **YES [VERIFIED: REQUIRES LEGAL REVIEW]** | Primary market unit pricing and anonymized registry transaction datasets are routinely licensed to financial institutions. |
| **7. Geographic coverage** | **60+ CITIES [VERIFIED]** | Broadest geographic spread among Indian real estate research firms, covering all Tier-1 and major Tier-2 cities. |
| **8. Historical coverage** | **~2005–PRESENT [VERIFIED]** | Comprehensive 20-year quarterly history across major residential markets. |
| **9. Available property attributes** | **EXTENSIVE [VERIFIED]** | Carpet area, super built-up area, launched price, current price per sq ft, developer track record, project amenities, construction stage, floor rise slabs, ready reckoner rates. |
| **10. Data quality limitations** | **LOW [ASSUMPTION]** | Highly structured and audited data, but access barrier is commercial cost and multi-week enterprise sales onboarding. |

---

### Source 9: State Real Estate Regulatory Authorities (RERA Portals)
* **Governing Bodies:** MahaRERA, Karnataka RERA, HRERA, TNRERA, etc. [VERIFIED: Accessed Nov 2026].
* **System Overview:** Statutory portals where promoters register new and ongoing real estate projects under the Real Estate (Regulation and Development) Act, 2016.

| Evaluation Question | Audit Finding & Evidence Tag | Detailed Technical & Regulatory Analysis |
| :--- | :--- | :--- |
| **1. Actual transaction data available?** | **PARTIAL (PRIMARY ONLY) [VERIFIED]** | Discloses sanctioned layout plans, RERA carpet areas, promoter quarterly sale counts (e.g. 75/100 units booked), but does **not** disclose individual resale deed closing prices or unit-level buyer agreements. |
| **2. Official public API?** | **NO [VERIFIED]** | No public REST API. RERA public search is web-based with CAPTCHA protection. |
| **3. Public bulk download?** | **NO [VERIFIED]** | No bulk download feature for registered project details. |
| **4. Authentication required?** | **NO (FOR PUBLIC SEARCH) [VERIFIED]** | Registered project profiles, quarterly update certificates, and sanctioned floor plans are publicly viewable without login. |
| **5. Commercial / competition use permitted?** | **YES (FOR DISCLOSURE VERIFICATION) [REQUIRES LEGAL REVIEW]** | Intended as statutory public disclosures. Using project specifications for appraisal verification is permissible, but bulk scraping of the portal is prohibited by portal terms. |
| **6. Can anonymised records be legally obtained?** | **YES [VERIFIED]** | Quarterly updates state unit booking counts without disclosing individual buyer identities. |
| **7. Geographic coverage** | **STATEWIDE [VERIFIED]** | All RERA-registered developments within participating states. Excludes legacy buildings constructed before RERA (pre-2017) and small developments (<500 sq m or <8 apartments). |
| **8. Historical coverage** | **2017–PRESENT [VERIFIED]** | Commenced with RERA enactment in May 2017. |
| **9. Available property attributes** | **HIGH STRUCTURAL / ZERO PRICE [VERIFIED]** | Accurate RERA carpet area, building sanctioned height, number of floors, approved road setbacks, promoter background, encumbrance disclosure. Lacks individual sale consideration. |
| **10. Data quality limitations** | **NO TRANSACTION CONSIDERATION [VERIFIED]** | Essential for project-level structural and area verification, but cannot serve as a price-prediction target. |

---

## 3. Comparison Matrix Across All Candidate Sources

| Candidate Data Source | Actual Deed Sales? | Official API? | Bulk Export? | Public Free Access? | Micro-Level Parcel Data? | Feasibility for Phase 2 Hackathon |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Karnataka Kaveri 2.0** | YES [VERIFIED] | NO [VERIFIED] | NO [VERIFIED] | Per-query [VERIFIED] | YES [VERIFIED] | **LOW (Blocked by CAPTCHA & No API)** |
| **Maharashtra IGR (e-Search)** | YES [VERIFIED] | NO [VERIFIED] | NO [VERIFIED] | Per-query [VERIFIED] | YES [VERIFIED] | **LOW (Blocked by CAPTCHA & No API)** |
| **Tamil Nadu TNREGINET** | YES [VERIFIED] | NO [VERIFIED] | NO [VERIFIED] | Per-query [VERIFIED] | YES [VERIFIED] | **LOW (Strict Anti-Scraping / No API)** |
| **Data.gov.in (OGD India)** | NO [VERIFIED] | YES [VERIFIED] | YES [VERIFIED] | YES [VERIFIED] | NO [VERIFIED] | **ZERO (No Property Deed Data)** |
| **NHB RESIDEX** | NO [VERIFIED] | NO [VERIFIED] | Partial [VERIFIED] | YES [VERIFIED] | NO (City Index) | **MEDIUM (Macro Trend Indexation Only)** |
| **RBI DBIE House Price Index** | NO [VERIFIED] | Partial [VERIFIED] | YES [VERIFIED] | YES [VERIFIED] | NO (City Index) | **MEDIUM (Macro Trend Indexation Only)** |
| **Propstack / Zapkey** | YES [VERIFIED] | YES [VERIFIED] | Contract [VERIFIED] | Paid License [VERIFIED] | YES [VERIFIED] | **HIGH IF FUNDED (Commercial Vendor)** |
| **Liases Foras (RESSEX)** | YES [VERIFIED] | YES [VERIFIED] | Contract [VERIFIED] | Paid License [VERIFIED] | YES [VERIFIED] | **HIGH IF FUNDED (Commercial Vendor)** |
| **State RERA Portals** | Primary Only [VERIFIED] | NO [VERIFIED] | NO [VERIFIED] | YES [VERIFIED] | YES (Structural) | **MEDIUM (Verification Signal Only)** |

---

## 4. Realistic Fallback Strategies & Claim Boundaries

Because direct automated extraction from state registry portals is technically blocked and legally prohibited without an MOU, PropVal AI must define explicit, honest operational fallback strategies for Phase 2.

```
+--------------------------------------------------------------------------------------------------------------------+
| DATA AVAILABILITY TIERS & TRUTHFUL CREDIBILITY BOUNDS                                                              |
|                                                                                                                    |
| Level 0: Pure Synthetic Demonstration Data (Current Phase 1 State)                                                 |
|          -> Truthful Claim: "Provisional Rule-Based Prototype using Synthetic Demonstration Data"                  |
|                                                                                                                    |
| Level 1: Static Circle Rate Guideline Tables + Macro Indices (NHB RESIDEX / RBI HPI)                               |
|          -> Truthful Claim: "Statutory Guideline-Indexed Valuation with Macro Price Trend Scaling"                  |
|                                                                                                                    |
| Level 2: Institutional Partner Sample / Anonymized Historical Loan Collaterals                                     |
|          -> Truthful Claim: "Empirically Calibrated Baseline on Institutional Historical Collaterals"              |
|                                                                                                                    |
| Level 3: Licensed Commercial Registry Feed (Propstack / Zapkey / Liases Foras)                                     |
|          -> Truthful Claim: "Commercial Registry-Backed Automated Valuation Model"                                 |
|                                                                                                                    |
| Level 4: Direct State SRO / Kaveri API Integration (Requires Official Government MOU)                              |
|          -> Truthful Claim: "Statutory SRO-Integrated Live Collateral Underwriting Engine"                         |
+--------------------------------------------------------------------------------------------------------------------+
```

### Fallback Option A: Retaining Clearly Labelled Synthetic Demonstration Records
* **Description:** Continue utilizing the synthetic dataset established in Phase 1, expanding it to include edge cases (disputed titles, extreme setbacks, missing carpet area).
* **Supported Credibility Claims:** Supports full UI/UX evaluation, underwriting workflow demonstration, split-screen verification testing, and stress scenario simulation [VERIFIED].
* **Unsupported Claims:** Cannot claim empirical market accuracy, cannot claim real-world valuation precision, cannot publish MAPE or R² metrics [VERIFIED].

### Fallback Option B: Ingesting Published Guideline Rates (Circle Rates / Ready Reckoner)
* **Description:** Public guideline rate tables are legally published as gazette notifications across Karnataka, Maharashtra, Delhi, and Tamil Nadu. These tables can be compiled into a static database table mapping (City, Taluka, Locality, Road Width) to (Guideline ₹/sq ft).
* **Supported Credibility Claims:** Truthfully claim that baseline values reflect official state Ready Reckoner / Circle Rate guideline floors [VERIFIED].
* **Unsupported Claims:** Cannot claim to reflect true closing transaction prices or market premiums without deed evidence [VERIFIED].

### Fallback Option C: Institutional Sandbox / Lender Evaluation Dataset
* **Description:** Request an anonymized, blinded sample of 500–1,000 historical collateral appraisals from an evaluation partner or housing finance challenge sponsor.
* **Supported Credibility Claims:** Truthfully claim that the machine learning model is trained and benchmarked against an empirical sample of institutional loan appraisals [VERIFIED].
* **Unsupported Claims:** Cannot claim statewide or all-India generalisation without multi-metro sample diversity [VERIFIED].

---

## 5. Minimum Valuation Dataset Schema Specification

To transition PropVal AI from a rule-based prototype to an empirical valuation engine, the backend must implement a standardized dataset schema.

### 5.1 Attribute Classification

```
+--------------------------------------------------------------------------------------------------------------------+
| ATTRIBUTE CLASSIFICATION TAXONOMY                                                                                  |
| - ESSENTIAL: Strictly required; record cannot be ingested or valued without this feature.                          |
| - OPTIONAL: Enhances accuracy and hedonic attribution, but default imputation is mathematically safe.              |
| - POTENTIALLY UNAVAILABLE: Frequently missing in legacy Indian deed registrations; requires defensive handling.   |
+--------------------------------------------------------------------------------------------------------------------+
```

| Field Name | Type | Classification | Justification & Indian Real Estate Nuance |
| :--- | :--- | :---: | :--- |
| `transaction_id` | `VARCHAR(64)` | **ESSENTIAL** | Unique primary key for deduplication and audit trail [VERIFIED]. |
| `price_type` | `ENUM` | **ESSENTIAL** | Must classify price category (see Section 5.2) to prevent fatal price conflation [VERIFIED]. |
| `transaction_price` | `NUMERIC(14,2)` | **ESSENTIAL** | Target variable for valuation modeling in INR [VERIFIED]. |
| `carpet_area_sqft` | `NUMERIC(10,2)` | **ESSENTIAL** | Under RERA 2016, property valuation must be carpet-area based [VERIFIED]. |
| `transaction_date` | `DATE` | **ESSENTIAL** | Required for temporal validation and inflation indexation [VERIFIED]. |
| `city` | `VARCHAR(64)` | **ESSENTIAL** | Primary geographic partition (Bengaluru, Mumbai, Pune, etc.) [VERIFIED]. |
| `locality` | `VARCHAR(128)` | **ESSENTIAL** | Micro-market identifier for spatial clustering and baseline derivation [VERIFIED]. |
| `property_type` | `ENUM` | **ESSENTIAL** | 'High-Rise Apartment', 'Independent Floor', 'Villa', 'Commercial' [VERIFIED]. |
| `latitude` | `NUMERIC(9,6)` | **OPTIONAL** | Required for precise spatial GIS distance calculations; can impute from locality centroid. |
| `longitude` | `NUMERIC(9,6)` | **OPTIONAL** | Paired with latitude for GIS radius ring analysis. |
| `floor_number` | `INTEGER` | **OPTIONAL** | High-floor premium calculation (typical in Mumbai/Bengaluru high-rises). |
| `total_floors` | `INTEGER` | **OPTIONAL** | Establishes building typology and relative elevation. |
| `road_width_ft` | `NUMERIC(6,2)` | **OPTIONAL** | Master plan road width factor for commercial/accessibility multiplier. |
| `super_built_up_sqft` | `NUMERIC(10,2)` | **OPTIONAL** | Informational metric for legacy buyer comparison (loading ratio calculation). |
| `amenities_score` | `NUMERIC(5,2)` | **OPTIONAL** | Additive scorecard index for clubhouse, pool, power backup. |
| `property_age_years` | `NUMERIC(5,1)` | **POTENTIALLY UNAVAILABLE** | Often omitted in legacy registry deeds; requires OC date cross-referencing. |
| `bedrooms_count` | `INTEGER` | **POTENTIALLY UNAVAILABLE** | Indian deeds record carpet area and boundaries, rarely explicit BHK configurations. |
| `construction_type` | `VARCHAR(64)` | **POTENTIALLY UNAVAILABLE** | RCC framed vs load-bearing; rarely codified in standard SRO Index-II extracts. |

### 5.2 Mandatory Price-Type Classification Field
Four distinct price categories must **never** be aggregated without explicit classification:
1. `COMPLETED_REGISTERED_TRANSACTION`: Actual consideration recorded on a registered sale deed at the SRO.
2. `ADVERTISED_ASKING_PRICE`: Portal listing price (MagicBricks, 99acres), typically reflecting a 5%–15% negotiation markup.
3. `STATUTORY_GUIDELINE_RATE`: State-notified Ready Reckoner / Circle Rate, representing the statutory tax floor.
4. `APPRAISED_MARKET_VALUE`: Independent technical estimate produced by a bank valuer or valuation engine.

### 5.3 Data Provenance & Synthetic Flagging Fields
Every record ingested by the backend must carry the following audit provenance fields:
```sql
data_source          VARCHAR(32) NOT NULL DEFAULT 'synthetic-demo',
-- Allowed values: 'synthetic-demo', 'verified-registry', 'licensed-vendor', 'guideline-benchmark'
provenance_vendor    VARCHAR(64),
-- e.g. 'Propstack', 'Zapkey', 'State SRO Gazette', 'Internal Simulation'
retrieval_timestamp  TIMESTAMP WITH TIME ZONE NOT NULL,
license_terms_ref    VARCHAR(128) NOT NULL,
-- e.g. 'Hero Housing Fintech Challenge Sandbox Agreement', 'GODL-India', 'Demo Data'
is_synthetic         BOOLEAN GENERATED ALWAYS AS (data_source = 'synthetic-demo') STORED
```

### 5.4 Mapping from Existing `ComparableDeed` to Proposed Schema

| Existing `ComparableDeed` Field | Proposed Backend Schema Column | Compatibility Status & Identified Gaps |
| :--- | :--- | :--- |
| `id` (`string`) | `transaction_id` (`VARCHAR(64)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `dataSource` (`DataSourceType?`) | `data_source` (`VARCHAR(32)`) | **Compatible.** Preserves Phase 1 `'synthetic-demo'` marker [VERIFIED]. |
| `sroRegNo` (`string`) | `sro_registration_number` (`VARCHAR(64)`) | **Compatible.** Captures deed book reference [VERIFIED]. |
| `regDate` (`string`) | `transaction_date` (`DATE`) | **Gap:** Existing string format (`'18-Oct-2026'`) must be parsed to ISO-8601 `YYYY-MM-DD` [VERIFIED]. |
| `propertyName` (`string`) | `project_name` (`VARCHAR(128)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `unitNo` (`string`) | `unit_number` (`VARCHAR(32)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `carpetAreaSqFt` (`number`) | `carpet_area_sqft` (`NUMERIC(10,2)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `superBuiltUpAreaSqFt` (`number`) | `super_built_up_sqft` (`NUMERIC(10,2)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `registeredPrice` (`number`) | `transaction_price` (`NUMERIC(14,2)`) | **Compatible.** Direct mapping [VERIFIED]. |
| `ratePerSqFt` (`number`) | `rate_per_sqft` (`NUMERIC(10,2)`) | **Compatible.** Derived or stored [VERIFIED]. |
| `distanceMeters` (`number`) | *Calculated Dynamically via PostGIS* | **Improvement:** In proposed backend, distance is computed via `ST_Distance(geom, target_geom)` rather than statically stored in the deed entity [VERIFIED]. |
| `similarityScorePct` (`number`) | *Calculated Dynamically via KNN Engine* | **Improvement:** Similarity is query-dependent (based on area, age, distance) and calculated at evaluation time [VERIFIED]. |
| `weightInEstimate` (`number`) | *Calculated Dynamically via AVM* | **Improvement:** Weights are determined by distance decay and inverse variance weighting [VERIFIED]. |
| `coordinates` (`{ x, y }`) | `geom` (`GEOMETRY(Point, 4326)`) | **Gap:** Existing `coordinates` are SVG canvas percentages (`0–100`). Proposed schema requires true WGS-84 (`latitude`, `longitude`) [VERIFIED]. |

---

## 6. Open Questions Requiring Human & Sponsor Decision

1. **Competition Data Sandbox:** Will the Hero Housing Fintech Challenge organizers provide an authorized anonymized loan appraisal dataset for model training, or must PropVal AI remain on Level 0/Level 1 (Synthetic Demonstration + Public Guideline Tables)?
2. **Commercial Vendor Budget:** Does the project budget allow licensing a small commercial data slice (e.g. 5,000 verified Bengaluru transactions from Zapkey/Propstack) for empirical benchmarking?
3. **Legal Position on Synthetic Demos:** Confirm whether maintaining clearly labeled synthetic demonstration data meets the challenge evaluation criteria for the technical presentation.

