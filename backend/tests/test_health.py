"""Tests for root and API v1 health endpoints."""

from fastapi.testclient import TestClient


def test_root_health(client: TestClient):
    """GET /health returns healthy status, service name and version."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert data["version"] == "0.2.0"
    assert data["engineType"] == "provisional rule-based estimation"
    assert "timestamp" in data


def test_api_v1_health(client: TestClient):
    """GET /api/v1/health returns database connectivity status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == "0.2.0"
    assert data["engineType"] == "provisional rule-based estimation"

