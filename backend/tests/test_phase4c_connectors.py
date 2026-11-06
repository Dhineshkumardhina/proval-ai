"""Comprehensive Unit and Security Tests for Phase 4C Connectors and Registry."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.connectors.base import ConnectorConfig, SyncCursor, ConnectorHealthStatus
from app.connectors.exceptions import AuthenticationError, ConnectorError
from app.connectors.registry import ConnectorRegistry
from app.connectors.propequity_connector import PropEquityConnector
from app.connectors.propstack_connector import PropStackConnector
from app.connectors.hfc_connector import HFCBankingPortfolioConnector
from app.connectors.rera_developer_connector import RERADeveloperConnector
from app.connectors.ogd_connector import OpenGovernmentDataConnector
from app.connectors.state_igr_connector import StateRegistrationDepartmentConnector


# =============================================================================
# 1. CONNECTOR REGISTRY TESTS
# =============================================================================

def test_connector_registry_contains_all_sources():
    """Verify that all Phase 4C connectors are registered in ConnectorRegistry."""
    available = ConnectorRegistry.list_available()
    expected_keys = [
        "zapkey_b2b",
        "propequity",
        "propstack",
        "hfc_banking",
        "rera_developer",
        "ogd_india",
        "state_igr",
        "mock_deed",
    ]
    for key in expected_keys:
        assert key in available, f"Connector key '{key}' missing from registry"


def test_connector_registry_factory_creates_instances():
    """Verify that ConnectorRegistry.create instantiates each connector type."""
    config = ConnectorConfig(
        source_id="src-test-01",
        source_code="TEST_CODE",
        base_url="https://api.zapkey.com",
        allow_test_endpoints=True,
    )
    conn = ConnectorRegistry.create("propequity", config)
    assert isinstance(conn, PropEquityConnector)

    conn_ps = ConnectorRegistry.create("propstack", config)
    assert isinstance(conn_ps, PropStackConnector)

    conn_hfc = ConnectorRegistry.create("hfc_banking", config)
    assert isinstance(conn_hfc, HFCBankingPortfolioConnector)

    conn_rera = ConnectorRegistry.create("rera_developer", config)
    assert isinstance(conn_rera, RERADeveloperConnector)

    conn_ogd = ConnectorRegistry.create("ogd_india", config)
    assert isinstance(conn_ogd, OpenGovernmentDataConnector)

    conn_igr = ConnectorRegistry.create("state_igr", config)
    assert isinstance(conn_igr, StateRegistrationDepartmentConnector)


def test_connector_registry_unknown_type_raises():
    """Verify that requesting an unregistered connector raises ConnectorError."""
    config = ConnectorConfig(source_id="src-1", source_code="S1", base_url="https://api.zapkey.com")
    with pytest.raises(ConnectorError) as exc_info:
        ConnectorRegistry.create("unsupported_provider", config)
    assert "Unknown connector type" in str(exc_info.value)


# =============================================================================
# 2. PROPEQUITY CONNECTOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_propequity_missing_key_raises_auth_error():
    """Verify that missing API key raises AuthenticationError."""
    config = ConnectorConfig(
        source_id="src-pe",
        source_code="PROPEQUITY",
        base_url="https://api.propequity.in",
        auth_token_env_var="NON_EXISTENT_PROPEQUITY_KEY_VAR",
    )
    conn = PropEquityConnector(config)
    with pytest.raises(AuthenticationError) as exc:
        await conn.authenticate()
    assert "Missing API credentials" in str(exc.value)


@pytest.mark.asyncio
async def test_propequity_authentication_success(monkeypatch):
    """Verify successful authentication against PropEquity verify endpoint."""
    monkeypatch.setenv("PROPEQUITY_API_KEY", "pe_secret_token_12345")
    config = ConnectorConfig(
        source_id="src-pe",
        source_code="PROPEQUITY",
        base_url="https://api.propequity.in",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={"status": "authenticated"})

    conn = PropEquityConnector(config, http_client=mock_http)
    auth_ok = await conn.authenticate()
    assert auth_ok is True
    mock_http.request.assert_called_once_with(
        method="GET",
        endpoint="/v1/auth/verify",
        headers={"Authorization": "Bearer pe_secret_token_12345", "Accept": "application/json", "User-Agent": "PropVal-AI-Acquisition/1.0 (PropEquity B2B Client)"},
    )


@pytest.mark.asyncio
async def test_propequity_incremental_fetch_pagination(monkeypatch):
    """Verify incremental sync pagination and cursor progression."""
    monkeypatch.setenv("PROPEQUITY_API_KEY", "pe_secret_token_12345")
    config = ConnectorConfig(
        source_id="src-pe",
        source_code="PROPEQUITY",
        base_url="https://api.propequity.in",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={
        "data": [
            {"transaction_id": "pe_001", "locality": "Golf Course Road", "price": 45000000},
            {"transaction_id": "pe_002", "locality": "Cyber City", "price": 28000000},
        ],
        "pagination": {"has_more": False},
    })

    conn = PropEquityConnector(config, http_client=mock_http)
    cursor = SyncCursor(page=1, page_size=2)
    batches = []
    async for batch in conn.fetch_incremental(cursor):
        batches.append(batch)

    assert len(batches) == 1
    assert batches[0].record_count == 2
    assert batches[0].raw_records[0]["transaction_id"] == "pe_001"
    assert batches[0].next_cursor.page == 2
    assert batches[0].has_more is False


def test_propequity_metadata_extraction():
    """Verify that PropEquity metadata specifies permitted purposes and retention terms."""
    config = ConnectorConfig(source_id="src-pe", source_code="PROPEQUITY", base_url="https://api.propequity.in")
    conn = PropEquityConnector(config)
    meta = conn.extract_source_metadata()
    assert meta["source_category"] == "LICENSED_PROVIDER"
    assert "MODEL_TRAINING" in meta["permitted_purposes"]
    assert meta["retention_restrictions"]["max_retention_days"] == 365


# =============================================================================
# 3. PROPSTACK CONNECTOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_propstack_health_check_success(monkeypatch):
    """Verify that PropStack connection test returns healthy status."""
    monkeypatch.setenv("PROPSTACK_API_KEY", "propstack_test_key_999")
    config = ConnectorConfig(
        source_id="src-ps",
        source_code="PROPSTACK",
        base_url="https://api.propstack.com",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={"status": "healthy"})

    conn = PropStackConnector(config, http_client=mock_http)
    health = await conn.test_connection()
    assert health.is_healthy is True
    assert health.status_code == 200


def test_propstack_metadata_extraction():
    """Verify PropStack metadata attributes."""
    config = ConnectorConfig(source_id="src-ps", source_code="PROPSTACK", base_url="https://api.propstack.com")
    conn = PropStackConnector(config)
    meta = conn.extract_source_metadata()
    assert meta["source_category"] == "DATA_AGGREGATOR"
    assert meta["access_tier"] == "CLASS_C_INSTITUTIONAL"


# =============================================================================
# 4. HFC BANKING PORTFOLIO CONNECTOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_hfc_connector_fetch(monkeypatch):
    """Verify HFC banking portfolio batch streaming."""
    monkeypatch.setenv("HFC_PARTNER_API_KEY", "hfc_bank_token_777")
    config = ConnectorConfig(
        source_id="src-hfc",
        source_code="HFC_BANK",
        base_url="https://api.zapkey.com",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={
        "collateral_records": [
            {"collateral_id": "hfc_101", "loan_account": "LA-9921", "appraised_value": 15000000},
        ],
        "pagination": {"has_more": False},
    })

    conn = HFCBankingPortfolioConnector(config, http_client=mock_http)
    batches = []
    async for b in conn.fetch_incremental(SyncCursor(page=1, page_size=10)):
        batches.append(b)

    assert len(batches) == 1
    assert batches[0].record_count == 1
    assert batches[0].raw_records[0]["collateral_id"] == "hfc_101"


# =============================================================================
# 5. RERA DEVELOPER CONNECTOR & REGISTRATION NUMBER VALIDATION
# =============================================================================

def test_rera_registration_number_validation():
    """Verify validation of state RERA registration numbers."""
    assert RERADeveloperConnector.validate_rera_registration_number("P51800001234") is True  # MahaRERA
    assert RERADeveloperConnector.validate_rera_registration_number("PRM/KA/RERA/1251/310/PR/170915/000123") is True  # Karnataka RERA
    assert RERADeveloperConnector.validate_rera_registration_number("UPRERAPRJ12345") is True  # UP RERA
    assert RERADeveloperConnector.validate_rera_registration_number("123 of 2017") is True  # HRERA
    assert RERADeveloperConnector.validate_rera_registration_number("INVALID#@!*&") is False
    assert RERADeveloperConnector.validate_rera_registration_number("") is False
    assert RERADeveloperConnector.validate_rera_registration_number(None) is False


# =============================================================================
# 6. OPEN GOVERNMENT DATA (data.gov.in) CONNECTOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_ogd_connector_fetch(monkeypatch):
    """Verify OGD data.gov.in resource streaming."""
    monkeypatch.setenv("DATA_GOV_IN_API_KEY", "ogd_gov_token_555")
    config = ConnectorConfig(
        source_id="src-ogd",
        source_code="OGD_INDIA",
        base_url="https://data.gov.in",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={
        "records": [
            {"sro_code": "SRO-01", "transaction_count": 520, "average_rate": 8500},
        ],
        "total": 1,
    })

    conn = OpenGovernmentDataConnector(config, http_client=mock_http)
    batches = []
    async for b in conn.fetch_incremental(SyncCursor(page=1, page_size=10)):
        batches.append(b)

    assert len(batches) == 1
    assert batches[0].record_count == 1
    meta = conn.extract_source_metadata()
    assert meta["source_category"] == "GOVERNMENT_OPEN_DATA"
    assert meta["access_tier"] == "CLASS_E_PUBLIC"


# =============================================================================
# 7. STATE REGISTRATION DEPARTMENT (IGR) CONNECTOR TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_state_igr_authentication(monkeypatch):
    """Verify State IGR certificate verification."""
    monkeypatch.setenv("IGR_CLIENT_TOKEN", "igr_cert_token_001")
    config = ConnectorConfig(
        source_id="src-igr",
        source_code="IGR_MAHARASHTRA",
        base_url="https://igrmaharashtra.gov.in",
        allow_test_endpoints=True,
    )
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={"status": "authenticated"})

    conn = StateRegistrationDepartmentConnector(config, http_client=mock_http)
    auth_ok = await conn.authenticate()
    assert auth_ok is True
    meta = conn.extract_source_metadata()
    assert meta["source_category"] == "STATE_REGISTRATION_DEPT"
    assert meta["access_tier"] == "CLASS_A_API"

