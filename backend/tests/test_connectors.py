"""Comprehensive test suite for Phase 4A-2 Data Connector Framework & Acquisition Pipeline."""

import os
import uuid
import pytest
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.connectors.base import ConnectorConfig, SyncCursor
from app.connectors.exceptions import (
    AuthenticationError,
    RateLimitExceededError,
    NetworkTimeoutError,
    SecurityViolationError,
    InvalidResponseError,
)
from app.connectors.http_client import ResilientHTTPClient
from app.connectors.zapkey_connector import ZapkeyB2BConnector
from app.connectors.mock_connector import MockDeedConnector
from app.connectors.registry import ConnectorRegistry
from app.models.data_source import DataSourceModel, IngestionJobModel, RawTransactionStagingModel
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel, DuplicateRecordModel
from app.services.acquisition_service import AcquisitionOrchestrator


@pytest.fixture(scope="module")
def db_session():
    """Create a clean database session for connector tests."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_source(db_session: Session):
    """Seed an authorized test data source."""
    code = f"TEST_SRC_{uuid.uuid4().hex[:6].upper()}"
    src = DataSourceModel(
        source_code=code,
        source_name="Test Karnataka SRO Sourced Provider",
        provider_name="Zapkey Commercial API",
        access_tier="CLASS_C_INSTITUTIONAL",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="Authorized Master Data Evaluation Agreement 2026",
        api_base_url="https://api.zapkey.com",
        rate_limit_per_minute=120,
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)
    return src


# =========================================================================
# 1. HTTP Client, Security (SSRF), & Retry Tests
# =========================================================================

def test_ssrf_protection_blocks_unauthorized_destinations():
    """Verify that outbound connector attempts to unauthorized domains or internal IPs are blocked."""
    with pytest.raises(SecurityViolationError) as exc_info:
        ResilientHTTPClient(base_url="http://169.254.169.254/latest/meta-data")
    assert "SSRF Prevention" in str(exc_info.value)

    with pytest.raises(SecurityViolationError) as exc_info2:
        ResilientHTTPClient(base_url="https://evil-attacker-site.com")
    assert "authorized domain whitelist" in str(exc_info2.value)


@pytest.mark.asyncio
async def test_resilient_http_client_rate_limiting():
    """Verify client throttles requests to adhere to rate_limit_per_minute."""
    client = ResilientHTTPClient(
        base_url="https://api.zapkey.com",
        rate_limit_per_minute=600,  # 10 req/sec -> 0.1s interval
    )
    start_time = datetime.now(timezone.utc)
    await client._throttle()
    await client._throttle()
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    assert elapsed >= 0.08  # Confirms pacing delay


# =========================================================================
# 2. Connector Authentication & Protocol Tests
# =========================================================================

@pytest.mark.asyncio
async def test_zapkey_connector_authentication_missing_key():
    """Verify Zapkey connector raises AuthenticationError when no credentials exist in environment."""
    old_val = os.environ.pop("ZAPKEY_API_KEY", None)
    try:
        config = ConnectorConfig(
            source_id="src-1",
            source_code="ZAPKEY_BLR",
            base_url="https://api.zapkey.com",
        )
        connector = ZapkeyB2BConnector(config)
        with pytest.raises(AuthenticationError) as exc_info:
            await connector.authenticate()
        assert "Missing API credentials" in str(exc_info.value)
    finally:
        if old_val:
            os.environ["ZAPKEY_API_KEY"] = old_val


@pytest.mark.asyncio
async def test_mock_connector_authentication_and_health():
    """Verify mock connector health verification and simulated failure modes."""
    config = ConnectorConfig(
        source_id="src-mock",
        source_code="MOCK_BLR",
        base_url="https://localhost",
    )
    mock_conn = MockDeedConnector(config)
    health = await mock_conn.test_connection()
    assert health.is_healthy is True
    assert health.status_code == 200

    # Test simulated auth failure
    mock_conn.should_fail_auth = True
    health_fail = await mock_conn.test_connection()
    assert health_fail.is_healthy is False
    assert health_fail.status_code == 401


# =========================================================================
# 3. Pagination & Incremental Cursor Tests
# =========================================================================

@pytest.mark.asyncio
async def test_mock_connector_pagination():
    """Verify cursor-based pagination streams across multiple discrete batches."""
    config = ConnectorConfig(
        source_id="src-mock",
        source_code="MOCK_BLR",
        base_url="https://localhost",
    )
    mock_conn = MockDeedConnector(config)
    cursor = SyncCursor(page=1, page_size=10)

    batches = []
    async for batch in mock_conn.fetch_incremental(cursor):
        batches.append(batch)
        if batch.next_cursor:
            cursor = batch.next_cursor

    # 24 total simulated records / 10 per page -> 3 batches (10, 10, 4)
    assert len(batches) == 3
    assert batches[0].record_count == 10
    assert batches[1].record_count == 10
    assert batches[2].record_count == 4
    assert batches[0].has_more is True
    assert batches[2].has_more is False


# =========================================================================
# 4. End-to-End Orchestrator, Staging, & Duplicate Defense
# =========================================================================

@pytest.mark.asyncio
async def test_orchestrator_acquisition_and_staging(db_session: Session, test_source: DataSourceModel):
    """Verify end-to-end acquisition: raw staging, normalization, and tamper-evident audit."""
    config = ConnectorConfig(
        source_id=test_source.id,
        source_code=test_source.source_code,
        base_url="https://localhost",
    )
    mock_conn = MockDeedConnector(config)
    orchestrator = AcquisitionOrchestrator(db_session)

    job = await orchestrator.execute_acquisition_job(
        source_id=test_source.id,
        connector=mock_conn,
        cursor=SyncCursor(page=1, page_size=10),
        target_dataset_name=f"E2E_Test_Dataset_{uuid.uuid4().hex[:6]}",
        max_batches=2,
    )

    assert job.status == "COMPLETED"
    assert job.records_fetched == 20
    assert job.records_staged == 20
    assert job.records_normalized == 20
    assert job.records_duplicate == 0
    assert job.audit_event_id is not None

    # Verify raw staging rows exist in DB
    staged_rows = (
        db_session.query(RawTransactionStagingModel)
        .filter(RawTransactionStagingModel.job_id == job.id)
        .all()
    )
    assert len(staged_rows) == 20
    assert staged_rows[0].pii_scrub_status == "CLEANSED"
    assert len(staged_rows[0].payload_hash_sha256) == 64


@pytest.mark.asyncio
async def test_duplicate_deed_protection(db_session: Session, test_source: DataSourceModel):
    """Verify that re-ingesting identical registered deeds is detected and routed to duplicate defense."""
    config = ConnectorConfig(
        source_id=test_source.id,
        source_code=test_source.source_code,
        base_url="https://localhost",
    )
    mock_conn = MockDeedConnector(config)
    orchestrator = AcquisitionOrchestrator(db_session)

    # First Run (Populates 10 deeds)
    job1 = await orchestrator.execute_acquisition_job(
        source_id=test_source.id,
        connector=mock_conn,
        cursor=SyncCursor(page=1, page_size=10),
        target_dataset_name=f"Deed_Run_1_{uuid.uuid4().hex[:6]}",
        max_batches=1,
    )
    assert job1.records_normalized == 10

    # Second Run with identical deeds (Should flag as duplicates)
    job2 = await orchestrator.execute_acquisition_job(
        source_id=test_source.id,
        connector=mock_conn,
        cursor=SyncCursor(page=1, page_size=10),
        target_dataset_name=f"Deed_Run_2_{uuid.uuid4().hex[:6]}",
        max_batches=1,
    )
    assert job2.status == "COMPLETED"
    assert job2.records_staged == 10
    assert job2.records_duplicate == 10
    assert job2.records_normalized == 0

    # Confirm records were logged in DuplicateRecordModel
    dups = (
        db_session.query(DuplicateRecordModel)
        .filter(DuplicateRecordModel.dataset_id != job1.source_id)
        .all()
    )
    assert len(dups) >= 10


# =========================================================================
# 5. Connector Registry Test
# =========================================================================

def test_connector_registry_factory():
    """Verify dynamic connector instantiation via registry."""
    config = ConnectorConfig(
        source_id="src-reg",
        source_code="ZAPKEY_REG",
        base_url="https://api.zapkey.com",
    )
    conn = ConnectorRegistry.create("zapkey_b2b", config)
    assert isinstance(conn, ZapkeyB2BConnector)

    mock = ConnectorRegistry.create("mock_deed", config)
    assert isinstance(mock, MockDeedConnector)

    avail = ConnectorRegistry.list_available()
    assert "zapkey_b2b" in avail
    assert "mock_deed" in avail

