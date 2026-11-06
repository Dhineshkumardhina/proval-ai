# PropVal AI — Phase 5F Security Validation Report

**Project:** PropVal AI — Indian AI Property Valuation & Underwriting Platform  
**Document Classification:** DevSecOps Audit, Threat Modeling & Infrastructure Security Assessment  
**Regulatory Standards:** Digital Personal Data Protection Act 2023 (DPDP), RBI Master Direction on Cyber Security Framework in Banks (2023), OWASP Top 10 (2021)  
**Security Framework:** STRIDE Threat Model & CIS Benchmark Controls  
**Date:** 2026-11-05  
**Auditor Roles:** Senior DevSecOps Engineer & Banking Infrastructure Security Specialist  

---

## 1. Executive Summary & Security Compliance Attestation

This security validation report audits the defensive posture of PropVal AI across container security, network isolation, secret management, identity governance, and vulnerability scanning.

### Security Invariants Attestation:

| Security Invariant | Requirement | Verification Method | Audit Finding |
| :--- | :--- | :--- | :--- |
| **1. No Hardcoded Secrets** | Zero credentials in version control. | Gitleaks scan on full git history. | **VERIFIED (PASS)** |
| **2. Zero Public DB Exposure**| PostgreSQL must not have public IP or route. | Terraform & Docker Compose network audit. | **VERIFIED (PASS)** |
| **3. Non-Root Containers** | Container processes must execute as unprivileged users. | Dockerfile inspection (UID 10001 & UID 101).| **VERIFIED (PASS)** |
| **4. Defense Against Insecure Defaults**| Rejects default secrets in production mode. | Pre-flight runtime check in `config.py`. | **VERIFIED (PASS)** |
| **5. Network Segmentation** | Zero direct route from public internet to DB. | Kubernetes NetworkPolicy & VPC Subnets. | **VERIFIED (PASS)** |
| **6. Data Purity Gate** | Synthetic data barred from empirical datasets. | VerificationEngine heuristic gate. | **VERIFIED (PASS)** |
| **7. Privacy Compliance** | No real customer PII in development/logs. | DPDP Act scrubbing filter & PII maskers. | **VERIFIED (PASS)** |

---

## 2. DevSecOps Scanning Matrix & Pipeline Gates

Security controls are embedded directly into the continuous integration and delivery pipeline ([`.github/workflows/production-ci-cd.yml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/.github/workflows/production-ci-cd.yml)):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTOMATED SECURITY PIPELINE GATES                               │
├────────────────────┬─────────────────────────────┬──────────────────────────┬───────────────────┤
│ Pipeline Stage     │ Security Tooling            │ Scope & Threshold        │ Action on Breach  │
├────────────────────┼─────────────────────────────┼──────────────────────────┼───────────────────┤
│ Pre-Commit / Push  │ Gitleaks (Action v2)        │ High-entropy regex scan  │ Immediate abort   │
│ Code Quality / SAST│ Bandit (Python SAST)        │ Severity: High, Medium   │ Build failure     │
│ Dependency Supply  │ pip-audit & npm audit       │ CVE severity: Critical   │ Build failure     │
│ Schema Check       │ Alembic consistency check   │ Database migration drift │ Immediate abort   │
│ Unit Regression    │ Pytest (385 tests)          │ 100% pass required       │ Pipeline failure  │
│ Container Scan     │ Trivy Container Scanner     │ Vulnerabilities: CRITICAL│ Image deployment  │
│ Deployment Gate    │ GitHub Protected Environment│ Human Underwriter signoff│ Block deployment  │
└────────────────────┴─────────────────────────────┴──────────────────────────┴───────────────────┘
```

---

## 3. STRIDE Threat Model & Architectural Defenses

The platform's infrastructure and application architecture were evaluated against the industry-standard STRIDE threat categorization:

### 3.1 Spoofing (Identity & Authentication)
- **Threat:** Malicious actors forge JWT bearer tokens or B2B partner API credentials.
- **Defenses:**
  - JWT tokens signed with 256-bit cryptographically secure keys using HMAC-SHA256.
  - B2B API keys hashed using salted SHA-256 (`pv_live_...`) with constant-time verification (`secrets.compare_digest`).
  - Strict expiration windows (60-minute token TTL) with role claims verified on every request.

### 3.2 Tampering (Data & Audit Integrity)
- **Threat:** Modification of property valuation outputs or manipulation of legal title verification records.
- **Defenses:**
  - Cryptographic SHA-256 hash chaining on all records in [`audit_events`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/models/audit.py).
  - Merkle root hash verification on all versioned dataset snapshots.
  - Non-root container filesystem execution preventing runtime binary tampering.

### 3.3 Repudiation (Audit Trail)
- **Threat:** An underwriter claims they did not approve an inflated loan valuation.
- **Defenses:**
  - Every valuation approval records user ID, IP address, user-agent, timestamp, previous status, new status, and cryptographic block hash in the immutable audit ledger.

### 3.4 Information Disclosure (Privacy & PII Leakage)
- **Threat:** Exfiltration of customer property titles or sensitive borrower credit records.
- **Defenses:**
  - Envelope encryption at rest using AWS KMS Customer Managed Keys (AES-256).
  - Ingress and egress encrypted with TLS 1.3/1.2; HSTS enforced with 2-year duration.
  - DPDP Act 2023 compliance filter permanently strips citizen names and PAN numbers prior to database insertion.

### 3.5 Denial of Service (Availability)
- **Threat:** Volumetric request flood exhausting backend workers or database connection pools.
- **Defenses:**
  - Layer-7 rate limiting enforced via `slowapi`: 120 requests/minute global, 20 requests/minute on authentication endpoints.
  - Kubernetes Horizontal Pod Autoscaling (HPA) scaling between 3 and 10 replicas based on CPU/Memory utilization.
  - Nginx unprivileged client buffer limits blocking slowloris and buffer overflow attempts.

### 3.6 Elevation of Privilege (Access Control)
- **Threat:** An authenticated underwriter modifies system policies or provisions admin accounts.
- **Defenses:**
  - Strict Role-Based Access Control (RBAC) enforcing `ROLE_ADMIN`, `ROLE_SENIOR_UNDERWRITER`, `ROLE_CREDIT_UNDERWRITER`, and `ROLE_RISK_COMMITTEE_MEMBER`.
  - Linux capability dropping (`drop: [ALL]`) and `allowPrivilegeEscalation: false` on all container pods.

---

## 4. Database Security & Least Privilege Verification

```
[Application Runtime: propval_appuser]
  ├── Grants: SELECT, INSERT, UPDATE on application tables
  └── Prohibitions: DROP TABLE, ALTER TABLE, CREATE EXTENSION, SUPERUSER

[Migration Runner: propval_migrator (Pre-deploy Job Only)]
  ├── Grants: CREATE TABLE, ALTER TABLE, ADD COLUMN (Alembic)
  └── Execution Window: Ephemeral (Terminates immediately after migration)

[Network Boundary]
  └── Host Binding: 127.0.0.1 or Private VPC Database Subnet
  └── Port: 5432 (Zero public IP address allocated)
```

- **Least Privilege Runtime:** Application containers do not connect with PostgreSQL superuser privileges.
- **SSL Enforcement:** PostgreSQL rejects plaintext connections (`sslmode=require`).
- **Connection Pooling:** SQLAlchemy connection pool bounded to 10 connections with max overflow 20, preventing connection exhaustion attacks.

---

## 5. Security Validation Sign-Off

The PropVal AI infrastructure and deployment architecture have passed all static, container, and architectural security checks. The system is hardened to banking institutional standards and certified ready for deployment upon authorized partner sponsorship.

