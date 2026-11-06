"""Tests for valuation estimation API endpoint (POST /api/v1/valuation/estimate)."""

from fastapi.testclient import TestClient


def test_estimate_valuation_endpoint_success(client: TestClient):
    """POST /api/v1/valuation/estimate returns 200 with full valuation payload."""
    payload = {
        "carpetAreaSqFt": 1250,
        "superBuiltUpAreaSqFt": 1650,
        "baseMarketRatePerSqFt": 9800,
        "circleRatePerSqFt": 7800,
        "floorRiseFactor": 350,
        "roadWidthFactor": 250,
        "amenitiesPremium": 400,
        "structuralDepreciation": 150,
        "underwriterHaircutPct": -5,
        "distressDiscountPct": 20,
        "ltvRatioPct": 75,
        "legalRiskPenaltyPct": 0,
        "applicationNo": "APP-TEST-001",
        "dataSource": "synthetic-demo",
    }
    response = client.post("/api/v1/valuation/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ruleAdjustedRatePerSqFt"] == 10650
    assert data["aiAdjustedRatePerSqFt"] == 10650
    assert data["grossMarketValue"] == 13312500
    assert data["netAssessedValue"] == 12646875
    assert data["distressLiquidationValue"] == 10117500
    assert data["maxSanctionAmount"] == 9485156
    assert data["deviationFromCircleRatePct"] == 36.5
    assert data["confidenceScorePct"] == 85.5
    assert data["engineVersion"] == "0.2.0"
    assert data["engineType"] == "provisional rule-based estimation"
    assert data["dataSource"] == "synthetic-demo"
    assert data["isProvisional"] is True
    assert len(data["attributionBreakdown"]) == 5


def test_estimate_valuation_validation_failure(client: TestClient):
    """POST /api/v1/valuation/estimate returns 422 if required fields are missing."""
    # Missing carpetAreaSqFt and baseMarketRatePerSqFt
    payload = {
        "superBuiltUpAreaSqFt": 1650,
        "circleRatePerSqFt": 7800,
    }
    response = client.post("/api/v1/valuation/estimate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
