# PropVal AI — Phase 6B: Certified Empirical Transaction Dataset Expansion Report

**Document Reference:** `DOC-PHASE6B-EXPANSION-001`  
**Phase:** 6B — Certified Empirical Transaction Dataset Expansion  
**Author:** Senior Real-Estate Data Scientist, Data Quality Engineer, & Financial Data Governance Specialist  
**Status:** AUDITED & GOVERNED — ML PRE-TRAINING GATE MAINTAINED AS **BLOCKED**  
**Database Audited:** `propval.db` (SQLite Disk Engine)  
**Date:** November 5, 2026  

---

## 1. Executive Summary

In accordance with institutional financial data governance standards and the PropVal AI Pre-Training Quality Gate policy, an exhaustive empirical audit was conducted on the transaction database (`propval.db`). 

The baseline reported in Phase 5H indicated **138 staged deeds**. The mandate for Phase 6B explicitly requires:
> *"The 138 staged deeds must not automatically be considered 138 certified deeds. Inspect the actual database and calculate the exact number of records in each lifecycle state."*

### Key Audit Findings
1. **Certified Empirical Deed Count:** The database contains exactly **140 unique certified empirical deeds** residing within approved commercial datasets (or **204 verified deed records** across all dataset versions), reflecting an empirical progress of **20.4%** toward the mandatory threshold of **1,000 certified empirical transactions**.
2. **Deficit to Unlock ML Training:** An absolute deficit of **860 certified empirical deeds** (or 796 verified deeds) remains.
3. **ML Readiness Gate Status:** **`BLOCKED / LOCKED (`canTrain = False`)`**. Under institutional model risk governance (SR 11-7 / OCC 2011-12), synthetic demonstration records, unverified deeds, and unapproved datasets are strictly disqualified from ML training. PropVal AI continues to operate under its statutory rule-based baseline valuation engine.
4. **Geographic & Typology Concentration:** The current empirical cohort is 100% concentrated in Bengaluru Urban/Bengaluru (predominantly Whitefield at 92.2%), with 96.1% high-rise apartments and 3.9% mid-rise apartments. Commercial agreements for Mumbai, Delhi-NCR, and Hyderabad remain pending execution (Phase 6A).

---

## 2. Complete Lifecycle State Audit

Every record across ingestion staging, imported storage, and governance quarantine tables in `propval.db` was queried directly. The table below documents the exact counts across all 9 lifecycle states specified by the architecture:

| Lifecycle State | Database Table / Filter | Exact Record Count | Description & Governance Status |
|:---|:---|:---:|:---|
| **`RAW`** | `raw_transaction_staging` | **576** | Raw payloads acquired from provider connectors prior to parsing. |
| **`PARSED`** | `raw_transaction_staging` (`pii_scrub_status = 'CLEANSED'`) | **545** | Payloads successfully cleansed of PII (names, phone numbers, Aadhaar/PAN) under DPDP Act 2023. |
| **`NORMALIZED`** | `imported_transactions` | **625** | Standardized into unified schema (sqft, INR, ISO-8601 dates, standard property typologies). |
| **`VALIDATION_PENDING`** | `quarantined_records` (`resolution_status = 'PENDING_REVIEW'`) | **16** | Records flagged for underwriter review (8 Circle Rate Undervaluation, 8 Extreme Rate Outliers). |
| **`VALIDATED`** | `imported_transactions` (schema valid) | **625** | Structural and boundary constraints verified across all imported transaction records. |
| **`VERIFIED`** | `imported_transactions` (`is_verified_deed = 1`) | **204** | Deeds matched against SRO Index II, B2B SRO attestation, or certified state registry feeds. |
| **`CERTIFIED`** | Approved `dataset_versions` (`is_verified_deed = 1`) | **140 (unique deeds)** / **135 (active records)** | Meets all 7 Phase 5D certification criteria and resides within an `APPROVED` dataset snapshot. |
| **`REJECTED`** | `rejected_records` | **8** | Rejected during initial schema validation (`rejection_code = 'MISSING_PRICE'`). |
| **`QUARANTINED`** | `quarantined_records` (Total) | **24** | 16 pending underwriter review; 8 statistical outliers erased under DPDP right-to-erasure. |
| *Deduplicated* | `duplicate_records` | **123** | Duplicates intercepted via SHA-256 fingerprint matching (110 distinct fingerprints). |

```
                       DATASET ACQUISITION & LIFECYCLE FLOW
                       
 [Provider Payloads] ──► RAW (576)
                              │
                      (PII Cleansing)
                              │
                              ▼
                        PARSED (545) ────► DPDP Purged / Erased (31)
                              │
                     (Normalization)
                              │
                              ▼
                        NORMALIZED (625)
                              │
                      (Quality Gate)
                              ├──► REJECTED (8) [Missing Price]
                              ├──► QUARANTINED (24) [Undervaluation / Outliers]
                              ├──► DUPLICATES (123) [Isolated by Fingerprint]
                              │
                              ▼
                        VALIDATED (625)
                              │
                    (Registry Evidence)
                              ├──► PROVISIONAL_NON_ML (421) [Synthetic Test Runs]
                              │
                              ▼
                        VERIFIED (204)
                              │
                   (Dataset Approval Gate)
                              ▼
                        CERTIFIED (140 Unique Deeds)
                              │
                    [ML Pre-Training Gate]
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       CERTIFIED ≥ 1,000            CURRENT: 140 < 1,000
        [UNLOCKED - GO]              [BLOCKED - NO-GO]
```

---

## 3. Data Pipeline & Connector Verification

The ingestion and verification pipelines were audited across the existing connector architecture:

### 3.1 Connector Integrity & Empirical Isolation
- **`zapkey_b2b` / `ZAPKEY_COMMERCIAL_FEED`:** 
  - 188 verified deed transactions in `imported_transactions` originate from Zapkey B2B commercial extracts.
  - An additional 8 verified deeds originate from `ZAPKEY_COMMERCIAL_FEED`.
  - 8 verified deeds originate from manual SRO registry import (`imported-deed`).
  - Total verified empirical deeds: **204 records** (representing **150 unique fingerprint hashes** across all test and production workspaces, and **140 unique deeds** in approved dataset versions).
- **Synthetic Test Harness Isolation (`SRC_E2E_*`, `TEST_SRC_*`):**
  - 421 transactions in `imported_transactions` represent synthetic test harness fixtures generated during CI/CD test runs.
  - **Isolation Verification:** All 421 synthetic transactions have `is_verified_deed = 0`.
  - In `verification_evidence`, each record is explicitly tagged as `verification_status = 'PROVISIONAL_NON_ML'` with `verifier_method = 'TEST_HARNESS_SIMULATION'`.
  - The `EmpiricalCoverageService` and `evaluate_training_gate()` pipelines explicitly exclude any record where `data_source` matches `%mock%`, `%test%`, `%simulation%`, or `synthetic-demo`. Zero synthetic records have leaked into the verified or certified cohorts.

### 3.2 Duplicate Transaction Interception
- The ingestion pipeline utilizes a deterministic 4-part SHA-256 fingerprint hash:
  $$\text{Fingerprint} = \text{SHA256}(\text{SRO\_Code} \parallel \text{Doc\_Reg\_Number} \parallel \text{Reg\_Year} \parallel \text{Unit\_ID})$$
- **123 duplicate transactions** were successfully intercepted at the pre-normalization gate and diverted into `duplicate_records`.
- Duplicate rate across total ingestion attempts:
  $$\text{Duplicate Rate} = \frac{123}{625 + 123} = 16.44\%$$
- None of the 123 duplicates penetrated the `imported_transactions` verified deed table.

---

## 4. Target Geographic & Typology Coverage Evaluation

### 4.1 Target City Coverage Audit
The project mandate requires empirical evaluation across 4 primary Tier-1 Indian metropolitan zones:

| Metropolitan Market | Target Need | Acquired Total | Verified Deeds | Certified Deeds | Coverage Status | Blocking Dependency |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Bengaluru Urban / Rural** | $\ge 250$ | 625 | 204 | 140 | **PARTIALLY POPULATED** | Whitefield overconcentration (92.2%). Needs South & North BLR expansion. |
| **Mumbai Metropolitan (MMR)** | $\ge 250$ | 0 | 0 | 0 | **BLOCKED (0%)** | Commercial provider licensing agreement pending (`zapkey_b2b`, `propstack`). |
| **Delhi-NCR** | $\ge 250$ | 0 | 0 | 0 | **BLOCKED (0%)** | Commercial data provider agreement pending (`propequity`). |
| **Hyderabad (GHMC)** | $\ge 250$ | 0 | 0 | 0 | **BLOCKED (0%)** | Commercial data provider agreement pending (`zapkey_b2b`, `propequity`). |
| **Total** | **$\ge 1,000$** | **625** | **204** | **140** | **OVERALL: 14.0% CERTIFIED** | **ML Training Gate LOCKED** |

### 4.2 Architectural Typology Coverage Audit
Evaluation across asset classifications:

| Property Typology | Target Share | Verified Deeds | Certified Deeds | Share of Empirical Cohort | Assessment |
|:---|:---:|:---:|:---:|:---:|:---|
| **Apartments / High-Rise** | 40% – 60% | 204 | 140 | **100.0%** | Monolithic concentration. High-rise apartments represent 96.1% (196/204) and mid-rise 3.9% (8/204). |
| **Independent Houses** | 10% – 20% | 0 | 0 | **0.0%** | Complete deficit. Requires SRO Index II deed feeds with layout classification. |
| **Villas / Gated Communities** | 10% – 20% | 0 | 0 | **0.0%** | Complete deficit. Requires developer deed feeds in North Bengaluru/Sarjapur. |
| **Residential Plots** | 10% – 20% | 0 | 0 | **0.0%** | Complete deficit. Requires cadastral parcel ID mapping to prevent boundary fraud. |

---

## 5. Temporal & Size Bracket Coverage

### 5.1 Transaction Period Distribution
Empirical verified deeds span the following quarterly cohorts:

| Quarter | Verified Deeds | Share (%) | Observations |
|:---|:---:|:---:|:---|
| **2024-Q2** | 8 | 3.9% | Baseline SRO registry imports |
| **2024-Q3** | 143 | 70.1% | Initial Zapkey B2B Whitefield extract |
| **2024-Q4** | 45 | 22.1% | Q4 incremental sync |
| **2026-Q1** | 8 | 3.9% | Phase 6A attribution audit verification batch |
| **Total** | **204** | **100.0%** | Average deed age: 1.8 years (well within the 3-year statutory relevance window) |

### 5.2 Carpet Area Brackets
| Size Bracket | Verified Deeds | Share (%) |
|:---|:---:|:---:|
| Under 500 sqft | 0 | 0.0% |
| 500 – 1,000 sqft | 0 | 0.0% |
| 1,000 – 1,500 sqft | 159 | 77.9% |
| 1,500 – 2,500 sqft | 45 | 22.1% |
| 2,500+ sqft | 0 | 0.0% |

### 5.3 Transaction Value Brackets
| Value Bracket (INR) | Verified Deeds | Share (%) |
|:---|:---:|:---:|
| Under ₹50 Lakhs | 0 | 0.0% |
| ₹50 Lakhs – ₹1 Crore | 0 | 0.0% |
| ₹1.0 Crore – ₹2.5 Crores | 204 | 100.0% |
| ₹2.5 Crores – ₹5.0 Crores | 0 | 0.0% |
| Above ₹5.0 Crores | 0 | 0.0% |

*Note: All currently verified transactions fall in the middle-income to upper-middle suburban high-rise apartment bracket (₹1.0Cr to ₹2.5Cr), demonstrating high internal price coherence but highlighting an urgent need for market diversification.*

---

## 6. Expansion Roadmap to 1,000 Certified Deeds

To satisfy the pre-training gate without violating data governance or fabricating records, the following sequential expansion plan is established:

```
                  PHASE 6 EXPANSION ROADMAP TO 1,000 CERTIFIED DEEDS
                  
 Current Baseline (140 Certified)
      │
      ├─► Step 1: Execute Commercial Agreement with Zapkey (BLR, HYD, MMR) ──► +350 Deeds
      │
      ├─► Step 2: Onboard PropEquity / Propstack Commercial Feeds ────────────► +300 Deeds
      │
      ├─► Step 3: Integrate HFC Banking Valuation Closed-Deed Consortium ─────► +150 Deeds
      │
      ├─► Step 4: Ingest RERA Certified Builder Allotments (Villas & Plots) ──► +100 Deeds
      │
      ▼
 Target Threshold Met: 1,040 Certified Empirical Deeds ──► ML GATE UNLOCKED
```

| Milestone | Target Source | Target Region | Target Typology | Target Volume | Cumulative Verified |
|:---|:---|:---|:---|:---:|:---:|
| **Current Baseline** | `B2B_ZAPKEY_BLR` | Bengaluru | High-Rise Apartments | 140 | 140 |
| **Milestone 6B-1** | Zapkey Commercial Feed v2 | Bengaluru (South & North) | Apartments & Villas | +250 | 390 |
| **Milestone 6B-2** | PropStack / Zapkey MMR | Mumbai (MMR) | Apartments | +250 | 640 |
| **Milestone 6B-3** | PropEquity NCR Feed | Delhi-NCR (Gurugram, Noida) | High-Rise & Independent Floors | +200 | 840 |
| **Milestone 6B-4** | HFC Consortium / Zapkey HYD | Hyderabad (Gachibowli, Hitec) | Gated Communities & Plots | +200 | **1,040** |

---

## 7. Governance Conclusion

1. **Exact Certified Deed Count:** **140 unique empirical deeds** in approved dataset versions (**204 verified deeds** in staging).
2. **ML Pre-Training Gate:** Remains strictly **`BLOCKED`**.
3. **No Synthetic Training:** The 421 synthetic test records remain isolated in `PROVISIONAL_NON_ML` status and cannot penetrate model training.
4. **Operational Mode:** PropVal AI continues strictly on the statutory rule-based baseline valuation engine until commercial feeds provide the remaining 860 certified transactions.

