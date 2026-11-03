"""Tests for Valuation Case management endpoints (CRUD, filtering, search, status transitions)."""

from fastapi.testclient import TestClient


def test_list_cases_seeded_demo_records(client: TestClient):
    """GET /api/v1/cases returns the 6 seeded demonstration cases."""
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 6
    # Verify Bengaluru case is present
    blr_case = next((c for c in data["items"] if c["id"] == "case-blr-89412"), None)
    assert blr_case is not None
    assert blr_case["city"] == "Bengaluru"
    assert blr_case["dataSource"] == "synthetic-demo"
    assert len(blr_case["comparables"]) > 0


def test_list_cases_filtering_and_search(client: TestClient):
    """GET /api/v1/cases correctly filters by city and status."""
    # Filter by city
    response = client.get("/api/v1/cases?city=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert all(c["city"] == "Mumbai" for c in data["items"])

    # Search borrower name
    response_search = client.get("/api/v1/cases?search=Sengupta")
    assert response_search.status_code == 200
    search_data = response_search.json()
    assert search_data["total"] >= 1
    assert "Sengupta" in search_data["items"][0]["borrowerName"]


def test_get_case_by_id_and_not_found(client: TestClient):
    """GET /api/v1/cases/{id} returns 200 for valid ID and 404 for unknown ID."""
    response = client.get("/api/v1/cases/case-blr-89412")
    assert response.status_code == 200
    case = response.json()
    assert case["id"] == "case-blr-89412"
    assert case["projectName"] == "Sobha Dream Acres"
    assert case["carpetAreaSqFt"] == 1215

    # 404 for non-existent case
    response_404 = client.get("/api/v1/cases/case-nonexistent-999")
    assert response_404.status_code == 404


def test_create_case_full_workflow(client: TestClient):
    """POST /api/v1/cases creates a new case, calculates valuation, and stores in database."""
    payload = {
        "borrowerName": "Aarav Sharma",
        "city": "Bengaluru",
        "projectName": "Godrej Splendour",
        "locality": "Whitefield",
        "unitAddress": "Flat 802, Tower 3",
        "pincode": "560066",
        "carpetAreaSqFt": 1150,
        "superBuiltUpAreaSqFt": 1480,
        "floorNo": 8,
        "loanRequested": 8000000,
        "declaredAgreementValue": 11000000,
        "underwriterHaircutPct": -2.0,
        "distressDiscountPct": 18.0,
        "ltvRatioPct": 75.0,
        "legalRiskPenaltyPct": 0.0,
    }
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201
    new_case = response.json()

    assert new_case["borrowerName"] == "Aarav Sharma"
    assert new_case["projectName"] == "Godrej Splendour"
    assert new_case["carpetAreaSqFt"] == 1150
    assert new_case["status"] == "READY_FOR_APPROVAL"
    assert new_case["dataSource"] == "synthetic-demo"
    assert new_case["latestValuation"] is not None
    assert new_case["latestValuation"]["netAssessedValue"] > 0

    # Verify newly created case is queryable via GET
    case_id = new_case["id"]
    get_res = client.get(f"/api/v1/cases/{case_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == case_id


def test_update_case_and_recalculate(client: TestClient):
    """PUT /api/v1/cases/{id} updates parameters and recalculates valuation."""
    case_id = "case-blr-89412"
    update_payload = {
        "underwriterHaircutPct": -10.0,
        "legalRiskPenaltyPct": 5.0,
    }
    response = client.put(f"/api/v1/cases/{case_id}", json=update_payload)
    assert response.status_code == 200
    updated_case = response.json()
    assert updated_case["underwriterHaircutPct"] == -10.0
    assert updated_case["legalRiskPenaltyPct"] == 5.0
    assert updated_case["latestValuation"] is not None


def test_update_case_status_and_audit_note(client: TestClient):
    """PATCH /api/v1/cases/{id}/status transitions status and records audit note."""
    case_id = "case-blr-89412"
    status_payload = {
        "status": "APPROVED",
        "auditNote": "Valuation digitally certified by Senior Underwriter.",
    }
    response = client.patch(f"/api/v1/cases/{case_id}/status", json=status_payload)
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "APPROVED"
    assert any("Valuation digitally certified" in note for note in updated["auditNotes"])


def test_delete_case(client: TestClient, admin_headers):
    """DELETE /api/v1/cases/{id} removes a case (Admin only). Non-admin is rejected."""
    # Create temporary case to delete
    create_res = client.post("/api/v1/cases", json={
        "borrowerName": "Delete Test User",
        "city": "Pune",
        "projectName": "Test Project",
        "unitAddress": "Unit 101",
        "carpetAreaSqFt": 800,
        "superBuiltUpAreaSqFt": 1050,
        "loanRequested": 4000000,
        "declaredAgreementValue": 5500000,
    })
    assert create_res.status_code == 201
    temp_id = create_res.json()["id"]

    # Non-admin attempt (client has senior_underwriter default) -> 403 Forbidden
    del_forbidden = client.delete(f"/api/v1/cases/{temp_id}")
    assert del_forbidden.status_code == 403

    # Admin delete -> 200 OK
    del_res = client.delete(f"/api/v1/cases/{temp_id}", headers=admin_headers)
    assert del_res.status_code == 200

    # Ensure 404 after deletion
    get_res = client.get(f"/api/v1/cases/{temp_id}")
    assert get_res.status_code == 404

