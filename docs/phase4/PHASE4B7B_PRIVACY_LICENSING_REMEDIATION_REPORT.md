# PROPVAL AI — PHASE 4B-7B REMEDIATION REPORT
## PRIVACY, TRANSACTION ERASURE, AND DATA LICENSING GOVERNANCE

**Document Reference:** `docs/phase4/PHASE4B7B_PRIVACY_LICENSING_REMEDIATION_REPORT.md`  
**Execution Date:** November 4, 2026  
**Status:** COMPLETED & REGRESSION VERIFIED (298/298 Backend Tests Passing)  
**Security & Governance Baseline:** Remediates Findings PRIV-01, LIC-01, and LEGAL-01 from `docs/phase4/PHASE4B6_INDEPENDENT_FINAL_GOVERNANCE_AUDIT.md`

---

## 1. Executive Summary

During the Phase 4B-6 Independent Governance Audit, critical deficiencies were identified in PropVal AI's data erasure lifecycle and data licensing compliance:
1. **Finding PRIV-01 (Incomplete Erasure Lifecycle):** The previous `erase_transaction_record` method deleted records from `ImportedTransactionModel` and `VerificationEvidenceModel`, but left active records in `RawTransactionStagingModel`, `DuplicateRecordModel`, `QuarantinedRecordModel`, and serialized JSON arrays within immutable `DatasetVersionModel` snapshots. Additionally, retained transaction hashes in audit events risked re-identification.
2. **Finding LIC-01 (Non-Enforced Licensing Metadata & Inferred ML Permissions):** Contractual licensing fields on `DataSourceModel` (`permitted_purposes`, `retention_restrictions`, `valid_from`, `valid_until`, `authorization_status`) functioned as passive database documentation rather than active blocking gates. Moreover, model training permission was improperly assumed from ingestion permission, and retention defaulted uniformly to a static 90-day timeline regardless of contract terms.
3. **Finding LEGAL-01 (Premature DPDP Compliance Claims):** System documentation claimed full compliance under the Digital Personal Data Protection (DPDP) Act 2023 based solely on technical PII scrubbing, without addressing core legal dilemmas regarding fiduciary status, public registry exemptions, and statutory retention conflicts.

Phase 4B-7B resolves these findings by:
- Engineering a centralized 7-tier `TransactionErasureService` executing across all primary, derived, staged, quarantined, duplicate, and snapshot stores inside atomic database transactions with deterministic rollback.
- Implementing an institutional `DataPolicyService` that actively validates source authorization status, agreement validity dates, explicit contractual purposes, and independent ML training authorizations before ingestion, export, or model training.
- Introducing dynamic source-specific retention rules with authorized legal hold overrides and tamper-evident audit logging.
- Formulating a structured legal dossier detailing seven unresolved DPDP Act 2023 questions for qualified Indian legal counsel.

---

## 2. Affected Models & Database Architecture

The following existing database models participate in the remediated erasure and policy enforcement workflows:

| Model | Table Name | Role in Governance & Erasure |
| :--- | :--- | :--- |
| `DataSourceModel` | `data_sources` | Enforces `authorization_status`, `valid_from`, `valid_until`, `permitted_purposes` JSON list, and `retention_restrictions` JSON configuration. |
| `ImportedTransactionModel` | `imported_transactions` | Primary empirical property transaction record store. Targeted for permanent deletion during erasure requests. |
| `VerificationEvidenceModel` | `verification_evidence` | Cryptographic evidence, provenance logs, and algorithmic match scores tied to transactions. Deleted during erasure. |
| `DuplicateRecordModel` | `duplicate_records` | Deduplication tracking table storing duplicate references and fingerprint links. Deleted during erasure. |
| `QuarantinedRecordModel` | `quarantined_records` | Records failing verification checks (e.g. zero price, out-of-bounds coordinates). Deleted during erasure. |
| `RawTransactionStagingModel` | `raw_transaction_staging` | Pre-normalization raw JSON payloads. Purged based on source-specific retention policy or immediately during erasure. |
| `DatasetVersionModel` | `dataset_versions` | Immutable point-in-time dataset snapshots. Serialized transaction ID lists (`included_transaction_ids`) are sanitized, record counts decremented, Merkle checksums recalculated, and revision markers appended. |
| `AuditEventModel` | `audit_events` | Append-only SHA-256 hash-chained ledger. Minimizes audit payloads to salted, non-reversible hashes to prevent re-identification. |

---

## 3. Centralized Transaction Erasure Workflow (`TransactionErasureService`)

### 3.1 Multi-Tier Erasure Architecture

The newly created `TransactionErasureService` in `backend/app/services/erasure_service.py` executes a coordinated multi-tier deletion across all storage locations within a single SQLAlchemy transaction:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Centralized Erasure Workflow                         │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ 1. Identification Phase                      │
             │ Query Imported, Staging, Duplicate,           │
             │ Quarantine, and Dataset Snapshots             │
             └───────────────────────┬───────────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ 2. Deletion Phase (Atomic Transaction)        │
             │ • Tier 1: VerificationEvidenceModel           │
             │ • Tier 2: DuplicateRecordModel                │
             │ • Tier 3: QuarantinedRecordModel              │
             │ • Tier 4: RawTransactionStagingModel          │
             │ • Tier 5: ImportedTransactionModel            │
             │ • Tier 6: DatasetVersionModel Snapshots       │
             │   - Remove ID from included_transaction_ids   │
             │   - Decrement total_records & verified_records│
             │   - Recalculate dataset_checksum_sha256       │
             │   - Append '[AMENDED_UNDER_DPDP_REQUEST]'     │
             │ • Tier 7: DatasetMetadataModel Record Counts  │
             └───────────────────────┬───────────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ 3. Atomic Commit & Audit Minimization         │
             │ Salted SHA-256 reference recorded in hash     │
             │ chain without leaking raw property/owner data │
             └───────────────────────────────────────────────┘
```

### 3.2 Atomic Rollback Mechanism
If any database failure occurs during the multi-tier deletion (e.g., query error, database constraint, I/O disruption):
1. `db.rollback()` is invoked immediately, restoring all rows across all 7 tiers to their pre-erasure state.
2. A specialized failure event `EVENT_DATASET_ERASURE_FAILED` is recorded in the append-only audit log with the exception description.
3. The method returns `{"success": False, "error": "TRANSACTION_ROLLBACK"}` allowing caller retry or incident alerting.

### 3.3 Audit Minimization & Re-Identification Risk Assessment
Under DPDP Act 2023 Section 12, data fiduciaries must erase personal data upon request unless statutory retention applies. A naive implementation that logs `"deleted_id": "tx_12345", "property": "Villa 4, Palm Meadows"` violates privacy minimization by persisting identifying data in the immutable audit log.
- **Salted Hash Reference:** The audit event payload records `salt_prefix:sha256(transaction_id)`. Without access to the deleted database row, this hash cannot be correlated with an individual or physical parcel.
- **No Residual Personal Data:** Raw PII, owner names, addresses, and unit numbers are omitted from the audit payload.
- **Cryptographic Anonymization Limitation:** A simple SHA-256 hash of low-entropy values (e.g., small integer IDs or known addresses) can be cracked via rainbow tables. PropVal AI employs system-salted hashing to mitigate precomputation attacks.

### 3.4 Storage Limitations (Backups & Snapshots)
- **Database Snapshots:** Relational tables and active SQLite/PostgreSQL instances are scrubbed in real time.
- **Read-Only Physical Backups:** Offsite cryptographic disk backups (WAL archives, AWS S3/GCS immutable vaults) cannot be surgically edited without invalidating entire archive volumes. PropVal AI documents that data in disaster-recovery backups is subject to cryptographic key expiration or automated 30-day lifecycle roll-off, rather than live rewriting.

---

## 4. Purpose and Retention Policy Service (`DataPolicyService`)

### 4.1 Enforceable Ingestion Controls

Located in `backend/app/services/policy_service.py`, `DataPolicyService.verify_source_for_ingestion` enforces:
1. **Authorization Status:** Sources must hold `DOCUMENTED_AND_AUTHORIZED` (or `TEST_ONLY` during synthetic harness execution). Sources with status `PENDING_LEGAL_REVIEW`, `SUSPENDED`, or `REVOKED` are strictly rejected.
2. **Agreement Validity Window:** Compares current UTC time against `valid_from` and `valid_until`. If `now < valid_from`, acquisition is blocked with `"agreement is not yet active"`. If `now > valid_until`, acquisition is blocked with `"authorization expired"`.
3. **Explicit Permitted Purposes:** Checks `permitted_purposes` JSON list. An acquisition request with purpose `DATA_INGESTION` is rejected if `DATA_INGESTION` is absent.

### 4.2 Decoupled ML Training Permissions (No Inferred Rights)

Per FINDING 2, **never infer ML-training permission from general data-access permission**.
In `backend/app/services/policy_service.py` (`verify_dataset_and_source_for_ml`):
- To export a dataset for ML training or execute model training (`train_valuation_model`), the source contract **must explicitly list `MODEL_TRAINING`** in `permitted_purposes`.
- If a source only permits `DATA_INGESTION` and `VALUATION_ESTIMATION` (e.g., real-time single-property lookup API), ML training export is blocked with HTTP 403 Forbidden.
- Both the parent `DatasetMetadataModel` and the specific `DatasetVersionModel` must be in `APPROVED` status before any training records can be exported.

### 4.3 Configurable Source-Specific Retention Policies

The previous hardcoded `now - timedelta(days=90)` logic was replaced in `backend/app/services/acquisition_service.py` (`purge_expired_raw_staging`):
- Each source configures `retention_restrictions` JSON:
  ```json
  {
    "raw_staging_retention_days": 30,
    "legal_hold": false,
    "legal_hold_reason": null
  }
  ```
- Sources with stricter contractual terms (e.g., 30-day purge requirement) are purged after 30 days.
- Sources with extended contracts (e.g., 180-day retention) retain raw staging up to their contracted threshold.

### 4.4 Legal Hold Mechanism

When litigation, regulatory subpoena, or audit review requires preserving records:
- Setting `legal_hold: true` in `retention_restrictions` halts the purge of staging records regardless of age.
- Emits an immutable audit block `RETENTION_LEGAL_HOLD_APPLIED` containing the legal hold reason and record count preserved.
- When the legal hold is released by authorized legal personnel, records are subjected to immediate evaluation against the contractual retention timeline.

---

## 5. Outstanding Legal-Review Questions for Qualified Indian Counsel

Technical safeguards cannot substitute for legal advice under Indian jurisprudence. The following 7 legal questions have been prepared for formal consultation with qualified Indian legal counsel specializing in the Digital Personal Data Protection Act, 2023:

### 1. Data Fiduciary vs. Data Processor Characterization (DPDP Act § 2(i), § 2(j))
*Question:* When PropVal AI ingests property registration transaction data from third-party aggregators (e.g., Zapkey) or state sub-registrar portals to generate automated valuation models for lending banks, does PropVal AI act as a **Data Fiduciary** (determining the purpose and means of processing) or as a **Data Processor** (processing data on behalf of the commercial lender)? What contractual stipulations must be executed with partner banks to demarcate processing liability?

### 2. Applicable Lawful Basis for Ingesting Public Registration Records (DPDP Act § 4, § 7)
*Question:* Under the Registration Act, 1908, registered sale deeds are public records accessible to citizens upon payment of prescribed fees. Does the public availability of registered deeds exempt PropVal AI from obtaining express consent from property buyers and sellers, or does the commercial aggregation and machine learning analysis constitute processing that requires either consent or a recognized legitimate use under Section 7?

### 3. Data Erasure Conflicts with Statutory Anti-Money Laundering Laws (DPDP Act § 12 vs. PMLA 2002)
*Question:* If a property buyer or seller requests erasure of their personal transaction record under DPDP Act Section 12, how does PropVal AI reconcile this request with the mandatory 5-year record-retention requirements imposed by the Prevention of Money Laundering Act (PMLA), 2002, and Reserve Bank of India (RBI) Master Directions on Know Your Customer (KYC) for financial valuation records?

### 4. Permissibility of Retaining Cryptographic Hashes Following Erasure Requests
*Question:* Section 12 mandates the complete erasure of personal data unless required for compliance with law. Does retaining a salted SHA-256 fingerprint hash of a transaction (necessary to maintain the cryptographic integrity of the historical Merkle hash chain in the audit ledger) satisfy the statutory definition of erasure, or could an adversary correlate the hash with public land registry records and argue that personal data persists?

### 5. Cross-Border Processing & External Cloud AI Inference (DPDP Act § 16)
*Question:* When property attributes (locality, square footage, building age, transaction price, and historical deviation) are transmitted to cloud-hosted foundational models (such as Google Gemini API or Vertex AI instances located in US/EU regions) for automated underwriting commentary, does this constitute a cross-border data transfer subject to Central Government notifications under Section 16 of the DPDP Act? Does stripping individual names prior to API dispatch sufficiently render the payload non-personal data?

### 6. Machine Learning Derived Feature Ownership and Contractual License Restrictions
*Question:* When third-party proptech aggregators provide data under licenses permitting "valuation and market analytics," does training an offline machine learning model (e.g., gradient boosted regression trees or neural price surfaces) that inherently internalizes spatial pricing trends into model weights violate contractual restrictions against "creating derivative databases" or "model training"?

### 7. Notice and Consent Architecture for B2B2C Valuation Reports
*Question:* In scenarios where PropVal AI generates a valuation report delivered to a bank underwriter, who subsequently shares the valuation assessment with a retail mortgage applicant, what statutory notice (under DPDP Section 5) must be provided to the retail applicant regarding the automated processing of comparable property data in their neighborhood?

---

## 6. Test Verification & Acceptance Matrix

### 6.1 Phase 4B-7B Specific Test Suite (`test_privacy_licensing_remediation_phase4b7b.py`)

All 10 tests passed cleanly in 1.67 seconds:

| Test Name | Focus Area | Status |
| :--- | :--- | :--- |
| `test_multi_tier_erasure_removes_all_copies` | Verifies coordinated deletion across primary, staging, duplicate, quarantine, and dataset version snapshots | **PASSED** |
| `test_erasure_partial_failure_rolls_back_atomically` | Simulates database error during deletion; proves atomic rollback and failure audit recording | **PASSED** |
| `test_erasure_non_existent_transaction_returns_clean_not_found` | Negative test verifying clean handling for missing records | **PASSED** |
| `test_unauthorized_purpose_blocks_ingestion` | Verifies ingestion is rejected when requested purpose is missing from source `permitted_purposes` | **PASSED** |
| `test_missing_permitted_purposes_blocks_ingestion` | Verifies that null/empty `permitted_purposes` triggers immediate acquisition rejection | **PASSED** |
| `test_not_yet_active_agreement_blocks_ingestion` | Verifies future `valid_from` date halts data ingestion | **PASSED** |
| `test_ml_training_permission_never_inferred_from_general_access` | Proves that `DATA_INGESTION` permission does not permit ML export; requires explicit `MODEL_TRAINING` | **PASSED** |
| `test_readiness_gate_blocks_unapproved_dataset_and_source` | Verifies `MLReadinessGate` blocks datasets from unapproved sources or datasets in `PENDING` state | **PASSED** |
| `test_dynamic_source_specific_retention_purge` | Proves 30-day retention source is purged while 180-day source is retained | **PASSED** |
| `test_legal_hold_preserves_expired_records_with_audit` | Proves `legal_hold: true` halts purging and emits `RETENTION_LEGAL_HOLD_APPLIED` audit block | **PASSED** |

### 6.2 Full Regression Suite

The complete backend regression suite was executed across all 32 test modules:
```
============================== 298 passed, 2 warnings in 35.82s ===============================
```
- **Total Test Cases:** 298
- **Passed:** 298 (100%)
- **Failed:** 0
- **Regression Rate:** 0.00%

---

## 7. Remaining Limitations & Operational Guardrails

1. **Immutable Storage Snapshots:** Erasure updates all online databases and dataset version index arrays. Offline disaster recovery disk images are protected by 30-day retention lifecycles rather than live modification.
2. **Legal Dependencies:** Final determination of public land registry exemptions under the DPDP Act 2023 requires formal written opinion from qualified Indian legal counsel before deploying live aggregator feeds.
3. **Operational State:** Ingestion connectors remain strictly disabled (`TEST_ONLY` mock harness mode); no external API endpoints are invoked; no live Zapkey ingestion is enabled.

