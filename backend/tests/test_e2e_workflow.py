"""End-to-End Verification: Complete 10-Step Institutional Valuation Workflow."""

from fastapi.testclient import TestClient


def test_complete_end_to_end_valuation_workflow(client: TestClient):
    """Executes and verifies the full 10-step institutional property valuation lifecycle."""

    # STEP 1: User opens PropVal AI -> Root & API health verified
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    api_health = client.get("/api/v1/health")
    assert api_health.status_code == 200
    assert api_health.json()["database"] == "connected"

    # Initial cases list fetched by frontend on load
    initial_cases_res = client.get("/api/v1/cases")
    assert initial_cases_res.status_code == 200
    initial_count = initial_cases_res.json()["total"]
    assert initial_count >= 6

    # STEP 2 & 3: User opens New Case Modal and enters property information
    new_case_payload = {
        "borrowerName": "Meera & Siddharth Varma",
        "coBorrowerName": "Siddharth Varma",
        "cibilScore": 810,
        "city": "Bengaluru",
        "projectName": "Total Environment Windmills of Your Mind",
        "locality": "EPIP Zone, Whitefield",
        "unitAddress": "Apartment 502, Tower 2",
        "pincode": "560066",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 2500,
        "superBuiltUpAreaSqFt": 3300,
        "floorNo": 5,
        "totalFloors": 14,
        "ageYears": 1,
        "roadWidthFt": 60,
        "loanRequested": 25000000,           # ₹2.5 Cr
        "declaredAgreementValue": 35000000,  # ₹3.5 Cr
        "circleRatePerSqFt": 11000,
        "baseMarketRatePerSqFt": 14500,
        "floorRiseFactor": 300,
        "roadWidthFactor": 300,
        "amenitiesPremium": 600,
        "structuralDepreciation": 100,
        "underwriterHaircutPct": -3.0,
        "distressDiscountPct": 18.0,
        "ltvRatioPct": 75.0,
        "legalRiskPenaltyPct": 0.0,
        "assignedUnderwriter": "V. Sundaram (Sr. Underwriter - Tech Risk)",
    }

    # STEP 4: Frontend submits the request to FastAPI
    # STEP 5: Backend validates the request
    # STEP 6: Valuation engine calculates the estimate
    # STEP 7: Backend stores the valuation, property, and case records
    create_res = client.post("/api/v1/cases", json=new_case_payload)
    assert create_res.status_code == 201
    created_case = create_res.json()

    # STEP 8: Frontend receives and displays the valuation result
    created_id = created_case["id"]
    assert created_case["borrowerName"] == "Meera & Siddharth Varma"
    assert created_case["projectName"] == "Total Environment Windmills of Your Mind"
    assert created_case["status"] == "READY_FOR_APPROVAL"
    assert created_case["dataSource"] == "synthetic-demo"

    val = created_case["latestValuation"]
    assert val is not None
    assert val["engineType"] == "provisional rule-based estimation"
    assert val["netAssessedValue"] > 0
    assert val["grossMarketValue"] > 0
    assert val["maxSanctionAmount"] > 0
    assert len(val["attributionBreakdown"]) == 5

    # STEP 9: User reopens the saved case from the case queue or pipeline
    fetch_saved_res = client.get(f"/api/v1/cases/{created_id}")
    assert fetch_saved_res.status_code == 200
    saved_case = fetch_saved_res.json()
    assert saved_case["id"] == created_id

    # STEP 10: User views and interacts with valuation details (e.g. stress-test haircut override)
    update_res = client.put(f"/api/v1/cases/{created_id}", json={
        "underwriterHaircutPct": -5.0,
        "distressDiscountPct": 20.0,
    })
    assert update_res.status_code == 200
    updated_case = update_res.json()
    assert updated_case["underwriterHaircutPct"] == -5.0
    assert updated_case["distressDiscountPct"] == 20.0
    # Net assessed value reflects the updated haircut
    assert updated_case["latestValuation"]["netAssessedValue"] < val["netAssessedValue"]

    # Final sign-off transition
    signoff_res = client.patch(f"/api/v1/cases/{created_id}/status", json={
        "status": "APPROVED",
        "auditNote": "Valuation approved and digitally recorded.",
    })
    assert signoff_res.status_code == 200
    assert signoff_res.json()["status"] == "APPROVED"

