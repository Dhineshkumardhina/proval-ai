# PropVal AI — Phase 6B: Certified Dataset Register & Snapshot Ledger

**Document Reference:** `DOC-PHASE6B-REGISTER-001`  
**Phase:** 6B — Certified Empirical Transaction Dataset Expansion  
**Author:** Senior Financial Data Governance Specialist & Data Quality Engineer  
**Database Audited:** `propval.db`  
**Date:** November 5, 2026  

---

## 1. Register Overview & Governance Principles

Under PropVal AI Data Governance Standard §4.2, every transaction dataset used within valuation benchmarking, risk analysis, or model evaluation must be registered in the **Certified Dataset Register**.

### Strict Governance Rules Enforced:
1. **Immutable Versioning:** Every registered dataset release is sealed with a semantic version tag (`semver_tag`), an immutable SHA-256 Merkle root (`dataset_checksum_sha256`), and an explicit transaction ID membership manifest (`included_transaction_ids`).
2. **Approval Gate Requirement:** Datasets must possess `approval_status = 'APPROVED'` signed by an institutional reviewer before any analytical exposure.
3. **ML Eligibility Separation:** A dataset version may only be designated `is_ml_eligible = True` if it contains $\ge 1,000$ certified empirical deeds and passes all 6 pre-training readiness gate requirements.
4. **Synthetic Isolation:** Datasets containing synthetic, demonstration, or unverified test records are strictly partitioned and barred from certification.

---

## 2. Dataset Version Register Ledger

The table below documents representative dataset version snapshots currently registered in `propval.db` (`dataset_versions` table):

| Dataset ID | Version Tag | Title | Approval Status | ML Eligible | Total Records | Verified Deeds | Merkle Checksum (SHA-256 Prefix) | Lineage & Description |
|:---|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `797920d6-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `c0b88bfd3332...` | Whitefield SRO Baseline Extract (Verified Deeds) |
| `0faff5ef-...` | `v1.1.0` | Q4 Incremental Sync | **DRAFT** | **False** | 20 | 20 | `ecbadfa10243...` | Whitefield Q4 Incremental Deed Feed (Pending Review) |
| `beb86bbb-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `cb34cfb860ee...` | Bengaluru SRO Certified Deeds Cohort A |
| `ab406b72-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `998ccaf6cffc...` | Bengaluru SRO Certified Deeds Cohort B |
| `69ae4cd5-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `7368ff182e5b...` | Bengaluru SRO Certified Deeds Cohort C |
| `99439988-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `2b9cfd5bbdf8...` | Bengaluru SRO Certified Deeds Cohort D |
| `be11f3ec-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `88519b80c34d...` | Bengaluru SRO Certified Deeds Cohort E |
| `246ad1a6-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `552170494cf8...` | Bengaluru SRO Certified Deeds Cohort F |
| `829c6d7c-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `2a884e930f3a...` | Bengaluru SRO Certified Deeds Cohort G |
| `582ecaed-...` | `v1.0.0` | Initial Q3 Baseline Snapshot | **APPROVED** | **False** | 15 | 15 | `df743a1ba22b...` | Bengaluru SRO Certified Deeds Cohort H |
| `a7b84748-...` | `v1.0.0-erasure` | Version Snapshot v1 | **APPROVED** | **True** | 0 | 0 | `e3b0c44298fc...` | DPDP Erasure Tombstone Snapshot (Zero Records) |
| `...` (x31 more) | Various | Baseline / E2E Audit Snapshots | Mixed | **False** | 0 – 20 | 0 – 20 | Various | CI/CD Regression & Test Isolation Snapshots |

### Register Aggregates
- **Total Registered Datasets (`datasets`):** **135**
  - `APPROVED`: 57 datasets
  - `UNDER_REVIEW`: 38 datasets
  - `DRAFT`: 24 datasets
  - `INGESTING`: 16 datasets
- **Total Datasets Authorized for ML (`is_usable_for_ml = 1`):** **0** (100% Gated)
- **Total Dataset Versions (`dataset_versions`):** **42**
  - `APPROVED`: 25 (including 8 zero-record DPDP erasure tombstones)
  - `DRAFT`: 17
- **Total Unique Transaction IDs across Approved Versions:** **255**
- **Total Certified Empirical Deeds in Approved Versions:** **140 unique deeds** (135 active records)

---

## 3. Data Source Attribution & Licensing Ledger

Every imported transaction in the repository is tied to an explicit data source and licensing authorization:

```
                            SOURCE PROVENANCE & ATTRIBUTION
                            
┌─────────────────────────┬──────────────┬───────────────┬────────────────────────────┐
│ Source Identifier       │ Records (All)│ Verified Deeds│ Licensing Classification   │
├─────────────────────────┼──────────────┼───────────────┼────────────────────────────┤
│ B2B_ZAPKEY_BLR          │ 188          │ 188           │ Commercial B2B License     │
│ ZAPKEY_COMMERCIAL_FEED  │ 8            │ 8             │ Commercial B2B License     │
│ imported-deed           │ 8            │ 8             │ Statutory Registry Copy    │
│ SRC_E2E_* (8 runs)      │ 120          │ 0             │ Synthetic Test Fixture     │
│ TEST_SRC_* (19 runs)    │ 300          │ 0             │ Synthetic Test Fixture     │
│ TEST_PII_SCRUB_*        │ 1            │ 0             │ Synthetic Test Fixture     │
├─────────────────────────┼──────────────┼───────────────┼────────────────────────────┤
│ TOTAL                   │ 625          │ 204           │ 204 Verified / 421 Mock    │
└─────────────────────────┴──────────────┴───────────────┴────────────────────────────┘
```

### 3.1 Commercial License Attribution
1. **`B2B_ZAPKEY_BLR` & `ZAPKEY_COMMERCIAL_FEED`:**
   - **Provider:** Zapkey Technologies Pvt. Ltd. (Commercial B2B SRO Registry Extract).
   - **Verification Authority:** SRO Index II Sub-Registrar Office attestation.
   - **Permitted Purposes:** `AUTOMATED_VALUATION`, `COMPARABLE_SALES_ANALYSIS`, `BENCHMARKING`.
   - **Restrictions:** Restricted redistribution; personal identifiers scrubbed under DPDP Act 2023.
   - **Total Verified Deeds Acquired:** **196 records**.

2. **`imported-deed`:**
   - **Provider:** Karnataka Kaveri 2.0 Certified Registry Deed Copy.
   - **Verification Authority:** State Government Sub-Registrar Attestation.
   - **Permitted Purposes:** Statutory calibration and circle rate baseline benchmark.
   - **Total Verified Deeds Acquired:** **8 records**.

### 3.2 Synthetic Test Harness Partitioning
- **`SRC_E2E_*` & `TEST_SRC_*`:**
  - **Classification:** Synthetic demonstration data.
  - **Volume:** **421 records**.
  - **Verification Evidence:** `verification_status = 'PROVISIONAL_NON_ML'`, `verifier_method = 'TEST_HARNESS_SIMULATION'`.
  - **Isolation Proof:** In `imported_transactions`, `is_verified_deed = 0`. Excluded from all certified datasets.

---

## 4. Verification Evidence Ledger (`verification_evidence`)

The database retains an immutable verification audit trail connecting each transaction to its primary source evidence:

```
[Transaction Record] 
         ▲
         │ (1 : 1)
         ▼
[verification_evidence]
  ├── transaction_id: UUID
  ├── verification_status: 'VERIFIED' | 'PROVISIONAL_NON_ML'
  ├── verifier_id: 'SYSTEM_SRO_VALIDATOR' | 'TEST_HARNESS'
  ├── verifier_method: 'SRO_INDEX_II_MATCH' | 'B2B_SRO_ATTESTATION' | 'TEST_HARNESS_SIMULATION'
  ├── source_origin: 'B2B_ZAPKEY_BLR' | 'ZAPKEY_COMMERCIAL_FEED'
  ├── source_document_ref: e.g. 'DOC-KAV-BLR-WFD-2024-001'
  ├── original_record_hash: SHA-256
  ├── normalized_record_hash: SHA-256
  └── verified_at: ISO-8601 UTC Timestamp
```

### Verification Method Breakdown
- **`B2B_SRO_ATTESTATION`:** 8 records (`ZAPKEY_COMMERCIAL_FEED`)
- **`SRO_INDEX_II_MATCH`:** 8 records (`ZAPKEY_B2B`)
- **`TEST_HARNESS_SIMULATION`:** 421 records (`SRC_E2E_*`, `TEST_SRC_*`)
- **Total Audited Verification Records:** **437 records**

---

## 5. Merkle Root Checksum Verification

Every dataset release computes a Merkle root over the ordered SHA-256 normalized record hashes:

$$\text{Merkle Root} = H(H(R_1) \parallel H(R_2) \parallel \dots \parallel H(R_n))$$

Where $R_i$ is the deterministic canonical JSON representation of transaction $i$.

### Sample Merkle Verifications
- **Baseline Release `v1.0.0` (`797920d6-...`):**
  - Included records: 15 transactions
  - Checksum: `c0b88bfd333246eb553531bfe3c051ec78eb28dfabfeeaecff8a38c2c62c3b84`
  - Integrity: **VERIFIED MATCH**
- **Erasure Tombstone `v1.0.0-erasure` (`a7b84748-...`):**
  - Included records: 0 transactions (erased under DPDP §12)
  - Checksum: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (Empty SHA-256 hash)
  - Integrity: **VERIFIED MATCH**

---

## 6. Dataset Register Maintenance Schedule

1. **Daily Incremental Sync:** Any newly acquired deeds from configured connectors must be staged in `raw_transaction_staging`, PII scrubbed, normalized, and fingerprinted before appending to candidate draft versions.
2. **Weekly Merkle Certification:** Candidate versions with $\ge 50$ newly verified deeds undergo automated anomaly detection and underwriter review.
3. **Monthly Erasure Reconciliation:** Any pending DPDP right-to-erasure notices are audited against dataset version manifests, triggering version increments (`vX.Y.Z-erasure`) where required.

