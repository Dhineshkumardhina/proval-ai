"""Validation tests for production deployment health checks, readiness probes,
fail-fast configuration validator, and sensitive data log redaction.
"""

import logging
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.logging import redact_sensitive_text, SensitiveDataRedactor, log_security_event


def test_liveness_probes(client: TestClient):
    """Liveness probe must return 200 OK with alive status on both root and v1 paths."""
    for path in ["/health/live", "/api/v1/health/live"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


def test_readiness_probe_healthy(client: TestClient):
    """Readiness probe returns ready status when database is reachable."""
    for path in ["/health/ready", "/api/v1/health/ready"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["database"] == "connected"
        assert "mlEngine" in data
        assert "geminiIntegration" in data


def test_readiness_probe_database_failure(client: TestClient):
    """When database connectivity fails, readiness probe must return 503 Service Unavailable."""
    with patch("app.api.v1.endpoints.health.check_db_connectivity", return_value=(False, 0.0, "unknown")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
        assert data["database"] == "unavailable"
        assert data["status"] == "unhealthy"


def test_unavailable_external_service_not_reported_healthy(client: TestClient):
    """Rule enforcement: An unavailable external service must not be reported as healthy."""
    # Simulate Gemini service failure (HTTP 403 Forbidden or API outage)
    with patch(
        "app.api.v1.endpoints.health.check_gemini_integration",
        return_value={
            "status": "unavailable",
            "model": "gemini-2.5-flash",
            "cloudProcessingEnabled": False,
            "error": "Gemini API authentication/endpoint error: HTTP 403",
        },
    ):
        # 1. Readiness probe must report degraded status
        ready_resp = client.get("/health/ready")
        assert ready_resp.status_code == 200
        ready_data = ready_resp.json()
        assert ready_data["status"] == "degraded"
        assert ready_data["geminiIntegration"] == "unavailable"

        # 2. Comprehensive health check must NOT report "healthy"
        health_resp = client.get("/health")
        health_data = health_resp.json()
        assert health_data["status"] == "degraded"
        assert health_data["components"]["geminiIntegration"]["status"] == "unavailable"


def test_production_settings_validator_catches_sqlite():
    """In production environment, SQLite is strictly forbidden."""
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="sqlite:///./insecure.db",
        SECRET_KEY="a" * 32,
        BACKEND_CORS_ORIGINS=["https://example.com"],
    )
    with pytest.raises(ValueError, match="SQLite is strictly prohibited in production"):
        settings.validate_production_startup()


def test_production_settings_validator_catches_weak_secret():
    """In production environment, weak or placeholder SECRET_KEY is rejected."""
    with pytest.raises((ValueError, Exception), match="CRITICAL SECURITY CONFIGURATION ERROR"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql://user:pass@db:5432/proddb",
            SECRET_KEY="short",
            BACKEND_CORS_ORIGINS=["https://example.com"],
        )


def test_production_settings_validator_catches_wildcard_cors():
    """In production environment, wildcard '*' in CORS is rejected."""
    with pytest.raises(ValueError, match="Wildcard '\\*' in BACKEND_CORS_ORIGINS is strictly prohibited"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql://user:pass@db:5432/proddb",
            SECRET_KEY="a" * 32,
            BACKEND_CORS_ORIGINS=["*"],
        )


def test_log_redaction_secrets_and_pii():
    """Verify passwords, tokens, API keys, Aadhaar, and PAN are redacted from logs."""
    test_message = (
        "User login failed with password: 'SuperSecretPassword123' "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token.sig "
        "Aadhaar: 2345 6789 0123 PAN: ABCDE1234F "
        "postgresql://prod_user:StrongPassword987@db:5432/propval_db"
    )
    redacted = redact_sensitive_text(test_message)

    assert "SuperSecretPassword123" not in redacted
    assert "[REDACTED]" in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "2345 6789 0123" not in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_PAN]" in redacted
    assert "StrongPassword987" not in redacted


def test_request_correlation_id_header(client: TestClient):
    """Every request must be tagged with an X-Request-ID header."""
    response = client.get("/health/live")
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"].startswith("req-")
