# PropVal AI — Phase 7C Deliverable 3
# Production Database Deployment & PostgreSQL Native RLS Report

**Document ID:** `PROPVAL-DOC-PHASE7C-03`  
**Execution Timestamp:** 2026-11-06T11:38:50+05:30  
**Phase:** 7C — Live AWS Institutional Cloud Deployment  
**Author:** Senior PostgreSQL Security Architect & Lead Database Administrator  
**Status:** VALIDATED ON POSTGRESQL 18.6 (AWS RDS PROVISIONING BLOCKED PENDING CREDENTIALS)  

---

## 1. Executive Summary & Database Architecture

The production database architecture for PropVal AI is designed to replace all local development stores (SQLite) with an institutional-grade, multi-tenant relational engine:
- **Engine:** PostgreSQL 16.2 / 18.6 with PostGIS spatial extension.
- **Topology (Target Cloud):** Multi-AZ deployment in `ap-south-1` with synchronous physical replication to a secondary availability zone and cross-region automated backup replication to `ap-south-2` (Hyderabad).
- **Network Isolation:** Private subnets (`10.0.50.0/24`, `10.0.60.0/24`, `10.0.70.0/24`) with `publicly_accessible = false` and zero Internet Gateway route.
- **Envelope Encryption:** Storage volume and automated snapshots encrypted using AWS KMS Customer Managed Key (`propval_cmk`).
- **TLS/SSL Enforcement:** `rds.force_ssl = 1` parameter group rejects unencrypted plaintext connections.
- **Tenant Isolation:** PostgreSQL Native Row-Level Security (`FORCE ROW LEVEL SECURITY`) enforced at the database kernel level across all multi-tenant tables.

---

## 2. PostgreSQL Native Row-Level Security (RLS) Policy Audit

Tenant isolation cannot rely solely on application-layer `WHERE` clauses or FastAPI dependencies. In Phase 6D and Phase 7B, database-native RLS policies were implemented, forced, and verified.

### 2.1 Enforced Database Entities & Policies:
```sql
-- 1. Enable and Force RLS on all institutional tables
ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE institutions FORCE ROW LEVEL SECURITY;

ALTER TABLE institution_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE institution_policies FORCE ROW LEVEL SECURITY;

ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties FORCE ROW LEVEL SECURITY;

ALTER TABLE valuation_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE valuation_cases FORCE ROW LEVEL SECURITY;

ALTER TABLE valuation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE valuation_results FORCE ROW LEVEL SECURITY;

ALTER TABLE ai_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_audit_logs FORCE ROW LEVEL SECURITY;

ALTER TABLE erasure_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE erasure_requests FORCE ROW LEVEL SECURITY;

-- 2. Tenant Isolation Policy Template (Example: valuation_cases)
CREATE POLICY valuation_cases_tenant_isolation ON valuation_cases
AS RESTRICTIVE
USING (
    current_setting('app.current_tenant_id', true) = 'SUPERADMIN'
    OR institution_id = current_setting('app.current_tenant_id', true)
)
WITH CHECK (
    current_setting('app.current_tenant_id', true) = 'SUPERADMIN'
    OR institution_id = current_setting('app.current_tenant_id', true)
);

-- 3. Subquery Isolation for Tables without Direct Tenant Column (Example: ai_audit_logs)
CREATE POLICY ai_audit_logs_tenant_isolation ON ai_audit_logs
AS RESTRICTIVE
USING (
    current_setting('app.current_tenant_id', true) = 'SUPERADMIN'
    OR case_id IN (
        SELECT id FROM valuation_cases 
        WHERE institution_id = current_setting('app.current_tenant_id', true)
    )
);
```

### 2.2 Operational Verification on Live PostgreSQL 18.6
The schema initialization script (`backend/scripts/init_pg_schema.py`) and dedicated penetration test suite (`backend/tests/test_postgresql_native_rls_phase6d.py`) were executed against PostgreSQL 18.6 running in Ubuntu WSL (`172.17.163.225:5432`):

```
Connecting to PostgreSQL at postgresql+psycopg2://propval_user:***@172.17.163.225:5432/propval_test...
Recreating public schema and all tables from SQLAlchemy Base metadata...
Tables created successfully!
Application role 'propval_app_user' configured with NOBYPASSRLS!
PostgreSQL RLS Policies successfully enabled and forced across all tenant tables!
```

### 2.3 Automated RLS Penetration Test Results:
All 10 penetration test scenarios passed with 100% compliance:
1. `test_institution_a_accesses_own_data`: **PASS** (Institution A selects own valuation records).
2. `test_institution_b_accesses_own_data`: **PASS** (Institution B selects own valuation records).
3. `test_institution_a_cannot_access_institution_b_data`: **PASS** (Tenant A queries return 0 rows for Tenant B data).
4. `test_missing_tenant_context_fails_closed`: **PASS** (Queries without `app.current_tenant_id` return 0 rows).
5. `test_invalid_tenant_context_injection_rejected`: **PASS** (SQL injection in tenant session variable rejected).
6. `test_cross_tenant_insert_blocked_by_rls`: **PASS** (Attempted cross-tenant `INSERT` throws policy violation).
7. `test_cross_tenant_update_blocked`: **PASS** (Attempted cross-tenant `UPDATE` updates 0 rows).
8. `test_cross_tenant_delete_blocked`: **PASS** (Attempted cross-tenant `DELETE` deletes 0 rows).
9. `test_connection_pool_tenant_context_isolation`: **PASS** (Context reset verified across pooled connections).
10. `test_platform_admin_and_auditor_access`: **PASS** (Superadmin role access verified for compliance oversight).

---

## 3. Production vs. Staged Environment Status Comparison

| Feature / Control | Staged IaC Specification | Operational PostgreSQL 18.6 (Local) | AWS RDS Production (Cloud) |
| :--- | :--- | :--- | :--- |
| **Engine Version** | PostgreSQL 16.2 / PostGIS | PostgreSQL 18.6 / PostGIS | Staged (`main.tf`) |
| **Multi-AZ Replication** | Enabled (Synchronous Standby) | Single Node (WSL) | Staged (`main.tf`) |
| **Continuous PITR Backups** | 30-Day Automated Window | Manual File Snapshots | Staged (`main.tf`) |
| **KMS Envelope Encryption** | `alias/propval-production-cmk` | OS-Level File Protection | Staged (`main.tf`) |
| **SSL / TLS Enforcement** | `rds.force_ssl = 1` | Verified Active | Staged (`main.tf`) |
| **Native Kernel RLS** | Forced across 7 tenant tables | **VERIFIED (10/10 PASS)** | Ready for Migration |
| **Alembic Schema Head** | Migration `d4e5f6a7b8c9` | **HEAD APPLIED CLEANLY** | Ready for Container Job |
| **Live Cloud Provisioning** | Defined in Terraform | N/A | **BLOCKED (CREDENTIALS_PENDING)** |

---

## 4. Database Migration Runbook (For Cloud Deployment)

When AWS RDS PostgreSQL is instantiated:
1. **Automated Migration Hook:** Kubernetes pre-install Job `propval-db-migration` (`infra/k8s/ingress.yaml`) executes:
   ```bash
   alembic -c backend/alembic.ini upgrade head
   ```
2. **PostgreSQL RLS Enablement:** Run initialization script against cloud endpoint:
   ```bash
   DATABASE_URL="postgresql://propval_admin:...@propval-rds-production.c...ap-south-1.rds.amazonaws.com:5432/propval_db" \
   python backend/scripts/init_pg_schema.py
   ```
3. **Connectivity Verification:** Backend readiness probe `/health/ready` validates database connectivity and RLS policy enforcement before receiving production ingress traffic.

