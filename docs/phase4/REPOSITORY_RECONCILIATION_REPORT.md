# PROPVAL AI — REPOSITORY RECONCILIATION & DEVELOPMENT BASELINE REPORT

**Project:** PropVal AI — Institutional Real Estate Collateral Valuation & Automated Underwriting Platform  
**Audit Date:** November 5, 2026  
**Auditor / Engineering Role:** Antigravity Principal Systems Architect & Governance Lead  
**Execution Mode:** READ-ONLY AUDIT FIRST  
**Target Specification:** Repository Reconciliation prior to Phase 4B-7  
**File Path:** `docs/phase4/REPOSITORY_RECONCILIATION_REPORT.md`  

---

## 1. Executive Summary

A comprehensive, read-only architectural, git-state, implementation, test, and documentation audit was conducted on the PropVal AI repository (`https://github.com/Dhineshkumardhina/proval-ai`).

### Primary Audit Findings:
1. **Git State Divergence:** The repository is currently checked out on `phase1-credibility-remediation`. While Phase 2 backend foundations were committed to this branch (`107d004`), **the entire Phase 3 extensions and Phase 4 implementation (16 documentation reports, 4 database migrations, 3 API endpoints, 4 architecture packages, 3 models, 3 schemas, 3 services, and 12 test suites) reside strictly as uncommitted modifications (15 files) and untracked files (36 files/directories) in the local working tree**.
2. **GitHub Pull Request #1 Status:** PR #1 ("Phase1 credibility remediation") remains **OPEN** and **UNMERGED** on GitHub (`phase1-credibility-remediation` $\rightarrow$ `main`). The `main` branch remains on commit `ea2d696` (the initial baseline before Phase 1 audit) and contains zero backend, ML, or Phase 2/3/4 code.
3. **Test Baseline Reality:**
   - **Frontend Tests:** **26 passed, 0 failed (100%)**.
   - **TypeScript Verification:** **0 errors (100% clean)**.
   - **Production Frontend Build:** **100% successful** (1,682 modules built in 7.94s, clean `dist/` bundle).
   - **Backend Tests:** **297 passed, 1 failed (99.66%)** across 298 collected tests.
   - **Security Tests:** **87 passed, 0 failed (100%)** across 5 dedicated security suites; `bandit` reports 0 High / 0 Medium vulnerabilities; `npm audit` reports 0 vulnerabilities.
4. **Root Cause of Single Test Failure:** In `backend/tests/test_e2e_pipeline_validation.py` (line 156), `test_complete_e2e_pipeline_lifecycle` failed with `assert 403 == 400`. In Phase 4B-7B, `export_ml_training_manifest` introduced strict licensing enforcement (`DataPolicyService`), which correctly blocks ML exports from `TEST_ONLY` mock sources with `403 Forbidden`. The older test assertion expected the pipeline to bypass licensing and hit the 1,000 empirical deed threshold with `400 Bad Request`.
5. **Database Migration Drift:** The Alembic migration scripts define head revision `e2f34a5b6c7d`, whereas the local development database (`backend/propval.db`) is currently at `d8e90f12a345` (`Target database is not up to date`).
6. **Production Readiness Classification:** **CONDITIONALLY APPROVED FOR CONTROLLED INSTITUTIONAL DEMONSTRATION ONLY**. The platform is **NOT PRODUCTION READY** for live lending operations due to the absence of commercial deed contracts, unmigrated PostGIS cadastral polygon validation, zero live empirical deeds, and an uncommitted git working tree.

---

## 2. Git State Audit

### 2.1 Branch Inventory & Tracking
```
Active Working Branch: phase1-credibility-remediation
Tracking Branch:       origin/phase1-credibility-remediation (synchronized at commit 107d004)
Main Branch:           main (synchronized with origin/main at commit ea2d696)
```

### 2.2 Branch Divergence & Commit History
```
* 107d004 (HEAD -> phase1-credibility-remediation, origin/phase1-credibility-remediation)
|         feat: implement backend API, ML engine, database migrations, and containerization setup
* ce60a92 docs: preserve Phase 2A engineering assessment
* 8ad595b feat(audit): complete phase 1 credibility remediation and reports
* ea2d696 (origin/main, origin/HEAD, main)
          chore: initial baseline before phase 1 audit
```
- `phase1-credibility-remediation` is **3 commits ahead** of `main`.
- `main` is **0 commits ahead** of `phase1-credibility-remediation`.
- The `main` branch contains only the original React mockup and has received zero backend or governance updates.

### 2.3 Uncommitted Changes (15 Modified Files)
The following tracked files contain uncommitted changes reflecting Phase 3 and Phase 4 enhancements:
1. `backend/app/api/v1/endpoints/datasets.py` (+90, -12): Dataset export policy gates and version filtering.
2. `backend/app/api/v1/endpoints/health.py` (+24, -2): Extended deep readiness diagnostics.
3. `backend/app/api/v1/router.py` (+25, -2): Registered acquisition, dataset versions, and governance endpoints.
4. `backend/app/core/logging.py` (+4, -1): Sensitive PII redaction filter in logging formatters.
5. `backend/app/ml/readiness_gate.py` (+21, -2): Explicit source licensing checks prior to model training evaluation.
6. `backend/app/models/__init__.py` (+21, -2): Registered data source, verification, and dataset version models.
7. `backend/app/models/dataset.py` (+8, -0): Added approval status fields and relationship links.
8. `backend/app/schemas/dataset.py` (+10, -0): Dual-approval schema additions.
9. `backend/app/services/audit_service.py` (+16, -1): Salted cryptographic hash anonymization for audit ledger.
10. `backend/app/services/ingestion_service.py` (+41, -0): Pre-staging PII scrubbing integration.
11. `backend/app/services/privacy_service.py` (+143, -2): Deep dictionary PII scrubbing and regex engines.
12. `docs/phase3/PHASE3C_DATABASE_RELIABILITY_REPORT.md` (+38, -2): Database reliability adjustments.
13. `load_test_results.json` (+82, -31): Benchmark metrics.
14. `src/components/ModelGovernance/ModelGovernanceView.tsx` (+828, -75): Expanded institutional governance dashboard UI.
15. `src/services/apiClient.ts` (+153, -2): Added API client methods for dataset versions, acquisition, and governance metrics.

### 2.4 Untracked Files (36 Files and Folders)
The following files exist in the working directory but are completely untracked by Git:

#### Alembic Database Migrations (4 untracked):
- `backend/alembic/versions/b9c23d4e8f10_add_data_sources_and_connectors_staging.py`
- `backend/alembic/versions/c7d89e01f234_add_quarantined_records_and_verification_evidence.py`
- `backend/alembic/versions/d8e90f12a345_add_dataset_versions_table.py`
- `backend/alembic/versions/e2f34a5b6c7d_add_governance_authorization_and_dataset_workflows.py`

#### API Endpoints & Core Subsystems (4 untracked modules, 3 endpoints, 3 models, 3 schemas, 3 services):
- `backend/app/api/v1/endpoints/acquisition.py`
- `backend/app/api/v1/endpoints/dataset_versions.py`
- `backend/app/api/v1/endpoints/governance.py`
- `backend/app/connectors/` (base, http_client, mock, zapkey, registry)
- `backend/app/dataset_management/` (version_service)
- `backend/app/normalization/` (engine, geo_normalizer, unit_converter)
- `backend/app/verification/` (verification_engine)
- `backend/app/models/data_source.py`
- `backend/app/models/dataset_version.py`
- `backend/app/models/verification.py`
- `backend/app/schemas/data_source.py`
- `backend/app/schemas/dataset_version.py`
- `backend/app/schemas/governance_dashboard.py`
- `backend/app/services/acquisition_service.py`
- `backend/app/services/erasure_service.py`
- `backend/app/services/policy_service.py`

#### Backend Test Suites (12 untracked test suites):
- `backend/tests/test_connector_security_phase4b3.py`
- `backend/tests/test_connectors.py`
- `backend/tests/test_data_governance_phase4b.py`
- `backend/tests/test_dataset_versions.py`
- `backend/tests/test_e2e_pipeline_validation.py`
- `backend/tests/test_geospatial_quality_phase4b4.py`
- `backend/tests/test_governance_dashboard_phase4b5.py`
- `backend/tests/test_normalization.py`
- `backend/tests/test_privacy_engineering_phase4b2.py`
- `backend/tests/test_privacy_licensing_remediation_phase4b7b.py`
- `backend/tests/test_ssrf_remediation_phase4b7a.py`
- `backend/tests/test_verification.py`

#### Documentation (Phase 3 and Phase 4):
- `docs/phase3/PHASE3A0_REPOSITORY_REALITY_AUDIT.md`
- `docs/phase3/PHASE3B_SECURITY_AUDIT_REPORT.md`
- `docs/phase3/PHASE3E_DEPLOYMENT_READINESS_REPORT.md`
- `docs/phase3/PHASE3G_INSTITUTIONAL_DEMO_REPORT.md`
- `docs/phase3/PROPVAL_AI_DEMO_SCRIPT.md`
- `docs/phase4/` (16 complete engineering reports: 4A0-4A5, 4A final, 4B0-4B6, 4B7A, 4B7B)

---

## 3. Pull Request Status

### Pull Request #1 Inspection
- **PR Number:** #1
- **Title:** `Phase1 credibility remediation`
- **Head Branch:** `phase1-credibility-remediation`
- **Base Branch:** `main`
- **State:** `OPEN`
- **Merged:** `False`
- **GitHub URL:** `https://github.com/Dhineshkumardhina/proval-ai/pull/1`

### Architectural Impact of PR #1:
When PR #1 was initially created, its intent was strictly Phase 1 audit remediation. However, commit `107d004` ("feat: implement backend API, ML engine, database migrations, and containerization setup") was subsequently committed and pushed directly to `phase1-credibility-remediation`.

Consequently, PR #1 now encompasses the entire Phase 2 backend foundation under a Phase 1 title. Furthermore, because PR #1 was never merged into `main`, the `main` branch is entirely obsolete and disconnected from the current working state.

---

## 4. Actual Implementation Inventory

The codebase was inspected across 14 institutional functional subsystems:

| # | Subsystem / Capability | Primary Source Files | Documented Status | Actual Implementation Reality | Audit Verification |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **React Frontend** | `src/App.tsx`, `src/components/*`, `src/services/apiClient.ts` | Completed | React 19 SPA, Tailwind CSS, Lucide icons, role switching, offline API fallback. | **VERIFIED (Operational)** |
| **2** | **FastAPI Backend** | `backend/app/main.py`, `backend/app/api/v1/router.py`, `endpoints/*` | Completed | 13 endpoints on FastAPI 0.142.2, structured logging, CORS, rate limiting. | **VERIFIED (Operational)** |
| **3** | **Database Schema & Migrations** | `backend/app/models/*`, `backend/alembic/versions/*` | Completed | 10 models, 14 migrations. Drift detected: `propval.db` at `d8e90f12a345` vs head `e2f34a5b6c7d`. | **DRIFT DETECTED** |
| **4** | **Valuation Engine** | `src/utils/valuationEngine.ts`, `backend/app/services/valuation_service.py` | Completed | Deterministic rule-based valuation, circle rates, distress haircuts, 100% parity. | **VERIFIED (Operational)** |
| **5** | **CatBoost ML Pipeline** | `backend/app/ml/trainer.py`, `model_service.py`, `readiness_gate.py` | Gated | Regression pipeline implemented; locked by 1,000 empirical deed gate. | **VERIFIED (Gated)** |
| **6** | **SHAP Explainability** | `backend/app/ml/explainability.py` | Completed | TreeSHAP implemented; waterfall fallback active during rule-based operation. | **VERIFIED (Operational)** |
| **7** | **AI Underwriting Assistant** | `backend/app/services/gemini_service.py`, `endpoints/ai.py` | Completed | Gemini API integration with offline deterministic fallback briefing. | **VERIFIED (Operational)** |
| **8** | **Case Management** | `backend/app/services/case_service.py`, `endpoints/cases.py` | Completed | Full lifecycle state machine, RBAC guards, approved case immutability. | **VERIFIED (Operational)** |
| **9** | **Property Data Ingestion** | `backend/app/services/ingestion_service.py`, `acquisition_service.py` | Completed | CSV/Excel ingestion, magic byte verification, formula injection sanitization. | **VERIFIED (Operational)** |
| **10** | **Data Connectors & SSRF Defense** | `backend/app/connectors/*`, `http_client.py` | Hardened | Socket IP pinning (`SecuredPinningTransport`), IPv4-mapped IPv6 defense, port checks. | **VERIFIED (Operational)** |
| **11** | **Data Verification & Quarantine** | `backend/app/verification/*`, `models/verification.py` | Completed | Anomaly detection, quarantine isolation (`QuarantinedRecordModel`), evidence hashing. | **VERIFIED (Operational)** |
| **12** | **Dataset Versioning & Governance** | `backend/app/dataset_management/*`, `models/dataset_version.py` | Completed | Point-in-time snapshots, SemVer tags, Merkle-style root dataset SHA-256 checksums. | **VERIFIED (Operational)** |
| **13** | **Privacy & DPDP Erasure** | `backend/app/services/privacy_service.py`, `erasure_service.py` | Remediated | Deep PII scrubber, 7-tier centralized atomic `TransactionErasureService`. | **VERIFIED (Operational)** |
| **14** | **Audit Logging Ledger** | `backend/app/services/audit_service.py`, `models/audit.py` | Completed | Cryptographically linked SHA-256 chain, canonical JSON, tamper detection verification API. | **VERIFIED (Operational)** |

---

## 5. Live Test Baseline Results

All tests were executed directly in the current environment on November 5, 2026. **No historical test counts are reused.**

### 5.1 Frontend Test Execution (`npm run test`)
```
Command: tsx --test src/utils/valuationEngine.test.ts src/services/apiClient.test.ts
Total Suites: 2
Total Tests:  26
Passed:       26
Failed:       0
Skipped:      0
Duration:     1.02 seconds
Result:       100% PASS
```

### 5.2 TypeScript Compilation Check (`npm run lint`)
```
Command: tsc --noEmit
Output:  Clean (exit code 0)
Errors:  0
Result:  100% PASS
```

### 5.3 Production Frontend Build (`npm run build`)
```
Command: vite build
Modules Transformed: 1,682
Output Chunks:
  dist/index.html                                 1.68 kB │ gzip:  0.70 kB
  dist/assets/index-oyu_gXLu.css                 39.37 kB │ gzip:  8.41 kB
  dist/assets/rolldown-runtime-WkwZ5CU-.js        0.59 kB │ gzip:  0.36 kB
  dist/assets/NewCaseModal-DKYRyxJq.js            7.98 kB │ gzip:  2.73 kB
  dist/assets/UnderwritingPipeline-DhZBgLuQ.js    9.57 kB │ gzip:  2.51 kB
  dist/assets/vendor-icons-D0ctQliG.js           19.73 kB │ gzip:  7.13 kB
  dist/assets/RiskAuditDashboard-De_BVRZa.js     23.02 kB │ gzip:  5.63 kB
  dist/assets/ModelGovernanceView-Cc4rUtJX.js    31.34 kB │ gzip:  6.31 kB
  dist/assets/index-BaMSYgR_.js                 110.03 kB │ gzip: 26.57 kB
  dist/assets/vendor-react-CkxBCpPO.js          210.90 kB │ gzip: 65.85 kB
Build Duration: 7.94s
Result: 100% PASS (Zero warnings, zero build errors)
```

### 5.4 Backend Test Execution (`python -m pytest backend/tests`)
```
Command: python -m pytest backend/tests
Collected: 298 tests across 32 test files
Passed:    297 tests
Failed:    1 test
Warnings:  2 (Starlette HTTP status code deprecation warnings)
Duration:  42.95 seconds
```

#### Detailed Breakdown of Failing Test:
- **Test:** `backend/tests/test_e2e_pipeline_validation.py::test_complete_e2e_pipeline_lifecycle`
- **Location:** Line 156
- **Error Trace:**
  ```python
  assert exc_info.value.status_code == 400
  E assert 403 == 400
  E + where 403 = HTTPException(status_code=403, detail="Institutional Export Blocked by Licensing Policy: ML Processing Gated: Source 'SRC_E2E_CCFA9E' authorization status is 'TEST_ONLY'. Ingestion strictly requires 'DOCUMENTED_AND_AUTHORIZED'.").status_code
  ```
- **Factual Root Cause:** During Phase 4B-7B remediation, `DatasetVersionService.export_ml_training_manifest` was updated to call `DataPolicyService.check_dataset_licensing_compliance`. Because the mock connector creates a source with `authorization_status = "TEST_ONLY"`, the licensing gate aborts immediately with `HTTP 403 Forbidden`. The test previously expected the request to pass licensing and fail at the 1,000 deed empirical threshold with `HTTP 400 Bad Request`.

### 5.5 Security Test Baseline
- **Dedicated Security Suites:** 87 tests passed out of 87 tests (100% pass rate) across:
  - `test_security_remediation.py` (22 tests)
  - `test_ssrf_remediation_phase4b7a.py` (29 tests)
  - `test_connector_security_phase4b3.py` (16 tests)
  - `test_privacy_engineering_phase4b2.py` (10 tests)
  - `test_privacy_licensing_remediation_phase4b7b.py` (10 tests)
- **Static Security Scan (`bandit -r backend/app -ll`):** 11,741 lines scanned. **0 High, 0 Medium, 8 Low** severity findings.
- **Dependency Vulnerability Scan (`npm audit`):** **0 vulnerabilities**.

### 5.6 Database Migration Status
```
Command: python -m alembic check
Result:  FAILED ("Target database is not up to date.")
Scripts Head Revision: e2f34a5b6c7d (e2f34a5b6c7d_add_governance_authorization_and_dataset_workflows.py)
Current Database Rev:  d8e90f12a345 (backend/propval.db)
Unapplied Migrations:  1 revision pending execution
```

---

## 6. Documentation Reconciliation & Discrepancies

A systematic review of `docs/phase2/` (phase2a-2h), `docs/phase3/`, and `docs/phase4/` revealed the following discrepancies between documentation claims and repository reality:

### 1. Phase 4B-7B Test Count Claim Discrepancy
- **Claim:** `docs/phase4/PHASE4B7B_PRIVACY_LICENSING_REMEDIATION_REPORT.md` states: *"Status: COMPLETED & REGRESSION VERIFIED (298/298 Backend Tests Passing)"*.
- **Reality:** Current test execution yields **297 passed, 1 failed**. The test `test_complete_e2e_pipeline_lifecycle` was broken by the status code change introduced in that exact phase.

### 2. Data Quality Formula Mislabeling (Finding GOV-01)
- **Claim:** Documented and displayed in UI as a *"Weighted harmonic aggregate"*.
- **Reality:** Implemented in `backend/app/api/v1/endpoints/governance.py` (lines 274-295) and `src/components/ModelGovernance/ModelGovernanceView.tsx` as a **Weighted Arithmetic Mean** ($0.40 C + 0.30 V + 0.20 U + 0.10 K$).

### 3. Data Quality Denominator & Zero-Record Edge Case (Finding GOV-02)
- **Claim:** Robust data quality scoring across four institutional dimensions.
- **Reality:** Completeness evaluates only `total_valid_tx` (`ImportedTransactionModel`), ignoring rejected records. Furthermore, an empty database defaults to `100.0%` quality score rather than `0.0%` or `"NO_DATA"`.

### 4. PostGIS & Cadastral Parcel Engine (Finding GEO-01)
- **Claim:** Architectural documentation refers to spatial boundary verification and cadastral parcel mapping.
- **Reality:** PostGIS and `GeoAlchemy2` are completely absent. Spatial bounding checks are rectangular latitude/longitude arithmetic comparisons (`geo_normalizer.py`). Authoritative state polygon containment and digital revenue map (`BhuNaksha`) boundary validation do not exist.

### 5. Git & PR Representation
- **Claim:** PR #1 represents "Phase 1 credibility remediation".
- **Reality:** PR #1 has accumulated Phase 2 commits and remains unmerged, while the entire Phase 3 and Phase 4 bodies of work are uncommitted in the local tree.

---

## 7. Outstanding Technical Debt & Production Blockers

### 7.1 Outstanding Technical Debt
1. **Repository Hygiene Debt:** 15 modified and 36 untracked files are uncommitted, creating high risk of accidental data loss or regression.
2. **Database Migration Debt:** `backend/propval.db` is 1 migration behind Alembic head (`e2f34a5b6c7d`).
3. **E2E Test Regression:** `test_complete_e2e_pipeline_lifecycle` needs assertion alignment for the 403 status code.
4. **Formula Terminology Debt:** The Data Quality Score in backend and frontend must be relabeled to reflect its true arithmetic formulation.
5. **Quarantine Workflow Incompleteness:** The governance dashboard displays quarantined records, but no administrative endpoint exists to review, resolve, or re-ingest them.
6. **Starlette Deprecation Warnings:** Deprecated status codes (`HTTP_422_UNPROCESSABLE_ENTITY`, `HTTP_413_REQUEST_ENTITY_TOO_LARGE`) should be updated to `UNPROCESSABLE_CONTENT` and `CONTENT_TOO_LARGE`.

### 7.2 Institutional Production Blockers
1. **Commercial Data Counterparty Agreement (Zapkey / Propstack):** No executed B2B agreement or production credentials; live connector ingestion remains blocked.
2. **G2B SRO Gateway Access (Kaveri 2.0 / IGR Maharashtra):** No government MoU or API access; automated deed scraping is legally prohibited.
3. **Indian DPDP Act 2023 Legal Opinion:** Outstanding legal questions regarding Data Fiduciary classification and statutory retention require formal Indian legal counsel sign-off.
4. **Empirical ML Training Deed Threshold:** 0 empirical deeds exist in the database; CatBoost ML inference and conformal uncertainty calibration remain strictly locked behind the 1,000 empirical deed gate.
5. **Cadastral & Polygon Boundary Verification:** Absence of PostGIS polygon containment allows out-of-boundary and oceanic coordinates to pass rectangular bounding checks.

---

## 8. Recommended Development Branch & Next Actions

### 8.1 Development Branch Recommendation
Do **not** continue committing haphazardly to `phase1-credibility-remediation`, as that branch name is historically inaccurate.

**Recommended Branch Strategy:**
1. Leave `main` untouched for now (maintaining baseline stability).
2. Create a new development branch from current `HEAD`:
   ```bash
   git checkout -b feat/phase4-institutional-governance-baseline
   ```
3. Stage and commit the reconciled Phase 3 documentation, Phase 4 code, migrations, and test suites with a descriptive commit message:
   `feat(phase4): implement institutional data governance, connectors, and security remediation`
4. On GitHub, update PR #1 description or close PR #1 and open a clean PR from `feat/phase4-institutional-governance-baseline` into `main` after user review.

### 8.2 Recommended Immediate Next Actions (Phase 4B-7 Scope)
Once this audit report is acknowledged and approved by the user, execute the following technical remediations:

1. **Fix E2E Test Assertion:** Update `backend/tests/test_e2e_pipeline_validation.py` to expect `403` when an unauthorized/test-only dataset is exported for ML training, restoring 100% test pass rate (298/298).
2. **Apply Database Migration:** Execute `python -m alembic upgrade head` to bring `backend/propval.db` in synchronization with revision `e2f34a5b6c7d`.
3. **Remediate Governance Dashboard Labeling (GOV-01):** Update `formula_description` in `backend/app/api/v1/endpoints/governance.py` and `ModelGovernanceView.tsx` from "harmonic aggregate" to "PropVal AI Internal Institutional Data Quality Index (Weighted Arithmetic Mean)".
4. **Remediate Zero Edge-Case Quality Score (GOV-02):** Update `get_governance_metrics` to return `0.0%` or `"NO_DATA"` when zero records exist in the database.
5. **Create & Switch to Clean Development Branch:** Commit the baseline under explicit user authorization.
6. **Proceed to Phase 4B-7 Final Verification.**

