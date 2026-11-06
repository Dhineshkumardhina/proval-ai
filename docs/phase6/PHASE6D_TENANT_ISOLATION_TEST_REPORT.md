# PropVal AI — Phase 6D: PostgreSQL Native Tenant Isolation Test Report

**Document Reference:** `DOC-PHASE6D-TEST-REPORT-001`  
**Phase:** 6D — PostgreSQL Native Row-Level Security Implementation  
**Author:** Senior PostgreSQL Security Architect & Quality Assurance Specialist  
**Test Suite:** `backend/tests/test_postgresql_native_rls_phase6d.py`  
**Database Under Test:** Live PostgreSQL 18.6 (Ubuntu 18.6-0ubuntu0.26.04.1)  
**Connecting Role:** `propval_app_user` (Configured with `NOSUPERUSER NOBYPASSRLS`)  
**Test Result:** **10 / 10 PASSED (100% SUCCESS RATE)**  
**Date:** November 5, 2026  

---

## 1. Executive Summary & Verification Mandate

The Phase 6D mandate explicitly stipulates:
> *"Use a real PostgreSQL test environment. SQLite tests alone are insufficient to prove PostgreSQL RLS. Do not claim native RLS is operational until PostgreSQL integration tests pass."*

A live PostgreSQL 18.6 database environment was initialized and configured with native Row-Level Security (RLS) policies, transaction-scoped session variable management, and the dedicated unprivileged database role `propval_app_user`.

### Test Execution Summary
- **Total Test Cases:** 10
- **Passed:** **10**
- **Failed:** **0**
- **Execution Time:** 5.41 seconds
- **Database Engine Verified:** PostgreSQL 18.6 on x86_64, `psycopg2-binary 2.9.13`
- **Result:** **PostgreSQL Native Row-Level Security is verified as OPERATIONAL.**

---

## 2. Test Execution Matrix (10 Mandated Test Cases)

```
┌────┬────────────────────────────────────────────────────┬──────────────────────────────────────────┬────────┐
│ #  │ Test Scenario Description                          │ PostgreSQL Verification Mechanism        │ Status │
├────┼────────────────────────────────────────────────────┼──────────────────────────────────────────┼────────┤
│ 1  │ Institution A Accessing Own Data                   │ SELECT & INSERT with HDFC context        │ PASSED │
│ 2  │ Institution B Accessing Own Data                   │ SELECT & INSERT with ICICI context       │ PASSED │
│ 3  │ Institution A Accessing Institution B Data         │ Zero rows returned (Complete Blindness)  │ PASSED │
│ 4  │ Missing Tenant Context (Fail-Closed)               │ Zero rows returned when context is unset │ PASSED │
│ 5  │ Invalid / Malformed Tenant Context (Anti-SQLi)     │ Regex intercepts injection payloads      │ PASSED │
│ 6  │ Cross-Tenant INSERT Attempts                       │ WITH CHECK policy throws RLS violation   │ PASSED │
│ 7  │ Cross-Tenant UPDATE Attempts                       │ Zero rows updated                        │ PASSED │
│ 8  │ Cross-Tenant DELETE Attempts                       │ Zero rows deleted                        │ PASSED │
│ 9  │ Connection Pool Tenant-Context Isolation           │ Recycled connection returns 0 rows       │ PASSED │
│ 10 │ Privileged Admin & Compliance Auditor Roles        │ Admin sees all; Auditor sees audit logs  │ PASSED │
└────┴────────────────────────────────────────────────────┴──────────────────────────────────────────┴────────┘
```

---

## 3. Detailed Test Case Audit Evidence

### Test 1: Institution A Accessing Own Data
- **Function:** `test_institution_a_accesses_own_data`
- **Input:** `set_config('app.current_tenant_id', 'INST_A_HDFC', true)`
- **Action:** Created property `APP-HDFC-001` and valuation case for borrower "Ramesh Kumar (HDFC)".
- **Observation:** Querying `valuation_cases` returned exactly 1 record matching the created case.
- **Verdict:** **PASSED**

### Test 2: Institution B Accessing Own Data
- **Function:** `test_institution_b_accesses_own_data`
- **Input:** `set_config('app.current_tenant_id', 'INST_B_ICICI', true)`
- **Action:** Created property `APP-ICICI-001` and valuation case for borrower "Priya Sharma (ICICI)".
- **Observation:** Querying `valuation_cases` returned exactly 1 record matching the created case.
- **Verdict:** **PASSED**

### Test 3: Institution A Attempting to Access Institution B Data
- **Function:** `test_institution_a_cannot_access_institution_b_data`
- **Input:** Tenant context set to `'INST_A_HDFC'`.
- **Action:** Executed:
  ```sql
  SELECT * FROM valuation_cases WHERE institution_id = 'INST_B_ICICI';
  SELECT * FROM valuation_cases WHERE borrower_name ILIKE '%ICICI%';
  ```
- **Observation:** Returned **0 rows**. Even when explicit primary keys or SQL filters target Institution B's rows, PostgreSQL's query rewriter filters them out at the database kernel level before returning results to Python.
- **Verdict:** **PASSED**

### Test 4: Missing Tenant Context Fails Closed
- **Function:** `test_missing_tenant_context_fails_closed`
- **Input:** `reset_db_tenant_context()` (empty string / unset session variable).
- **Action:** Executed `SELECT * FROM valuation_cases;` and `SELECT * FROM institution_policies;`.
- **Observation:** Returned **0 rows**. Because `NULLIF(current_setting('app.current_tenant_id', true), '')` evaluates to `NULL`, the RLS predicate evaluates to falsy, guaranteeing that unauthenticated queries fail closed.
- **Verdict:** **PASSED**

### Test 5: Invalid / Malformed Tenant Context Protection
- **Function:** `test_invalid_tenant_context_injection_rejected`
- **Input Payloads Tested:**
  - `' OR '1'='1`
  - `INST_A'; DROP TABLE valuation_cases; --`
  - `INST_A' UNION SELECT * FROM users --`
  - `../../etc/passwd`
  - `INST_A\x00NULL`
- **Observation:** The `validate_tenant_id()` pre-validation regex (`^[a-zA-Z0-9_-]{1,64}$`) immediately threw `ValueError: Invalid tenant_id format`, preventing malformed input from ever reaching PostgreSQL parameter evaluation.
- **Verdict:** **PASSED**

### Test 6: Cross-Tenant INSERT Attempts Blocked
- **Function:** `test_cross_tenant_insert_blocked_by_rls`
- **Context:** Tenant set to `'INST_A_HDFC'`.
- **Action:** Attempted to insert a row into `valuation_cases` with `institution_id = 'INST_B_ICICI'`.
- **Observation:** PostgreSQL intercepted the write and raised an immediate exception:
  ```
  psycopg2.errors.InsufficientPrivilege: new row violates row-level security policy for table "valuation_cases"
  ```
- **Verdict:** **PASSED (Blocked by WITH CHECK Clause)**

### Test 7: Cross-Tenant UPDATE Attempts Blocked
- **Function:** `test_cross_tenant_update_blocked`
- **Context:** Tenant set to `'INST_A_HDFC'`.
- **Action:** Executed `UPDATE valuation_cases SET loan_requested = 1.0 WHERE institution_id = 'INST_B_ICICI'`.
- **Observation:** Exactly **0 rows updated**. Institution B's loan amounts remained completely unaltered.
- **Verdict:** **PASSED**

### Test 8: Cross-Tenant DELETE Attempts Blocked
- **Function:** `test_cross_tenant_delete_blocked`
- **Context:** Tenant set to `'INST_A_HDFC'`.
- **Action:** Executed `DELETE FROM valuation_cases WHERE institution_id = 'INST_B_ICICI'`.
- **Observation:** Exactly **0 rows deleted**. Institution B's rows were neither read nor deleted.
- **Verdict:** **PASSED**

### Test 9: Connection Pool Tenant-Context Isolation
- **Function:** `test_connection_pool_tenant_context_isolation`
- **Simulation:**
  1. Transaction 1 checked out connection, set tenant context to `INST_A_HDFC`, queried records, committed, and closed session (returning connection to pool).
  2. Transaction 2 checked out the recycled connection from the pool without setting any tenant context.
- **Observation:** Transaction 2 returned **0 rows**. Proves that `set_config('parameter', value, is_local=true)` automatically discards session parameters upon transaction termination, eliminating connection pool cross-contamination.
- **Verdict:** **PASSED**

### Test 10: Privileged Admin & Compliance Auditor Roles
- **Function:** `test_platform_admin_and_auditor_access`
- **Observations:**
  1. Setting `app.is_platform_admin = 'true'` permitted the global administrator to inspect cases across both `INST_A_HDFC` and `INST_B_ICICI`.
  2. Setting `app.is_compliance_auditor = 'true'` permitted the auditor to inspect audit ledger entries (`audit_events`) across all institutions, while queries against sensitive borrower cases (`valuation_cases`) returned **0 rows**, strictly enforcing duty separation.
- **Verdict:** **PASSED**

---

## 4. Pytest Execution Output (Direct CLI Log)

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\PROJECTS\dhina projects\proval ai\proval-ai
plugins: anyio-4.15.1, locust-2.47.0, platformdirs-4.13.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 10 items

backend/tests/test_postgresql_native_rls_phase6d.py::test_institution_a_accesses_own_data PASSED [ 10%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_institution_b_accesses_own_data PASSED [ 20%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_institution_a_cannot_access_institution_b_data PASSED [ 30%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_missing_tenant_context_fails_closed PASSED [ 40%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_invalid_tenant_context_injection_rejected PASSED [ 50%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_cross_tenant_insert_blocked_by_rls PASSED [ 60%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_cross_tenant_update_blocked PASSED [ 70%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_cross_tenant_delete_blocked PASSED [ 80%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_connection_pool_tenant_context_isolation PASSED [ 90%]
backend/tests/test_postgresql_native_rls_phase6d.py::test_platform_admin_and_auditor_access PASSED [100%]

============================= 10 passed in 5.41s ==============================
```

---

## 5. Security & Verification Certification

I hereby certify that database-native Row-Level Security has been implemented and tested against a real, operational PostgreSQL 18.6 instance. All 10 mandatory multi-tenant isolation scenarios have succeeded without exception.

