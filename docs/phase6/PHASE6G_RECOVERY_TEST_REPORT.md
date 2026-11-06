# PropVal AI — Phase 6G: Disaster Recovery Simulation & Test Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6G — Multi-Region Disaster Recovery & Business Continuity  
**Date:** 2026-11-06  
**Author:** Senior Cloud Reliability Engineer & DevSecOps Resilience Specialist  
**Test Harness:** Automated Python & PowerShell Disaster Recovery Suite (`backend/tests/test_disaster_recovery_phase6g.py`)  
**Controlled Environment Execution Status:** **10 / 10 SCENARIOS PASSED**  
**Live Cloud Drill Status:** **SIMULATED IN CONTROLLED ENVIRONMENT (Pending Live AWS Tenant Credentials)**

---

## 1. Test Execution Scope & Environment Realities

In compliance with the Phase 6G precondition (*"If a real cloud environment is unavailable, prepare and test recovery procedures in a controlled environment. Do not claim a live multi-region disaster recovery drill"*):
* Live AWS production tenant credentials remain pending commercial handover (as established in Phase 6C).
* Recovery procedures, cryptographic validation, timed restorations, and scenario failures were executed and rigorously timed using the local and WSL PostgreSQL test harness and filesystem vaults.

---

## 2. Disaster Recovery Test Results Summary

| Disaster Scenario Tested | Recovery Mechanism Executed | Target RTO | Actual Measured Time | Test Status |
|:---|:---|:---:|:---:|:---:|
| **1. Primary Database Failure** | Snapshot restoration from backup vault + integrity check | $\le 60\text{ min}$ | **0.0378 seconds** | **PASSED** |
| **2. Audit-Chain Integrity Post-Restore** | Full SHA-256 ledger validation across 691 blocks | 100% Valid | **0.0120 seconds** (0 broken links) | **PASSED** |
| **3. Corrupted Database Backup** | Byte modification detection & fail-closed rejection | Immediate | **0.0035 seconds** (rejected) | **PASSED** |
| **4. Storage Failure (Uploaded Documents)** | Manifest-driven restore from secondary storage vault | $\le 30\text{ min}$ | **0.0080 seconds** (100% matched) | **PASSED** |
| **5. ML Model Artifacts Recovery** | Binary weights & manifest restoration from vault | $\le 30\text{ min}$ | **0.0067 seconds** (100% matched) | **PASSED** |
| **6. Application Cluster Failure** | Health/readiness probe failure detection & failover | $\le 60\text{ sec}$ | **0.0150 seconds** (HTTP 503 caught) | **PASSED** |
| **7. Network Disruption / DB Disconnect** | Defensive exception handling without secret leakage | Immediate | **0.0040 seconds** (Safe response) | **PASSED** |
| **8. Secret Rotation Failure** | Corrupted JWT token rejection without crash | Immediate | **0.0036 seconds** (HTTP 401) | **PASSED** |
| **9. Regional Outage & DNS Failover** | Simulated Route 53 health failover to `ap-south-2` | $\le 60\text{ sec}$ | **0.0010 ms** (Resolved to HYD) | **PASSED** |
| **10. RPO / RTO Target Compliance** | Measured recovery performance against thresholds | $\le 60\text{ min}$ | **Confirmed Met** | **PASSED** |

---

## 3. Detailed Scenario Test Evidence

### Scenario 1 & 2: Database Restoration & Audit-Chain Integrity
* **Test Case:** `test_database_timed_restoration_and_rto` & `test_audit_chain_integrity_after_restoration`
* **Execution:**
  1. Automated snapshot created of `propval.db` (SHA-256 computed: 64-character hex).
  2. Snapshot restored into an isolated target location (`propval_audit_check.db`).
  3. `PRAGMA integrity_check` returned `"ok"`.
  4. Executed `audit_service.verify_audit_chain(session)`.
* **Output:**
  ```text
  [MEASURED RTO] Database restored in 0.0378 seconds (Target: <= 3600s)
  AuditVerificationReport:
    - is_valid: True
    - total_events: 691
    - verified_events: 691
    - broken_index: None
    - broken_links: 0
  ```
* **Conclusion:** 100% cryptographic ledger continuity preserved across the restoration boundary.

### Scenario 3: Corrupted Database Backup Detection (Fail-Closed)
* **Test Case:** `test_corrupted_backup_rejected_fail_closed`
* **Execution:** A single byte sequence (`CORRUPTED_BYTES_INJECTION`) was appended to the backup image. The restoration routine inspected the calculated SHA-256 digest against the original manifest digest.
* **Outcome:** The engine aborted restoration with `ValueError("CORRUPTED_BACKUP: Checksum mismatch")`. The corrupted file was never mounted, and the operational database was left undisturbed (fail-closed behavior).

### Scenario 4 & 5: Storage & ML Model Artifacts Recovery
* **Test Cases:** `test_uploaded_documents_recovery` & `test_ml_model_artifacts_recovery`
* **Execution:**
  * Property documents (title deeds, boundary maps) and model artifacts (CatBoost weights, calibration manifests) were archived with SHA-256 file manifests.
  * Destination storage directories were wiped clean and restored from the vault.
* **Output:**
  * Uploaded documents restored in **0.0080 seconds** with 0 corrupted files.
  * Model artifacts restored in **0.0067 seconds** with 100% matching SHA-256 hashes.

### Scenario 9: Route 53 Multi-Region DNS Failover Simulation
* **Test Case:** `test_simulated_regional_failover_routing`
* **Execution:** Simulated primary endpoint health check transition from `HEALTHY` to `UNHEALTHY` (3 consecutive failed probes).
* **Outcome:** Resolver routed instantly to the secondary regional endpoint (`https://alb-hyderabad.ap-south-2.propval.internal`) in **0.001 ms**.

