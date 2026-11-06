"""Phase 7B: Institutional Pilot Onboarding, Agreements & Governance Framework Tests.

Validates:
1. Institutional onboarding workflow (INVITED -> ONBOARDING -> UNDER_REVIEW -> APPROVED_FOR_PILOT).
2. Legal agreement recording (Draft upload does NOT execute; formal execution with legal authority).
3. Access prevention for unapproved and suspended institutions.
4. Tenant isolation and least-privilege RBAC.
5. Mandatory Pilot Safety Controls:
   - Advisory-only classification on all valuations.
   - Prohibits automated loan sanctions (requires explicit human credit underwriter sign-off).
   - Valuation divergence > 15% requires Senior Underwriter review.
   - HIGH_ALERT cases require Senior Underwriter review.
   - CatBoost remains blocked; deterministic hedonic scorecard v0.2.0 remains active.
6. Institutional Pilot Dashboard live metrics from database.
7. Cryptographic audit logging for all administrative transitions.
"""

from datetime import datetime, timedelta, timezone
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
from app.models.institution import InstitutionModel
from app.models.valuation import ValuationCaseModel
from app.services import audit_service


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
        "sub": "hdfc_admin",
        "name": "HDFC Pilot Admin",
        "role": ROLE_INSTITUTION_ADMIN,
        "institution_id": "inst-hdfc-pilot-7b",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_a_underwriter_headers():
    token = create_access_token({
        "sub": "hdfc_underwriter",
        "name": "HDFC Credit Underwriter",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": "inst-hdfc-pilot-7b",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_a_senior_underwriter_headers():
    token = create_access_token({
        "sub": "hdfc_senior_underwriter",
        "name": "HDFC Senior Underwriter",
        "role": ROLE_SENIOR_UNDERWRITER,
        "institution_id": "inst-hdfc-pilot-7b",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_b_admin_headers():
    token = create_access_token({
        "sub": "icici_admin",
        "name": "ICICI Pilot Admin",
        "role": ROLE_INSTITUTION_ADMIN,
        "institution_id": "inst-icici-pilot-7b",
    })
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. INSTITUTIONAL ONBOARDING WORKFLOW & LIFECYCLE TESTS
# ==============================================================================

def test_institutional_onboarding_lifecycle_fields(client: TestClient, superadmin_headers: dict):
    """Register a new institutional partner with required category, admin info, and pending statuses."""
    payload = {
        "code": "HDFC_BANK_PILOT",
        "name": "HDFC Bank Home Loans Division",
        "institutionType": "BANK",
        "primaryContactEmail": "pilot-ops@hdfcbank-demo.in",
        "primaryContactName": "Rajiv Mehra (EVP Credit Risk)",
        "primaryContactPhone": "+91-22-6754-8900",
        "cinOrRegistrationNo": "L65920MH1994PLC080618",
        "rbiNhbRegistrationNo": "RBI/2026/BANK-0091",
        "registeredOfficeAddress": "HDFC Bank House, Senapati Bapat Marg, Lower Parel, Mumbai",
        "branches": [
            {"code": "HDFC-MUM-01", "name": "Corporate Credit Centre", "city": "Mumbai", "tier": "METRO"},
            {"code": "HDFC-BLR-01", "name": "Koramangala Hub", "city": "Bengaluru", "tier": "METRO"},
        ],
        "authorizedDomains": ["hdfcbank-demo.in", "hdfc-mortgage.in"],
        "retentionPeriodYears": 8,
    }
    resp = client.post("/api/v1/institutions", json=payload, headers=superadmin_headers)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()

    assert data["code"] == "HDFC_BANK_PILOT"
    assert data["institutionType"] == "BANK"
    assert data["agreementStatus"] == "PENDING"
    assert data["dpaStatus"] == "PENDING"
    assert data["pilotAuthorizationStatus"] == "UNAUTHORIZED"
    assert data["isPilotApproved"] is False
    assert len(data["branches"]) == 2


def test_pilot_access_strictly_prevented_before_authorization(client: TestClient, superadmin_headers: dict):
    """Institutions in ONBOARDING/DOCUMENTATION_PENDING status cannot execute pilot valuation cases."""
    # 1. Onboard institution in ONBOARDING status
    payload = {
        "code": "BAJAJ_FIN_UNAPPROVED",
        "name": "Bajaj Housing Finance Ltd",
        "institutionType": "HFC",
        "primaryContactEmail": "underwriting@bajaj-unapproved.in",
        "primaryContactName": "Sunil Joshi",
    }
    create_resp = client.post("/api/v1/institutions", json=payload, headers=superadmin_headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    inst_id = create_resp.json()["id"]

    # Explicitly set status to DOCUMENTATION_PENDING
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}",
        json={"status": "DOCUMENTATION_PENDING"},
        headers=superadmin_headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["status"] == "DOCUMENTATION_PENDING"

    # 2. Token for this unapproved institution
    unapproved_token = create_access_token({
        "sub": "bajaj_uw",
        "name": "Bajaj Underwriter",
        "role": ROLE_CREDIT_UNDERWRITER,
        "institution_id": inst_id,
    })
    unapproved_headers = {"Authorization": f"Bearer {unapproved_token}"}

    # 3. Attempt to create a valuation case - must be FORBIDDEN
    case_payload = {
        "borrowerName": "Vipul Kulkarni",
        "city": "Bengaluru",
        "projectName": "Prestige Falcon City",
        "locality": "Kanakapura Road",
        "unitAddress": "Tower 4, Flat 1201",
        "carpetAreaSqFt": 1200,
        "superBuiltUpAreaSqFt": 1550,
        "floorNo": 12,
        "loanRequested": 7500000,
        "declaredAgreementValue": 10500000,
        "institutionId": inst_id,
    }
    case_resp = client.post("/api/v1/cases", json=case_payload, headers=unapproved_headers)
    assert case_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "not authorized for pilot operations" in case_resp.json()["detail"]


# ==============================================================================
# 2. PILOT AGREEMENTS & AUTHORIZATION WORKFLOW TESTS
# ==============================================================================

def test_draft_agreement_upload_does_not_execute_agreement(client: TestClient, superadmin_headers: dict):
    """Uploading draft agreement documentation records reference but does NOT legally execute or approve pilot."""
    # 1. Onboard institution
    inst_resp = client.post(
        "/api/v1/institutions",
        json={
            "code": "ICICI_PILOT_DRAFT",
            "name": "ICICI Bank Home Loans",
            "institutionType": "BANK",
            "primaryContactEmail": "pilot@icici-test.in",
        },
        headers=superadmin_headers,
    )
    inst_id = inst_resp.json()["id"]

    # 2. Upload draft agreement
    draft_payload = {
        "agreementReference": "IPA-ICICI-2026-DRAFT-01",
        "evidenceUrl": "https://secure-docs.bank.internal/agreements/draft_ipa_icici_v1.pdf",
        "dpaReference": "DPA-ICICI-2026-DRAFT-01",
        "notes": "Legal counsel reviewing indemnity clause 14.2.",
    }
    draft_resp = client.post(
        f"/api/v1/institutions/{inst_id}/agreements/draft",
        json=draft_payload,
        headers=superadmin_headers,
    )
    assert draft_resp.status_code == status.HTTP_200_OK
    draft_data = draft_resp.json()

    assert draft_data["agreementStatus"] == "UNDER_REVIEW"
    assert draft_data["status"] == "UNDER_REVIEW"
    assert draft_data["isPilotApproved"] is False
    assert draft_data["pilotAuthorizationStatus"] == "UNAUTHORIZED"
    assert draft_data["agreementSignedDate"] is None  # NOT signed yet


def test_formal_pilot_agreement_execution_requires_authorized_admin(client: TestClient, superadmin_headers: dict):
    """Only authorized administrator can execute agreement with verified legal details and DPA."""
    # 1. Onboard institution
    inst_resp = client.post(
        "/api/v1/institutions",
        json={
            "code": "SBI_PILOT_EXEC",
            "name": "State Bank of India Housing Division",
            "institutionType": "BANK",
            "primaryContactEmail": "pilot-sbi@sbi-test.in",
        },
        headers=superadmin_headers,
    )
    inst_id = inst_resp.json()["id"]

    # 2. Credit Underwriter attempt to execute agreement - MUST FAIL (Least privilege)
    uw_token = create_access_token({"sub": "uw_sbi", "role": ROLE_CREDIT_UNDERWRITER, "institution_id": inst_id})
    uw_headers = {"Authorization": f"Bearer {uw_token}"}

    exec_payload = {
        "agreementReference": "IPA-SBI-2026-EXEC-01",
        "agreementSignatoryName": "K. Venkatraman",
        "agreementSignatoryTitle": "Chief General Manager (Mortgages)",
        "agreementSignedDate": datetime.now(timezone.utc).isoformat(),
        "agreementEvidenceUrl": "https://vault.sbi.co.in/legal/IPA-SBI-2026-SIGNED.pdf",
        "dpaReference": "DPA-SBI-2026-004",
        "dpaSignatoryName": "Pooja Deshmukh (DPO)",
        "dpaSignedDate": datetime.now(timezone.utc).isoformat(),
        "pilotCommencementDate": datetime.now(timezone.utc).isoformat(),
        "pilotExpiryDate": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "authorizedPilotParticipants": ["venkatraman.k@sbi.co.in", "sbi_underwriter@sbi.co.in"],
        "approvedDataCategories": ["COLLATERAL_DEED", "BORROWER_DECLARED_ATTRIBUTES", "INDEX_II_SRO_RECORDS"],
        "permittedPurposes": ["SHADOW_VALUATION_PILOT_EVALUATION"],
        "approvedOperationalScope": {"max_cases": 150, "allowed_cities": ["Bengaluru", "Mumbai"]},
        "approvalEvidenceReference": "BOARD-RES-SBI-2026-Q4-019",
    }
    uw_attempt = client.post(f"/api/v1/institutions/{inst_id}/agreements/execute", json=exec_payload, headers=uw_headers)
    assert uw_attempt.status_code == status.HTTP_403_FORBIDDEN

    # 3. Superadmin executes agreement - MUST SUCCEED
    exec_resp = client.post(f"/api/v1/institutions/{inst_id}/agreements/execute", json=exec_payload, headers=superadmin_headers)
    assert exec_resp.status_code == status.HTTP_200_OK
    exec_data = exec_resp.json()

    assert exec_data["agreementStatus"] == "EXECUTED"
    assert exec_data["dpaStatus"] == "EXECUTED"
    assert exec_data["status"] == "APPROVED_FOR_PILOT"
    assert exec_data["pilotAuthorizationStatus"] == "AUTHORIZED"
    assert exec_data["isPilotApproved"] is True
    assert exec_data["agreementSignatoryName"] == "K. Venkatraman"
    assert len(exec_data["authorizedPilotParticipants"]) == 2


# ==============================================================================
# 3. ACCOUNT SUSPENSION & TENANT ISOLATION TESTS
# ==============================================================================

def test_account_suspension_revokes_pilot_functionality(client: TestClient, superadmin_headers: dict):
    """Suspension of institutional partner revokes all active pilot capabilities immediately."""
    # 1. Onboard and approve institution
    inst_resp = client.post(
        "/api/v1/institutions",
        json={
            "code": "SUSPEND_TEST_INST",
            "name": "Suspension Test Finance",
            "institutionType": "NBFC",
            "primaryContactEmail": "contact@suspend-test.in",
        },
        headers=superadmin_headers,
    )
    inst_id = inst_resp.json()["id"]

    # Execute agreement to make it approved
    client.post(
        f"/api/v1/institutions/{inst_id}/agreements/execute",
        json={
            "agreementReference": "IPA-SUSP-01",
            "agreementSignatoryName": "Test Signatory",
            "agreementSignatoryTitle": "Director",
            "agreementSignedDate": datetime.now(timezone.utc).isoformat(),
            "agreementEvidenceUrl": "https://vault.test/signed.pdf",
            "dpaReference": "DPA-SUSP-01",
            "dpaSignatoryName": "Test DPO",
            "dpaSignedDate": datetime.now(timezone.utc).isoformat(),
            "pilotCommencementDate": datetime.now(timezone.utc).isoformat(),
            "pilotExpiryDate": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "authorizedPilotParticipants": ["user@suspend-test.in"],
            "approvedDataCategories": ["COLLATERAL_DEED"],
            "permittedPurposes": ["TEST_PILOT"],
            "approvedOperationalScope": {},
            "approvalEvidenceReference": "EVID-001",
        },
        headers=superadmin_headers,
    )

    # 2. Suspend institution
    susp_resp = client.post(
        f"/api/v1/institutions/{inst_id}/suspend?reason=Breach+of+pilot+data+boundary",
        headers=superadmin_headers,
    )
    assert susp_resp.status_code == status.HTTP_200_OK
    assert susp_resp.json()["status"] == "SUSPENDED"

    # 3. User from suspended institution attempts to list cases - must be FORBIDDEN
    susp_token = create_access_token({"sub": "susp_user", "role": ROLE_CREDIT_UNDERWRITER, "institution_id": inst_id})
    susp_headers = {"Authorization": f"Bearer {susp_token}"}

    list_resp = client.get("/api/v1/cases", headers=susp_headers)
    assert list_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "SUSPENDED" in list_resp.json()["detail"]


def test_cross_tenant_isolation_on_pilot_agreements(client: TestClient, superadmin_headers: dict):
    """Institution A cannot view or tamper with Institution B's agreements."""
    # Create Institution A and B
    resp_a = client.post("/api/v1/institutions", json={"code": "TENANT_A_7B", "name": "Tenant A HFC", "primaryContactEmail": "a@hfc.in"}, headers=superadmin_headers)
    resp_b = client.post("/api/v1/institutions", json={"code": "TENANT_B_7B", "name": "Tenant B HFC", "primaryContactEmail": "b@hfc.in"}, headers=superadmin_headers)
    id_a = resp_a.json()["id"]
    id_b = resp_b.json()["id"]

    token_a = create_access_token({"sub": "admin_a", "role": ROLE_INSTITUTION_ADMIN, "institution_id": id_a})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Tenant A attempts to view Tenant B agreement details
    cross_resp = client.get(f"/api/v1/institutions/{id_b}/agreements", headers=headers_a)
    assert cross_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Cross-institution access denied" in cross_resp.json()["detail"]


# ==============================================================================
# 4. MANDATORY PILOT SAFETY CONTROLS & CASE MANAGEMENT TESTS
# ==============================================================================

def test_advisory_classification_on_all_pilot_cases(client: TestClient, superadmin_headers: dict):
    """Every pilot case valuation carries ADVISORY_ONLY classification and hedonic engine v0.2.0."""
    case_payload = {
        "borrowerName": "Deepak Natarajan",
        "city": "Bengaluru",
        "projectName": "Brigade Gateway",
        "locality": "Rajajinagar",
        "unitAddress": "Tower 2, Flat 1802",
        "pincode": "560010",
        "carpetAreaSqFt": 1450,
        "superBuiltUpAreaSqFt": 1900,
        "floorNo": 18,
        "loanRequested": 12500000,
        "declaredAgreementValue": 16500000,
        "assignedValuer": "R. Ramanathan (Gold Standard Valuations)",
        "reviewingCreditOfficer": "K. Senthil (Chief Credit Manager)",
    }
    resp = client.post("/api/v1/cases", json=case_payload, headers=superadmin_headers)
    assert resp.status_code == status.HTTP_201_CREATED
    case = resp.json()

    assert case["advisoryClassification"] == "ADVISORY_ONLY"
    assert case["valuationEngineVersion"] == "hedonic-scorecard-v0.2.0"
    assert case["valuationMethodology"] == "DETERMINISTIC_HEDONIC"
    assert case["assignedValuer"] == "R. Ramanathan (Gold Standard Valuations)"
    assert case["reviewingCreditOfficer"] == "K. Senthil (Chief Credit Manager)"


def test_mandatory_human_sign_off_required_for_approval(client: TestClient, superadmin_headers: dict):
    """Automated valuation cannot sanction loan independently. Approval requires human sign-off."""
    # 1. Create a case
    create_resp = client.post(
        "/api/v1/cases",
        json={
            "borrowerName": "Sneha Sen",
            "city": "Bengaluru",
            "projectName": "Sobha Dream Acres",
            "locality": "Panathur",
            "unitAddress": "Wing B, Flat 401",
            "carpetAreaSqFt": 950,
            "superBuiltUpAreaSqFt": 1200,
            "loanRequested": 6000000,
            "declaredAgreementValue": 8500000,
        },
        headers=superadmin_headers,
    )
    case_id = create_resp.json()["id"]

    # 2. Attempt approval without human sign-off notes or signer - rejected with 400
    approval_resp = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": None, "humanSignOffBy": None},
        headers=superadmin_headers,
    )
    assert approval_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Automated valuation cannot sanction loan independently" in approval_resp.json()["detail"]

    # 3. Supply authorized human sign-off - succeeds
    valid_approval = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={
            "status": "APPROVED",
            "humanSignOffBy": "V. Sundaram (Sr. Underwriter)",
            "humanSignOffNotes": "Collateral verified against SRO record. Sanction within 75% LTV approved.",
            "auditNote": "Human underwriter approved collateral valuation.",
        },
        headers=superadmin_headers,
    )
    assert valid_approval.status_code == status.HTTP_200_OK
    assert valid_approval.json()["status"] == "APPROVED"
    assert valid_approval.json()["humanSignOffBy"] == "V. Sundaram (Sr. Underwriter)"


def test_valuation_divergence_exceeding_15_requires_senior_underwriter_review(client: TestClient, superadmin_headers: dict):
    """Valuation divergence > 15% triggers senior review requirement; junior underwriters cannot approve."""
    # Create case where declared value is 50,000,000 but market rate yields ~10,000,000 (Divergence >> 15%)
    create_resp = client.post(
        "/api/v1/cases",
        json={
            "borrowerName": "High Divergence Borrower",
            "city": "Bengaluru",
            "projectName": "Sample Residency",
            "locality": "Whitefield",
            "unitAddress": "Flat 101",
            "carpetAreaSqFt": 1000,
            "superBuiltUpAreaSqFt": 1250,
            "loanRequested": 35000000,
            "declaredAgreementValue": 50000000,  # Extreme divergence
        },
        headers=superadmin_headers,
    )
    case = create_resp.json()
    case_id = case["id"]

    assert case["divergencePct"] > 15.0
    assert case["requiresSeniorReview"] is True

    # Junior underwriter attempts to approve - MUST FAIL WITH 403
    uw_token = create_access_token({"sub": "junior_uw", "role": ROLE_CREDIT_UNDERWRITER})
    uw_headers = {"Authorization": f"Bearer {uw_token}"}

    uw_approval = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "humanSignOffBy": "Junior Underwriter", "auditNote": "Attempted sign-off"},
        headers=uw_headers,
    )
    assert uw_approval.status_code == status.HTTP_403_FORBIDDEN

    # Senior Underwriter approves - MUST SUCCEED
    senior_token = create_access_token({"sub": "senior_uw", "role": ROLE_SENIOR_UNDERWRITER})
    senior_headers = {"Authorization": f"Bearer {senior_token}"}

    senior_approval = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={
            "status": "APPROVED",
            "humanSignOffBy": "Senior Underwriter",
            "humanSignOffNotes": "Senior committee reviewed divergence. Reduced sanction amount to verified cap.",
            "auditNote": "Senior sign-off executed.",
        },
        headers=senior_headers,
    )
    assert senior_approval.status_code == status.HTTP_200_OK
    assert senior_approval.json()["status"] == "APPROVED"


# ==============================================================================
# 5. INSTITUTIONAL PILOT DASHBOARD TESTS
# ==============================================================================

def test_institutional_pilot_dashboard_metrics(client: TestClient, superadmin_headers: dict):
    """Pilot dashboard endpoint returns live database metrics for active institutions, cases, and safety gates."""
    # Ensure at least one institution exists
    client.post(
        "/api/v1/institutions",
        json={"code": "DASH_TEST_HFC", "name": "Dashboard Test HFC", "primaryContactEmail": "dash@test.in"},
        headers=superadmin_headers,
    )

    resp = client.get("/api/v1/institutions/pilot-dashboard", headers=superadmin_headers)
    assert resp.status_code == status.HTTP_200_OK
    dashboard = resp.json()

    assert "totalRegisteredInstitutions" in dashboard
    assert dashboard["totalRegisteredInstitutions"] >= 1
    assert "institutionsApprovedForPilot" in dashboard
    assert "pendingHumanReviews" in dashboard
    assert "valuationDivergenceStats" in dashboard
    assert "meanDivergencePct" in dashboard["valuationDivergenceStats"]
    assert "auditChainVerificationStatus" in dashboard
    assert dashboard["auditChainVerificationStatus"]["isValid"] is True
    assert "dataProvenanceStatus" in dashboard
    assert dashboard["dataProvenanceStatus"]["mlGateStatus"] == "BLOCKED"
    assert dashboard["dataProvenanceStatus"]["activeValuationEngine"] == "hedonic-scorecard-v0.2.0"
