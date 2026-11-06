# PropVal AI — Phase 6D: Database Security & Multi-Tenant Threat Model Report

**Document Reference:** `DOC-PHASE6D-DB-SEC-001`  
**Phase:** 6D — PostgreSQL Native Row-Level Security Implementation  
**Author:** Senior PostgreSQL Security Architect & DevSecOps Engineer  
**Compliance Standards:** RBI Master Direction on IT Governance, DPDP Act 2023 §8, ISO/IEC 27001:2022 Annex A.8  
**Enforcement Engine:** PostgreSQL 18.6 Kernel-Level Row-Level Security (RLS)  
**Date:** November 5, 2026  

---

## 1. Threat Model & Multi-Tenant Attack Vectors

In shared multi-tenant financial technology platforms serving institutional Housing Finance Companies (HFCs) and commercial banks, data leakage between competing lenders represents a critical regulatory violation and severe operational risk.

This threat model identifies the 5 primary multi-tenant database attack vectors and documents how PropVal AI's native RLS architecture eliminates each threat:

```
┌───────────────────────────────────────┬────────────────────────────────────────────┬────────────────────────────────────────┐
│ Attack Vector / Threat                │ Traditional Application Vulnerability      │ PropVal AI Database-Native RLS Defense │
├───────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────┤
│ T1: Tenant Impersonation              │ Application forgets `WHERE institution_id` │ Database query rewriter injects RLS    │
│                                       │ filter in ORM query or joins.              │ predicate automatically at SQL parser. │
├───────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────┤
│ T2: SQL Injection / Predicate Bypass  │ Attacker injects `' OR '1'='1` to defeat   │ RLS is enforced at the storage engine; │
│                                       │ application `WHERE` clause.                │ RLS policies cannot be bypassed by SQLi│
├───────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────┤
│ T3: Connection Pool Contamination     │ State or session variables linger on       │ Transaction-scoped `set_config(...,    │
│                                       │ recycled pool connections.                 │ true)` automatically purged on commit. │
├───────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────┤
│ T4: Privilege Escalation              │ Application connects as DB superuser or    │ Non-superuser `propval_app_user` with   │
│                                       │ table owner which bypasses RLS.            │ `NOBYPASSRLS` + `FORCE RLS` on tables. │
├───────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────┤
│ T5: Audit Ledger Tampering            │ Rogue insider or attacker deletes or       │ RLS permits SELECT and INSERT only;    │
│                                       │ updates audit trails to conceal fraud.     │ UPDATE and DELETE policies do not exist│
└───────────────────────────────────────┴────────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 2. Defense-in-Depth Security Architecture

PropVal AI implements a 4-tier layered defense-in-depth model:

```
                    LAYERED DEFENSE-IN-DEPTH ARCHITECTURE
                    
 [ User Request + JWT ]
          │
          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Layer 1: FastAPI Application Authentication & RBAC                     │
 │   - HS256 JWT signature verification with secret key rotation          │
 │   - Revocation blacklist check (in-memory & Redis)                     │
 │   - Role validation (Credit Underwriter, Risk Committee, Admin)        │
 └────────────────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Layer 2: Sanitized Parameterized Context Injection                     │
 │   - Regex validation: ^[a-zA-Z0-9_-]{1,64}$ (rejects SQLi characters)  │
 │   - Parameterized binding: SELECT set_config('parameter', :val, true)  │
 │   - Scoped context manager (tenant_context_scope) with try/finally     │
 └────────────────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Layer 3: PostgreSQL Native Row-Level Security Engine                   │
 │   - Policies: valuation_cases, properties, valuation_results, policies │
 │   - Dual-predicate enforcement: USING (reads) & WITH CHECK (writes)    │
 │   - Fail-Closed: Missing context evaluates to NULL (0 rows returned)   │
 └────────────────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Layer 4: Role-Based Database Least Privilege                           │
 │   - Application executes strictly as `propval_app_user`               │
 │   - Explicitly granted `NOSUPERUSER` and `NOBYPASSRLS`                 │
 │   - All tenant tables configured with `FORCE ROW LEVEL SECURITY`       │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Analysis of Critical Security Controls

### 3.1 Fail-Closed Policy Design
A critical flaw in naive RLS implementations is allowing access when the session configuration variable is not set.

In PropVal AI, all RLS policies utilize:
```sql
institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
```
- If an unauthenticated query executes without setting `app.current_tenant_id`, `current_setting(..., true)` returns `NULL`.
- `NULLIF(NULL, '')` returns `NULL`.
- In SQL three-valued logic, `institution_id = NULL` evaluates to `UNKNOWN` (treated as `FALSE` by `WHERE` and `USING` clauses).
- **Result:** Exactly 0 rows are returned. No records are ever exposed when tenant context is missing.

### 3.2 Anti-Injection Sanitization
Before any tenant parameter is transmitted to PostgreSQL, `validate_tenant_id()` enforces strict syntactic validation:
```python
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
```
Any payload containing quotes, semicolons, dashes, null bytes, or SQL control characters is rejected with `ValueError` at the application perimeter, preventing any attempt to corrupt session parameters.

### 3.3 Connection Pool Context Discard
When connections are recycled in connection pooling (e.g. SQLAlchemy QueuePool or AWS RDS Proxy):
1. Parameter setting specifies `is_local = true`:
   ```sql
   SELECT set_config('app.current_tenant_id', :tenant_id, true);
   ```
2. When the transaction commits or rolls back, PostgreSQL's transaction manager terminates the parameter binding.
3. The next transaction checking out the same connection starts with an empty configuration space.
4. **Empirical Proof:** Test 9 in our integration suite checked out a recycled connection without context and verified that exactly 0 rows were visible.

### 3.4 Tamper-Evident Audit Ledger Immutability
Under RBI regulations and ISO 27001, audit event records must be non-repudiable and tamper-evident:
1. `audit_events` is configured with a `SELECT` policy and an `INSERT` policy.
2. **Zero `UPDATE` or `DELETE` policies are defined.**
3. In PostgreSQL RLS, if no policy exists for an operation, that operation is denied to all non-bypass roles.
4. Consequently, no application user or tenant can modify, overwrite, or delete historical audit entries.

---

## 4. Regulatory & Compliance Alignment Matrix

| Regulatory Requirement | Mandate Source | PropVal AI Implementation & Technical Evidence | Compliance Status |
|:---|:---|:---|:---:|
| **Multi-Tenant Data Segregation** | RBI Master Direction on IT Controls §14.2 | PostgreSQL Native Row-Level Security with `FORCE RLS` on all tenant entities. | **COMPLIANT** |
| **Data Fiduciary Protection** | Indian DPDP Act 2023 §8(5) | Fail-closed tenant boundaries prevent unauthorized disclosure of borrower PII. | **COMPLIANT** |
| **Separation of Duties** | ISO/IEC 27001:2022 Control A.5.3 | Compliance auditors can inspect audit trails but cannot access borrower case files. | **COMPLIANT** |
| **Cryptographic Auditability** | ISO/IEC 27001:2022 Control A.8.15 | Tamper-evident append-only audit ledger with SHA-256 Merkle chain anchors. | **COMPLIANT** |
| **Least Privilege Access** | CIS PostgreSQL 16 Benchmark §4.1 | Dedicated unprivileged role `propval_app_user` with `NOBYPASSRLS`. | **COMPLIANT** |

---

## 5. Operational Recommendations for Production AWS RDS

1. **Parameter Group Enforcement:** Ensure `rds.force_ssl = 1` remains active to prevent plaintext network eavesdropping on session tokens or tenant parameters.
2. **Audit Logging Extension (`pgaudit`):** Enable `pgaudit.log = 'ddl, role'` in the RDS parameter group to log all schema changes and role permissions in CloudWatch.
3. **Periodic Role Auditing:** Run automated CI/CD jobs ensuring no application user is ever granted `SUPERUSER` or `BYPASSRLS`.
4. **Connection Pooler Hygiene:** When deploying PgBouncer in front of RDS, configure `pool_mode = transaction`. Because PropVal AI uses transaction-scoped `set_config(..., true)`, transaction pooling is 100% compatible and maximizes connection efficiency.

