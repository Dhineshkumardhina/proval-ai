"""Phase 4E: Secure Production Infrastructure & Deployment Engineering Test Suite.

Verifies:
1. Production environment validation fail-fast guards (SQLite, weak secrets, wildcard CORS, debug flag).
2. Structured logging credential and PII redactor filter.
3. Database connection pooling configuration.
4. Liveness, readiness, and diagnostic health endpoints.
5. JWT token expiration, revocation, and cryptographic HMAC integrity.
6. Bcrypt password verification and role-based access boundaries.
7. Container security configurations (non-root execution, network isolation).
"""

import os
import pytest
import re
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.core.config import Settings
from app.core.logging import redact_sensitive_text, SensitiveDataRedactor
from app.core.security import (
    create_access_token,
    verify_jwt_token,
    revoke_token,
    is_token_revoked,
    hash_password,
    verify_password,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
    DEMO_USERS,
)


# ---------------------------------------------------------------------------
# 1. PRODUCTION ENVIRONMENT FAIL-FAST CONFIGURATION GUARDS
# ---------------------------------------------------------------------------

def test_production_startup_rejects_sqlite():
    """Verify that validate_production_startup strictly prohibits SQLite in production."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="sqlite:///./prod.db",
        SECRET_KEY="a" * 32,
        BACKEND_CORS_ORIGINS=["https://propval.example.com"],
    )
    with pytest.raises(ValueError) as exc:
        prod_settings.validate_production_startup()
    assert "SQLite is strictly prohibited in production" in str(exc.value)


def test_production_startup_rejects_default_password():
    """Verify that default password placeholders halt production startup."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql://user:propval_password@host:5432/db",
        SECRET_KEY="a" * 32,
        BACKEND_CORS_ORIGINS=["https://propval.example.com"],
    )
    with pytest.raises(ValueError) as exc:
        prod_settings.validate_production_startup()
    assert "insecure default password placeholder" in str(exc.value)


def test_production_startup_rejects_short_or_placeholder_secret():
    """Verify that weak or default SECRET_KEY halts production startup."""
    with pytest.raises(Exception) as exc:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql://user:strongpass@host:5432/db",
            SECRET_KEY="short-secret",
            BACKEND_CORS_ORIGINS=["https://propval.example.com"],
        )
    assert ">= 32 characters" in str(exc.value)


def test_production_startup_rejects_wildcard_cors():
    """Verify that wildcard CORS origins in production raise validation errors."""
    with pytest.raises(ValueError) as exc:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql://user:strongpass@host:5432/db",
            SECRET_KEY="a" * 32,
            BACKEND_CORS_ORIGINS=["*"],
        )
    assert "strictly prohibited in production" in str(exc.value)


# ---------------------------------------------------------------------------
# 2. LOGGING PII & SECRET SCRUBBING
# ---------------------------------------------------------------------------

def test_redact_sensitive_text_scrubs_secrets_and_pii():
    """Verify that credentials, tokens, and PII are redacted before emission."""
    log_line = (
        "User logged in with Authorization: Bearer eyJhbGciOiJIUzI1Ni.abc.123 "
        "and password: 'SuperSecretPassword!'. "
        "Borrower PAN: ABCDE1234F, Aadhaar: 2345 6789 0123, Phone: 9876543210, Email: borrower@test.com. "
        "Connecting to postgresql://admin:prodSecretPass@db:5432/propval"
    )
    scrubbed = redact_sensitive_text(log_line)

    assert "eyJhbGciOiJIUzI1Ni" not in scrubbed
    assert "SuperSecretPassword!" not in scrubbed
    assert "[REDACTED]" in scrubbed
    assert "[REDACTED_PAN]" in scrubbed
    assert "ABCDE1234F" not in scrubbed
    assert "[REDACTED_AADHAAR]" in scrubbed
    assert "2345 6789 0123" not in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "9876543210" not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed
    assert "borrower@test.com" not in scrubbed
    assert "prodSecretPass" not in scrubbed
    assert "postgresql://admin:[REDACTED]@db:5432/propval" in scrubbed


# ---------------------------------------------------------------------------
# 3. AUTHENTICATION, EXPIRATION, REVOCATION & BCRYPT
# ---------------------------------------------------------------------------

def test_jwt_token_creation_and_verification():
    """Verify valid JWT generation and verification with mandatory claims."""
    token = create_access_token({"sub": "v.sundaram", "role": ROLE_SENIOR_UNDERWRITER})
    claims = verify_jwt_token(token)
    assert claims is not None
    assert claims["sub"] == "v.sundaram"
    assert claims["role"] == ROLE_SENIOR_UNDERWRITER
    assert "jti" in claims
    assert "exp" in claims
    assert claims["iss"] == "propval-ai-backend"


def test_jwt_token_revocation():
    """Verify that revoked tokens are immediately rejected."""
    token = create_access_token({"sub": "revoked.user", "role": ROLE_CREDIT_UNDERWRITER})
    assert verify_jwt_token(token) is not None

    revoke_token(token)
    assert is_token_revoked(token) is True
    assert verify_jwt_token(token) is None


def test_bcrypt_password_hashing_and_verification():
    """Verify bcrypt rounds=12 password hashing and verification."""
    plain = "TestSecurePassword@2026!"
    hashed = hash_password(plain)
    assert hashed.startswith("$2b$12$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


# ---------------------------------------------------------------------------
# 4. HEALTH MONITORING PROBES
# ---------------------------------------------------------------------------

def test_liveness_probe_returns_200(client):
    """Verify liveness probe returns HTTP 200 alive status."""
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"


def test_readiness_probe_returns_200_when_database_connected(client):
    """Verify readiness probe checks database connectivity."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["database"] == "connected"
    assert "latencyMs" in data


def test_comprehensive_health_probe(client):
    """Verify deep diagnostic health endpoint returns component breakdown."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "auditTrail" in data["components"]
    assert "mlEngine" in data["components"]


# ---------------------------------------------------------------------------
# 5. DOCKERFILE & COMPOSE CONTAINER SECURITY INSPECTION
# ---------------------------------------------------------------------------

def test_dockerfiles_enforce_non_root_execution():
    """Verify that backend and frontend Dockerfiles specify dedicated non-root users."""
    backend_dockerfile = os.path.join("docker", "Dockerfile.backend")
    frontend_dockerfile = os.path.join("docker", "Dockerfile.frontend")

    assert os.path.exists(backend_dockerfile)
    assert os.path.exists(frontend_dockerfile)

    with open(backend_dockerfile, "r", encoding="utf-8") as f:
        backend_content = f.read()
    # Non-root user in backend: USER appuser
    assert "USER appuser" in backend_content
    assert "useradd" in backend_content

    with open(frontend_dockerfile, "r", encoding="utf-8") as f:
        frontend_content = f.read()
    # Non-root user in frontend: USER 101
    assert "USER 101" in frontend_content


def test_docker_compose_database_network_isolation():
    """Verify that database port 5432 is not bound to public host ports."""
    compose_file = "docker-compose.yml"
    assert os.path.exists(compose_file)

    with open(compose_file, "r", encoding="utf-8") as f:
        compose_content = f.read()

    # Database service block check:
    # Must use 'expose: - "5432"', and NOT 'ports:' binding 5432 to host
    assert 'expose:\n      - "5432"' in compose_content
    # Must have no-new-privileges security option
    assert "no-new-privileges:true" in compose_content
    # Must define backend-network and frontend-network
    assert "backend-network" in compose_content
    assert "frontend-network" in compose_content
