"""Phase 6D Integration Test Suite: PostgreSQL Native Row-Level Security (RLS).

Executes against a REAL PostgreSQL 18 database with:
- Dedicated unprivileged role `propval_app_user` (NOBYPASSRLS).
- Real PostgreSQL RLS policies enabled and forced.
- Transaction-scoped tenant configuration (`set_config(..., true)`).

Verifies all 10 mandated test cases:
1. Institution A accessing its own data.
2. Institution B accessing its own data.
3. Institution A attempting to access Institution B data.
4. Missing tenant context fails closed (0 rows).
5. Invalid/malformed tenant context injection protection.
6. Cross-tenant INSERT attempts blocked by WITH CHECK policy.
7. Cross-tenant UPDATE attempts blocked.
8. Cross-tenant DELETE attempts blocked.
9. Connection pool tenant-context isolation across sequential transactions.
10. Privileged role and compliance auditor access controls.
"""

import os
import subprocess
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError, InternalError, IntegrityError

from app.core.tenant_context import (
    set_db_tenant_context,
    reset_db_tenant_context,
    tenant_context_scope,
    validate_tenant_id,
)
from app.models.institution import InstitutionModel, InstitutionPolicyModel
from app.models.valuation import ValuationCaseModel, ValuationResultModel
from app.models.property import PropertyRecord
from app.models.audit import AuditEventModel


def get_pg_url(role="propval_app_user", password="app_user_password"):
    """Resolve PostgreSQL connection URL pointing to real WSL or localhost database."""
    try:
        wsl_ip = subprocess.check_output(['wsl', '-e', 'hostname', '-I']).decode().split()[0]
    except Exception:
        wsl_ip = "127.0.0.1"
    return f"postgresql+psycopg2://{role}:{password}@{wsl_ip}:5432/propval_test"


@pytest.fixture(scope="module")
def pg_engine():
    """Module-level engine connected as unprivileged application user."""
    url = get_pg_url()
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def admin_engine():
    """Engine connected as superuser for setup and tear-down."""
    url = get_pg_url(role="propval_user", password="propval_password")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def setup_tenants(admin_engine):
    """Seed base institutions using superuser connection."""
    with admin_engine.connect() as conn:
        # Clean tenant test data
        conn.execute(text("DELETE FROM audit_events;"))
        conn.execute(text("DELETE FROM valuation_results;"))
        conn.execute(text("DELETE FROM valuation_cases;"))
        conn.execute(text("DELETE FROM properties;"))
        conn.execute(text("DELETE FROM institution_policies;"))
        conn.execute(text("DELETE FROM institutions;"))

        # Create Institution A and Institution B
        conn.execute(text("""
            INSERT INTO institutions (id, code, name, institution_type, status, primary_contact_email, created_at, updated_at)
            VALUES 
                ('INST_A_HDFC', 'HDFC_BANK', 'HDFC Bank Ltd', 'BANK', 'ACTIVE', 'admin@hdfc.internal', NOW(), NOW()),
                ('INST_B_ICICI', 'ICICI_BANK', 'ICICI Bank Ltd', 'BANK', 'ACTIVE', 'admin@icici.internal', NOW(), NOW());
        """))
        conn.commit()


@pytest.fixture
def pg_session(pg_engine):
    """Provides a transactional session as propval_app_user."""
    SessionLocal = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# -----------------------------------------------------------------------------
# 1. Institution A Accessing Its Own Data
# -----------------------------------------------------------------------------
def test_institution_a_accesses_own_data(pg_session: Session):
    """Verify that Institution A can create and query its own valuation cases and properties."""
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")

    prop_id = str(uuid.uuid4())
    prop = PropertyRecord(
        id=prop_id,
        institution_id="INST_A_HDFC",
        application_no="APP-HDFC-001",
        project_name="Prestige Lakeside",
        unit_address="Tower 1, Flat 101",
        locality="Whitefield",
        city="Bengaluru",
        pincode="560066",
        carpet_area_sqft=1200.0,
        super_built_up_area_sqft=1500.0,
    )
    pg_session.add(prop)

    case_id = str(uuid.uuid4())
    case = ValuationCaseModel(
        id=case_id,
        institution_id="INST_A_HDFC",
        property_id=prop_id,
        borrower_name="Ramesh Kumar (HDFC)",
        loan_requested=7500000.0,
        declared_agreement_value=9000000.0,
        branch="Whitefield Branch",
        assigned_underwriter="UW-01",
    )
    pg_session.add(case)
    pg_session.commit()

    # Query back as Institution A
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")
    cases = pg_session.query(ValuationCaseModel).filter(ValuationCaseModel.id == case_id).all()
    assert len(cases) == 1
    assert cases[0].borrower_name == "Ramesh Kumar (HDFC)"


# -----------------------------------------------------------------------------
# 2. Institution B Accessing Its Own Data
# -----------------------------------------------------------------------------
def test_institution_b_accesses_own_data(pg_session: Session):
    """Verify that Institution B can create and query its own valuation cases and properties."""
    set_db_tenant_context(pg_session, tenant_id="INST_B_ICICI")

    prop_id = str(uuid.uuid4())
    prop = PropertyRecord(
        id=prop_id,
        institution_id="INST_B_ICICI",
        application_no="APP-ICICI-001",
        project_name="Brigade Gateway",
        unit_address="Block B, Flat 402",
        locality="Malleshwaram",
        city="Bengaluru",
        pincode="560055",
        carpet_area_sqft=1400.0,
        super_built_up_area_sqft=1750.0,
    )
    pg_session.add(prop)

    case_id = str(uuid.uuid4())
    case = ValuationCaseModel(
        id=case_id,
        institution_id="INST_B_ICICI",
        property_id=prop_id,
        borrower_name="Priya Sharma (ICICI)",
        loan_requested=9500000.0,
        declared_agreement_value=12000000.0,
        branch="Malleshwaram Branch",
        assigned_underwriter="UW-02",
    )
    pg_session.add(case)
    pg_session.commit()

    # Query back as Institution B
    set_db_tenant_context(pg_session, tenant_id="INST_B_ICICI")
    cases = pg_session.query(ValuationCaseModel).filter(ValuationCaseModel.id == case_id).all()
    assert len(cases) == 1
    assert cases[0].borrower_name == "Priya Sharma (ICICI)"


# -----------------------------------------------------------------------------
# 3. Institution A Attempting to Access Institution B Data
# -----------------------------------------------------------------------------
def test_institution_a_cannot_access_institution_b_data(pg_session: Session):
    """Verify that when tenant context is set to Institution A, Institution B's rows are completely invisible."""
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")

    # Attempt to query all cases or specifically filter for Institution B
    cases = pg_session.query(ValuationCaseModel).filter(ValuationCaseModel.institution_id == "INST_B_ICICI").all()
    assert len(cases) == 0, "Security Violation: Institution A retrieved Institution B records!"

    # Attempt to query specifically for ICICI borrower
    icici_cases = pg_session.query(ValuationCaseModel).filter(
        ValuationCaseModel.borrower_name.ilike("%ICICI%")
    ).all()
    assert len(icici_cases) == 0, "Security Violation: Institution A retrieved ICICI cases by borrower name!"


# -----------------------------------------------------------------------------
# 4. Missing Tenant Context Fails Closed
# -----------------------------------------------------------------------------
def test_missing_tenant_context_fails_closed(pg_session: Session):
    """Verify that queries without active tenant context return 0 rows (Fail Closed)."""
    reset_db_tenant_context(pg_session)

    # With no context, all tenant rows should be invisible
    cases = pg_session.query(ValuationCaseModel).all()
    assert len(cases) == 0, f"Fail-closed breach: Missing context returned {len(cases)} rows!"

    policies = pg_session.query(InstitutionPolicyModel).all()
    assert len(policies) == 0


# -----------------------------------------------------------------------------
# 5. Invalid / Malformed Tenant Context Protection
# -----------------------------------------------------------------------------
def test_invalid_tenant_context_injection_rejected():
    """Verify that SQL injection attempts in tenant_id are intercepted before touching PostgreSQL."""
    malicious_inputs = [
        "' OR '1'='1",
        "INST_A'; DROP TABLE valuation_cases; --",
        "INST_A' UNION SELECT * FROM users --",
        "../../etc/passwd",
        "INST_A\x00NULL",
    ]
    for bad_id in malicious_inputs:
        with pytest.raises(ValueError) as excinfo:
            validate_tenant_id(bad_id)
        assert "Invalid tenant_id format" in str(excinfo.value)


# -----------------------------------------------------------------------------
# 6. Cross-Tenant INSERT Attempts Blocked by WITH CHECK Policy
# -----------------------------------------------------------------------------
def test_cross_tenant_insert_blocked_by_rls(pg_session: Session):
    """Verify that an active tenant cannot insert records with another institution's tenant ID."""
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")

    prop_id = str(uuid.uuid4())
    prop = PropertyRecord(
        id=prop_id,
        institution_id="INST_A_HDFC",
        application_no=f"APP-{uuid.uuid4().hex[:6]}",
        project_name="Test Tower",
        unit_address="Unit 1",
        locality="Whitefield",
        city="Bengaluru",
        pincode="560066",
        carpet_area_sqft=1000.0,
        super_built_up_area_sqft=1200.0,
    )
    pg_session.add(prop)
    pg_session.flush()

    # Attempt cross-tenant insert (HDFC session inserting for ICICI)
    spoofed_case = ValuationCaseModel(
        id=str(uuid.uuid4()),
        institution_id="INST_B_ICICI",  # Mismatched tenant
        property_id=prop_id,
        borrower_name="Malicious Injected Case",
        loan_requested=5000000.0,
        declared_agreement_value=6000000.0,
        branch="Fraud Branch",
        assigned_underwriter="Hacker",
    )
    pg_session.add(spoofed_case)

    with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as excinfo:
        pg_session.commit()
    
    err_msg = str(excinfo.value).lower()
    assert "row-level security" in err_msg or "violates" in err_msg or "policy" in err_msg


# -----------------------------------------------------------------------------
# 7. Cross-Tenant UPDATE Attempts Blocked
# -----------------------------------------------------------------------------
def test_cross_tenant_update_blocked(pg_session: Session):
    """Verify that a tenant cannot update records belonging to another institution."""
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")

    # Attempt to update ICICI cases
    updated_rows = pg_session.query(ValuationCaseModel).filter(
        ValuationCaseModel.institution_id == "INST_B_ICICI"
    ).update({"loan_requested": 1.0})
    pg_session.commit()

    assert updated_rows == 0, f"Cross-tenant update succeeded! {updated_rows} rows modified."


# -----------------------------------------------------------------------------
# 8. Cross-Tenant DELETE Attempts Blocked
# -----------------------------------------------------------------------------
def test_cross_tenant_delete_blocked(pg_session: Session):
    """Verify that a tenant cannot delete records belonging to another institution."""
    set_db_tenant_context(pg_session, tenant_id="INST_A_HDFC")

    # Attempt to delete ICICI cases
    deleted_rows = pg_session.query(ValuationCaseModel).filter(
        ValuationCaseModel.institution_id == "INST_B_ICICI"
    ).delete()
    pg_session.commit()

    assert deleted_rows == 0, f"Cross-tenant delete succeeded! {deleted_rows} rows destroyed."


# -----------------------------------------------------------------------------
# 9. Connection Pool Tenant Context Isolation Across Sequential Transactions
# -----------------------------------------------------------------------------
def test_connection_pool_tenant_context_isolation(pg_engine):
    """Verify that transaction-local context does not leak across pooled connection reuse."""
    SessionLocal = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)

    # Transaction 1: Operate as Institution A
    s1 = SessionLocal()
    set_db_tenant_context(s1, tenant_id="INST_A_HDFC")
    a_cases = s1.query(ValuationCaseModel).all()
    assert len(a_cases) >= 1
    s1.commit()
    s1.close()  # Connection returned to pool

    # Transaction 2: Fresh session without setting context (simulating pool checkout by another worker)
    s2 = SessionLocal()
    # No set_db_tenant_context called!
    leaked_cases = s2.query(ValuationCaseModel).all()
    s2.close()

    assert len(leaked_cases) == 0, (
        f"Critical Connection Pool Leakage: Session checked out from pool retained tenant context "
        f"and exposed {len(leaked_cases)} records!"
    )


# -----------------------------------------------------------------------------
# 10. Privileged Role & Compliance Auditor Access Restrictions
# -----------------------------------------------------------------------------
def test_platform_admin_and_auditor_access(pg_session: Session):
    """Verify that Platform Admins can see all cases, and Compliance Auditors can inspect audit logs."""
    # 1. Platform Admin access
    set_db_tenant_context(pg_session, tenant_id="", is_admin=True)
    all_cases = pg_session.query(ValuationCaseModel).all()
    # Should see cases from both Institution A and Institution B
    institutions_found = set(c.institution_id for c in all_cases)
    assert "INST_A_HDFC" in institutions_found
    assert "INST_B_ICICI" in institutions_found

    # 2. Add an audit event for Institution A
    evt = AuditEventModel(
        event_id=str(uuid.uuid4()),
        sequence_number=1001,
        event_type="VALUATION_COMPLETED",
        actor_id="UW-01",
        actor_role="CREDIT_UNDERWRITER",
        institution_id="INST_A_HDFC",
        payload_json='{"status": "APPROVED"}',
        prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
        current_hash=uuid.uuid4().hex,
    )
    pg_session.add(evt)
    pg_session.commit()

    # 3. Compliance Auditor access (can see all audit logs across tenants)
    set_db_tenant_context(pg_session, tenant_id="", is_admin=False, is_auditor=True)
    audit_logs = pg_session.query(AuditEventModel).all()
    assert len(audit_logs) >= 1

    # But compliance auditor cannot see valuation cases without admin role!
    auditor_cases = pg_session.query(ValuationCaseModel).all()
    assert len(auditor_cases) == 0, "Auditor without admin role should not see raw valuation cases!"
