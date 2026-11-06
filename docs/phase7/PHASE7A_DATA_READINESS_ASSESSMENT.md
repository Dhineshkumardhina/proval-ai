# PropVal AI — Phase 7A: Data Readiness Assessment
**Empirical Transaction Dataset Audit & Pre-Training Governance Review**
**Document Reference:** `docs/phase7/PHASE7A_DATA_READINESS_ASSESSMENT.md`  
**Execution Date:** November 6, 2026  
**Auditor / Role:** Senior Real-Estate Data Scientist, Data Governance Specialist, and Quantitative Model Validator  

---

## 1. Executive Summary

This assessment presents an exhaustive audit of the empirical transaction records, data acquisition staging pipelines, data cleansing engines, and dataset versioning registry in PropVal AI.

The primary objective is to verify whether the data corpus satisfies institutional banking standards, statutory Digital Personal Data Protection (DPDP) Act requirements, and the **mandatory 1,000-certified-deed precondition** required to train and deploy the CatBoost machine learning model.

### Key Finding:
* **Verified Real-World Deeds Available:** **410 deeds**
* **Approved Baseline Snapshot Deeds:** **140 unique deeds**
* **Certified Deeds Eligible for Production ML Training:** **0 deeds**
* **ML Training Gate Status:** **BLOCKED** (Deficit of 590 certified empirical transactions).
* **Pilot Valuation Mechanism:** **Fully Operational** via the audited, deterministic rule-based hedonic valuation engine.

---

## 2. Complete Transaction Lifecycle State Audit

Every transaction ingested into PropVal AI passes through an explicit state machine. The current database census (`propval.db`) reveals the exact distribution:

```
[RAW Payload] ──(PII Scrub)──► [PARSED] ──(Unit Normalization)──► [NORMALIZED]
                                                                       │
           ┌───────────────────────────────────────────────────────────┴───────────────────────┐
           ▼                                                                                   ▼
   [VALIDATION_PENDING]                                                                   [VALIDATED]
           │                                                                                   │
     (Quarantine Alert)                                                             (SRO Index II / Deed Match)
           ▼                                                                                   ▼
    [QUARANTINED] (50)                                                                  [VERIFIED] (410)
           │                                                                                   │
   (Circle Rate / Anomaly)                                                              (1,000 Gate Check)
           │                                                                                   ▼
           ▼                                                                            [CERTIFIED] (0)
    [REJECTED] (17)                                                                            │
   (Missing Price / Area)                                                                      ▼
                                                                                     [ML MODEL TRAINING]
```

### Exact Lifecycle Census Table

| State | Definition | Count | Audit Finding |
| :--- | :--- | :---: | :--- |
| **RAW** | Unprocessed payload stored in `raw_transaction_staging` | **1,134** | Raw records received from automated staging and batch imports. |
| **PARSED** | PII scrubbed (names, Aadhaar, PAN masked to DPDP hash) | **1,067** | 1,067 records marked `CLEANSED`; 50 purged; 17 erased under DPDP right to be forgotten. |
| **NORMALIZED** | Standardized Indian units (sqft, INR Lakh/Crore, lat/lng) | **1,236** | All imported records normalized in `imported_transactions`. |
| **VALIDATION_PENDING** | Awaiting automated or manual quarantine clearance | **33** | 16 circle rate alerts + 17 rate outlier alerts under active review. |
| **VALIDATED** | Conforms to structural schema and positive value ranges | **1,236** | Verified syntactically; non-negative pricing and area constraints met. |
| **VERIFIED** | Attested by statutory SRO Index II, deed number, or B2B feed | **410** | 377 from `B2B_ZAPKEY_BLR`, 16 from `ZAPKEY_COMMERCIAL_FEED`, 17 from `imported-deed`. |
| **APPROVED** | Sealed in frozen, immutable `dataset_versions` snapshots | **140** | Unique approved deeds across baseline registered snapshots. |
| **CERTIFIED** | Certified for ML training ($\ge 1,000$ deeds, licensed, validated) | **0** | **Gate Enforced.** Zero records certified for ML due to the 1,000 minimum threshold. |
| **QUARANTINED** | Flagged for severe rate anomalies or statutory undervaluation | **50** | 16 undervaluation (circle rate), 17 extreme outliers, 17 DPDP erased. |
| **REJECTED** | Discarded permanently due to missing prices or null areas | **17** | Missing mandatory transaction price (`code: MISSING_PRICE`). |
| **DUPLICATES** | Detected and quarantined by SHA-256 fingerprinting | **240** | 240 duplicate instances identified across 209 distinct fingerprints. |

---

## 3. Data Source Attribution & Licensing Status

| Data Source Identifier | Source Type | Declared Licensing Tier | Total Records | Verified Deeds | ML Usability Status |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `B2B_ZAPKEY_BLR` | Commercial B2B Partner Feed | `COMMERCIAL_RESTRICTED` | 377 | 377 | Permitted for Rule-Based Benchmarking; Blocked for ML until $\ge 1,000$ |
| `ZAPKEY_COMMERCIAL_FEED` | Staged API Ingestion | `COMMERCIAL_RESTRICTED` | 16 | 16 | Permitted for Rule-Based Benchmarking; Blocked for ML until $\ge 1,000$ |
| `imported-deed` | Historical Seed Registry | `INTERNAL_REFERENCE` | 17 | 17 | Historical baseline reference; Blocked for ML training |
| `TEST_SRC_*` (54 Batches) | Synthetic Test Harness Feeds | `SYNTHETIC_TEST_ONLY` | 826 | 0 | **STRICTLY DISQUALIFIED** from all production valuation & ML |

> **Key Rule Verification:**  
> The `test_synthetic_data_strictly_disqualified` test in `test_empirical_training_phase6f.py` enforces that any dataset marked `is_synthetic = 1` or tagged with `TEST_HARNESS_SIMULATION` is rejected by the pre-training gate with a critical security error.

---

## 4. Geographic & Property Type Distribution

### 4.1 Geographic Distribution (Verified Deeds Only)

| Locality | Sub-Market / Municipality | City | Verified Deeds | Sample Median Price (₹/sqft) |
| :--- | :--- | :--- | :---: | :---: |
| **Whitefield** | Bengaluru East (IT Corridor) | Bengaluru Urban | 376 | ₹8,450 / sqft |
| **Koramangala** | Bengaluru South (Tier 1 Residential) | Bengaluru Urban | 17 | ₹14,200 / sqft |
| **Indiranagar** | Bengaluru East (Tier 1 Commercial/Res) | Bengaluru Urban | 17 | ₹16,800 / sqft |
| **Total** | **Bengaluru Metropolitan Area** | — | **410** | — |

*Audit Note:* Geographic concentration is currently 100% focused on the Bengaluru Urban IT and central corridors. Expansion into Mumbai (MMR) and Delhi-NCR micro-markets is planned for commercial activation in Phase 7B.

### 4.2 Property Type Distribution

| Property Type | Total Ingested | Verified Deeds | Percentage of Verified |
| :--- | :---: | :---: | :---: |
| **High-Rise Apartment** | 1,219 | 393 | 95.8% |
| **Apartment (Mid-Rise/Gated)** | 17 | 17 | 4.2% |
| **Independent Villa / Plot** | 0 | 0 | 0.0% |

---

## 5. Missing Value & Field Completeness Analysis

Analysis across all 410 verified empirical deeds:

| Field Name | Completeness (%) | Null Count | Risk & Remediation |
| :--- | :---: | :---: | :--- |
| `carpet_area_sqft` | **100.0%** | 0 | Mandatory field. 100% complete across all verified deeds. |
| `transaction_price` | **100.0%** | 0 | Mandatory field. Zero missing values. |
| `price_per_sqft` | **100.0%** | 0 | Computed directly from transaction price / carpet area. |
| `guideline_rate_per_sqft` | **69.8%** | 124 | Derived from Sub-Registrar Office circle rate lookup tables. Missing 30.2% in unmapped sub-survey plots. |
| `latitude` & `longitude` | **65.9%** | 140 | Coordinates resolved via geocoding; 34.1% fall back to locality centroid. |
| `deviation_from_guideline_pct`| **3.9%** | 394 | Only computed when official statutory circle rate is explicitly present. |
| `built_up_area_sqft` | **0.0%** | 410 | In Indian registration deeds, carpet area is statutory; built-up is frequently omitted. |
| `floor_no` & `total_floors` | **0.0%** | 410 | Missing from raw deed extracts; requires building society plan integration. |
| `age_years` | **0.0%** | 410 | Inferred from completion certificate; default amortization depreciation used. |

---

## 6. Strict Defense of the 1,000 Certified Deed Threshold

### Why Lowering the Gate is Strictly Prohibited:
1. **Statistical Power in Micro-Markets:** Indian real estate markets exhibit high micro-market variance. A sample size under 1,000 transactions yields insufficient degrees of freedom across 15+ hedonic features (micro-locality, age, floor rise, amenities, builder tier, guideline rate deviation).
2. **Overfitting & Conformal Calibration:** Quantile regression and conformal prediction require a clean split into training ($N \approx 600$), validation ($N \approx 200$), and calibration sets ($N \ge 200$). Calibrating predictive intervals on fewer than 200 held-out empirical deeds violates finite-sample coverage guarantees.
3. **Banking Regulatory Audits (RBI & NHB Guidelines):** Automated Valuation Models (AVMs) used in bank underwriting must demonstrate empirical robustness against statutory registration evidence. Using an unverified model trained on an insufficient sample exposes financial institutions to credit risk and capital charge penalties.

### Phase 7 Operational Decision:
* **The CatBoost pre-training readiness gate remains firmly locked.**
* **The deterministic rule-based hedonic valuation engine continues to power all institutional pilot evaluations.**
* Phase 7B will ingest the remaining 590 certified empirical transactions through authorized commercial feeds, unlocking model training in Phase 7E.

