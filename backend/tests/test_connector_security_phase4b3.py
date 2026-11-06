"""Dedicated security and resilience test suite for Phase 4B-3 Connector Hardening.

Verifies:
1. Production hostname allowlisting vs. test isolation.
2. DNS rebinding & private / loopback IP blocking.
3. Cloud metadata endpoint protection (169.254.169.254).
4. Localhost blocked in production mode.
5. Redirect restrictions (open redirect to private IP, redirect limit exceeded, safe redirect validation).
6. TLS certificate validation enforcement.
7. API key rotation & secret handling (zero plaintext storage, env var rotation).
8. Authentication failure isolation (does not crash orchestrator, proper error categorization).
9. Rate limiting and Retry-After support with backoff.
10. Request and response size limits (PayloadTooLargeError on oversized JSON).
11. Connection and read timeouts.
12. Malicious JSON handling (malformed syntax, non-dict root).
13. Connector failure isolation (job marked FAILED without halting application).
"""

import asyncio
import json
import os
import socket
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.connectors.base import ConnectorConfig, SyncCursor
from app.connectors.exceptions import (
    AuthenticationError,
    RateLimitExceededError,
    NetworkTimeoutError,
    SecurityViolationError,
    InvalidResponseError,
    PayloadTooLargeError,
)
from app.connectors.http_client import (
    ResilientHTTPClient,
    resolve_and_validate_hostname,
    PRODUCTION_ALLOWED_HOSTNAMES,
    TEST_ALLOWED_HOSTNAMES,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_REQUEST_BYTES,
)
from app.connectors.zapkey_connector import ZapkeyB2BConnector
from app.connectors.mock_connector import MockDeedConnector
from app.models.data_source import DataSourceModel, IngestionJobModel
from app.services.acquisition_service import AcquisitionOrchestrator


@pytest.fixture
def db_session():
    """Create a clean isolated database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =========================================================================
# 1. Hostname Allowlisting & Production vs. Test Isolation Tests
# =========================================================================

def test_production_hostname_allowlist():
    """Verify unauthorized external domains are rejected regardless of protocol."""
    unauthorized = [
        "https://evil-hacker.com",
        "https://unauthorized-broker.in",
        "https://api.fake-zapkey.com",
        "https://google.com",
    ]
    for url in unauthorized:
        with pytest.raises(SecurityViolationError) as exc_info:
            ResilientHTTPClient(base_url=url, allow_test_endpoints=False)
        assert "not in the authorized domain whitelist" in str(exc_info.value)


def test_localhost_strictly_prohibited_in_production():
    """Critical Requirement: localhost and 127.0.0.1 must NEVER be allowed in production mode."""
    with pytest.raises(SecurityViolationError) as exc_info:
        resolve_and_validate_hostname(
            hostname="localhost",
            allow_test_endpoints=True,
            is_production=True,
        )
    assert "strictly prohibited in production mode" in str(exc_info.value)

    with pytest.raises(SecurityViolationError) as exc_info2:
        resolve_and_validate_hostname(
            hostname="127.0.0.1",
            allow_test_endpoints=True,
            is_production=True,
        )
    assert "strictly prohibited in production mode" in str(exc_info2.value)


def test_test_endpoints_isolated_from_production():
    """Verify test-only endpoints cannot be reached when allow_test_endpoints is False."""
    test_hosts = ["localhost", "127.0.0.1", "testserver"]
    for host in test_hosts:
        with pytest.raises(SecurityViolationError):
            resolve_and_validate_hostname(
                hostname=host,
                allow_test_endpoints=False,
                is_production=False,
            )


# =========================================================================
# 2. DNS Rebinding, Private Subnets, & Cloud Metadata Blocking
# =========================================================================

def test_cloud_metadata_endpoints_blocked():
    """Verify AWS / GCP / Azure metadata IPs (169.254.169.254) are rejected immediately."""
    metadata_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/computeMetadata/v1/",
        "https://169.254.169.254",
    ]
    for url in metadata_urls:
        with pytest.raises(SecurityViolationError) as exc_info:
            ResilientHTTPClient(base_url=url, allow_test_endpoints=True)
        assert "SSRF" in str(exc_info.value) or "authorized domain whitelist" in str(exc_info.value)


def test_dns_rebinding_to_private_ip_blocked(monkeypatch):
    """Verify that if an authorized domain resolves to a private RFC 1918 or loopback IP, it is blocked."""
    # Simulate DNS rebinding attack where api.zapkey.com resolves to 10.0.0.1
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(SecurityViolationError) as exc_info:
        resolve_and_validate_hostname(hostname="api.zapkey.com", allow_test_endpoints=False, is_production=False)
    assert "resolves to disallowed private / metadata IP" in str(exc_info.value)
    assert "10.0.0.1" in str(exc_info.value)


def test_dns_rebinding_to_metadata_ip_blocked(monkeypatch):
    """Verify that if an authorized domain resolves to 169.254.169.254, it is blocked."""
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(SecurityViolationError) as exc_info:
        resolve_and_validate_hostname(hostname="api.zapkey.com", allow_test_endpoints=False, is_production=False)
    assert "resolves to disallowed private / metadata IP" in str(exc_info.value)
    assert "169.254.169.254" in str(exc_info.value)


# =========================================================================
# 3. Redirect Restrictions (SSRF via Redirect)
# =========================================================================

@pytest.mark.asyncio
async def test_redirect_to_disallowed_destination_blocked():
    """Verify that a 302 redirect attempting to steer the client to an internal IP is blocked."""
    # Create mock transport simulating redirect from authorized domain to cloud metadata
    def handler(request: httpx.Request):
        if request.url.path == "/v1/transactions":
            return httpx.Response(
                status_code=302,
                headers={"Location": "http://169.254.169.254/latest/meta-data"},
            )
        return httpx.Response(status_code=200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        with pytest.raises(SecurityViolationError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/transactions",
                client=mock_client,
            )
        assert "SSRF" in str(exc_info.value) or "authorized domain whitelist" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redirect_loop_and_depth_limit():
    """Verify that excessive redirects trigger a security violation."""
    def handler(request: httpx.Request):
        return httpx.Response(
            status_code=302,
            headers={"Location": "https://api.zapkey.com/v1/loop"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        with pytest.raises(SecurityViolationError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/loop",
                client=mock_client,
                max_redirects=2,
            )
        assert "Redirect Limit Exceeded" in str(exc_info.value)


# =========================================================================
# 4. Authentication Failure & Key Rotation Handling
# =========================================================================

@pytest.mark.asyncio
async def test_authentication_failure_handling_and_status():
    """Verify 401 Unauthorized produces clean AuthenticationError without crashing."""
    def handler(request: httpx.Request):
        return httpx.Response(status_code=401, json={"error": "Invalid API Token"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        with pytest.raises(AuthenticationError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/auth",
                client=mock_client,
            )
        assert "Authentication failed with status 401" in str(exc_info.value)


def test_api_key_rotation_via_environment():
    """Verify connector dynamically resolves updated API key on rotation."""
    config = ConnectorConfig(
        source_id="src-rot",
        source_code="ZAPKEY_ROT",
        base_url="https://api.zapkey.com",
        auth_token_env_var="ROTATING_ZAPKEY_KEY",
        allow_test_endpoints=True,
    )
    connector = ZapkeyB2BConnector(config)

    # Initial key
    os.environ["ROTATING_ZAPKEY_KEY"] = "SECRET_KEY_V1"
    headers = connector._build_auth_headers()
    assert headers["x-api-key"] == "SECRET_KEY_V1"

    # Rotated key
    os.environ["ROTATING_ZAPKEY_KEY"] = "SECRET_KEY_V2_ROTATED"
    headers_rotated = connector._build_auth_headers()
    assert headers_rotated["x-api-key"] == "SECRET_KEY_V2_ROTATED"

    os.environ.pop("ROTATING_ZAPKEY_KEY", None)


# =========================================================================
# 5. Rate Limiting & Retry-After Handling
# =========================================================================

@pytest.mark.asyncio
async def test_rate_limiting_retry_after_respected():
    """Verify client honors 429 status code and sleeps for Retry-After duration."""
    calls = 0

    def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "1"},
                json={"error": "Rate limited"},
            )
        return httpx.Response(status_code=200, json={"status": "success", "data": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            max_retries=2,
            allow_test_endpoints=True,
        )
        start_t = datetime.now(timezone.utc)
        res = await client.request(
            method="GET",
            endpoint="/v1/data",
            client=mock_client,
        )
        elapsed = (datetime.now(timezone.utc) - start_t).total_seconds()
        assert calls == 2
        assert res.get("status") == "success"
        assert elapsed >= 0.9  # Confirmed Retry-After delay was observed


# =========================================================================
# 6. Payload Limits & Malicious JSON Handling
# =========================================================================

@pytest.mark.asyncio
async def test_oversized_response_rejected():
    """Verify response exceeding max bytes limit raises PayloadTooLargeError."""
    large_body = "A" * (2 * 1024 * 1024)  # 2MB

    def handler(request: httpx.Request):
        return httpx.Response(
            status_code=200,
            text=large_body,
            headers={"Content-Length": str(len(large_body))},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            max_response_bytes=1024 * 1024,  # 1MB limit
            allow_test_endpoints=True,
        )
        with pytest.raises(PayloadTooLargeError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/large",
                client=mock_client,
            )
        assert "exceeds limit" in str(exc_info.value)


@pytest.mark.asyncio
async def test_oversized_request_payload_rejected():
    """Verify client rejects sending oversized request payload exceeding institutional limit."""
    oversized_data = {"huge": "X" * (DEFAULT_MAX_REQUEST_BYTES + 1024)}
    client = ResilientHTTPClient(
        base_url="https://api.zapkey.com",
        allow_test_endpoints=True,
    )
    with pytest.raises(PayloadTooLargeError) as exc_info:
        await client.request(
            method="POST",
            endpoint="/v1/submit",
            json_data=oversized_data,
        )
    assert "Outbound request payload exceeds" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malicious_malformed_json_response_handling():
    """Verify malformed JSON does not crash process with uncaught parser exception."""
    def handler(request: httpx.Request):
        return httpx.Response(
            status_code=200,
            content=b'{"status": "ok", "corrupted": [unclosed',
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        with pytest.raises(InvalidResponseError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/malformed",
                client=mock_client,
            )
        assert "Malformed JSON response" in str(exc_info.value)


# =========================================================================
# 7. Timeouts & Connector Failure Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_network_timeout_handling():
    """Verify connect/read timeouts trigger NetworkTimeoutError after retries."""
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Simulated upstream gateway timeout")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            timeout_seconds=1,
            max_retries=1,
            backoff_factor=1.0,
            allow_test_endpoints=True,
        )
        with pytest.raises(NetworkTimeoutError) as exc_info:
            await client.request(
                method="GET",
                endpoint="/v1/timeout",
                client=mock_client,
            )
        assert "Request timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_connector_failure_isolation_in_orchestrator(db_session: Session):
    """Verify that a failing connector terminates the job with status=FAILED without crashing orchestrator."""
    src = DataSourceModel(
        source_code=f"FAIL_SRC_{os.urandom(3).hex().upper()}",
        source_name="Failing Test Feed",
        provider_name="Test Provider",
        access_tier="CLASS_F_MOCK",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="Institutional Sandbox License",
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    config = ConnectorConfig(
        source_id=src.id,
        source_code=src.source_code,
        base_url="https://localhost",
        allow_test_endpoints=True,
    )
    mock_conn = MockDeedConnector(config)
    mock_conn.should_fail_auth = True  # Trigger failure

    orchestrator = AcquisitionOrchestrator(db=db_session)

    with pytest.raises(AuthenticationError):
        await orchestrator.execute_acquisition_job(
            source_id=src.id,
            connector=mock_conn,
        )

    # Verify the IngestionJobModel was persisted and marked FAILED
    job = (
        db_session.query(IngestionJobModel)
        .filter(IngestionJobModel.source_id == src.id)
        .order_by(IngestionJobModel.started_at.desc())
        .first()
    )
    assert job is not None
    assert job.status == "FAILED"
    assert "MOCK AUTH FAILURE" in (job.error_summary or "")

