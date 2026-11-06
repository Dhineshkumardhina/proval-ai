# PropVal AI — Phase 5D Certified Empirical Transaction Acquisition Report

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Data Governance, Empirical Validation & ML Gate Status Audit  
**Regulatory Standards:** RBI Guidelines on Model Risk Management, NHB Valuation Standards, DPDP Act 2023  
**Audit Standard:** ISO 8000 (Data Quality) & ISO/IEC 25010 Software Product Quality  
**Date:** 2026-11-05  
**Auditor Roles:** Senior Real-Estate Data Scientist & Property Transaction Data Governance Specialist  

> [!CAUTION]
> **CRITICAL INSTITUTIONAL GOVERNANCE STATEMENT — ML TRAINING GATE STATUS: LOCKED**  
> **Target Required for ML Training Gate:** 1,000 unique, certified, licensed empirical property deeds.  
> **Current Certified Empirical Deeds in Database:** **46** (Progress: 4.6% of threshold).  
> **Deficit Remaining:** **954 certified empirical transactions.**  
> **ML Readiness Status:** **LOCKED / NO-GO (`canTrain = False`).**  
> **PropVal AI does NOT generate synthetic records, count mock data, include duplicates, or count unverified transactions to satisfy this threshold.**  
> Until commercial licensing agreements provide the required $\ge 1,000$ verified deeds, PropVal AI's machine-learning training pipeline remains locked, and the platform continues executing strictly on its statutory rule-based baseline valuation engine.

---

## 1. Executive Summary

Phase 5D establishes the formal empirical data governance, acceptance criteria, pipeline audit, and dataset quality framework required for the PropVal AI machine learning valuation model.

The platform enforces a non-negotiable **1,000-certified-transaction training gate** (`MINIMUM_RECORDS_THRESHOLD = 1000` in [`backend/app/ml/readiness_gate.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/readiness_gate.py)). To preserve institutional credibility and prevent machine learning hallucinations on mortgage valuations:
1. Synthetic demonstration records are explicitly disqualified from ML training.
2. Unverified or asking-price listings cannot be counted as deeds.
3. Duplicates and statistical anomalies are automatically quarantined.
4. The exact empirical count is audited directly against the database ledger.

---

## 2. Ingestion, Normalization, Verification & Versioning Pipeline Audit

The PropVal AI empirical transaction acquisition pipeline comprises four decoupled, tamper-evident stages:

```
[Raw Provider Deed Feed]
         │
         ▼
[Stage 1: Ingestion & Egress Defense]
 - Hostname Whitelist Pinning (SSRF Defense)
 - Stream / Batch Ingestion via BaseConnector
 - Raw Payload SHA-256 Hashing
         │
         ▼
[Stage 2: Standardization & Normalization]
 - Area Conversion (Sq.m / Gaj / Gunta / Bigha ➔ Sq.ft)
 - Currency Normalization (Lakhs / Crores ➔ INR)
 - Geospatial Normalization & SRO Jurisdictions
         │
         ▼
[Stage 3: Verification & Anomaly Quarantine]
 - SRO Index II Deed Reference Validation
 - Circle Rate Undervaluation Detection (>50% discount)
 - Rate Outlier IQR Boundary Inspection
 - SHA-256 Canonical Fingerprint Deduplication
 - Synthetic Quarantine Gate (MOCK / TEST ➔ is_verified_deed=False)
         │
         ▼
[Stage 4: Dataset Versioning & Governance Ledger]
 - Immutable SemVer Snapshot Creation (v1.0.0, v1.1.0)
 - Merkle-Root Dataset SHA-256 Checksum Calculation
 - ML Training Gate Audit (Strict >= 1,000 Verified Threshold)
```

### 2.1 Stage 1: Ingestion Pipeline Audit
- Implemented in [`backend/app/services/ingestion_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/services/ingestion_service.py) and [`backend/app/connectors/`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/connectors/).
- Each incoming stream or batch records dataset provenance, original filename, and SHA-256 file checksum in `DatasetMetadataModel`.
- Transport-level SSRF defenses verify destination hostnames before opening connections.

### 2.2 Stage 2: Normalization Pipeline Audit
- Implemented in [`backend/app/normalization/engine.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/normalization/engine.py), [`unit_converter.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/normalization/unit_converter.py), [`currency_normalizer.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/normalization/currency_normalizer.py), and [`geo_normalizer.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/normalization/geo_normalizer.py).
- Converts 17 regional Indian land units (Square Yards, Gunta, Ground, Cent, Bigha, Marla, Kanal, Cottah, etc.) into standardized square feet (`carpet_area_sqft`).
- Parses regional currency formats (INR, Lakhs, Crores) into exact integer float values.
- Validates latitude and longitude within Indian national territorial bounding boxes ($6^\circ\text{N} - 37.6^\circ\text{N}$, $68.7^\circ\text{E} - 97.4^\circ\text{E}$).

### 2.3 Stage 3: Verification & Quarantine Pipeline Audit
- Implemented in [`backend/app/verification/verification_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/verification/verification_service.py).
- Evaluates statistical anomalies via `TransactionAnomalyDetector`. Records with price deviations exceeding guideline rates by $>300\%$ or undervalued by $>50\%$ are routed to `quarantined_records`.
- Evaluates duplicate transactions by checking SHA-256 fingerprint collisions. Duplicate rows are logged in `duplicate_records` without corrupting the transaction ledger.
- Enforces synthetic data quarantine: Any record originating from mock connectors or test suites is flagged with `is_verified_deed = False` and `PROVISIONAL_NON_ML`.

### 2.4 Stage 4: Versioning Pipeline Audit
- Implemented in [`backend/app/dataset_management/version_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/dataset_management/version_service.py).
- Creates immutable SemVer dataset versions (e.g. `v1.0.0`, `v1.1.0`) with Merkle-style root hashes computed from sorted transaction fingerprints.
- Verifies approval status and licensing authorization before snapshot sealing.

---

## 3. Certified Transaction Acceptance Criteria

To achieve certification as an empirical transaction deed eligible for model training, a record must satisfy **all 7 mandatory criteria**:

| Criterion | Specification | Enforcement Mechanism | Failure Action |
| :--- | :--- | :--- | :--- |
| **1. Source Authorization** | Licensed commercial provider (PropEquity, Zapkey, PropStack) or official State IGR gateway under valid contract. | `DataPolicyService.verify_dataset_and_source_for_ml()` | Blocked with `PURPOSE_RESTRICTION` |
| **2. Non-Synthetic Origin** | No `MOCK`, `TEST`, `SIMULATION`, or synthetic benchmark tag in source ID, reference, or dataset. | `VerificationEngine` source inspection | Quarantined (`is_verified_deed=False`, `PROVISIONAL_NON_ML`) |
| **3. Deed Proof & Reference**| Must reference a registered deed number (e.g. `REG/4421/2026/BK1`) and Sub-Registrar Office (SRO). | Registration reference validation | Rejected (`is_asking_price=True`) |
| **4. Geographic Precision** | Valid Indian state, district, locality, pincode, and GPS coordinates with $\ge 4$ decimal precision digits. | `GeoNormalizer` bounding box check | Rejected to `rejected_records` |
| **5. Physical Attribute Realism**| Standardized carpet area between 150 sq.ft and 25,000 sq.ft; recognized property type (e.g. High-Rise Apartment). | `TransactionAnomalyDetector` | Quarantined to `quarantined_records` |
| **6. Economic Validity** | Transaction price $> 0$; price/sq.ft between ₹1,200 and ₹250,000; circle rate undervaluation $< 50\%$. | Guideline comparison check | Quarantined to `quarantined_records` |
| **7. Cryptographic Lineage** | Original raw payload SHA-256 hash, normalized record hash, and unique fingerprint hash preserved. | `VerificationEvidenceModel` insertion | Transaction rejected |

---

## 4. Complete Transaction Lifecycle Accounting

An exhaustive audit of the database repository (`propval.db`) reveals the exact lifecycle accounting of every transaction record in the system:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           TRANSACTION LIFECYCLE RECONCILIATION                          │
├────────────────────────────────────────────────────────┬──────────────┬─────────────────┤
│ Lifecycle Category                                     │ Record Count │ Percentage      │
├────────────────────────────────────────────────────────┼──────────────┼─────────────────┤
│ Total Imported Transactions in Database                │ 137          │ 100.0%          │
│ ├─ Certified Verified Empirical Deeds (Class A / B)   │ 46           │ 33.6%           │
│ └─ Synthetic / Test Simulation Records (Class F)       │ 91           │ 66.4%           │
├────────────────────────────────────────────────────────┼──────────────┼─────────────────┤
│ Quarantined Suspicious / Anomalous Records             │ 6            │ N/A (Isolated)  │
│ ├─ CIRCLE_RATE_UNDERVALUATION (>50% below circle rate) │ 3            │ 50.0%           │
│ ├─ RATE_OUTLIER_ANOMALY (Extreme ₹950,000/sqft)        │ 2            │ 33.3%           │
│ └─ STATISTICAL_OUTLIER (Excess variance)               │ 1            │ 16.7%           │
├────────────────────────────────────────────────────────┼──────────────┼─────────────────┤
│ Duplicate Records Detected & Rejected                  │ 25           │ N/A (Rejected)  │
├────────────────────────────────────────────────────────┼──────────────┼─────────────────┤
│ Schema Validation Failures / Malformed Rows            │ 2            │ N/A (Rejected)  │
├────────────────────────────────────────────────────────┼──────────────┼─────────────────┤
│ Immutable Dataset Version Snapshots Sealed             │ 10           │ N/A (Snapshots) │
└────────────────────────────────────────────────────────┴──────────────┴─────────────────┘
```

---

## 5. Certified Empirical Breakdown by Data Source

Only records with `is_verified_deed = True` and non-synthetic provenance are classified as certified empirical deeds:

| Data Source Code | Ingested Deeds | Certified Deeds | Empirical Status | Primary Geographic Micro-Market |
| :--- | :--- | :--- | :--- | :--- |
| `B2B_ZAPKEY_BLR` | 42 | 42 | **CERTIFIED EMPIRICAL** | Bengaluru Urban (Whitefield) |
| `ZAPKEY_COMMERCIAL_FEED` | 2 | 2 | **CERTIFIED EMPIRICAL** | Bengaluru (Indiranagar / Koramangala) |
| `imported-deed` | 2 | 2 | **CERTIFIED EMPIRICAL** | Bengaluru Urban |
| `SRC_E2E_329F8C` | 15 | 0 | **DISQUALIFIED (E2E TEST)** | Test harness simulation |
| `SRC_E2E_9321B4` | 15 | 0 | **DISQUALIFIED (E2E TEST)** | Test harness simulation |
| `TEST_SRC_0177C2` | 10 | 0 | **DISQUALIFIED (UNIT TEST)**| Test harness simulation |
| `TEST_SRC_BBA80D` | 20 | 0 | **DISQUALIFIED (UNIT TEST)**| Test harness simulation |
| `TEST_SRC_CF2A8C` | 10 | 0 | **DISQUALIFIED (UNIT TEST)**| Test harness simulation |
| `TEST_SRC_CF63A4` | 20 | 0 | **DISQUALIFIED (UNIT TEST)**| Test harness simulation |
| `TEST_PII_SCRUB_...` | 1 | 0 | **DISQUALIFIED (UNIT TEST)**| Test harness simulation |
| **TOTALS** | **137** | **46** | **46 CERTIFIED DEEDS** | **Bengaluru Micro-Markets** |

---

## 6. ML Readiness Gate Evaluation & Training Gate Lock

We executed the institutional readiness evaluation via `evaluate_training_gate()` on the active dataset corpus:

```json
{
  "passed": false,
  "canTrain": false,
  "totalRecords": 46,
  "validRecords": 46,
  "requiredRecordsThreshold": 1000,
  "deficit": 954,
  "verifiedDeedRatio": 1.0,
  "priceSanityVerified": true,
  "blockingIssues": [
    "INSUFFICIENT_SAMPLE_SIZE: Dataset contains only 46 valid records. Institutional risk policy mandates a minimum of 1000 verified records per micro-market (Deficit: 954 records).",
    "INSUFFICIENT_GEOGRAPHIC_DIVERSITY: Transactions span only 3 micro-market(s). Minimum of 3 distinct micro-markets required to prevent extreme spatial overfitting.",
    "MONOLITHIC_PROPERTY_TYPES: Dataset contains only 1 primary property type (High-Rise Apartment 95.7%)."
  ],
  "governanceRecommendation": "READINESS: NO-GO. Training is strictly GATED due to 3 blocking issue(s). Dataset has 46 valid records (requires 1000). PropVal AI continues operating on the statutory rule-based baseline engine."
}
```

### Institutional Risk Audit Verdict:
The ML Training Gate remains **FIRM AND UNCOMPROMISED**. PropVal AI rejects premature or hallucinated machine-learning training. Model training will remain locked until commercial partner activation supplies the remaining 954 certified empirical deeds.

---

## 7. Action Plan to Unlock the 1,000 Empirical Threshold

To transition the ML training gate from `LOCKED` to `OPEN`:
1. **Commercial Licensing Execution (Phase 5C):**  
   Execute commercial B2B data licenses with Zapkey, PropEquity, or PropStack.
2. **Batch SRO Deed Ingestion:**  
   Ingest a batch of $\ge 1,500$ raw deeds from Mumbai Metropolitan Region (MMR) and Bengaluru Urban.
3. **Pipeline Normalization & Verification:**  
   Process raw deeds through the Phase 4B/4C normalization engine, anticipating $\approx 5\%$ duplicate rate and $\approx 2\%$ quarantine rate, netting $>1,200$ certified empirical deeds.
4. **Snapshot Sealing & Retesting:**  
   Seal version `v2.0.0` with Merkle SHA-256 root hash, submit for Chief Credit Officer approval, and re-evaluate `evaluate_training_gate()`.

