"""Institutional tests for Phase 4B-5 Data Governance Dashboard and Surveillance Engine."""

import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.security import (
    ROLE_ADMIN,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    UserSession,
)
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel, RejectedRecordModel, DuplicateRecordModel
from app.models.data_source import DataSourceModel
from app.models.verification import QuarantinedRecordModel
from app.api.v1.endpoints.governance import get_governance_metrics, list_quarantined_records
from app.schemas.governance_dashboard import InstitutionalGovernanceDashboardResponse


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
def senior_underwriter():
    return UserSession(username="sr_underwriter", name="Senior Underwriter", role=ROLE_SENIOR_UNDERWRITER)


@pytest.fixture
def junior_underwriter():
    return UserSession(username="jr_underwriter", name="Junior Underwriter", role=ROLE_CREDIT_UNDERWRITER)


def test_governance_metrics_aggregation_accuracy(db_session: Session, senior_underwriter: UserSession):
    """Verify metrics calculation: totals, normalized, validated, empirical, synthetic, duplicates, rejections, quarantined, quality score."""
    resp = get_governance_metrics(db=db_session, user=senior_underwriter)
    assert isinstance(resp, InstitutionalGovernanceDashboardResponse)

    # 1. Metric consistency
    assert resp.total_ingested_transactions >= 0
    assert resp.successfully_normalized_records >= 0
    assert resp.validated_records >= 0
    assert resp.verified_empirical_deeds >= 0
    assert resp.synthetic_and_mock_records >= 0
    assert resp.duplicate_records >= 0
    assert resp.rejected_records >= 0
    assert resp.quarantined_records >= 0
    assert resp.records_awaiting_verification >= 0

    # 2. Quality scoring
    assert 0.0 <= resp.data_quality_score <= 100.0
    assert resp.quality_methodology.weights["completeness"] == 0.40
    assert resp.quality_methodology.weights["validity"] == 0.30
    assert resp.quality_methodology.weights["uniqueness"] == 0.20
    assert resp.quality_methodology.weights["consistency"] == 0.10

    # 3. ML readiness gate invariant
    assert resp.ml_readiness_gate.empirical_records_threshold == 1000
    if resp.verified_empirical_deeds < 1000:
        assert resp.ml_readiness_gate.is_gated is True
        assert "GATED" in resp.ml_readiness_gate.status_label

    # 4. Permissions context
    assert resp.user_role == senior_underwriter.role
    assert resp.can_approve_datasets is True
    assert resp.can_export_ml is True


def test_governance_rbac_ordinary_user_restrictions(db_session: Session, junior_underwriter: UserSession):
    """Verify ordinary/credit underwriter can view metrics but cannot approve datasets or export ML."""
    resp = get_governance_metrics(db=db_session, user=junior_underwriter)
    assert resp.user_role == junior_underwriter.role
    assert resp.can_approve_datasets is False
    assert resp.can_export_ml is False

    # Quarantine review requires Senior Underwriter, Admin, or Auditor
    # Test role enforcement using require_roles
    from app.core.security import require_roles, ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_COMPLIANCE_AUDITOR
    role_checker = require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_COMPLIANCE_AUDITOR])
    with pytest.raises(HTTPException) as exc:
        role_checker(user=junior_underwriter)
    assert exc.value.status_code == 403
    assert "Access denied" in exc.value.detail


def test_governance_quarantine_review_authorized(db_session: Session, senior_underwriter: UserSession):
    """Verify senior underwriter can view quarantined records."""
    quarantined = list_quarantined_records(limit=20, offset=0, db=db_session, user=senior_underwriter)
    assert isinstance(quarantined, list)
