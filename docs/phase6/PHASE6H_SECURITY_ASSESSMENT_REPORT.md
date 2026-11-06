# PropVal AI — Phase 6H: Security Assessment & VAPT Scope Specification

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6H — Independent External Security Assessment & Final Production Readiness Audit  
**Date:** 2026-11-06  
**Author:** Principal Cybersecurity Assessor, Penetration Testing Specialist & DevSecOps Lead  
**Assessment Standard:** OWASP Top 10 (2021), OWASP API Security Top 10 (2023), RBI Cyber Security Framework  
**External Certification Status:** **INTERNAL ASSESSMENT COMPLETED — PENDING FORMAL CERT-IN EMPANELLED AUDIT**

---

## 1. Important Regulatory Disclosure Regarding CERT-In

> [!IMPORTANT]
> In strict compliance with regulatory standards (*"Do not claim CERT-In empanelled VAPT certification unless a genuine qualified external assessor has performed and issued the assessment"*):
> 
> This document specifies the comprehensive internal security evaluation, vulnerability assessment, and the **formal external VAPT engagement specification**. Formal CERT-In empanelled certification has **not** yet been issued. An external assessment by a recognized CERT-In empanelled cybersecurity auditing firm must be commissioned before full commercial general-availability release.

---

## 2. Vulnerability Assessment Across Key Security Vectors

### 2.1 OWASP API Security Top 10 Evaluation

| OWASP API Risk | PropVal AI Defense Implementation | Verification Evidence | Assessment Status |
|:---|:---|:---|:---:|
| **API1: Broken Object Level Authorization (BOLA)** | Database-native PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY`) on all tenant entities. | Cross-tenant access attempts return 0 rows (`test_institution_a_cannot_access_institution_b_data`). | **VERIFIED HARDENED** |
| **API2: Broken Authentication** | Cryptographic JWT tokens (`HS256`, 480 min expiry), bcrypt password hashing (work factor 12). | Invalid/corrupted tokens rejected with HTTP 401 (`test_invalid_credential_fails_gracefully`). | **VERIFIED HARDENED** |
| **API3: Broken Object Property Level Authorization** | Pydantic strict schemas with field validation; sensitive internal fields stripped from responses. | PII redactor scrubs Aadhaar/PAN before serialization. | **VERIFIED HARDENED** |
| **API4: Unrestricted Resource Consumption** | SlowAPI rate limiting: global 120 req/min, auth 20 req/min. File upload ceiling: 25 MB. | Uploads exceeding max size rejected with HTTP 413 (`test_upload_exceeding_max_size_rejected`). | **VERIFIED HARDENED** |
| **API5: Broken Function Level Authorization (BFLA)** | Strict RBAC dependency (`require_role("ADMIN")`). Non-admin users cannot perform case deletions or institutional policy modifications. | Cross-role privilege escalation blocked (`test_rbac_case_deletion_admin_only_and_audit_logged`). | **VERIFIED HARDENED** |
| **API6: Server-Side Request Forgery (SSRF)** | Outbound IP validator blocks RFC 1918 private subnets, loopback `127.0.0.1`, link-local `169.254.169.254`, and DNS rebinding. | SSRF test suite verified 100% blocked (`test_ssrf_remediation_phase4b7a.py`). | **VERIFIED HARDENED** |
| **API7: Security Misconfiguration** | OWASP HTTP security headers (`nosniff`, `DENY`, `HSTS`, `CSP`). Strict CORS allowlist with wildcard `*` prohibited in production. | Middleware pipeline verified (`test_security_remediation.py`). | **VERIFIED HARDENED** |
| **API8: Lack of Protection from Automated Threats** | Rate limiting, timing-safe credential comparisons, circuit breakers on external connectors. | Brute force attempts throttled. | **VERIFIED HARDENED** |
| **API9: Improper Inventory Management** | Centralized FastAPI router with explicit API versioning (`/api/v1`). Deprecated routes disabled. | Verified via OpenAPI `/docs` inspection. | **VERIFIED HARDENED** |
| **API10: Unsafe Consumption of APIs** | Strict timeout limits (3.0s), response schema validation, and fail-closed circuit breakers for third-party providers. | Verified via connector mock tests (`test_provider_integration_phase6a.py`). | **VERIFIED HARDENED** |

---

## 3. SQL Injection & Database Native RLS Verification

### 3.1 Parameterized Queries & ORM Protections
* SQLAlchemy 2.1.3 eliminates SQL injection vulnerabilities through parameterized statement compilation.
* Direct string concatenation in SQL statements is strictly barred across the entire codebase.

### 3.2 Row-Level Security Policy Review
Policies defined in `backend/alembic/versions/c3d4e5f6a7b8_phase6d_postgresql_native_rls.py`:
```sql
CREATE POLICY tenant_isolation_policy ON valuation_cases
  FOR ALL
  TO propval_app_user
  USING (
    current_setting('app.is_platform_admin', true) = 'true'
    OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
  )
  WITH CHECK (
    current_setting('app.is_platform_admin', true) = 'true'
    OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
  );
```
* **Kernel Enforcement:** Evaluated inside PostgreSQL's query execution engine.
* **Fail-Closed Semantics:** When `app.current_tenant_id` is unset or empty, `NULLIF` evaluates to `NULL`. The comparison `institution_id = NULL` evaluates to `UNKNOWN` under SQL three-valued logic, returning 0 rows.
* **Connection Pool Hygiene:** `set_config('app.current_tenant_id', :id, true)` ties the context strictly to the transaction boundary. Upon transaction commit or rollback, the parameter is immediately cleared.

---

## 4. Container & Cloud Infrastructure Security Audit

### 4.1 Container Hardening
* Base image: Python 3.14 slim.
* Execution user: Non-root `appuser:appgroup` (`uid 10001:10001`).
* Filesystem: Root filesystem mounted as read-only (`readOnlyRootFilesystem: true`).
* Capabilities: `securityContext.capabilities.drop: ["ALL"]`.
* Privilege Escalation: `allowPrivilegeEscalation: false`.

### 4.2 Kubernetes Manifests
* 9 manifests audited and validated via `infra/validate_infra.py`.
* Network policies restrict pod-to-pod communication: backend only accepts traffic from frontend and ingress controller; database is unreachable from frontend pods.
* Secrets injected dynamically via AWS Secrets Manager CSI driver (`secrets-provider-class.yaml`).

---

## 5. Scope Specification for External CERT-In VAPT Engagement

To facilitate seamless commissioning of the external penetration testing engagement, the following scope package is established:

```
TARGET ASSETS FOR EXTERNAL VAPT:
1. Web Application: https://portal.propval.internal (React 18 SPA)
2. API Gateway:     https://api.propval.internal/api/v1 (FastAPI)
3. Ingress ALB:     AWS Application Load Balancer (TLS 1.3 / Port 443)
4. Network Scope:   VPC Public and Private Subnets (10.0.0.0/16)
5. Tenant Contexts: Institution A (HFC Alpha) vs Institution B (HFC Beta)

METHODOLOGY REQUIREMENTS:
- Black-Box External Penetration Testing.
- Gray-Box Multi-Tenant Isolation Testing (Attempting cross-tenant BOLA / RLS bypass).
- Authenticated Role-Based Privilege Escalation Testing (Valuer -> Admin).
- SSRF Fuzzing against SRO/Zapkey connector integration points.
- Cryptographic Review of JWT signing and SHA-256 audit block chain.
```

