"""Tests for Comparable deeds query endpoint."""

from fastapi.testclient import TestClient


def test_search_comparables_all(client: TestClient):
    """GET /api/v1/comparables returns comparable deeds extracted from cases."""
    response = client.get("/api/v1/comparables")
    assert response.status_code == 200
    comps = response.json()
    assert isinstance(comps, list)
    assert len(comps) > 0
    first_comp = comps[0]
    assert "sroRegNo" in first_comp
    assert "registeredPrice" in first_comp
    assert first_comp.get("dataSource") == "synthetic-demo"


def test_search_comparables_by_case(client: TestClient):
    """GET /api/v1/comparables?case_id=case-blr-89412 returns only comparables for that case."""
    response = client.get("/api/v1/comparables?case_id=case-blr-89412")
    assert response.status_code == 200
    comps = response.json()
    assert len(comps) >= 1
    assert any("Sobha" in c["propertyName"] for c in comps)

