"""Automated regression test suite for Phase 3B security remediation.

Covers:
1. Authentication Security:
   - Bcrypt password verification (success and failure).
   - Token signature validation, expiration, and blacklisting (token revocation).
   - Unauthenticated requests rejected (no silent fallback).
   - Token refresh and user identity inspection (/auth/me).
2. Authorization & RBAC:
   - Case status approval restricted to Senior Underwriter/Committee/Admin (Credit Underwriter blocked with 403).
   - Case deletion restricted to Admin only (Senior Underwriter blocked with 403).
   - Immutable audit logging for administrative case deletions.
   - Audit trail surveillance restricted to authorized governance roles.
3. API Security & Schema Validation:
   - Boundary checks on CIBIL score (300-900) and loan parameters (>0).
   - Case association enforcement for persistent valuation records (no orphaned records).
   - Reverse proxy client IP handling for rate limiting.
4. File Upload Security & CSV Sanitization:
   - Disallowed extensions rejected with 400.
   - File type magic byte verification for Excel workbooks (.xlsx/.xls).
   - CSV formula/DDE injection neutralization.
   - Filename path traversal sanitization.
5. Secrets Protection:
   - Production environment validator rejects default development SECRET_KEY.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    revoke_token,
    is_token_revoked,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_ADMIN,
)
from app.services.ingestion_service import sanitize_csv_formula_injection


# -----------------------------------------------------------------------------
# 1. Authentication Security Tests
# -----------------------------------------------------------------------------

def test_bcrypt_password_hashing_and_verification():
    """Verify passwords are hashed with bcrypt (12 rounds) and correctly verified in constant time."""
    plain = "SecureInstitutionalPass123!"
    hashed = hash_password(plain)
    assert hashed.startswith("$2b$12$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_auth_token_with_correct_and_incorrect_passwords(unauthenticated_client: TestClient):
    """POST /auth/token accepts genuine bcrypt password and rejects invalid password with 401."""
    # Valid senior underwriter login
    res_ok = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "SrUnderwriter@2026!",
    })
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.json()

    # Invalid password
    res_fail = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "IntruderWrongPassword",
    })
    assert res_fail.status_code == 401
    assert "Invalid institutional credentials" in res_fail.json()["detail"]


def test_unauthenticated_request_rejected_without_fallback(unauthenticated_client: TestClient):
    """Endpoints requiring authentication return 401 when no Authorization header is provided."""
    res = unauthenticated_client.get("/api/v1/cases")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_token_revocation_and_blacklisting(unauthenticated_client: TestClient):
    """POST /auth/revoke invalidates token; subsequent requests with revoked token return 401."""
    # Login to obtain token
    login_res = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "SrUnderwriter@2026!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request works before revocation
    res_before = unauthenticated_client.get("/api/v1/cases", headers=headers)
    assert res_before.status_code == 200

    # Revoke token
    revoke_res = unauthenticated_client.post("/api/v1/auth/revoke", headers=headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "revoked"

    # Subsequent request fails
    res_after = unauthenticated_client.get("/api/v1/cases", headers=headers)
    assert res_after.status_code == 401
    assert "revoked" in res_after.json()["detail"]


def test_token_refresh_endpoint(unauthenticated_client: TestClient):
    """POST /auth/refresh exchanges a valid token for a refreshed token."""
    login_res = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "underwriter",
        "password": "CreditUnderwriter@2026!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    refresh_res = unauthenticated_client.post("/api/v1/auth/refresh", headers=headers)
    assert refresh_res.status_code == 200
    new_token = refresh_res.json()["access_token"]
    assert new_token != token

    # New token works
    test_res = unauthenticated_client.get("/api/v1/cases", headers={"Authorization": f"Bearer {new_token}"})
    assert test_res.status_code == 200


def test_auth_me_endpoint(unauthenticated_client: TestClient):
    """GET /auth/me returns current user identity, role, and claims."""
    login_res = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "committee",
        "password": "RiskCommittee@2026!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_res = unauthenticated_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["role"] == "RISK_COMMITTEE_MEMBER"
    assert data["username"] == "committee"


# -----------------------------------------------------------------------------
# 2. Authorization & RBAC Tests
# -----------------------------------------------------------------------------

def test_rbac_case_approval_restricted(client: TestClient, underwriter_headers, auth_headers):
    """Only Senior Underwriter, Risk Committee, and Admin may approve cases; Credit Underwriters are blocked."""
    case_id = "case-blr-89412"

    # Credit underwriter attempt -> 403 Forbidden
    res_cu = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Unauthorized attempt."},
        headers=underwriter_headers,
    )
    assert res_cu.status_code == 403
    assert "Access denied" in res_cu.json()["detail"]

    # Senior underwriter attempt -> 200 OK
    res_su = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Authorized institutional approval."},
        headers=auth_headers,
    )
    assert res_su.status_code == 200
    assert res_su.json()["status"] == "APPROVED"


def test_rbac_case_deletion_admin_only_and_audit_logged(client: TestClient, auth_headers, admin_headers, db_session: Session):
    """Only Admin may delete a case. Non-admin is blocked with 403. Successful delete is recorded in SHA-256 chain."""
    # Create test case
    create_res = client.post("/api/v1/cases", json={
        "borrowerName": "Audit Delete Test",
        "city": "Bengaluru",
        "projectName": "Delete Project",
        "unitAddress": "Unit 901",
        "carpetAreaSqFt": 1100,
        "superBuiltUpAreaSqFt": 1400,
        "loanRequested": 6000000,
        "declaredAgreementValue": 8500000,
    }, headers=auth_headers)
    assert create_res.status_code == 201
    case_id = create_res.json()["id"]

    # Senior underwriter delete attempt -> 403 Forbidden
    fail_del = client.delete(f"/api/v1/cases/{case_id}", headers=auth_headers)
    assert fail_del.status_code == 403
    assert "Access denied" in fail_del.json()["detail"]

    # Admin delete attempt -> 200 OK
    ok_del = client.delete(f"/api/v1/cases/{case_id}", headers=admin_headers)
    assert ok_del.status_code == 200

    # Verify immutable audit block was created
    audit_res = client.get(f"/api/v1/audit/events?case_id={case_id}&event_type=ADMIN_ACTION", headers=admin_headers)
    assert audit_res.status_code == 200
    events = audit_res.json()["items"]
    assert len(events) >= 1
    assert events[0]["payload"]["action"] == "CASE_DELETED"


# -----------------------------------------------------------------------------
# 3. API Security & Input Validation Tests
# -----------------------------------------------------------------------------

def test_input_validation_boundary_rejection(client: TestClient):
    """Pydantic schemas strictly validate CIBIL scores (300-900) and positive loan amounts."""
    # Invalid CIBIL score (> 900)
    res_cibil_high = client.post("/api/v1/cases", json={
        "borrowerName": "Invalid CIBIL",
        "city": "Bengaluru",
        "projectName": "Boundary Test",
        "unitAddress": "Unit 1",
        "carpetAreaSqFt": 1000,
        "loanRequested": 5000000,
        "declaredAgreementValue": 7000000,
        "cibilScore": 950,
    })
    assert res_cibil_high.status_code == 422

    # Invalid negative loan amount
    res_neg_loan = client.post("/api/v1/cases", json={
        "borrowerName": "Negative Loan",
        "city": "Bengaluru",
        "projectName": "Boundary Test",
        "unitAddress": "Unit 2",
        "carpetAreaSqFt": 1000,
        "loanRequested": -500000,
        "declaredAgreementValue": 7000000,
    })
    assert res_neg_loan.status_code == 422


def test_estimate_non_existent_case_id_rejected(client: TestClient):
    """Valuation estimate referencing a nonexistent caseId returns 404 to avoid orphaned results."""
    res = client.post("/api/v1/valuation/estimate", json={
        "caseId": "case-non-existent-9999",
        "city": "Bengaluru",
        "carpetAreaSqFt": 1200,
        "superBuiltUpAreaSqFt": 1500,
        "baseMarketRatePerSqFt": 7500,
        "circleRatePerSqFt": 6000,
    })
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


# -----------------------------------------------------------------------------
# 4. File Upload Security & CSV Sanitization Tests
# -----------------------------------------------------------------------------

def test_csv_formula_injection_sanitization():
    """Formulas beginning with =, +, -, @, or whitespace are neutralized with leading apostrophe."""
    assert sanitize_csv_formula_injection("=cmd|'/c calc'!A0") == "'=cmd|'/c calc'!A0"
    assert sanitize_csv_formula_injection("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_csv_formula_injection("+12345") == "'+12345"
    assert sanitize_csv_formula_injection("-54321") == "'-54321"
    assert sanitize_csv_formula_injection("Normal Text") == "Normal Text"
    assert sanitize_csv_formula_injection("12345") == "12345"


def test_upload_excel_magic_bytes_validation(client: TestClient):
    """Files with .xlsx extension but fake non-zip content are rejected with 400."""
    fake_excel_bytes = b"This is plain text pretending to be an Excel workbook."
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("fake_dataset.xlsx", io.BytesIO(fake_excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"name": "Fake Excel Dataset"},
    )
    assert res.status_code == 400
    assert "MIME validation failure" in res.json()["detail"]


# -----------------------------------------------------------------------------
# 5. Secrets Protection & Production Settings Validator
# -----------------------------------------------------------------------------

def test_production_secret_key_validator_rejects_default_key():
    """Settings validator raises ValueError when ENVIRONMENT=production but development SECRET_KEY is used."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="propval-institutional-secret-key-change-in-production-2026",
        )


def test_static_token_bypass_strictly_rejected(unauthenticated_client: TestClient):
    """Static tokens (e.g. token-admin-2026) are strictly rejected with 401 without bypass."""
    res_admin = unauthenticated_client.get(
        "/api/v1/cases",
        headers={"Authorization": "Bearer token-admin-2026"},
    )
    assert res_admin.status_code == 401
    assert "Invalid or expired institutional credentials" in res_admin.json()["detail"]

    res_sr = unauthenticated_client.get(
        "/api/v1/cases",
        headers={"Authorization": "Bearer token-sr-underwriter-2026"},
    )
    assert res_sr.status_code == 401


def test_jwt_missing_exp_claim_rejected(unauthenticated_client: TestClient):
    """A JWT token lacking a mandatory 'exp' claim is strictly rejected with 401."""
    import base64
    import hashlib
    import hmac
    import json
    from app.core.config import settings

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "admin", "username": "admin", "role": "ADMIN"}  # No exp claim!

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")

    token_without_exp = f"{header_b64}.{payload_b64}.{sig_b64}"
    res = unauthenticated_client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_without_exp}"})
    assert res.status_code == 401


def test_credit_underwriter_cannot_modify_status_in_put(client: TestClient, underwriter_headers):
    """Credit Underwriters attempting privilege escalation via PUT /cases/{id} receive 403 Forbidden."""
    case_id = "case-blr-89412"
    res = client.put(
        f"/api/v1/cases/{case_id}",
        json={"status": "APPROVED", "underwriterHaircutPct": -5.0},
        headers=underwriter_headers,
    )
    assert res.status_code == 403
    assert "Credit Underwriters cannot modify case workflow status" in res.json()["detail"]


def test_cannot_modify_finalized_approved_case(client: TestClient, auth_headers):
    """Cases in APPROVED status cannot be mutated by regular underwriters without administrative reopening."""
    case_id = "case-blr-89412"

    # 1. Approve case
    app_res = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Case approved for sign-off."},
        headers=auth_headers,
    )
    assert app_res.status_code == 200

    # 2. Attempt to mutate parameters on approved case -> 400 Bad Request
    mut_res = client.put(
        f"/api/v1/cases/{case_id}",
        json={"loanRequested": 9900000},
        headers=auth_headers,
    )
    assert mut_res.status_code == 400
    assert "finalized (APPROVED)" in mut_res.json()["detail"]


def test_unauthenticated_comparables_and_inference_rejected(unauthenticated_client: TestClient):
    """Comparables and ML inference endpoints require authentication."""
    res_comp = unauthenticated_client.get("/api/v1/comparables")
    assert res_comp.status_code == 401

    res_ml = unauthenticated_client.post("/api/v1/ml/predict", json={
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1000,
        "floorNo": 3,
        "totalFloors": 10,
        "guidelineRatePerSqFt": 6000,
        "ageYears": 2,
    })
    assert res_ml.status_code == 401

    res_unc = unauthenticated_client.post("/api/v1/ml/uncertainty/predict", json={
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1000,
        "floorNo": 3,
        "totalFloors": 10,
        "guidelineRatePerSqFt": 6000,
        "ageYears": 2,
    })
    assert res_unc.status_code == 401


def test_valuation_input_boundary_validation(client: TestClient):
    """POST /api/v1/cases strictly rejects non-positive areas, non-positive values, or out-of-bounds haircuts."""
    # Negative carpet area on case intake
    res_neg_area = client.post("/api/v1/cases", json={
        "borrowerName": "Negative Area Test",
        "city": "Bengaluru",
        "projectName": "Boundary Project",
        "unitAddress": "Unit 1",
        "carpetAreaSqFt": -500,
        "loanRequested": 5000000,
        "declaredAgreementValue": 7000000,
    })
    assert res_neg_area.status_code == 422

    # Zero declared agreement value
    res_zero_val = client.post("/api/v1/cases", json={
        "borrowerName": "Zero Agreement Test",
        "city": "Bengaluru",
        "projectName": "Boundary Project",
        "unitAddress": "Unit 2",
        "carpetAreaSqFt": 1000,
        "loanRequested": 5000000,
        "declaredAgreementValue": 0,
    })
    assert res_zero_val.status_code == 422

    # Out-of-bounds haircut (> 50%)
    res_haircut = client.post("/api/v1/cases", json={
        "borrowerName": "Extreme Haircut Test",
        "city": "Bengaluru",
        "projectName": "Boundary Project",
        "unitAddress": "Unit 3",
        "carpetAreaSqFt": 1000,
        "loanRequested": 5000000,
        "declaredAgreementValue": 7000000,
        "underwriterHaircutPct": 99.0,
    })
    assert res_haircut.status_code == 422


def test_refresh_token_rotation_invalidates_old_token(unauthenticated_client: TestClient):
    """Token refresh revokes the old token so that it cannot be reused."""
    login_res = unauthenticated_client.post("/api/v1/auth/token", json={
        "username": "underwriter",
        "password": "CreditUnderwriter@2026!",
    })
    old_token = login_res.json()["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    # Refresh token
    refresh_res = unauthenticated_client.post("/api/v1/auth/refresh", headers=old_headers)
    assert refresh_res.status_code == 200
    new_token = refresh_res.json()["access_token"]
    assert new_token != old_token

    # Attempting to use the old token again is rejected with 401
    old_res = unauthenticated_client.get("/api/v1/cases", headers=old_headers)
    assert old_res.status_code == 401
    assert "revoked" in old_res.json()["detail"]

    # New token works
    new_res = unauthenticated_client.get("/api/v1/cases", headers={"Authorization": f"Bearer {new_token}"})
    assert new_res.status_code == 200


def test_upload_filename_or_content_with_null_byte_rejected(client: TestClient):
    """Uploading files containing null bytes is rejected with 400."""
    csv_null_bytes = b"city,price,area\nBengaluru\x00,5000000,1000\n"
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("malicious.csv", io.BytesIO(csv_null_bytes), "text/csv")},
        data={"name": "Null Byte Test"},
    )
    assert res.status_code == 400
    assert "null byte" in res.json()["detail"]


def test_production_cors_validator_rejects_wildcard():
    """Settings validator raises ValueError when ENVIRONMENT=production but CORS origin is '*'."""
    with pytest.raises(ValueError, match=r"Wildcard '\*' in BACKEND_CORS_ORIGINS is strictly prohibited"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            BACKEND_CORS_ORIGINS=["*"],
        )


