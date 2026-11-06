"""Phase 5G — Controlled Institutional Shadow Underwriting Pilot Tests.

Verifies:
1. Parallel shadow valuation calculation on institutional test cases.
2. Latency measurement verifying sub-second computation (< 100 ms).
3. Underwriter override and haircut update calculation integrity.
4. Cryptographic audit event logging for case status updates.
5. Invariant check verifying shadow mode does not autonomously approve cases.
"""

import time
import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.models.valuation import ValuationCaseModel
from app.models.audit import AuditEventModel
from app.schemas.case import ValuationCaseUpdate
from app.schemas.valuation import ValuationInputParams
from app.services.valuation_service import calculate_valuation
from app.services.case_service import update_case, update_case_status, to_case_response
from app.services.audit_service import record_audit_event, EVENT_CASE_STATUS_CHANGED
from app.core.security import create_access_token, ROLE_SENIOR_UNDERWRITER, ROLE_CREDIT_UNDERWRITER


@pytest.fixture
def underwriter_headers():
    token = create_access_token({
        "sub": "senior_underwriter_01",
        "name": "Senior Pilot Underwriter",
        "role": ROLE_SENIOR_UNDERWRITER,
    })
    return {"Authorization": f"Bearer {token}"}


# ----------------------------------------------------------------------
# 1. Shadow Valuation Computation & Latency Benchmark
# ----------------------------------------------------------------------

def test_shadow_valuation_computation_and_latency():
    """Verify that shadow valuation computes correctly with sub-second latency (<100ms)."""
    val_params = ValuationInputParams(
        carpetAreaSqFt=1200.0,
        superBuiltUpAreaSqFt=1450.0,
        baseMarketRatePerSqFt=8500.0,
        circleRatePerSqFt=7200.0,
        floorRiseFactor=200.0,
        roadWidthFactor=250.0,
        amenitiesPremium=400.0,
        structuralDepreciation=0.0,
        underwriterHaircutPct=0.0,
        distressDiscountPct=17.5,
        ltvRatioPct=75.0,
        legalRiskPenaltyPct=0.0,
    )

    t0 = time.perf_counter()
    result = calculate_valuation(val_params)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert result is not None
    assert result.grossMarketValue > 0
    assert result.netAssessedValue > 0
    assert result.maxSanctionAmount > 0
    assert result.maxSanctionAmount < result.grossMarketValue
    assert latency_ms < 100.0  # Must be fast for real-time shadow underwriting


# ----------------------------------------------------------------------
# 2. Underwriter Override & Audit Event Verification
# ----------------------------------------------------------------------

def test_underwriter_override_and_audit_logging(db_session):
    """Verify that underwriter haircut override logs an immutable audit event."""
    # Find an existing demonstration case
    case = db_session.query(ValuationCaseModel).filter(ValuationCaseModel.id == "case-blr-89412").first()
    assert case is not None

    # Apply 5% additional underwriter haircut
    updated_resp = update_case(
        db=db_session,
        case_id=case.id,
        case_in=ValuationCaseUpdate(underwriterHaircutPct=5.0),
    )
    assert updated_resp is not None
    assert updated_resp.underwriterHaircutPct == 5.0

    # Transition status
    updated_status_resp = update_case_status(
        db=db_session,
        case_id=case.id,
        new_status="REVIEW_REQUIRED",
        audit_note="Applied 5% additional risk haircut due to high guideline premium.",
    )
    assert updated_status_resp is not None
    assert updated_status_resp.status == "REVIEW_REQUIRED"

    # Record institutional audit event
    audit_evt = record_audit_event(
        db=db_session,
        event_type=EVENT_CASE_STATUS_CHANGED,
        actor_id="senior_underwriter_sharma",
        payload={"case_id": case.id, "haircut_pct": 5.0, "status": "REVIEW_REQUIRED", "action": "UNDERWRITER_HAIRCUT_APPLIED"},
        case_id=case.id,
        actor_role=ROLE_SENIOR_UNDERWRITER,
    )
    assert audit_evt is not None
    assert audit_evt.actor_id == "senior_underwriter_sharma"
    assert audit_evt.current_hash is not None


# ----------------------------------------------------------------------
# 3. Non-Decisional Shadow Pilot Invariant
# ----------------------------------------------------------------------

def test_shadow_valuation_is_provisional_and_non_decisional():
    """Verify that valuation outputs are explicitly marked as provisional without autonomous decisions."""
    val_params = ValuationInputParams(
        carpetAreaSqFt=1000.0,
        baseMarketRatePerSqFt=10000.0,
        circleRatePerSqFt=8000.0,
    )
    result = calculate_valuation(val_params)

    assert result.isProvisional is True
    assert "provisional rule-based estimation" in result.engineType
    # Verify confidence bounds
    assert 0.0 < result.confidenceScorePct <= 100.0
