"""Tests for authentication and role-based access endpoints."""

from fastapi.testclient import TestClient


def test_auth_token_success(client: TestClient):
    """POST /api/v1/auth/token generates valid access token for demo account."""
    response = client.post("/api/v1/auth/token", json={
        "username": "senior_underwriter",
        "password": "SrUnderwriter@2026!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "SENIOR_UNDERWRITER"
    assert data["token_type"] == "bearer"


def test_auth_token_invalid_user(client: TestClient):
    """POST /api/v1/auth/token returns 401 for unknown user."""
    response = client.post("/api/v1/auth/token", json={
        "username": "unknown_intruder",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_authenticated_request_with_bearer_token(client: TestClient):
    """Requests with valid Bearer token authenticate properly."""
    # Obtain token
    token_res = client.post("/api/v1/auth/token", json={
        "username": "underwriter",
        "password": "CreditUnderwriter@2026!",
    })
    token = token_res.json()["access_token"]

    # Use token in header
    response = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_invalid_bearer_token_rejected(unauthenticated_client: TestClient):
    """Requests with forged Bearer token return 401 Unauthorized."""
    response = unauthenticated_client.get("/api/v1/cases", headers={"Authorization": "Bearer forged-token-xyz"})
    assert response.status_code == 401

