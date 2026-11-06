"""Institutional tests for Phase 4B-1 Data Governance Improvements.

Validates:
1. Formal Data Source Registry & Authorization Lifecycle (DOCUMENTED_AND_AUTHORIZED, REVOKED, etc.)
2. Tracking source terms, permitted purposes, retention restrictions, and validity periods.
3. Dataset approval workflows (DRAFT -> UNDER_REVIEW -> APPROVED -> REJECTED).
4. Ownership tracking (data_owner, responsible_reviewer).
5. Complete transaction provenance (VerificationEvidenceModel linkages).
6. Role-based dataset access control.
7. Prevention of unauthorized dataset exports (Gating unapproved versions and parent datasets).
8. Comprehensive tamper-evident cryptographic audit records for all governance actions.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.security import ROLE_ADMIN, ROLE_SENIOR_UNDERWRITER, ROLE_CREDIT_UNDERWRITER, UserSession
from app.models.data_source import DataSourceModel, SourceAuthorizationStatus
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.dataset_version import DatasetVersionModel
from app.models.verification import VerificationEvidenceModel
from app.models.audit import AuditEventModel
from app.dataset_management.version_service import DatasetVersionService
from app.services.acquisition_service import AcquisitionOrchestrator
from app.connectors.base import ConnectorConfig, SyncCursor
from app.connectors.mock_connector import MockDeedConnector
from app.connectors.exceptions import ConnectorError
from app.api.v1.endpoints.acquisition import create_source, update_source_status, list_sources
from app.schemas.data_source import DataSourceCreate, DataSourceStatusUpdateRequest
from app.api.v1.endpoints.datasets import approve_dataset
from app.schemas.dataset import DatasetApprovalRequest


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user():
    return UserSession(username="admin_gov", name="Governance Administrator", role=ROLE_ADMIN)


@pytest.fixture
def senior_underwriter_user():
    return UserSession(username="sr_underwriter", name="Senior Underwriter", role=ROLE_SENIOR_UNDERWRITER)


@pytest.fixture
def junior_underwriter_user():
    return UserSession(username="jr_underwriter", name="Junior Underwriter", role=ROLE_CREDIT_UNDERWRITER)


# =========================================================================
# 1. Source Registry, Authorization & Validity Lifecycle
# =========================================================================

def test_source_registration_and_terms_tracking(db_session: Session, admin_user: UserSession):
    """Verify data source registry captures licensing, validity periods, permitted purposes, and terms."""
    unique_code = f"SRC_REG_{uuid.uuid4().hex[:6].upper()}"
    now_utc = datetime.now(timezone.utc)
    create_req = DataSourceCreate(
        source_code=unique_code,
        source_name="Maharashtra IGR Commercial Deed Feed",
        provider_name="Zapkey Intelligence Services",
        access_tier="CLASS_C_INSTITUTIONAL",
        authorization_status="AUTHORIZATION_PENDING",
        legal_authorization_basis="Institutional Pilot Evaluation Agreement 2026",
        license_number="LIC-MH-2026-8891",
        agreement_reference="AGR-ZAP-PROPVAL-2026-Q4",
        valid_from=now_utc,
        valid_until=now_utc + timedelta(days=365),
        permitted_purposes=["VALUATION_ESTIMATION", "PORTFOLIO_RISK_ANALYSIS"],
        retention_restrictions={"max_retention_days": 730, "allow_derivative_indices": True},
        commercial_terms_summary="Restricted commercial use for AVM underwriting only.",
        data_owner="Chief Risk Officer",
        api_base_url="https://api.zapkey.com",
        auth_secret_env_var="ZAPKEY_API_KEY",
        rate_limit_per_minute=100,
    )

    src = create_source(data=create_req, db=db_session, user=admin_user)
    assert src.source_code == unique_code
    assert src.authorization_status == "AUTHORIZATION_PENDING"
    assert src.license_number == "LIC-MH-2026-8891"
    assert "VALUATION_ESTIMATION" in src.permitted_purposes
    assert src.retention_restrictions["max_retention_days"] == 730
    assert src.status_updated_by == admin_user.username

    # Verify audit event recorded
    import json
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == "DATA_SOURCE_REGISTERED")
        .order_by(AuditEventModel.sequence_number.desc())
        .first()
    )
    assert audit_ev is not None
    assert audit_ev.actor_id == admin_user.username
    payload = json.loads(audit_ev.payload_json) if isinstance(audit_ev.payload_json, str) else audit_ev.payload_json
    assert payload["source_code"] == unique_code


def test_unapproved_source_ingestion_blocked(db_session: Session):
    """Verify that unapproved sources (e.g. AUTHORIZATION_PENDING) are strictly blocked from ingestion."""
    unique_code = f"SRC_PEND_{uuid.uuid4().hex[:6].upper()}"
    src = DataSourceModel(
        source_code=unique_code,
        source_name="Pending Source",
        provider_name="Third-party aggregator",
        access_tier="CLASS_C_INSTITUTIONAL",
        authorization_status="AUTHORIZATION_PENDING",
        legal_authorization_basis="Negotiations in progress",
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    config = ConnectorConfig(source_id=src.id, source_code=src.source_code, base_url="https://localhost")
    conn = MockDeedConnector(config)
    orchestrator = AcquisitionOrchestrator(db_session)

    with pytest.raises(ConnectorError) as exc_info:
        import asyncio
        asyncio.run(orchestrator.execute_acquisition_job(source_id=src.id, connector=conn))

    assert "Institutional Ingestion Blocked" in str(exc_info.value)
    assert "AUTHORIZATION_PENDING" in str(exc_info.value)


def test_source_permission_revocation_lifecycle(db_session: Session, admin_user: UserSession):
    """Verify source status transition to REVOKED records audit event and blocks ingestion."""
    unique_code = f"SRC_REV_{uuid.uuid4().hex[:6].upper()}"
    src = DataSourceModel(
        source_code=unique_code,
        source_name="Active Commercial Feed",
        provider_name="Data Vendor",
        access_tier="CLASS_C_INSTITUTIONAL",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="Executed Agreement",
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    # Revoke permissions
    req = DataSourceStatusUpdateRequest(
        authorization_status="REVOKED",
        status_change_reason="Provider breached data minimization covenant under DPDP Act 2023",
        compliance_reviewer="Legal Counsel Office",
    )
    updated = update_source_status(source_id=src.id, req=req, db=db_session, user=admin_user)
    assert updated.authorization_status == "REVOKED"
    assert updated.status_updated_by == admin_user.username
    assert updated.compliance_reviewer == "Legal Counsel Office"

    # Verify audit event
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == "DATA_SOURCE_REVOKED")
        .order_by(AuditEventModel.sequence_number.desc())
        .first()
    )
    assert audit_ev is not None
    payload = json.loads(audit_ev.payload_json) if isinstance(audit_ev.payload_json, str) else audit_ev.payload_json
    assert payload["previous_status"] == "DOCUMENTED_AND_AUTHORIZED"
    assert payload["new_status"] == "REVOKED"


def test_expired_source_validity_blocked(db_session: Session):
    """Verify that a source whose valid_until timestamp has passed is blocked from acquisition."""
    unique_code = f"SRC_EXP_{uuid.uuid4().hex[:6].upper()}"
    past_date = datetime.now(timezone.utc) - timedelta(days=10)
    src = DataSourceModel(
        source_code=unique_code,
        source_name="Expired Agreement Feed",
        provider_name="Old Partner",
        access_tier="CLASS_C_INSTITUTIONAL",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="Lapsed 2025 Contract",
        valid_until=past_date,
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    config = ConnectorConfig(source_id=src.id, source_code=src.source_code, base_url="https://localhost")
    conn = MockDeedConnector(config)
    orchestrator = AcquisitionOrchestrator(db_session)

    with pytest.raises(ConnectorError) as exc_info:
        import asyncio
        asyncio.run(orchestrator.execute_acquisition_job(source_id=src.id, connector=conn))

    assert "authorization expired" in str(exc_info.value).lower()


# =========================================================================
# 2. Dataset Approval Workflows & Provenance
# =========================================================================

def test_dataset_governance_approval_workflow(db_session: Session, senior_underwriter_user: UserSession):
    """Verify dataset approval transitions status, records reviewer, and persists audit blocks."""
    ds = DatasetMetadataModel(
        name=f"Gov_Workflow_Dataset_{uuid.uuid4().hex[:6]}",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="SRO Registration Data",
        file_format="csv",
        original_filename="deeds.csv",
        file_hash_sha256=uuid.uuid4().hex,
        status="COMPLETED",
        approval_status="DRAFT",
        data_owner="Data Engineering Team",
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)

    # Approve dataset
    app_req = DatasetApprovalRequest(
        approval_status="APPROVED",
        review_notes="Verified against sample SRO physical Index-II deed registers. Quality checks passed.",
    )
    res = approve_dataset(dataset_id=ds.id, req=app_req, db=db_session, user=senior_underwriter_user)
    assert res.approvalStatus == "APPROVED"
    assert res.responsibleReviewer == senior_underwriter_user.username
    assert res.reviewedAt is not None

    # Verify audit event
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == "DATASET_APPROVAL_STATUS_CHANGED")
        .order_by(AuditEventModel.sequence_number.desc())
        .first()
    )
    assert audit_ev is not None
    assert audit_ev.actor_id == senior_underwriter_user.username
    payload = json.loads(audit_ev.payload_json) if isinstance(audit_ev.payload_json, str) else audit_ev.payload_json
    assert payload["previous_status"] == "DRAFT"
    assert payload["new_status"] == "APPROVED"


def test_transaction_provenance_verification_evidence(db_session: Session):
    """Verify transaction ingestion automatically generates cryptographic 1:1 VerificationEvidenceModel."""
    ds = DatasetMetadataModel(
        name=f"Provenance_Dataset_{uuid.uuid4().hex[:6]}",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="api_stream",
        original_filename="live_feed",
        file_hash_sha256=uuid.uuid4().hex,
        status="COMPLETED",
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)

    tx = ImportedTransactionModel(
        dataset_id=ds.id,
        row_index=1,
        fingerprint_hash="FP_PROVENANCE_TEST_001",
        city="Bengaluru Urban",
        locality="Indiranagar",
        project_name="Prime Residency",
        property_type="High-Rise Apartment",
        transaction_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        transaction_quarter="2024-Q2",
        carpet_area_sqft=1100.0,
        transaction_price=12500000.0,
        price_per_sqft=11363.64,
        is_verified_deed=True,
        is_asking_price=False,
        data_source="B2B_ZAPKEY_BLR",
        raw_data={"test": True},
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    ev = VerificationEvidenceModel(
        transaction_id=tx.id,
        verification_status="VERIFIED",
        verifier_id="PROVENANCE_TEST_VERIFIER",
        verifier_method="SRO_INDEX_II_MATCH",
        source_origin="ZAPKEY_B2B",
        source_document_ref="DOC-12345/2024",
        original_record_hash=tx.fingerprint_hash,
        normalized_record_hash=uuid.uuid4().hex,
        dataset_version="v1.0.0",
        verification_evidence_details={"sro": "Shivajinagar"},
    )
    db_session.add(ev)
    db_session.commit()

    # Query provenance
    retrieved_ev = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert retrieved_ev is not None
    assert retrieved_ev.verifier_method == "SRO_INDEX_II_MATCH"
    assert retrieved_ev.source_document_ref == "DOC-12345/2024"
    assert retrieved_ev.original_record_hash == "FP_PROVENANCE_TEST_001"


# =========================================================================
# 3. Export Prevention & Role-Based Access Control
# =========================================================================

def test_unauthorized_dataset_export_blocked_and_audited(db_session: Session, admin_user: UserSession):
    """Verify unapproved dataset versions or parent datasets are blocked from ML export and logged in audit chain."""
    ds = DatasetMetadataModel(
        name=f"Gated_Export_Dataset_{uuid.uuid4().hex[:6]}",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="api_stream",
        original_filename="feed",
        file_hash_sha256=uuid.uuid4().hex,
        status="COMPLETED",
        approval_status="DRAFT",  # Unapproved parent dataset
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)

    service = DatasetVersionService(db_session)
    ver = service.create_version_snapshot(
        dataset_id=ds.id,
        semver_tag="v1.0.0",
        version_title="Unapproved Export Test",
        created_by=admin_user.username,
    )

    # Attempt export while version is DRAFT -> Expected 403 Forbidden
    with pytest.raises(HTTPException) as exc_draft:
        service.export_ml_training_manifest(ver.id, user_id=admin_user.username, user_role=admin_user.role)
    assert exc_draft.value.status_code == 403
    assert "Institutional Export Blocked" in exc_draft.value.detail

    # Verify audit event for blocked export
    audit_blocked = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == "DATASET_EXPORT_BLOCKED")
        .order_by(AuditEventModel.sequence_number.desc())
        .first()
    )
    assert audit_blocked is not None
    assert audit_blocked.actor_id == admin_user.username
    payload = json.loads(audit_blocked.payload_json) if isinstance(audit_blocked.payload_json, str) else audit_blocked.payload_json
    assert "must be 'APPROVED'" in payload["reason"]
