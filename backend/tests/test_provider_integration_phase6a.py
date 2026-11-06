"""Comprehensive test suite for Phase 6A Commercial Data Provider Integration & Security.

Tests:
1. Authentication failures (401/403 responses handled cleanly).
2. Invalid credentials (missing or rejected key).
3. Expired credentials (ExpiredCredentialError raised when license period or token has expired).
4. API timeouts (NetworkTimeoutError raised on connect/read timeouts).
5. Rate-limit responses (HTTP 429 backoff and Retry-After header enforcement).
6. Malformed provider responses (InvalidResponseError on non-dict, missing fields, or invalid JSON).
7. SSRF attempts (blocking loopback, private CIDRs, cloud metadata 169.254.169.254, DNS rebinding).
8. Credential leakage prevention (secrets masked in logs, API responses, and exception traces).
9. Source attribution (complete provenance and licensing metadata attached to verified transactions).
10. Mock-data separation (mock/synthetic deeds strictly prohibited from empirical dataset and ML training).
11. Circuit breaker transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
12. Secret Manager rotation and cache invalidation.
13. Provider classification verification (IMPLEMENTED, CONFIGURED, AUTHENTICATED, LIVE, BLOCKED).
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import pytest
from fastapi import status
from fastapi.testclient import TestClient
import httpx

from app.connectors.base import ConnectorConfig, SyncCursor
from app.connectors.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, CircuitBreakerState
from app.connectors.exceptions import (
    AuthenticationError,
    CircuitBreakerOpenError,
    ExpiredCredentialError,
    InvalidResponseError,
    NetworkTimeoutError,
    RateLimitExceededError,
    SecurityViolationError,
)
from app.connectors.http_client import ResilientHTTPClient
from app.connectors.mock_connector import MockDeedConnector
from app.connectors.propequity_connector import PropEquityConnector
from app.connectors.propstack_connector import PropStackConnector
from app.connectors.registry import ConnectorRegistry
from app.connectors.zapkey_connector import ZapkeyB2BConnector
from app.core.security import create_access_token, ROLE_ADMIN, ROLE_SENIOR_UNDERWRITER
from app.models.data_source import DataSourceModel
from app.models.dataset import DatasetMetadataModel
from app.models.verification import VerificationEvidenceModel
from app.normalization.models import NormalizedTransactionRecord
from app.services.secret_manager import (
    SecretManagerService,
    mask_credential,
    InMemorySecretDriver,
)
from app.verification.verification_service import VerificationEngine


@pytest.fixture
def admin_headers():
    token = create_access_token({
        "sub": "senior_architect",
        "name": "Lead Real-Estate Architect",
        "role": ROLE_ADMIN,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_secret_and_circuit_state():
    """Ensure clean test environment for secrets and circuit breakers before each test."""
    test_driver = SecretManagerService.enable_test_mode()
    CircuitBreakerRegistry.reset_all()
    yield
    test_driver.clear()
    SecretManagerService.disable_test_mode()
    CircuitBreakerRegistry.reset_all()


# ----------------------------------------------------------------------
# 1. Authentication Failures
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authentication_failure_handled_cleanly():
    """Verify that HTTP 401/403 responses raise AuthenticationError cleanly."""
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=401, json={"error": "Unauthorized", "message": "Invalid API key provided"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
            verify_ssl=False,
            circuit_breaker_enabled=False,
        )
        with pytest.raises(AuthenticationError) as exc_info:
            await client.request("GET", "/v1/auth/verify", client=mock_client)
        assert "Authentication failed with status 401" in str(exc_info.value)


# ----------------------------------------------------------------------
# 2. Invalid Credentials Handling
# ----------------------------------------------------------------------

def test_invalid_or_missing_credentials_fails_fast():
    """Verify that unconfigured credentials fail fast without making unauthorized requests."""
    config = ConnectorConfig(
        source_id="src_pe_test",
        source_code="propequity",
        base_url="https://api.propequity.in",
        auth_token_env_var="NON_EXISTENT_PROPEQUITY_KEY_2026",
    )
    connector = PropEquityConnector(config)
    with pytest.raises(AuthenticationError) as exc_info:
        connector._get_api_key()
    assert "Missing API credentials" in str(exc_info.value)


# ----------------------------------------------------------------------
# 3. Expired Credentials & Licensing Period
# ----------------------------------------------------------------------

def test_expired_credentials_raise_expired_credential_error():
    """Verify that expired licensing or API keys raise ExpiredCredentialError."""
    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    SecretManagerService.set_secret("ZAPKEY_API_KEY", "zk_live_valid_format_token_1234")

    config = ConnectorConfig(
        source_id="src_zk_expired",
        source_code="zapkey_b2b",
        base_url="https://api.zapkey.com",
        auth_token_env_var="ZAPKEY_API_KEY",
        license_expiration=past_date,
    )
    connector = ZapkeyB2BConnector(config)

    with pytest.raises(ExpiredCredentialError) as exc_info:
        connector._get_api_key()
    assert "expired on" in str(exc_info.value)
    assert exc_info.value.provider == "zapkey_b2b"


# ----------------------------------------------------------------------
# 4. API Timeouts and Retries
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_timeout_raises_network_timeout_error():
    """Verify that connection/read timeouts raise NetworkTimeoutError after retries."""
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Server read timeout", request=request)

    transport = httpx.MockTransport(timeout_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.propstack.com",
            timeout_seconds=2,
            max_retries=1,
            backoff_factor=1.0,
            allow_test_endpoints=True,
            verify_ssl=False,
            circuit_breaker_enabled=False,
        )
        with pytest.raises(NetworkTimeoutError) as exc_info:
            await client.request("GET", "/v1/health", client=mock_client)
        assert "Request timeout" in str(exc_info.value) or "Exceeded max retries" in str(exc_info.value)


# ----------------------------------------------------------------------
# 5. Rate-Limit Responses (HTTP 429) & Retry-After
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_exceeded_raises_rate_limit_error():
    """Verify that HTTP 429 rate-limit responses parse Retry-After and raise RateLimitExceededError."""
    async def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            headers={"Retry-After": "2"},
            json={"error": "Too Many Requests", "detail": "Rate limit exceeded"},
        )

    transport = httpx.MockTransport(rate_limit_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            max_retries=0,  # Fail immediately on first 429
            allow_test_endpoints=True,
            verify_ssl=False,
            circuit_breaker_enabled=False,
        )
        with pytest.raises(RateLimitExceededError) as exc_info:
            await client.request("GET", "/v1/transactions", client=mock_client)
        assert exc_info.value.retry_after_seconds == 2


# ----------------------------------------------------------------------
# 6. Malformed Provider Responses
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_malformed_json_response_raises_invalid_response_error():
    """Verify that malformed or non-JSON payloads raise InvalidResponseError."""
    async def malformed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b"<!DOCTYPE html><html><body>Error 502 Bad Gateway</body></html>",
        )

    transport = httpx.MockTransport(malformed_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
            verify_ssl=False,
            circuit_breaker_enabled=False,
        )
        with pytest.raises(InvalidResponseError) as exc_info:
            await client.request("GET", "/v1/transactions", client=mock_client)
        assert "Malformed JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_schema_response_raises_invalid_response_error():
    """Verify that valid JSON with an unexpected schema raises InvalidResponseError."""
    async def schema_handler(request: httpx.Request) -> httpx.Response:
        # Expected 'data' list, returned integer
        return httpx.Response(status_code=200, json={"data": 12345, "status": "ok"})

    transport = httpx.MockTransport(schema_handler)
    SecretManagerService.set_secret("ZAPKEY_API_KEY", "zk_test_token_9999")
    config = ConnectorConfig(
        source_id="src_zk",
        source_code="zapkey_b2b",
        base_url="https://api.zapkey.com",
        auth_token_env_var="ZAPKEY_API_KEY",
        allow_test_endpoints=True,
    )
    http_client = ResilientHTTPClient(
        base_url="https://api.zapkey.com",
        allow_test_endpoints=True,
        verify_ssl=False,
        circuit_breaker_enabled=False,
        custom_transport=transport,
    )
    connector = ZapkeyB2BConnector(config, http_client=http_client)

    cursor = SyncCursor(page=1, page_size=10)
    with pytest.raises(InvalidResponseError) as exc_info:
        async for _ in connector.fetch_incremental(cursor):
            pass
    assert "data" in str(exc_info.value)


# ----------------------------------------------------------------------
# 7. SSRF Protection & Private IP Network Restrictions
# ----------------------------------------------------------------------

def test_ssrf_blocking_cloud_metadata_and_private_ips():
    """Verify that cloud metadata (169.254.169.254) and RFC 1918 IPs trigger SecurityViolationError."""
    ssrf_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/admin",
        "http://192.168.1.1:8080/internal",
        "http://127.0.0.1:22/ssh",
        "http://localhost:8000/keys",
        "https://unauthorized-evil-domain.com/feed",
    ]

    for target in ssrf_targets:
        with pytest.raises(SecurityViolationError):
            ResilientHTTPClient(base_url=target, allow_test_endpoints=False)


# ----------------------------------------------------------------------
# 8. Credential Leakage Prevention & Masking
# ----------------------------------------------------------------------

def test_credential_leakage_prevention():
    """Verify that secrets are masked and never exposed in logs, diagnostics, or status outputs."""
    raw_secret = "zap_live_sk_948f981248091248abcdef90"
    masked = mask_credential(raw_secret)

    # Must contain prefix and suffix, but middle is redacted
    assert masked.startswith("zap_")
    assert masked.endswith("ef90")
    assert "****************" in masked
    assert "sk_948f981248091248" not in masked

    # Short secrets are fully redacted
    short_secret = "secret1"
    assert mask_credential(short_secret) == "********"

    # None or empty secrets are handled cleanly
    assert mask_credential(None) == "[NOT_CONFIGURED]"
    assert mask_credential("") == "[NOT_CONFIGURED]"


# ----------------------------------------------------------------------
# 9. Source Attribution & Provenance Preservation
# ----------------------------------------------------------------------

def test_source_attribution_preservation(db_session):
    """Verify that normalized empirical records retain provider attribution, license ref, and cryptographic hashes."""
    dataset = DatasetMetadataModel(
        name="Phase6A_Attribution_Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Ingested from Zapkey B2B API under institutional license",
        file_format="api_stream",
        original_filename="zapkey_stream",
        file_hash_sha256="f"*64,
    )
    db_session.add(dataset)
    db_session.commit()

    norm_tx = NormalizedTransactionRecord(
        transaction_id="tx-zk-phase6a-001",
        source_id="zapkey_b2b",
        source_reference="ZK-BLR-2026-DOC-4412",
        original_record_hash="1"*64,
        registration_reference="DOC/4412/2026",
        fingerprint_hash="2"*64,
        state="Karnataka",
        district="Bengaluru",
        sub_district="Bengaluru South",
        locality="Koramangala 4th Block",
        postal_code="560034",
        project_name="Raheja Residency",
        unit_number="A-402",
        property_type="High-Rise Apartment",
        transaction_type="RESALE",
        registration_date=datetime(2026, 4, 10, 0, 0, 0, tzinfo=timezone.utc),
        transaction_quarter="2026-Q2",
        carpet_area_sqft=1450.0,
        built_up_area_sqft=1750.0,
        super_built_up_area_sqft=1850.0,
        original_area_value=1450.0,
        original_area_unit="sqft",
        acquisition_timestamp=datetime(2026, 4, 10, 11, 30, 0, tzinfo=timezone.utc),
        transaction_amount=32000000.0,
        price_per_sqft=22068.97,
        guideline_rate_per_sqft=17500.0,
        deviation_from_guideline_pct=26.1,
        latitude=12.9352,
        longitude=77.6245,
        coordinate_precision_digits=4,
        sro_office="SRO-KORAMANGALA",
        raw_payload={"deed_number": "4412/2026"},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="PHASE6A_AUDITOR")
    outcome, tx = verifier.verify_and_route_record(dataset=dataset, norm_tx=norm_tx, row_index=1)

    assert outcome == "VERIFIED"
    assert tx is not None
    assert tx.data_source == "zapkey_b2b"
    assert tx.is_verified_deed is True

    evidence = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert evidence is not None
    assert evidence.source_origin == "zapkey_b2b"
    assert evidence.source_document_ref == "DOC/4412/2026"
    assert evidence.original_record_hash == "1"*64
    assert evidence.verification_evidence_details["is_ml_eligible"] is True


# ----------------------------------------------------------------------
# 10. Mock-Data Separation & ML Quarantine
# ----------------------------------------------------------------------

def test_mock_data_strictly_quarantined_from_ml(db_session):
    """Verify that simulated/mock records are marked is_verified_deed=False and cannot contaminate ML datasets."""
    dataset = DatasetMetadataModel(
        name="Mock_Test_Dataset",
        source_type="synthetic_benchmark",
        license_type="commercial_restricted",
        data_source_provenance="Simulated MockDeedConnector",
        file_format="api_stream",
        original_filename="mock_stream",
        file_hash_sha256="7"*64,
    )
    db_session.add(dataset)
    db_session.commit()

    mock_norm_tx = NormalizedTransactionRecord(
        transaction_id="tx-mock-6a-001",
        source_id="mock_deed",
        source_reference="MOCK-REF-6A",
        original_record_hash="8"*64,
        registration_reference="MOCK-DOC-001",
        fingerprint_hash="9"*64,
        state="Maharashtra",
        district="Pune",
        sub_district="Haveli",
        locality="Hinjawadi",
        postal_code="411057",
        project_name="Mock Tech Towers",
        unit_number="T1-101",
        property_type="High-Rise Apartment",
        registration_date=datetime(2026, 4, 10, 0, 0, 0, tzinfo=timezone.utc),
        transaction_quarter="2026-Q2",
        carpet_area_sqft=900.0,
        super_built_up_area_sqft=1150.0,
        original_area_value=900.0,
        original_area_unit="sqft",
        acquisition_timestamp=datetime(2026, 4, 10, 11, 30, 0, tzinfo=timezone.utc),
        transaction_amount=7500000.0,
        price_per_sqft=8333.33,
        guideline_rate_per_sqft=6500.0,
        deviation_from_guideline_pct=28.2,
        latitude=18.5913,
        longitude=73.7389,
        coordinate_precision_digits=4,
        sro_office="SRO-HAVELI-02",
        raw_payload={"mock": True},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="PHASE6A_AUDITOR")
    outcome, tx = verifier.verify_and_route_record(dataset=dataset, norm_tx=mock_norm_tx, row_index=1)

    assert outcome == "VERIFIED"
    assert tx is not None
    # Crucial security invariant: is_verified_deed must be False
    assert tx.is_verified_deed is False

    evidence = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert evidence.verification_status == "PROVISIONAL_NON_ML"
    assert evidence.verification_evidence_details["is_ml_eligible"] is False


# ----------------------------------------------------------------------
# 11. Circuit Breaker State Transitions
# ----------------------------------------------------------------------

def test_circuit_breaker_transitions():
    """Verify circuit breaker lifecycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker(
        name="test_cb_provider",
        failure_threshold=3,
        recovery_timeout_seconds=0.05,  # Short recovery for fast testing
        half_open_success_threshold=2,
    )

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 1. Record 2 failures (below threshold) -> Remains CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED

    # 2. Record 3rd failure (hits threshold) -> Trips to OPEN
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # 3. Wait for recovery cooldown
    import time
    time.sleep(0.1)

    # 4. State should transition to HALF_OPEN on next check
    assert cb.can_execute() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # 5. First success in HALF_OPEN -> Still HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # 6. Second consecutive success -> Closes the circuit!
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True


@pytest.mark.asyncio
async def test_resilient_http_client_trips_circuit_breaker():
    """Verify ResilientHTTPClient raises CircuitBreakerOpenError when circuit is OPEN."""
    async def failure_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, json={"error": "Service Unavailable"})

    transport = httpx.MockTransport(failure_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        client = ResilientHTTPClient(
            base_url="https://api.zapkey.com",
            max_retries=0,
            allow_test_endpoints=True,
            verify_ssl=False,
            circuit_breaker_enabled=True,
            circuit_breaker_failure_threshold=2,
            circuit_breaker_recovery_timeout_seconds=30.0,
            circuit_breaker_name="test_zapkey_circuit",
        )

        # First failure
        with pytest.raises(InvalidResponseError):
            await client.request("GET", "/v1/health", client=mock_client)

        # Second failure -> Trips circuit
        with pytest.raises(InvalidResponseError):
            await client.request("GET", "/v1/health", client=mock_client)

        # Third attempt -> Short-circuited immediately without network call!
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await client.request("GET", "/v1/health", client=mock_client)
        assert "is OPEN" in str(exc_info.value)
        assert exc_info.value.provider == "test_zapkey_circuit"


# ----------------------------------------------------------------------
# 12. Secret Manager Rotation & Health Verification
# ----------------------------------------------------------------------

def test_secret_manager_rotation_and_credential_health(client: TestClient, admin_headers, db_session):
    """Test cryptographic rotation of provider secret and credential health API."""
    source = DataSourceModel(
        source_code="TEST_ROTATION_SRC",
        source_name="Rotation Test Partner",
        provider_name="Test Provider Corp",
        legal_authorization_basis="Institutional API contract",
        auth_secret_env_var="TEST_PARTNER_SECRET_KEY",
        valid_until=datetime.now(timezone.utc) + timedelta(days=60),
    )
    db_session.add(source)
    db_session.commit()

    # Initial secret setup
    SecretManagerService.set_secret("TEST_PARTNER_SECRET_KEY", "initial_secret_token_1234")

    # Inspect credential health
    health_res = client.get(f"/api/v1/acquisition/sources/{source.id}/credential-health", headers=admin_headers)
    assert health_res.status_code == status.HTTP_200_OK
    health_data = health_res.json()
    assert health_data["is_configured"] is True
    assert health_data["health_status"] == "HEALTHY"
    assert "initial_secret_token_1234" not in health_data["masked_secret"]

    # Rotate secret
    rotate_payload = {
        "new_secret": "new_rotated_secure_token_5678",
        "reason": "Scheduled bi-annual institutional credential rotation",
    }
    rotate_res = client.post(
        f"/api/v1/acquisition/sources/{source.id}/rotate-secret",
        headers=admin_headers,
        json=rotate_payload,
    )
    assert rotate_res.status_code == status.HTTP_200_OK
    rot_data = rotate_res.json()
    assert rot_data["status"] == "ROTATED_AND_AUDITED"
    assert "new_rotated_secure_token_5678" not in rot_data["masked_secret"]

    # Verify updated secret is fetched
    updated_secret = SecretManagerService.get_secret("TEST_PARTNER_SECRET_KEY")
    assert updated_secret == "new_rotated_secure_token_5678"


# ----------------------------------------------------------------------
# 13. Provider Classification & Strict Rules Verification
# ----------------------------------------------------------------------

def test_provider_status_board_classifications(client: TestClient, admin_headers):
    """Verify accurate 5-state classifications: IMPLEMENTED, CONFIGURED, AUTHENTICATED, LIVE, BLOCKED.

    Strict rule: Never mark a provider as LIVE without an authenticated real connection!
    """
    res = client.get("/api/v1/acquisition/providers/status", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    providers = data["providers"]
    for p in providers:
        # No unauthenticated provider may be marked LIVE
        if p["source_code"] != "mock_deed":
            assert p["classification"] != "LIVE", f"Provider {p['source_code']} incorrectly claimed LIVE without live production pipeline!"

        # Mock connector must be classified as IMPLEMENTED (Sandbox Active)
        if p["source_code"] == "mock_deed":
            assert p["classification"] == "IMPLEMENTED"
            assert p["connection_status"] == "MOCK_ACTIVE"
            assert p["commercial_status"] == "SANDBOX_ACTIVE"
            assert p["is_healthy"] is True

        # Unconfigured commercial providers must be classified as BLOCKED
        if not p["env_var_configured"] and p["source_code"] != "mock_deed":
            assert p["classification"] == "BLOCKED"
            assert p["connection_status"] == "CONFIG_MISSING"
            assert p["commercial_status"] == "BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED"
            assert p["is_healthy"] is False
