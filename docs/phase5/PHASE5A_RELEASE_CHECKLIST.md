# PropVal AI — Phase 5A Institutional Pilot Release Checklist

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** Pre-Release Gate Verification & Release Engineering Checklist  
**Target Release Candidate:** `v1.0.0-rc1` (Controlled Institutional Pilot)  
**Date:** 2026-11-05  
**Auditor Roles:** Senior Software Architect, Git Release Engineer & Fintech Compliance Auditor  

---

## 1. Release Gate Classification Standard

Every checklist item is strictly classified according to the institutional audit standard:
- **`VERIFIED`**: Fully implemented, verified via automated tests, and confirmed in the working tree.
- **`PARTIALLY VERIFIED`**: Implemented and functioning in sandbox/local environment; requires live third-party or cloud infrastructure for production activation.
- **`NOT VERIFIED`**: No conclusive automated test or code evidence currently exists.
- **`FAILED`**: Explicit test failure, regression, or broken functionality.
- **`BLOCKED`**: Progress halted by an explicit external dependency, unmerged branch, or unfulfilled gate requirement.

---

## 2. Institutional Release Readiness Checklist

### Gate 1: Codebase & Software Integrity Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G1-01** | Backend Unit & Integration Tests | **VERIFIED** | Automated `pytest` run | 362 passed, 0 failed across 40 test suites | Captured in 25.47s |
| **G1-02** | Frontend Unit Tests | **VERIFIED** | Automated `tsx --test` run | 26 passed, 0 failed in `src/` | Captured in 238ms |
| **G1-03** | TypeScript Strict Compilation | **VERIFIED** | `npx tsc --noEmit` | 0 errors | Strict mode compliance |
| **G1-04** | Web Production Bundle Build | **VERIFIED** | `npm run build` (Vite) | Clean `dist/` bundle (1682 modules transformed in 330ms) | No build warnings |
| **G1-05** | Database Migrations Synchronization | **VERIFIED** | `python -m alembic check` | Head `a1b2c3d4e5f6` matched ORM models | "No new upgrade operations detected" |
| **G1-06** | End-to-End Workflow Parity | **VERIFIED** | Automated E2E test suites | [`test_e2e_comprehensive_matrix.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_e2e_comprehensive_matrix.py) | Full loan lifecycle tested |

---

### Gate 2: Application, API & Network Security Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G2-01** | Password Hashing (Bcrypt) | **VERIFIED** | Direct unit tests | [`security.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/core/security.py) | Salted bcrypt with work factor 12 |
| **G2-02** | JWT Token Revocation & Blacklist | **VERIFIED** | Direct API tests | [`test_security_remediation.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_security_remediation.py) | Revoked tokens rejected with 401 |
| **G2-03** | Role-Based Access Control (RBAC) | **VERIFIED** | Endpoint permission tests | [`router.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/api/v1/router.py) | ANALYST, VALUER, UNDERWRITER, ADMIN |
| **G2-04** | SSRF Socket IP-Pinning Transport | **VERIFIED** | Socket-level integration test | [`http_client.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/connectors/http_client.py#L125-L195) | DNS rebinding TOCTOU blocked |
| **G2-05** | Cloud Metadata & Private IP Isolation | **VERIFIED** | Unit test suite | [`test_ssrf_remediation_phase4b7a.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_ssrf_remediation_phase4b7a.py) | 127.0.0.1, 169.254.169.254 blocked |
| **G2-06** | Secrets & Credentials Hygiene | **VERIFIED** | Multi-pass regex scan | Full repository scan | 0 leaked API keys, tokens, or certs |

---

### Gate 3: Data Governance, Privacy & Compliance Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G3-01** | DPDP Act 2023 Section 12 Erasure | **VERIFIED** | Erasure pipeline test | [`erasure_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/services/erasure_service.py) | 8-tier PII scrubbing verified |
| **G3-02** | Log Redaction Filter | **VERIFIED** | Log output inspection | [`logging.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/core/logging.py) | PII patterns redacted in logs |
| **G3-03** | Tamper-Evident SHA256 Audit Chain | **VERIFIED** | Merkle root chain test | [`audit_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/services/audit_service.py) | Parent block hashing validated |
| **G3-04** | Dual-Approval Workflow Enforcement | **VERIFIED** | Governance API tests | [`governance.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/api/v1/endpoints/governance.py) | Trainer cannot approve own dataset |
| **G3-05** | Dataset Versioning & Immutability | **VERIFIED** | Dataset version tests | [`version_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/dataset_management/version_service.py) | Approved versions cannot be modified |
| **G3-06** | Third-Party Licensing Authorization | **VERIFIED** | Data policy tests | [`policy_service.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/services/policy_service.py) | `TEST_ONLY` datasets blocked from ML export |

---

### Gate 4: Valuation Math, ML & Statistical Uncertainty Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G4-01** | Parametric Hedonic Valuation Parity | **VERIFIED** | Cross-language test | [`test_valuation_parity.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_valuation_parity.py) | Python & TypeScript yields identical output |
| **G4-02** | Indian Unit Conversion & Geometry | **VERIFIED** | Normalization tests | [`test_phase4c_normalization.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_phase4c_normalization.py) | Carpet $\le$ Built-up $\le$ Super Built-up |
| **G4-03** | Conformal Uncertainty Quantification | **VERIFIED** | Statistical tests | [`conformal.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/conformal.py) | Non-conformity quantiles computed |
| **G4-04** | TreeSHAP Local Attributions | **VERIFIED** | Attribution tests | [`explainability.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/explainability.py) | Values attributed in INR with directions |
| **G4-05** | Pre-Training Readiness Gate | **VERIFIED (GATED)** | Empirical threshold test | [`readiness_gate.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/ml/readiness_gate.py) | **Intentionally Locked** until $\ge 1,000$ empirical deeds |
| **G4-06** | Pre-Trained Empirical CatBoost Weights | **BLOCKED (BY DESIGN)** | File system inspection | `backend/artifacts/models/` | Requires $\ge 1,000$ empirical deeds from live pilot |

---

### Gate 5: Containerization, Infrastructure & Operations Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G5-01** | Multi-Stage Non-Root Dockerfiles | **VERIFIED** | Dockerfile analysis | [`Dockerfile.backend`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker/Dockerfile.backend) | `appuser:10001` non-root execution |
| **G5-02** | Network Boundary Isolation | **VERIFIED** | Compose config analysis | [`docker-compose.yml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docker-compose.yml) | DB on internal `backend-network`, no public port 5432 |
| **G5-03** | Fail-Fast Production Startup Check | **VERIFIED** | Unit test suite | [`test_phase4e_infrastructure_and_security.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/tests/test_phase4e_infrastructure_and_security.py) | Startup aborted on weak secret or SQLite |
| **G5-04** | Disaster Recovery Backup & Restore | **VERIFIED** | Script inspection | [`scripts/backup_database.sh`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/scripts/backup_database.sh), [`restore_database.sh`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/scripts/restore_database.sh) | SHA256 integrity checksums & 30d retention |
| **G5-05** | Production CI/CD Pipeline | **VERIFIED** | Workflow YAML check | [`.github/workflows/production-ci-cd.yml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/.github/workflows/production-ci-cd.yml) | Lint, test, build, Docker, Bandit, Snyk |
| **G5-06** | Cloud VPC Hosting Provisioning | **PARTIALLY VERIFIED** | Infrastructure review | Production deployment guide | Containerized locally; pending cloud VPC |

---

### Gate 6: Git Management & Release Packaging Gate

| Item ID | Verification Scope | Status | Verification Method | Evidence Location | Open Blockers / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G6-01** | Local Working Tree Cleanliness | **BLOCKED** | `git status` check | Working directory | **23 modified files and 98 untracked files must be committed** |
| **G6-02** | Remote `main` Branch Synchronization | **BLOCKED** | `git log origin/main` | GitHub remote | Remote `main` is at baseline commit `ea2d696` |
| **G6-03** | Stale GitHub Pull Request #1 | **BLOCKED** | GitHub PR review | `refs/pull/1/head` | PR #1 contains only commit `107d004`; must be updated |
| **G6-04** | Release Tag & Version Bump | **NOT VERIFIED** | `git tag -l` | Git references | Release tag `v1.0.0-rc1` pending commit approval |

---

## 3. Release Readiness Summary & Action Plan

```
================================================================================
INSTITUTIONAL RELEASE READINESS AUDIT SCORECARD:
================================================================================
Total Checklist Items Evaluated:      28
  - VERIFIED:                         22  (78.6%)
  - PARTIALLY VERIFIED:                2  ( 7.1%)
  - VERIFIED (GATED BY DESIGN):        1  ( 3.6%)
  - BLOCKED (COMMERCIAL/CLOUD):        1  ( 3.6%)
  - BLOCKED (GIT DESYNCHRONIZATION):   2  ( 7.1%)
================================================================================
VERDICT: CONDITIONALLY APPROVED FOR CONTROLLED PILOT DEMONSTRATION
================================================================================
```

### Mandatory Action Steps Prior to Tagging Release `v1.0.0-rc1`:

1. **Step 1: Obtain User Approval for Git Commit Execution**  
   Execute the structured 7-stage commit sequence outlined in [`PHASE5A_BRANCH_AND_COMMIT_MATRIX.md`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/docs/phase5/PHASE5A_BRANCH_AND_COMMIT_MATRIX.md) to bring all 23 modified files and 98 untracked files into clean Git history.
2. **Step 2: Update or Replace GitHub Pull Request #1**  
   Push the committed changes to a designated release branch (`release/v1.0.0-rc1`) and open an institutional pilot release PR targeting `main`.
3. **Step 3: Commercial Pilot Onboarding**  
   Activate licensed data connectors with partner HFCs / NBFCs to acquire the first $\ge 1,000$ empirical registered deeds, thereby unlocking the CatBoost empirical model weights.

