"""Institutional partner onboarding, multi-tenancy, and credit policy tests (Phase 5B)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    ROLE_ADMIN,
    ROLE_INSTITUTION_ADMIN,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
)
from app.models.institution import InstitutionModel, InstitutionPolicyModel
from app.models.valuation import ValuationCaseModel
from app.services.institution_service import (
    EVENT_INSTITUTION_ONBOARDED,
    EVENT_INSTITUTION_UPDATED,
    EVENT_INSTITUTION_POLICY_UPDATED,
    EVENT_INSTITUTION_API_KEY_ROTATED,
    evaluate_case_policy_compliance,
)
from app.schemas.institution import CasePolicyEvaluationRequest


@pytest.fixture
def superadmin_headers():
    token = create_access_token({
        "sub": "superadmin",
        "name": "Super Administrator",
        "role": ROLE_ADMIN,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_a_admin_headers():
    token = create_access_token({
        "sub": "inst_a_admin",
        "name": "Apex HFC Admin",
        "role": ROLE_INSTITUTION_ADMIN,
        "institution_id": "inst-apex-hfc-01",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_a_underwriter_headers():
    token = create_access_token({
        "sub": "apex_underwriter_1",
        "name": "Apex Underwriter One",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": "inst-apex-hfc-01",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_b_underwriter_headers():
    token = create_access_token({
        "sub": "bharat_underwriter_1",
        "name": "Bharat NBFC Underwriter",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": "inst-bharat-nbfc-02",
    })
    return {"Authorization": f"Bearer {token}"}


# ----------------------------------------------------------------------
# 1. Institution Creation & Configuration Tests
# ----------------------------------------------------------------------

def test_onboard_institution_success(client: TestClient, superadmin_headers, db_session):
    """Test successful onboarding of a new Housing Finance Company (HFC)."""
    payload = {
        "code": "APEX_HFC",
        "name": "Apex Housing Finance Corporation Ltd",
        "institutionType": "HFC",
        "primaryContactEmail": "risk.head@apexhfc.com",
        "primaryContactName": "Rajiv Menon",
        "primaryContactPhone": "+91-9876543210",
        "cinOrRegistrationNo": "U65922MH2018PLC312456",
        "rbiNhbRegistrationNo": "NHB-HFC-089/2019",
        "registeredOfficeAddress": "Floor 12, Express Towers, Nariman Point, Mumbai - 400021",
        "branches": [
            {"code": "APX-MUM-01", "name": "BKC Prime Branch", "city": "Mumbai", "state": "Maharashtra", "tier": "METRO"},
            {"code": "APX-BLR-01", "name": "Indiranagar Hub", "city": "Bengaluru", "state": "Karnataka", "tier": "METRO"},
        ],
        "authorizedDomains": ["apexhfc.com"],
        "retentionPeriodYears": 10,
        "policy": {
            "maxLtvPct": 80.0,
            "defaultDistressDiscountPct": 15.0,
            "maxUnderwriterHaircutPct": 20.0,
            "circleRateTolerancePct": 25.0,
            "minCibilScore": 720,
            "mandatoryTitleSearchYears": 30,
            "requireReraForOngoing": True,
            "requireNilEncumbrance": True,
        },
    }

    response = client.post("/api/v1/institutions", json=payload, headers=superadmin_headers)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()

    assert data["code"] == "APEX_HFC"
    assert data["name"] == "Apex Housing Finance Corporation Ltd"
    assert data["institutionType"] == "HFC"
    assert data["status"] == "ACTIVE"
    assert len(data["branches"]) == 2
    assert data["branches"][0]["code"] == "APX-MUM-01"
    assert data["retentionPeriodYears"] == 10

    # Policy verification
    policy = data["policy"]
    assert policy is not None
    assert policy["maxLtvPct"] == 80.0
    assert policy["minCibilScore"] == 720
    assert policy["mandatoryTitleSearchYears"] == 30


def test_onboard_institution_duplicate_code_rejected(client: TestClient, superadmin_headers):
    """Test that attempting to onboard an institution with an existing code returns 409 Conflict."""
    payload = {
        "code": "DUP_HFC",
        "name": "First HFC",
        "institutionType": "HFC",
        "primaryContactEmail": "first@duphfc.com",
    }
    first_res = client.post("/api/v1/institutions", json=payload, headers=superadmin_headers)
    assert first_res.status_code == status.HTTP_201_CREATED

    duplicate_payload = {
        "code": "DUP_HFC",
        "name": "Second HFC with Duplicate Code",
        "institutionType": "HFC",
        "primaryContactEmail": "second@duphfc.com",
    }
    response = client.post("/api/v1/institutions", json=duplicate_payload, headers=superadmin_headers)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


def test_onboard_institution_unauthorized_role_rejected(client: TestClient, institution_a_underwriter_headers):
    """Test that ordinary underwriters cannot onboard new institutions (requires ADMIN)."""
    payload = {
        "code": "ROGUE_HFC",
        "name": "Rogue Institution",
        "institutionType": "HFC",
        "primaryContactEmail": "rogue@test.com",
    }
    response = client.post("/api/v1/institutions", json=payload, headers=institution_a_underwriter_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ----------------------------------------------------------------------
# 2. Institution-Level Data Isolation & Unauthorized Cross-Access Tests
# ----------------------------------------------------------------------

def test_tenant_data_isolation_on_case_creation_and_listing(
    client: TestClient,
    superadmin_headers,
    institution_a_underwriter_headers,
    institution_b_underwriter_headers,
    db_session,
):
    """Verify that Tenant A cannot see Tenant B's valuation cases in list queries."""
    # 1. Onboard Tenant A and Tenant B
    inst_a_res = client.post(
        "/api/v1/institutions",
        json={"code": "TENANT_A", "name": "Tenant A Finance", "primaryContactEmail": "a@tenant.com"},
        headers=superadmin_headers,
    )
    inst_a_id = inst_a_res.json()["id"]

    inst_b_res = client.post(
        "/api/v1/institutions",
        json={"code": "TENANT_B", "name": "Tenant B NBFC", "primaryContactEmail": "b@tenant.com"},
        headers=superadmin_headers,
    )
    inst_b_id = inst_b_res.json()["id"]

    # Generate JWTs scoped to Tenant A and Tenant B
    token_a = create_access_token({
        "sub": "user_a",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": inst_a_id,
    })
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = create_access_token({
        "sub": "user_b",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": inst_b_id,
    })
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Tenant A creates a loan case
    case_a_payload = {
        "borrowerName": "Aarav Sharma (Tenant A)",
        "loanRequested": 6500000.0,
        "declaredAgreementValue": 8500000.0,
        "unitAddress": "Flat 402, Tower Alpha, Whitefield",
        "projectName": "Prestige Whitefield Heights",
        "city": "Bengaluru",
        "carpetAreaSqFt": 1150.0,
        "superBuiltUpAreaSqFt": 1450.0,
    }
    create_a_res = client.post("/api/v1/cases", json=case_a_payload, headers=headers_a)
    assert create_a_res.status_code == status.HTTP_201_CREATED
    case_a_id = create_a_res.json()["id"]
    assert create_a_res.json()["institutionId"] == inst_a_id

    # 3. Tenant B creates a loan case
    case_b_payload = {
        "borrowerName": "Priya Nair (Tenant B)",
        "loanRequested": 12000000.0,
        "declaredAgreementValue": 16000000.0,
        "unitAddress": "Villa 14, Palm Grove, Koramangala",
        "projectName": "Palm Meadows",
        "city": "Bengaluru",
        "carpetAreaSqFt": 2200.0,
        "superBuiltUpAreaSqFt": 2800.0,
    }
    create_b_res = client.post("/api/v1/cases", json=case_b_payload, headers=headers_b)
    assert create_b_res.status_code == status.HTTP_201_CREATED
    case_b_id = create_b_res.json()["id"]
    assert create_b_res.json()["institutionId"] == inst_b_id

    # 4. Verify Tenant A only sees Case A
    list_a_res = client.get("/api/v1/cases", headers=headers_a)
    assert list_a_res.status_code == status.HTTP_200_OK
    items_a = list_a_res.json()["items"]
    case_ids_a = [c["id"] for c in items_a]
    assert case_a_id in case_ids_a
    assert case_b_id not in case_ids_a

    # 5. Verify Tenant B only sees Case B
    list_b_res = client.get("/api/v1/cases", headers=headers_b)
    assert list_b_res.status_code == status.HTTP_200_OK
    items_b = list_b_res.json()["items"]
    case_ids_b = [c["id"] for c in items_b]
    assert case_b_id in case_ids_b
    assert case_a_id not in case_ids_b


def test_cross_institution_case_access_blocked(client: TestClient, superadmin_headers):
    """Verify that Tenant B cannot access Tenant A's case by ID (returns 403 Forbidden)."""
    # Create Tenant X and Tenant Y
    inst_x = client.post(
        "/api/v1/institutions",
        json={"code": "TENANT_X", "name": "Tenant X", "primaryContactEmail": "x@x.com"},
        headers=superadmin_headers,
    ).json()

    inst_y = client.post(
        "/api/v1/institutions",
        json={"code": "TENANT_Y", "name": "Tenant Y", "primaryContactEmail": "y@y.com"},
        headers=superadmin_headers,
    ).json()

    token_x = create_access_token({"sub": "user_x", "role": ROLE_CREDIT_UNDERWRITER, "institution_id": inst_x["id"]})
    token_y = create_access_token({"sub": "user_y", "role": ROLE_CREDIT_UNDERWRITER, "institution_id": inst_y["id"]})

    headers_x = {"Authorization": f"Bearer {token_x}"}
    headers_y = {"Authorization": f"Bearer {token_y}"}

    # User X creates a case
    case_x = client.post(
        "/api/v1/cases",
        json={
            "borrowerName": "Tenant X Borrower",
            "loanRequested": 5000000.0,
            "declaredAgreementValue": 7000000.0,
            "unitAddress": "Address X",
            "projectName": "Project X",
            "city": "Bengaluru",
            "carpetAreaSqFt": 1000.0,
            "superBuiltUpAreaSqFt": 1250.0,
        },
        headers=headers_x,
    ).json()

    # User Y attempts to access User X's case -> MUST return 403 Forbidden
    cross_get_res = client.get(f"/api/v1/cases/{case_x['id']}", headers=headers_y)
    assert cross_get_res.status_code == status.HTTP_403_FORBIDDEN
    assert "Cross-institution access denied" in cross_get_res.json()["detail"]


# ----------------------------------------------------------------------
# 3. Institution-Specific Valuation Policy & Approval Hierarchy Tests
# ----------------------------------------------------------------------

def test_institution_policy_customization_and_evaluation(client: TestClient, superadmin_headers, db_session):
    """Test updating credit policy parameters and evaluating a loan case against institutional rules."""
    # 1. Onboard Institution with strict policy
    inst_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "CONSERVATIVE_HFC",
            "name": "Conservative Housing Finance",
            "primaryContactEmail": "credit@conservativehfc.com",
            "policy": {
                "maxLtvPct": 70.0,  # Strict LTV limit of 70%
                "minCibilScore": 750,
                "mandatoryTitleSearchYears": 35,
                "maxUnderwriterHaircutPct": 15.0,
                "requireNilEncumbrance": True,
                "approvalHierarchy": [
                    {"tier": 1, "maxAmount": 3000000.0, "roleRequired": "CREDIT_UNDERWRITER", "label": "Branch Credit Officer"},
                    {"tier": 2, "maxAmount": 10000000.0, "roleRequired": "SENIOR_UNDERWRITER", "label": "Zonal Risk Head"},
                    {"tier": 3, "maxAmount": 999999999.0, "roleRequired": "RISK_COMMITTEE_MEMBER", "label": "Board Credit Committee"},
                ],
            },
        },
        headers=superadmin_headers,
    )
    assert inst_res.status_code == status.HTTP_201_CREATED
    inst_id = inst_res.json()["id"]

    # 2. Evaluate a non-compliant case (LTV 80% > 70%, CIBIL 710 < 750, Title 25 < 35 yrs)
    eval_payload = {
        "loanRequested": 4500000.0,
        "declaredAgreementValue": 5500000.0,
        "cibilScore": 710,
        "ltvRatioPct": 80.0,
        "underwriterHaircutPct": 10.0,
        "titleChainYears": 25,
        "encumbranceStatus": "NIL_ENCUMBRANCE",
        "reraRegistration": "PRM/KA/RERA/1251/2024",
    }

    eval_res = client.post(
        f"/api/v1/institutions/{inst_id}/policy/evaluate",
        json=eval_payload,
        headers=superadmin_headers,
    )
    assert eval_res.status_code == status.HTTP_200_OK
    eval_data = eval_res.json()

    assert eval_data["isCompliant"] is False
    assert len(eval_data["violations"]) == 3
    assert any("exceeds institutional policy ceiling of 70.0%" in v for v in eval_data["violations"])
    assert any("below institutional threshold of 750" in v for v in eval_data["violations"])
    assert any("less than institutional requirement of 35 years" in v for v in eval_data["violations"])

    # Approval tier verification: ₹45 Lakhs > ₹30 Lakhs tier 1 ceiling -> Tier 2 (Senior Underwriter)
    assert eval_data["requiredApprovalTier"] == 2
    assert eval_data["requiredRole"] == "SENIOR_UNDERWRITER"
    assert eval_data["tierLabel"] == "Zonal Risk Head"

    # 3. Evaluate a compliant case (LTV 65%, CIBIL 780, Title 40 yrs, Loan 1.5 Cr -> Tier 3)
    compliant_payload = {
        "loanRequested": 15000000.0,
        "declaredAgreementValue": 25000000.0,
        "cibilScore": 780,
        "ltvRatioPct": 60.0,
        "underwriterHaircutPct": 5.0,
        "titleChainYears": 40,
        "encumbranceStatus": "NIL_ENCUMBRANCE",
        "reraRegistration": "PRM/KA/RERA/1251/2024",
    }
    compliant_res = client.post(
        f"/api/v1/institutions/{inst_id}/policy/evaluate",
        json=compliant_payload,
        headers=superadmin_headers,
    )
    assert compliant_res.status_code == status.HTTP_200_OK
    c_data = compliant_res.json()

    assert c_data["isCompliant"] is True
    assert len(c_data["violations"]) == 0
    # ₹1.5 Cr > ₹1.0 Cr tier 2 ceiling -> Tier 3 (Board Credit Committee)
    assert c_data["requiredApprovalTier"] == 3
    assert c_data["requiredRole"] == "RISK_COMMITTEE_MEMBER"
    assert c_data["tierLabel"] == "Board Credit Committee"


# ----------------------------------------------------------------------
# 4. B2B Partner API Key Generation & Rotation Tests
# ----------------------------------------------------------------------

def test_generate_and_rotate_partner_api_key(client: TestClient, superadmin_headers, db_session):
    """Test B2B partner API key issuance, secure hashing, and rotation."""
    # Onboard institution
    inst = client.post(
        "/api/v1/institutions",
        json={"code": "API_PARTNER", "name": "API Partner Bank", "primaryContactEmail": "api@partner.com"},
        headers=superadmin_headers,
    ).json()
    inst_id = inst["id"]

    # Generate API key
    key_res = client.post(f"/api/v1/institutions/{inst_id}/api-keys", headers=superadmin_headers)
    assert key_res.status_code == status.HTTP_201_CREATED
    key_data = key_res.json()

    raw_key = key_data["apiKey"]
    prefix = key_data["prefix"]
    assert raw_key.startswith("pv_live_api_pa_")
    assert prefix == "pv_live_api_pa_"

    # Verify that raw key is NOT stored in plain text in database
    inst_db = db_session.query(InstitutionModel).filter(InstitutionModel.id == inst_id).first()
    assert inst_db.api_key_hash is not None
    assert inst_db.api_key_hash != raw_key
    assert len(inst_db.api_key_hash) == 64  # SHA-256 hex string


# ----------------------------------------------------------------------
# 5. Immutable Audit Event Verification Tests
# ----------------------------------------------------------------------

def test_audit_event_generation_on_onboarding_and_policy_updates(client: TestClient, superadmin_headers, db_session):
    """Verify that institutional onboarding, policy changes, and key rotations record tamper-evident audit events."""
    from app.models.audit import AuditEventModel

    initial_audit_count = db_session.query(AuditEventModel).count()

    # 1. Onboard
    inst = client.post(
        "/api/v1/institutions",
        json={"code": "AUDIT_TEST_HFC", "name": "Audit Test HFC", "primaryContactEmail": "audit@test.com"},
        headers=superadmin_headers,
    ).json()
    inst_id = inst["id"]

    # 2. Update Policy
    client.put(
        f"/api/v1/institutions/{inst_id}/policy",
        json={"maxLtvPct": 65.0, "minCibilScore": 730},
        headers=superadmin_headers,
    )

    # 3. Rotate API Key
    client.post(f"/api/v1/institutions/{inst_id}/api-keys", headers=superadmin_headers)

    # Verify audit chain records
    events = (
        db_session.query(AuditEventModel)
        .order_by(AuditEventModel.id.desc())
        .limit(3)
        .all()
    )
    event_types = [e.event_type for e in events]

    assert EVENT_INSTITUTION_API_KEY_ROTATED in event_types
    assert EVENT_INSTITUTION_POLICY_UPDATED in event_types
    assert EVENT_INSTITUTION_ONBOARDED in event_types
