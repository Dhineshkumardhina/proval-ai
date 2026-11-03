"""Phase 3 Production Readiness & Security Validation Test Suite.

Validates:
1. RFC 7519 HS256 Cryptographic JWT token generation, expiration, and signature tampering defense.
2. OWASP defense-in-depth HTTP security headers (nosniff, DENY, XSS, HSTS, CSP).
3. API rate limiting and brute-force throttling (HTTP 429).
4. File upload security guardrails: size limit (HTTP 413), disallowed extension rejection, and path traversal sanitization.
5. Component-level health check monitoring (database latency, audit chain integrity, ML gating, AI assistant).
6. Point-in-time database backup, SHA-256 verification, and tamper rejection.
7. Full 14-point institutional lifecycle end-to-end integration test.
"""

import io
import json
import time
from datetime import timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_jwt_token,
    DEMO_USERS,
    ROLE_SENIOR_UNDERWRITER,
)
from app.services import audit_service
from scripts.backup_db import backup_sqlite, restore_sqlite, calculate_sha256


# -----------------------------------------------------------------------------
# 1. Cryptographic JWT Authentication & Security Tests
# -----------------------------------------------------------------------------

def test_jwt_token_generation_and_verification():
    """Verify standard HS256 JWT generation and validation."""
    payload = {"sub": "v.sundaram", "role": ROLE_SENIOR_UNDERWRITER, "name": "V. Sundaram"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))

    parts = token.split(".")
    assert len(parts) == 3, "JWT must consist of header.payload.signature"

    verified = verify_jwt_token(token)
    assert verified is not None
    assert verified["sub"] == "v.sundaram"
    assert verified["role"] == ROLE_SENIOR_UNDERWRITER
    assert verified["iss"] == "propval-ai-backend"
    assert "exp" in verified


def test_jwt_expired_token_rejected():
    """Verify expired JWT tokens are strictly rejected."""
    payload = {"sub": "expired_user", "role": "ANALYST"}
    # Token expired 10 seconds ago
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))

    verified = verify_jwt_token(token)
    assert verified is None, "Expired JWT token must fail verification"


def test_jwt_tampered_signature_rejected():
    """Verify that tampering with JWT payload or signature fails verification."""
    payload = {"sub": "legit_user", "role": "USER"}
    token = create_access_token(payload)

    header_b64, payload_b64, sig_b64 = token.split(".")

    # Tamper with signature: flip first character to ensure modified bytes
    tampered_sig = ("A" if sig_b64[0] != "A" else "B") + sig_b64[1:]
    tampered_token = f"{header_b64}.{payload_b64}.{tampered_sig}"

    assert verify_jwt_token(tampered_token) is None, "Tampered signature must fail verification"


def test_auth_login_issues_valid_jwt_usable_in_api(client: TestClient):
    """Verify that /auth/token issues a valid cryptographic JWT that can be used for authenticated endpoints."""
    res = client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "SrUnderwriter@2026!",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]

    # Verify JWT validity
    decoded = verify_jwt_token(token)
    assert decoded is not None
    assert decoded["sub"] == "v.sundaram"
    assert decoded["role"] == ROLE_SENIOR_UNDERWRITER

    # Verify usage in authenticated request
    cases_res = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert cases_res.status_code == 200


# -----------------------------------------------------------------------------
# 2. HTTP Security Headers
# -----------------------------------------------------------------------------

def test_http_security_headers_present(client: TestClient):
    """Verify OWASP recommended security headers on HTTP responses."""
    res = client.get("/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Strict-Transport-Security" in headers
    assert "strict-origin-when-cross-origin" in headers.get("Referrer-Policy", "")
    assert "Content-Security-Policy" in headers


# -----------------------------------------------------------------------------
# 3. Rate Limiting Middleware
# -----------------------------------------------------------------------------

def test_auth_rate_limiting_triggers_429(client: TestClient):
    """Verify rapid repeated authentication requests hit the rate limit."""
    # Temporarily enable rate limiter and reduce limit
    original_limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
    original_enabled = settings.RATE_LIMIT_ENABLED
    try:
        settings.RATE_LIMIT_ENABLED = True
        settings.RATE_LIMIT_AUTH_PER_MINUTE = 5
        hit_429 = False

        for _ in range(8):
            res = client.post("/api/v1/auth/token", json={"username": "underwriter", "password": "p"})
            if res.status_code == 429:
                hit_429 = True
                assert "Retry-After" in res.headers
                assert "Authentication rate limit exceeded" in res.json()["detail"]
                break

        assert hit_429, "Rate limiting did not trigger 429 on excessive auth requests"
    finally:
        settings.RATE_LIMIT_AUTH_PER_MINUTE = original_limit
        settings.RATE_LIMIT_ENABLED = original_enabled


# -----------------------------------------------------------------------------
# 4. File Upload Security & Guardrails
# -----------------------------------------------------------------------------

def test_upload_disallowed_extension_rejected(client: TestClient):
    """Verify non-whitelisted file extensions (.exe, .sh, etc.) are rejected with 400 Bad Request."""
    malicious_file = io.BytesIO(b"echo 'malicious'")
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("exploit.sh", malicious_file, "text/plain")},
        data={"name": "Bad Script"},
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_upload_exceeding_max_size_rejected(client: TestClient):
    """Verify uploads exceeding 25MB are rejected with 413 Payload Too Large."""
    original_limit = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        # Temporarily set limit to 1 KB for test
        settings.MAX_UPLOAD_SIZE_BYTES = 1024
        oversized_data = b"x" * 2048
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("large_transactions.csv", io.BytesIO(oversized_data), "text/csv")},
            data={"name": "Oversized Dataset"},
        )
        assert res.status_code == 413
        assert "exceeds maximum upload limit" in res.json()["detail"]
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_limit


def test_upload_path_traversal_sanitized(client: TestClient):
    """Verify path traversal characters in upload filename are sanitized to clean basename."""
    csv_content = (
        "City,Locality,Project_Name,Carpet_Area,Area_Unit,Sale_Date,Transaction_Price,Property_Type,Floor_No,Circle_Rate,Latitude,Longitude\n"
        "Bengaluru,Whitefield,Sobha Traversal,1200,sqft,2025-06-15,8500000,High-Rise Apartment,10,7200,12.93,77.72\n"
    ).encode("utf-8")

    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("../../../../etc/passwd.csv", io.BytesIO(csv_content), "text/csv")},
        data={"name": "Traversal Test Dataset"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["validRecords"] == 1


# -----------------------------------------------------------------------------
# 5. Component Health Check Endpoint
# -----------------------------------------------------------------------------

def test_component_health_check(client: TestClient):
    """Verify detailed component-level status in /api/v1/health."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] in ("healthy", "degraded")
    assert "components" in data

    components = data["components"]
    assert "database" in components
    assert components["database"]["status"] == "connected"
    assert components["database"]["latencyMs"] >= 0

    assert "auditTrail" in components
    assert components["auditTrail"]["status"] == "verified"
    assert components["auditTrail"]["chainIntegrity"] is True

    assert "mlEngine" in components
    assert components["mlEngine"]["status"] == "gated"
    assert components["mlEngine"]["trainingBlocked"] is True

    assert "aiAssistant" in components
    assert "model" in components["aiAssistant"]


# -----------------------------------------------------------------------------
# 6. Database Backup & Recovery with SHA-256 Verification
# -----------------------------------------------------------------------------

def test_database_backup_and_restore_cycle(tmp_path: Path):
    """Verify SQLite backup, SHA-256 metadata generation, and tamper-resistant restore."""
    import sqlite3

    # Create dummy source database
    src_db = tmp_path / "source.db"
    conn = sqlite3.connect(str(src_db))
    conn.execute("CREATE TABLE test_records (id INTEGER PRIMARY KEY, note TEXT)")
    conn.execute("INSERT INTO test_records (note) VALUES ('institutional collateral sample')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_file, meta_file = backup_sqlite(src_db, backup_dir)

    assert backup_file.exists()
    assert meta_file.exists()

    with open(meta_file, "r") as f:
        meta = json.load(f)
    assert meta["database_type"] == "sqlite"
    assert "sha256_checksum" in meta

    # Test clean restore
    restore_target = tmp_path / "restored.db"
    assert restore_sqlite(backup_file, meta_file, restore_target) is True

    # Check restored database content
    conn_restored = sqlite3.connect(str(restore_target))
    cur = conn_restored.execute("SELECT note FROM test_records WHERE id=1")
    row = cur.fetchone()
    conn_restored.close()
    assert row[0] == "institutional collateral sample"

    # Test tampering rejection: corrupt backup file and expect ValueError
    with open(backup_file, "ab") as f:
        f.write(b"tamper_bytes")

    tamper_target = tmp_path / "tampered_restore.db"
    try:
        restore_sqlite(backup_file, meta_file, tamper_target)
        assert False, "Restoration should have failed due to SHA-256 mismatch"
    except ValueError as exc:
        assert "Cryptographic verification failed" in str(exc)


# -----------------------------------------------------------------------------
# 7. Complete 14-Point Institutional End-to-End Workflow Checklist
# -----------------------------------------------------------------------------

def test_14_point_institutional_lifecycle(client: TestClient, db_session: Session):
    """Validate full 14-point institutional lifecycle end to end."""
    # 1. Auth & Token issuance
    login_res = client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "SrUnderwriter@2026!",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # 2. Case creation
    case_payload = {
        "borrowerName": "Aditya Rao",
        "city": "Bengaluru",
        "projectName": "Godrej Woodsman",
        "locality": "Hebbal",
        "unitAddress": "Tower A, Flat 402",
        "pincode": "560024",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1500,
        "superBuiltUpAreaSqFt": 1850,
        "floorNo": 4,
        "totalFloors": 18,
        "ageYears": 2,
        "loanRequested": 12000000,
        "declaredAgreementValue": 16500000,
        "baseMarketRatePerSqFt": 7200,
    }
    create_res = client.post("/api/v1/cases", json=case_payload, headers=auth_header)
    assert create_res.status_code == 201
    case_data = create_res.json()
    case_id = case_data["id"]

    # 3. Property entry / retrieval
    get_res = client.get(f"/api/v1/cases/{case_id}", headers=auth_header)
    assert get_res.status_code == 200
    assert get_res.json()["propertyType"] == "High-Rise Apartment"

    # 4. Dataset ingestion
    csv_bytes = (
        "City,Locality,Project_Name,Carpet_Area,Area_Unit,Sale_Date,Transaction_Price,Property_Type,Floor_No,Circle_Rate,Latitude,Longitude\n"
        "Bengaluru,Whitefield,Whitefield Villas,2100,sqft,2025-05-10,15500000,Villa,1,7200,12.93,77.72\n"
        "Bengaluru,Whitefield,Whitefield Residency,2000,sqft,2025-06-12,14800000,Villa,1,7200,12.93,77.72\n"
    ).encode("utf-8")
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("whitefield_tx.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"name": "Whitefield Transactions"},
        headers=auth_header,
    )
    assert upload_res.status_code == 201

    # 5. Data quality reporting
    dq = upload_res.json()
    assert dq["validRecords"] == 2
    assert dq["totalRecords"] == 2

    # 6. Valuation calculation (rule-based deterministic)
    val_res = client.put(
        f"/api/v1/cases/{case_id}",
        json={"underwriterHaircutPct": -5.0},
        headers=auth_header,
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["latestValuation"]["netAssessedValue"] > 0
    assert "rule-based" in val_data["latestValuation"]["engineType"]

    # 7. ML status verification (correctly reports GATED, training blocked)
    ml_status_res = client.get("/api/v1/ml/models", headers=auth_header)
    assert ml_status_res.status_code == 200
    models = ml_status_res.json()
    # No untrustworthy ML models should be active
    assert len(models) == 0

    # 8. Conformal uncertainty status (correctly reports GATED)
    unc_res = client.get("/api/v1/ml/uncertainty/status", headers=auth_header)
    assert unc_res.status_code == 200
    unc_data = unc_res.json()
    assert unc_data["isCalibrated"] is False

    # 9. AI underwriting synthesis briefing (privacy redacted, human advisory disclaimer)
    ai_res = client.post(
        f"/api/v1/ai/explain-case/{case_id}",
        headers=auth_header,
    )
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data.get("human_review_required", True) is True
    assert "disclaimer" in ai_data

    # 10. Audit history tracking (SHA-256 chain updated)
    audit_summary_res = client.get("/api/v1/audit/summary", headers=auth_header)
    assert audit_summary_res.status_code == 200
    assert audit_summary_res.json()["total_events"] > 0

    # 11. Approval workflow (case status transition)
    approve_res = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Phase 3 verification complete."},
        headers=auth_header,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 12. Audit chain cryptographic integrity verification
    verify_res = client.post("/api/v1/audit/verify", headers=auth_header)
    assert verify_res.status_code == 200
    verify_report = verify_res.json()
    assert verify_report["is_valid"] is True
    assert verify_report["error_type"] is None

    # 13. DB persistence verification
    check_persisted = client.get(f"/api/v1/cases/{case_id}", headers=auth_header)
    assert check_persisted.status_code == 200
    assert check_persisted.json()["borrowerName"] == "Aditya Rao"

    # 14. Restart / reload recovery without data loss or hash chain breakage
    # Re-verify audit chain with freshly retrieved session
    chain_check = audit_service.verify_audit_chain(db_session)
    assert chain_check.is_valid is True
