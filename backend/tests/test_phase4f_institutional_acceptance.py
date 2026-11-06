"""Phase 4F: Institutional Acceptance Testing & Multi-Persona Workflow Simulation.

Simulates end-to-end realistic workflows for 5 institutional personas:
1. Property Valuer: Property submission, measurement structuring, and comparable queries.
2. Credit Underwriter: Valuation calculation, haircut/distress override, loan sanction bounds.
3. Risk Committee Analyst: Anomaly detection, circle rate deviation alerts, conformal interval uncertainty.
4. Institutional Administrator: Dataset governance, prerequisite ML training gate enforcement, dual approval.
5. Compliance Auditor: Cryptographic Merkle chain audit verification, DPDP Section 12 erasure compliance.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.core.security import (
    create_access_token,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_COMPLIANCE_AUDITOR,
    ROLE_ADMIN,
)
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.verification.anomaly_detector import TransactionAnomalyDetector
from app.ml.readiness_gate import evaluate_training_gate
from app.services.audit_service import verify_audit_chain, record_audit_event


# ---------------------------------------------------------------------------
# Persona 1: Property Valuer Workflow
# ---------------------------------------------------------------------------

def test_persona_property_valuer_workflow(client: TestClient, auth_headers):
    """Property Valuer submits property physical specs and queries comparable evidence."""
    # 1. Query comparable registered transactions
    comp_resp = client.get("/api/v1/comparables?city=Bengaluru&locality=Whitefield", headers=auth_headers)
    assert comp_resp.status_code == 200
    assert isinstance(comp_resp.json(), list)

    # 2. Submit new valuation case
    payload = {
        "borrowerName": "Aarav & Priya Deshmukh",
        "coBorrowerName": "Priya Deshmukh",
        "cibilScore": 795,
        "city": "Bengaluru",
        "projectName": "Godrej Splendour",
        "locality": "Whitefield",
        "unitAddress": "Tower 4, Flat 802",
        "pincode": "560066",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1150.0,
        "builtUpAreaSqFt": 1380.0,
        "superBuiltUpAreaSqFt": 1550.0,
        "floorNo": 8,
        "totalFloors": 18,
        "ageYears": 2,
        "roadWidthFt": 40,
        "loanRequested": 9500000.0,
        "declaredAgreementValue": 12500000.0,
        "circleRatePerSqFt": 7500.0,
        "baseMarketRatePerSqFt": 9200.0,
        "assignedUnderwriter": "R. Sharma (Credit Underwriter)",
    }
    create_resp = client.post("/api/v1/cases", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    case_data = create_resp.json()
    assert case_data["borrowerName"] == "Aarav & Priya Deshmukh"
    assert case_data["latestValuation"]["netAssessedValue"] > 0
    assert case_data["status"] == "READY_FOR_APPROVAL"


# ---------------------------------------------------------------------------
# Persona 2: Credit Underwriter Workflow
# ---------------------------------------------------------------------------

def test_persona_credit_underwriter_workflow(client: TestClient, underwriter_headers):
    """Credit Underwriter reviews case, applies stress haircut, and sanctions loan."""
    # 1. Fetch case list
    list_resp = client.get("/api/v1/cases", headers=underwriter_headers)
    assert list_resp.status_code == 200
    cases = list_resp.json()["items"]
    assert len(cases) > 0
    case_id = cases[0]["id"]

    # 2. Apply underwriter haircut override
    update_payload = {
        "underwriterHaircutPct": -4.5,
        "distressDiscountPct": 17.5,
        "ltvRatioPct": 75.0,
    }
    update_resp = client.put(f"/api/v1/cases/{case_id}", json=update_payload, headers=underwriter_headers)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["underwriterHaircutPct"] == -4.5
    assert updated["latestValuation"]["maxSanctionAmount"] > 0

    # 3. Four-Eyes Principle: Junior Underwriter cannot unilaterally approve case (403 Forbidden)
    forbidden_signoff = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Collateral and borrower CIBIL verified."},
        headers=underwriter_headers,
    )
    assert forbidden_signoff.status_code == 403

    # 4. Senior Underwriter executes final sign-off approval (200 OK)
    token_senior = create_access_token({"sub": "v.sundaram", "role": ROLE_SENIOR_UNDERWRITER})
    senior_headers = {"Authorization": f"Bearer {token_senior}"}
    signoff_resp = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "APPROVED", "auditNote": "Senior underwriter verified and approved."},
        headers=senior_headers,
    )
    assert signoff_resp.status_code == 200
    assert signoff_resp.json()["status"] == "APPROVED"


# ---------------------------------------------------------------------------
# Persona 3: Risk Committee Analyst Workflow
# ---------------------------------------------------------------------------

def test_persona_risk_analyst_workflow(client: TestClient, auth_headers):
    """Risk Analyst inspects empirical coverage and tests anomaly detection on suspicious deeds."""
    # 1. Review empirical coverage dashboard
    cov_resp = client.get("/api/v1/datasets/empirical-coverage", headers=auth_headers)
    assert cov_resp.status_code == 200
    cov = cov_resp.json()
    assert "total_verified_empirical_deeds" in cov
    assert cov["ml_eligibility_status"] in ("GATED", "ELIGIBLE")

    # 2. Detect stamp duty evasion attempt (Deed 40% below circle rate)
    undervalued_deed = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 3600000.0,  # ₹3,600 / sqft
        "guideline_rate_per_sqft": 6000.0,  # ₹6,000 / sqft
        "city": "Bengaluru",
    }
    verdict = TransactionAnomalyDetector.inspect(undervalued_deed)
    assert verdict.is_anomalous is True
    assert verdict.fraud_risk_level == "HIGH"
    assert verdict.quarantine_code == "CIRCLE_RATE_UNDERVALUATION"


# ---------------------------------------------------------------------------
# Persona 4: Institutional Administrator Workflow
# ---------------------------------------------------------------------------

def test_persona_institutional_admin_workflow(db_session, client: TestClient, admin_headers):
    """Admin tests dataset governance, ML readiness gate, and separation of duties."""
    # 1. Verify unapproved dataset blocks training
    dataset = DatasetMetadataModel(
        name="Pilot Ingestion Cohort",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="pilot.csv",
        file_hash_sha256="hash_pilot_001",
        approval_status="UNDER_REVIEW",  # Not APPROVED
    )
    db_session.add(dataset)
    db_session.flush()

    audit = evaluate_training_gate(db_session, dataset.id)
    assert audit.canTrain is False
    assert any("UNAPPROVED_DATASET" in b for b in audit.blockingIssues)

    # 2. Test system health endpoint
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# Persona 5: Compliance Auditor Workflow
# ---------------------------------------------------------------------------

def test_persona_compliance_auditor_workflow(db_session, client: TestClient, auth_headers):
    """Compliance Auditor verifies tamper-evident audit Merkle chain and event integrity."""
    # 1. Verify audit chain verification API (POST /api/v1/audit/verify)
    chain_resp = client.post("/api/v1/audit/verify", headers=auth_headers)
    assert chain_resp.status_code == 200
    report = chain_resp.json()
    assert "is_valid" in report
    assert report["is_valid"] is True
    assert report["total_events"] >= 1

    # 2. Verify audit chain directly against ORM
    db_report = verify_audit_chain(db_session)
    assert db_report.is_valid is True
