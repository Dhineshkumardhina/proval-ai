# PropVal AI — Phase 5C Data License & Usage Governance Matrix

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Data Governance, Privacy Compliance & Legal Rights Matrix  
**Regulatory Frameworks:** Digital Personal Data Protection Act 2023 (DPDP), Information Technology Act 2000, Section 43A, RBI Master Direction on Outsourcing of Financial Services, NHB HFC Guidelines  
**Audit Standard:** ISO/IEC 27701 (Privacy Information Management) & ISO 8000 (Data Quality)  
**Date:** 2026-11-05  
**Auditor Roles:** Senior Data Governance Architect & Institutional Compliance Counsel  

> [!IMPORTANT]
> **Data Privacy & Statutory Governance Mandate:**  
> Indian real estate transactions contain public records (Registration Act 1908, Sub-Registrar Office Index II deeds) alongside sensitive institutional credit data. Under the Digital Personal Data Protection Act 2023 (DPDP Act) and RBI regulatory directives, **all personal identifiers (borrower names, Aadhaar/PAN references, seller names, contact details) must be cryptographically redacted or permanently stripped prior to storage and machine learning ingestion.**  
> PropVal AI strictly ingests only **economic, cadastral, structural, and spatial attributes** of real estate transactions.

---

## 1. Data Classification Taxonomy

PropVal AI categorizes all ingested real-estate data into 5 distinct operational and regulatory tiers:

| Tier Code | Classification Tier | Description & Source Origin | Permitted Storage | ML Model Eligibility |
| :--- | :--- | :--- | :--- | :--- |
| **CLASS_A** | **Official SRO Registered Deeds** | Directly attested Sub-Registrar Office (SRO) Index II deed records. | Permanent (Hashed PII) | **Eligible** (`is_verified_deed=True`) |
| **CLASS_B** | **Licensed B2B Commercial Feeds** | Contractually licensed transactional feeds (PropEquity, Zapkey, PropStack). | As per License Terms | **Eligible** (`is_verified_deed=True`) |
| **CLASS_C** | **Institutional Loan Book Portfolios**| Consortium HFC/NBFC historical mortgage collateral transaction books. | 8 Years (RBI Mandate) | **Eligible** (`is_verified_deed=True`) |
| **CLASS_D** | **Public & Open Government Data** | State circle rates, guideline values, RERA disclosures, Census spatial layers. | Indefinite Public Data | **Reference Only** (Guideline Baseline) |
| **CLASS_F** | **Synthetic & Simulation Fixtures**| In-memory generated test deeds, seed benchmarks, developer mock datasets. | Ephemeral / Sandbox | **STRICTLY QUARANTINED** (`is_verified_deed=False`) |

---

## 2. Comprehensive Provider Data License & Usage Matrix

The following matrix governs the legal acquisition basis, permitted operational uses, privacy constraints, and retention rules for every provider integrated into PropVal AI:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    PROPVAL AI DATA USAGE & GOVERNANCE MATRIX                                     │
├────────────────────┬──────────────┬────────────┬─────────────────────────────┬───────────────────┬──────────────┤
│ Provider Name      │ Identifier   │ Class Tier │ Permitted Purposes          │ DPDP / PII Action │ ML Eligible? │
├────────────────────┼──────────────┼────────────┼─────────────────────────────┼───────────────────┼──────────────┤
│ PropEquity         │ propequity   │ CLASS_B    │ Hedonic Val, ML Training    │ Mask Party Names  │ YES (Deeds)  │
│ Zapkey B2B         │ zapkey_b2b   │ CLASS_B    │ Valuation, Comparables, ML  │ Redact Citizen PII│ YES (Deeds)  │
│ PropStack          │ propstack    │ CLASS_B    │ Commercial/Resi Valuation   │ Redact Citizen PII│ YES (Deeds)  │
│ HFC Consortium     │ hfc_banking  │ CLASS_C    │ Underwriting, Risk Models   │ Pseudonymize Acct │ YES (Deeds)  │
│ RERA Authorities   │ rera_dev     │ CLASS_D    │ Project Validation, Timelines│ None (Public Org) │ Reference    │
│ OGD India          │ ogd_india    │ CLASS_D    │ Guideline Rates, Wards      │ None (Public Data)│ Reference    │
│ State IGR (Govt)   │ state_igr    │ CLASS_A    │ SRO Attestation, Deeds, ML  │ Strip Parties PII │ YES (Deeds)  │
│ Mock Generator     │ mock_deed    │ CLASS_F    │ Development & E2E Testing   │ N/A (Fictitious)  │ NEVER (FALSE)│
└────────────────────┴──────────────┴────────────┴─────────────────────────────┴───────────────────┴──────────────┘
```

---

### Detailed Provider Profiles:

### 2.1 PropEquity (`propequity`)
- **Legal Authorization Basis:** B2B Commercial Data License Agreement with P.E. Analytics Ltd.
- **Permitted Purposes:**
  - Automated Valuation Model (AVM) hedonic calculation.
  - Hedonic price index construction.
  - Supervised machine learning training (CatBoost regression).
  - Sub-market trend analysis and absorption rate analytics.
- **Prohibited Uses:**
  - Direct redistribution or resale of raw bulk data feeds.
  - De-anonymization or reverse-engineering of buyer/seller identities.
  - Public web publishing of raw transaction deed rows.
- **PII Governance:** Buyer and seller names delivered in raw feeds are discarded during normalization; only survey numbers, project names, carpet areas, transaction prices, and registration quarters are persisted.
- **Retention Schedule:** Retained for the duration of the active institutional enterprise license + 3 years archival.
- **Empirical Status:** `is_verified_deed = True` upon SRO registration reference validation.

---

### 2.2 Zapkey B2B API (`zapkey_b2b`)
- **Connector Identifier:** `zapkey_b2b`
- **Legal Authorization Basis:** Partner API Agreement with Zapkey Technologies Pvt Ltd.
- **Permitted Purposes:**
  - Real-time registered deed retrieval for comparable property analysis.
  - Underwriter verification of project-level floor-wise transaction history.
  - Empirical training of localized micro-market pricing models.
- **Prohibited Uses:**
  - Wholesale crawling or automated mirroring of the Zapkey database.
  - Sublicensing to unauthorized non-member institutions.
- **PII Governance:** Citizen identification, mobile numbers, PAN numbers, and document scan images are strictly excluded from API ingestion.
- **Retention Schedule:** Retained across rolling 10-year valuation comparables windows.
- **Empirical Status:** `is_verified_deed = True`.

---

### 2.3 PropStack (`propstack`)
- **Connector Identifier:** `propstack`
- **Legal Authorization Basis:** Commercial Enterprise Access Agreement with PropStack Data Services.
- **Permitted Purposes:**
  - Commercial and residential registered transaction benchmarking.
  - Grade-A commercial lease rental yield calibration.
  - Construction milestone tracking.
- **Prohibited Uses:**
  - Public dissemination of individual deed transactions without redaction.
- **PII Governance:** Entity names for corporate leases permitted; individual retail residential buyer identities redacted.
- **Retention Schedule:** 7 years active storage.
- **Empirical Status:** `is_verified_deed = True`.

---

### 2.4 HFC Consortium Portfolio Feeds (`hfc_banking`)
- **Connector Identifier:** `hfc_banking`
- **Legal Authorization Basis:** Mutual Consortium Data Sharing MoU under RBI/NHB Fair Lending Framework.
- **Permitted Purposes:**
  - Collateral valuation calibration across participating mortgage lenders.
  - Historical loan default vs. valuation haircut correlation analysis.
  - Stress testing of loan-to-value (LTV) liquidation haircuts.
- **Prohibited Uses:**
  - Cross-institutional borrower poaching or marketing solicitation.
  - Disclosure of member bank loan account numbers or customer profiles.
- **PII Governance:** Strict tokenization; loan account numbers replaced with salted HMAC-SHA256 hashes; customer identities removed at member firewall before ingestion.
- **Retention Schedule:** 8 years post-loan closure in compliance with RBI preservation guidelines.
- **Empirical Status:** `is_verified_deed = True` if backed by registered mortgage deed.

---

### 2.5 State RERA Developer Disclosures (`rera_developer`)
- **Connector Identifier:** `rera_developer`
- **Legal Authorization Basis:** Real Estate (Regulation and Development) Act 2016 statutory public disclosures.
- **Permitted Purposes:**
  - Project registration status and statutory completion date verification.
  - Developer quarterly progress report validation.
  - Litigated parcel identification.
- **Prohibited Uses:**
  - Automated Denial-of-Service requesting against state RERA web infrastructure.
- **PII Governance:** Developer corporate registrations are public; promoter personal contact numbers are masked.
- **Retention Schedule:** Indefinite public reference.
- **Empirical Status:** Reference metadata only (`is_asking_price = False`, non-deed).

---

### 2.6 Open Government Data — OGD India (`ogd_india`)
- **Connector Identifier:** `ogd_india`
- **Legal Authorization Basis:** National Data Sharing and Accessibility Policy (NDSAP) / Open Data License — India.
- **Permitted Purposes:**
  - Official circle rate / Ready Reckoner guideline rate lookups.
  - Administrative boundary geometry (BBMP wards, taluks, villages).
  - Infrastructure proximity indexing (Metro stations, railway lines, highways).
- **Prohibited Uses:**
  - Claiming government endorsement of automated valuations.
- **PII Governance:** Contains zero personal data.
- **Retention Schedule:** Indefinite open reference.
- **Empirical Status:** Reference guideline baseline (`guideline_rate_per_sqft`).

---

### 2.7 State Registration Departments / Inspector General of Registration (`state_igr`)
- **Connector Identifier:** `state_igr`
- **Legal Authorization Basis:** Direct State Government MoU / Electronic Search Gateway authorization (e.g. IGR Maharashtra e-Search, Kaveri Karnataka, TNREGINET).
- **Permitted Purposes:**
  - Certified SRO Index II deed attestation.
  - Primary source deed provenance for institutional mortgage underwriting.
  - Golden-record empirical ground truth for ML valuation calibration.
- **Prohibited Uses:**
  - Automated bulk scraping of public portals without express state IT authorization.
  - Commercial resale of state land records.
- **PII Governance:** Strict compliance with DPDP Act Section 6; citizen personal identifiers stripped, retaining only land parcel survey numbers, built-up areas, stamp duty paid, and registration values.
- **Retention Schedule:** Permanent statutory audit trail.
- **Empirical Status:** `is_verified_deed = True` (Highest authenticity tier: `SRO_INDEX_II_MATCH`).

---

### 2.8 Mock & Benchmark Data (`mock_deed`)
- **Connector Identifier:** `mock_deed`
- **Legal Authorization Basis:** Internally created synthetic test data fixtures.
- **Permitted Purposes:**
  - Automated continuous integration (CI) test execution.
  - Developer local sandbox environment testing.
  - UI prototyping and end-to-end load testing.
- **Strict Prohibition:**
  - **CANNOT be used for real customer property valuations.**
  - **CANNOT satisfy the 1,000 empirical deed threshold for ML activation.**
- **Enforcement Mechanism:**
  - Enforced in code via [`backend/app/verification/verification_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/verification/verification_service.py).
  - Sets `is_verified_deed = False`.
  - Sets `verification_status = "PROVISIONAL_NON_ML"`.

---

## 3. Data Protection (DPDP Act 2023) Architecture

```
[Raw Incoming Transaction Deed Payload]
                  │
                  ▼
   ┌─────────────────────────────┐
   │  DPDP Compliance Filter     │
   │  - Redact Buyer/Seller Name │
   │  - Redact Aadhaar/PAN No    │
   │  - Mask Phone & Emails      │
   │  - Retain SRO Office & Deed#│
   └──────────────┬──────────────┘
                  │ Cleaned Payload
                  ▼
   ┌─────────────────────────────┐
   │ SHA-256 Payload Hash Stored │
   │ (Cryptographic Traceability)│
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌─────────────────────────────┐
   │ Normalized Property Record  │
   │ - Carpet Area (sq.ft)       │
   │ - Transaction Price (INR)   │
   │ - Cadastral Survey Number   │
   │ - Spatial Coordinates (GPS) │
   └─────────────────────────────┘
```

### Privacy Principles Enforced:
1. **Purpose Limitation:** Transaction data is processed solely for credit collateral risk assessment, statutory valuation, and hedonic property valuation.
2. **Data Minimization:** No personal contact details, domestic tenancy agreements, or personal biometric/identity tokens are stored in the transaction table.
3. **Right of Erasure / Rectification:** If an SRO or court issues a cancellation deed or rectification notice, the platform updates the corresponding transaction status to `SUPERSEDED_BY_RECTIFICATION` and re-indexes the collateral records.

---

## 4. Audit & Regulatory Compliance Evidence

This matrix satisfies:
- **RBI Digital Lending Guidelines (2022/2023):** Clause 5 (Data Privacy and Storage), ensuring financial transaction data is stored exclusively on servers located within India.
- **National Housing Bank (NHB) Valuation Standards:** Mandatory preservation of valuation comparables documentation for a minimum of 8 years.
- **Section 43A of Information Technology Act 2000:** Reasonable security practices and procedures for sensitive economic data.

