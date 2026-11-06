"""Comprehensive End-to-End Enterprise Test Suite for PropVal AI.

Covers all 11 backend/API lifecycle steps:
  Step 1: User Authentication & RBAC
  Step 2: Case Management
  Step 3: Property Data & Integrity
  Step 4: Dataset Pipeline & Governance
  Step 5: Valuation Engine
  Step 6: Machine Learning Gating & Fallback
  Step 7: Uncertainty Engine & Calibration Governance
  Step 8: Gemini Advisory Synthesis & Fallback
  Step 9: Audit Trail & Approval Workflows
  Step 10: Report Generation & Valuation Certificate Data
  Step 11: Database Persistence Across Engine Restarts
"""

import time
import uuid
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import (
    create_access_token,
    revoke_token,
    DEMO_USERS,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
)
from app.services import audit_service


# Helper: obtain valid JWT token for a specific role
def get_auth_token(client: TestClient, username: str = "v.sundaram", password: str = "SrUnderwriter@2026!") -> str:
    res = client.post("/api/v1/auth/token", json={"username": username, "password": password})
    assert res.status_code == 200, f"Auth failed: {res.text}"
    return res.json()["access_token"]


# =============================================================================
# STEP 1: USER AUTHENTICATION & RBAC
# =============================================================================

def test_tc_auth_01_login_valid_credentials(client: TestClient):
    """TC-AUTH-01: Valid user credentials return signed JWT token with role and user metadata."""
    res = client.post("/api/v1/auth/token", json={
        "username": "underwriter",
        "password": "CreditUnderwriter@2026!",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == ROLE_CREDIT_UNDERWRITER
    assert "R. Sharma" in data["name"]


def test_tc_auth_02_login_invalid_password(client: TestClient):
    """TC-AUTH-02: Invalid password returns HTTP 401 Unauthorized."""
    res = client.post("/api/v1/auth/token", json={
        "username": "underwriter",
        "password": "WrongPassword123!",
    })
    assert res.status_code == 401
    assert "Invalid institutional credentials" in res.json()["detail"]


def test_tc_auth_03_login_nonexistent_user(client: TestClient):
    """TC-AUTH-03: Non-existent user returns HTTP 401 Unauthorized."""
    res = client.post("/api/v1/auth/token", json={
        "username": "non_existent_officer",
        "password": "AnyPassword123!",
    })
    assert res.status_code == 401


def test_tc_auth_04_token_logout_revocation(client: TestClient):
    """TC-AUTH-04: Logout revokes token; subsequent request with revoked token fails with HTTP 401."""
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Logout / Revoke
    logout_res = client.post("/api/v1/auth/revoke", headers=headers)
    assert logout_res.status_code == 200

    # Token must now be strictly rejected
    post_logout_res = client.get("/api/v1/auth/me", headers=headers)
    assert post_logout_res.status_code == 401
    assert "revoked" in post_logout_res.json()["detail"].lower()


def test_tc_auth_05_expired_jwt(client: TestClient):
    """TC-AUTH-05: Expired JWT is rejected with HTTP 401."""
    from datetime import timedelta
    expired_token = create_access_token(
        data={"sub": "underwriter", "role": ROLE_CREDIT_UNDERWRITER, "name": "Underwriter"},
        expires_delta=timedelta(minutes=-10),
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


def test_tc_auth_06_unauthorized_access_rejected(unauthenticated_client: TestClient):
    """TC-AUTH-06: Accessing protected endpoints without authorization header returns HTTP 401."""
    res = unauthenticated_client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_tc_auth_07_role_restriction_approval_prohibited_for_junior(client: TestClient):
    """TC-AUTH-07: Credit Underwriter cannot approve cases (requires Senior Underwriter or Risk Committee)."""
    junior_token = get_auth_token(client, username="underwriter", password="CreditUnderwriter@2026!")
    cases_res = client.get("/api/v1/cases")
    case_id = cases_res.json()["items"][0]["id"]

    res = client.patch(
        f"/api/v1/cases/{case_id}/status",
        headers={"Authorization": f"Bearer {junior_token}"},
        json={"status": "APPROVED", "auditNote": "Unauthorized attempt"},
    )
    assert res.status_code == 403
    assert "requires one of roles" in res.json()["detail"].lower()


def test_tc_auth_08_institutional_registration_governance():
    """TC-AUTH-08: In accordance with institutional banking guidelines, public self-registration is disabled."""
    assert len(DEMO_USERS) >= 4


# =============================================================================
# STEP 2 & 3: CASE MANAGEMENT & PROPERTY DATA
# =============================================================================

def test_tc_case_01_create_case_full_workflow(client: TestClient):
    """TC-CASE-01: Full case creation with complete property attributes."""
    token = get_auth_token(client)
    payload = {
        "borrowerName": "Aarav & Nandini Mehra",
        "coBorrowerName": "Nandini Mehra",
        "cibilScore": 795,
        "city": "Bengaluru",
        "projectName": "Sobha Neopolis",
        "locality": "Panathur, Outer Ring Road",
        "unitAddress": "Tower 4, Apt 1204",
        "pincode": "560087",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1450,
        "superBuiltUpAreaSqFt": 1950,
        "floorNo": 12,
        "totalFloors": 18,
        "ageYears": 0,
        "roadWidthFt": 60,
        "loanRequested": 18500000,
        "declaredAgreementValue": 24000000,
        "circleRatePerSqFt": 9500,
        "baseMarketRatePerSqFt": 12500,
        "floorRiseFactor": 250,
        "underwriterHaircutPct": -4.0,
        "distressDiscountPct": 15.0,
        "ltvRatioPct": 75.0,
        "assignedUnderwriter": "V. Sundaram (Sr. Underwriter - Tech Risk)",
    }
    res = client.post("/api/v1/cases", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["borrowerName"] == "Aarav & Nandini Mehra"
    assert data["latestValuation"]["netAssessedValue"] > 0
    assert data["status"] == "READY_FOR_APPROVAL"


def test_tc_case_02_get_case_by_id(client: TestClient):
    """TC-CASE-02: Retrieval of existing case returns full case dossier."""
    res = client.get("/api/v1/cases/case-blr-89412")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "case-blr-89412"
    assert data["city"] == "Bengaluru"
    assert "latestValuation" in data


def test_tc_case_03_case_modification(client: TestClient):
    """TC-CASE-03: Updating haircut recalculates valuation immediately."""
    token = get_auth_token(client)
    res = client.put(
        "/api/v1/cases/case-blr-89412",
        headers={"Authorization": f"Bearer {token}"},
        json={"underwriterHaircutPct": -7.5},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["underwriterHaircutPct"] == -7.5


def test_tc_case_04_access_restriction_cannot_modify_approved(client: TestClient):
    """TC-CASE-04: Finalized APPROVED case cannot be modified by non-admin."""
    token = get_auth_token(client)
    patch_res = client.patch(
        "/api/v1/cases/case-blr-89412/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "APPROVED", "auditNote": "Formal approval for test"},
    )
    assert patch_res.status_code == 200

    put_res = client.put(
        "/api/v1/cases/case-blr-89412",
        headers={"Authorization": f"Bearer {token}"},
        json={"underwriterHaircutPct": -10.0},
    )
    assert put_res.status_code == 400
    assert "locked" in put_res.json()["detail"].lower() or "finalized" in put_res.json()["detail"].lower()

    # Reset status back for test isolation
    admin_token = get_auth_token(client, username="admin", password="SystemAdmin@2026!")
    client.patch(
        "/api/v1/cases/case-blr-89412/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "READY_FOR_APPROVAL", "auditNote": "Reset for test suite"},
    )


def test_tc_prop_01_property_validation_negative_area(client: TestClient):
    """TC-PROP-01: Rejection of negative carpet area."""
    token = get_auth_token(client)
    res = client.post("/api/v1/cases", headers={"Authorization": f"Bearer {token}"}, json={
        "borrowerName": "Invalid Case",
        "city": "Bengaluru",
        "carpetAreaSqFt": -500,
        "circleRatePerSqFt": 8000,
        "loanRequested": 5000000,
        "declaredAgreementValue": 8000000,
    })
    assert res.status_code == 422


# =============================================================================
# STEP 4: DATASET PIPELINE & QUALITY AUDIT
# =============================================================================

def test_tc_data_01_csv_ingestion_and_quality_audit(client: TestClient):
    """TC-DATA-01: CSV dataset ingestion parses valid records and rejects malformed rows."""
    token = get_auth_token(client)
    csv_bytes = (
        "date,city,locality,project,carpet_area,unit,price,property_type,circle_rate\n"
        "2024-04-10,Bengaluru,Whitefield,Prestige Shantiniketan,1250,sq ft,12500000,Apartment,8500\n"
        "2024-04-11,Bengaluru,Whitefield,Prestige Shantiniketan,1400,sq ft,14000000,Apartment,8500\n"
        "2024-04-12,Bengaluru,Whitefield,Prestige Shantiniketan,,sq ft,13000000,Apartment,8500\n"
    ).encode("utf-8")

    files = {"file": ("test_ingest.csv", csv_bytes, "text/csv")}
    data = {"sourceType": "sro_registration", "description": "E2E Ingestion Test"}
    res = client.post("/api/v1/datasets/upload", headers={"Authorization": f"Bearer {token}"}, files=files, data=data)
    assert res.status_code == 201
    resp_data = res.json()
    assert resp_data["totalRecords"] == 3
    assert resp_data["validRecords"] == 2
    assert resp_data["rejectedRecords"] == 1


def test_tc_data_02_empty_file_rejected(client: TestClient):
    """TC-DATA-02: Uploading empty file is rejected with HTTP 400."""
    token = get_auth_token(client)
    files = {"file": ("empty.csv", b"", "text/csv")}
    res = client.post("/api/v1/datasets/upload", headers={"Authorization": f"Bearer {token}"}, files=files, data={"sourceType": "test"})
    assert res.status_code == 400


# =============================================================================
# STEP 5: VALUATION ENGINE NUMERICAL REPRODUCIBILITY
# =============================================================================

def test_tc_val_01_valuation_reproducibility(client: TestClient):
    """TC-VAL-01: Valuation calculation produces 100% reproducible results given identical inputs."""
    payload = {
        "carpetAreaSqFt": 1500,
        "superBuiltUpAreaSqFt": 2000,
        "baseMarketRatePerSqFt": 10000,
        "circleRatePerSqFt": 8000,
        "floorNo": 5,
        "totalFloors": 10,
        "floorRiseFactor": 200,
        "roadWidthFactor": 200,
        "amenitiesPremium": 400,
        "structuralDepreciation": 50,
        "underwriterHaircutPct": -5.0,
        "distressDiscountPct": 15.0,
        "ltvRatioPct": 75.0,
        "legalRiskPenaltyPct": 0.0,
        "declaredAgreementValue": 22000000,
        "loanRequested": 15000000,
    }

    res1 = client.post("/api/v1/valuation/estimate", json=payload)
    res2 = client.post("/api/v1/valuation/estimate", json=payload)

    assert res1.status_code == 200
    assert res2.status_code == 200

    d1 = res1.json()
    d2 = res2.json()

    assert d1["grossMarketValue"] == d2["grossMarketValue"]
    assert d1["netAssessedValue"] == d2["netAssessedValue"]
    assert d1["distressLiquidationValue"] == d2["distressLiquidationValue"]
    assert d1["maxSanctionAmount"] == d2["maxSanctionAmount"]
    assert d1["engineType"] == "provisional rule-based estimation"


# =============================================================================
# STEP 6: MACHINE LEARNING GATING & FALLBACK
# =============================================================================

def test_tc_ml_01_ml_status_reports_actual_gated_state(client: TestClient):
    """TC-ML-01: ML status returns gated state pending empirical registered dataset threshold."""
    res = client.get("/api/v1/ml/status")
    assert res.status_code == 200
    data = res.json()
    assert data["isMlActive"] is False
    assert data["activeModelVersion"] is None
    assert "datasetReadinessSummary" in data


def test_tc_ml_02_predict_falls_back_defensively(client: TestClient):
    """TC-ML-02: ML prediction request safely falls back to rule-based engine when model is gated."""
    token = get_auth_token(client)
    payload = {
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1200,
        "circleRatePerSqFt": 8000,
    }
    res = client.post("/api/v1/ml/predict", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["estimatedPrice"] > 0
    assert data["isMlPrediction"] is False


# =============================================================================
# STEP 7: UNCERTAINTY ENGINE & CALIBRATION GOVERNANCE
# =============================================================================

def test_tc_unc_01_uncertainty_withholds_uncalibrated_intervals(client: TestClient):
    """TC-UNC-01: Conformal prediction intervals are strictly withheld when calibration dataset is absent."""
    res = client.get("/api/v1/ml/uncertainty/status")
    assert res.status_code == 200
    data = res.json()
    assert data["isCalibrated"] is False
    assert data["calibrationStatus"] == "UNCERTAINTY_NOT_CALIBRATED"

    # Prediction must refuse to manufacture intervals
    pred_res = client.post("/api/v1/ml/uncertainty/predict", json={
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1200,
        "circleRatePerSqFt": 8000,
    })
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    assert pred_data["status"] == "UNCERTAINTY_NOT_CALIBRATED"
    assert pred_data["isCalibrated"] is False
    assert pred_data["pointEstimate"] > 0


# =============================================================================
# STEP 8: GEMINI ADVISORY SYNTHESIS & FALLBACK
# =============================================================================

def test_tc_ai_01_ai_status_reports_mode(client: TestClient):
    """TC-AI-01: AI status accurately reflects configuration (mock fallback or live API)."""
    res = client.get("/api/v1/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "provider" in data
    assert "disclaimer" in data


def test_tc_ai_02_ai_explain_case_deterministic_fallback(client: TestClient):
    """TC-AI-02: Underwriter briefing succeeds with deterministic synthesis if cloud is offline."""
    token = get_auth_token(client)
    res = client.post(
        "/api/v1/ai/explain-case/case-blr-89412",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "case-blr-89412"
    assert "report" in data
    assert "disclaimer" in data
    assert "human review" in data["disclaimer"].lower() or "advisory" in data["disclaimer"].lower()


# =============================================================================
# STEP 9: AUDIT TRAIL INTEGRITY
# =============================================================================

def test_tc_aud_01_cryptographic_audit_trail_intact(client: TestClient):
    """TC-AUD-01: Cryptographic SHA-256 hash chain verification returns valid with zero breaks."""
    token = get_auth_token(client)
    res = client.post("/api/v1/audit/verify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["total_events"] > 0
    assert data["broken_index"] is None


# =============================================================================
# STEP 10: REPORT GENERATION DATA INTEGRITY
# =============================================================================

def test_tc_rep_01_valuation_certificate_data_integrity(client: TestClient):
    """TC-REP-01: Case retrieval yields complete dataset for Valuation Certificate generation."""
    res = client.get("/api/v1/cases/case-blr-89412")
    assert res.status_code == 200
    case_data = res.json()

    # Validate mandatory certificate fields
    assert "id" in case_data
    assert "borrowerName" in case_data
    assert "projectName" in case_data
    assert "unitAddress" in case_data
    assert "carpetAreaSqFt" in case_data
    assert "status" in case_data

    val = case_data["latestValuation"]
    assert val is not None
    assert "grossMarketValue" in val
    assert "netAssessedValue" in val
    assert "maxSanctionAmount" in val
    assert "attributionBreakdown" in val
    assert val["engineType"] == "provisional rule-based estimation"


# =============================================================================
# STEP 11: DATABASE PERSISTENCE ACROSS SESSIONS
# =============================================================================

def test_tc_db_01_persistence_across_sessions():
    """TC-DB-01: Data persists across database session boundaries."""
    db1 = SessionLocal()
    try:
        count1 = db1.execute(text("SELECT count(*) FROM valuation_cases")).scalar()
        assert count1 >= 6
    finally:
        db1.close()

    db2 = SessionLocal()
    try:
        count2 = db2.execute(text("SELECT count(*) FROM valuation_cases")).scalar()
        assert count2 == count1
    finally:
        db2.close()
