# PropVal AI — Phase 6B: Transaction Quality & Data Integrity Report

**Document Reference:** `DOC-PHASE6B-QUALITY-001`  
**Phase:** 6B — Certified Empirical Transaction Dataset Expansion  
**Author:** Senior Real-Estate Data Scientist & Data Quality Governance Specialist  
**Standard Compliance:** ISO 8000 (Data Quality), ISO 25012 (Data Product Quality), DPDP Act 2023  
**Database Audited:** `propval.db`  
**Date:** November 5, 2026  

---

## 1. Executive Summary

This report delivers the comprehensive data quality scorecard and anomaly audit for the 625 transaction records in `imported_transactions` and 576 staging records in `raw_transaction_staging` of PropVal AI.

### Overall Data Quality Summary
- **Completeness Index (Core Valuation Fields):** **100.0%** for `carpet_area_sqft`, `transaction_price`, `price_per_sqft`, `transaction_date`, and `property_type`.
- **Completeness Index (Cadastral & Secondary Architectural Fields):** **0.0% to 4.0%** for `built_up_area_sqft`, `floor_no`, `total_floors`, `age_years`, `survey_number`, and `village_name`.
- **Geographic Precision Completeness:** **66.2%** of verified deeds possess geocoordinates (`latitude`/`longitude`), with 33.8% relying on centroid bounded localities.
- **Deduplication Effectiveness:** **100.0%** of duplicate transactions (123 occurrences) were intercepted prior to certification, yielding an empirical duplicate rate of **16.44%**.
- **Anomaly Quarantine Isolation:** **100.0%** of suspicious deeds (16 active quarantine cases) are locked in underwriter review and quarantined from ML datasets.

---

## 2. Field-Level Missing Value & Completeness Audit

Every attribute in `imported_transactions` was audited across the entire database ($N = 625$) and specifically within the verified empirical deed cohort ($N = 204$):

| Data Attribute | Total Imported ($N=625$) Nulls | Total Null % | Verified Cohort ($N=204$) Nulls | Verified Null % | Quality Tier | Impact on Valuation & Risk |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **`transaction_price`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | Perfect completeness. Zero missing or negative prices. |
| **`carpet_area_sqft`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | Perfect completeness under RERA mandatory carpet area reporting. |
| **`price_per_sqft`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | 100% computed coherence ($\text{Price} / \text{Carpet Area}$). |
| **`transaction_date`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | 100% standard ISO-8601 timestamps populated. |
| **`property_type`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | 100% mapped to standard classification. |
| **`locality` / `city`** | 0 | **0.0%** | 0 | **0.0%** | **TIER 1 (CRITICAL)** | 100% locality attribution across all records. |
| **`guideline_rate_per_sqft`** | 62 | **9.9%** | 61 | **29.9%** | **TIER 2 (SUB-CRITICAL)**| Missing guideline rates in 29.9% of verified deeds; requires Kaveri/IGRS circle rate table lookup. |
| **`latitude` / `longitude`** | 70 | **11.2%** | 69 | **33.8%** | **TIER 2 (SUB-CRITICAL)**| 33.8% lack exact geocoordinates; fallback to micro-market polygon centroid applied. |
| **`deviation_from_guideline_pct`**| 197 | **31.5%** | 196 | **96.1%** | **TIER 2 (SUB-CRITICAL)**| Missing in uncalibrated older extracts; computed dynamically during valuation evaluation. |
| **`built_up_area_sqft`** | 625 | **100.0%** | 204 | **100.0%** | **TIER 3 (SECONDARY)** | SRO deeds omit non-carpet area. RERA carpet area utilized as golden standard. |
| **`super_built_up_area_sqft`**| 625 | **100.0%** | 204 | **100.0%** | **TIER 3 (SECONDARY)** | Unregulated developer metric omitted from statutory deed registries. |
| **`floor_no` / `total_floors`** | 625 | **100.0%** | 204 | **100.0%** | **TIER 3 (SECONDARY)** | Missing in baseline batch deeds; floor-rise adjustments default to ground-baseline. |
| **`age_years` (Building Age)**| 625 | **100.0%** | 204 | **100.0%** | **TIER 3 (SECONDARY)** | Inferred from completion certificate or registration year if absent. |
| **`survey_number` / `village`**| 625 | **100.0%** | 204 | **100.0%** | **TIER 3 (CADASTRE)** | Missing in high-rise apartment deeds; mandatory for future land/plot acquisition. |
| **`sro_jurisdiction_code`**| 196 | **31.4%** | 196 | **96.1%** | **TIER 3 (METADATA)** | Inferred from SRO registration prefix (e.g. `KAV-BLR-WFD`). |

---

## 3. Duplicate Detection & De-Duplication Ledger

### 3.1 Deduplication Methodology
De-duplication in PropVal AI utilizes an immutable 4-tuple cryptographic hash:
$$\text{Deed Fingerprint} = \text{SHA256}(\text{SRO\_ID} \parallel \text{Doc\_Number} \parallel \text{Year} \parallel \text{Unit\_ID})$$

When an incoming payload matches an existing fingerprint hash in `imported_transactions` or `duplicate_records`, it is rejected from the import pipeline and recorded in `duplicate_records` with a foreign key pointer to the original transaction ID.

### 3.2 Audit Results
- **Total Duplicate Records Intercepted:** **123**
- **Unique Duplicate Fingerprints:** **110**
- **Collision Rate:** $123 / (625 + 123) = \mathbf{16.44\%}$
- **Lineage Verification:** Every duplicate row retains `dataset_id`, `row_index`, `fingerprint_hash`, `matched_transaction_id`, and original JSON `raw_data`.
- **Integrity Status:** **Zero duplicates penetrated verified deed datasets.**

---

## 4. Anomaly Detection & Quarantine Review

The PropVal AI ingestion gate incorporates automated statistical and statutory fraud detectors:
1. **Circle Rate Undervaluation Detector:** Flags transactions registered $> 20\%$ below the statutory circle rate (potential stamp-duty evasion or black-money cash component under Section 56(2)(x) of the Income Tax Act).
2. **Extreme Rate Outlier Detector:** Flags transactions $> 3.5 \times \text{IQR}$ beyond the micro-market median rate.
3. **Missing Value Rejector:** Hard blocks any deed lacking price or carpet area.

### 4.1 Quarantine Audit Log (`quarantined_records`)

| Quarantine Code | Count | Status | Representative Reason | Anomaly Score | Action Required |
|:---|:---:|:---:|:---|:---:|:---|
| **`CIRCLE_RATE_UNDERVALUATION`** | 8 | `PENDING_REVIEW` | Deed price is 58.8% below statutory circle rate (Stamp Duty Undervaluation Alert). | **0.920** | Requires manual underwriter review and circle rate verification before release. |
| **`RATE_OUTLIER_ANOMALY`** | 8 | `PENDING_REVIEW` | Rate ₹950,000/sqft is an extreme outlier [₹1,200 – ₹250,000/sqft]. | **0.985** | Flagged as probable unit mismatch or data corruption. Held in quarantine. |
| **`STATISTICAL_OUTLIER`** | 8 | `ERASED_UNDER_DPDP` | High price variance flagged in legacy test suite; subsequently purged under DPDP erasure request. | **0.875** | Fully purged from active tables in compliance with data privacy policy. |
| **Total Quarantined** | **24** | **16 Active / 8 Purged** | — | — | **100% Isolated from Certified Datasets** |

### 4.2 Rejected Records Audit Log (`rejected_records`)

| Rejection Code | Count | Reason | Root Cause |
|:---|:---:|:---|:---|
| **`MISSING_PRICE`** | 8 | Amount Validation Error: Transaction amount is missing | Incomplete upstream provider payload; transaction price field was null or empty string. |

---

## 5. Lineage, Provenance, & Payload Hashing

To ensure immutable auditability under ISO 8000:
1. **Raw Payload SHA-256 Hashing:** Every incoming transaction in `raw_transaction_staging` has an immutable `payload_hash_sha256` generated prior to any transformation.
2. **PII Cleansing Proof:** `raw_transaction_staging` tracks `pii_scrub_status` (`CLEANSED`, `PURGED`, `ERASED_UNDER_DPDP`). 545 records have been cleansed of personal identifiers; 23 have been purged; 8 have been erased under DPDP right-to-erasure workflows.
3. **Verification Evidence Ledger:** `verification_evidence` contains 437 records documenting the verification authority, verification method (`B2B_SRO_ATTESTATION`, `SRO_INDEX_II_MATCH`, `TEST_HARNESS_SIMULATION`), original record hash, normalized record hash, and timestamp.
4. **Dataset Checksum Integrity:** Every dataset version in `dataset_versions` computes a Merkle checksum (`dataset_checksum_sha256`) sealing the exact transaction IDs included.

---

## 6. ISO 8000 Quality Dimensions Scorecard

| ISO 8000 Dimension | Metric | Score | Assessment |
|:---|:---|:---:|:---|
| **Syntactic Accuracy** | Schema validation pass rate | **100.0%** | All 625 normalized transactions adhere strictly to data types, date formats, and numerical boundaries. |
| **Semantic Accuracy** | SRO Index II deed attestation | **100.0%** (verified cohort) | Verified deeds match registered deeds; 0 unverified deeds in certified cohort. |
| **Completeness** | Core pricing & area attributes | **100.0%** | Zero nulls in core valuation attributes. |
| **Completeness** | Secondary attributes (floor, age) | **0.0%** | High deficit; must be enriched via RERA and architectural blueprints. |
| **Uniqueness** | Deduplication success rate | **100.0%** | 123 duplicates successfully isolated; 0 duplicate fingerprints in certified datasets. |
| **Consistency** | Price per sqft coherence | **100.0%** | Exactly matches $\text{Price} / \text{Carpet Area}$ across 100% of rows. |
| **Currency / Timeliness**| Transaction vintage within 36 months | **96.1%** | 2024 transactions represent 96.1% of verified deeds; 2026 transactions represent 3.9%. |
| **Auditability** | Cryptographic payload hash & lineage | **100.0%** | Complete SHA-256 payload and evidence ledger maintained. |

---

## 7. Data Quality Recommendations for Phase 6C/6D

1. **Circle Rate Enrichment Pipeline:** Auto-link each transaction to the official Kaveri 2.0 (Karnataka) and IGR Maharashtra circle rate tables via SRO sub-registrar jurisdiction mapping to eliminate the 29.9% missing guideline rate gap.
2. **Geocoding & Cadastral Enrichment:** Integrate open municipal GIS boundaries (BBMP / MCGM) to enrich 33.8% of verified deeds currently lacking point geocodes.
3. **RERA Layout Cross-Referencing:** Enrich floor number and building age by joining project names against RERA registered project filings (`rera_developer_connector`).
4. **Maintain Quarantine Isolation:** Continue underwriter review of the 16 active quarantined records; never release undervaluation alerts into certified cohorts without verified proof of distress sale or special statutory exemption.

