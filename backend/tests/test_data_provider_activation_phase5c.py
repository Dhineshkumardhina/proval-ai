"""Tests for licensed real-world data provider activation and governance (Phase 5C)."""

import os
from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.connectors.registry import ConnectorRegistry
from app.connectors.base import ConnectorConfig
from app.connectors.exceptions import AuthenticationError, SecurityViolationError
from app.connectors.propequity_connector import PropEquityConnector
from app.connectors.zapkey_connector import ZapkeyB2BConnector
from app.connectors.propstack_connector import PropStackConnector
from app.connectors.hfc_connector import HFCBankingPortfolioConnector
from app.connectors.rera_developer_connector import RERADeveloperConnector
from app.connectors.ogd_connector import OpenGovernmentDataConnector
from app.connectors.state_igr_connector import StateRegistrationDepartmentConnector
from app.connectors.mock_connector import MockDeedConnector
from app.core.security import create_access_token, ROLE_ADMIN, ROLE_SENIOR_UNDERWRITER
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.verification import VerificationEvidenceModel
from app.normalization.models import NormalizedTransactionRecord
from app.verification.verification_service import VerificationEngine


@pytest.fixture
def admin_headers():
    token = create_access_token({
        "sub": "data_officer",
        "name": "Institutional Data Officer",
        "role": ROLE_ADMIN,
    })
    return {"Authorization": f"Bearer {token}"}


# ----------------------------------------------------------------------
# 1. Audit of All 8 Registered Data Connectors
# ----------------------------------------------------------------------

def test_all_connectors_registered_and_available():
    """Verify that all 8 connectors are registered and discoverable in the connector registry."""
    available = ConnectorRegistry.list_available()
    expected_connectors = {
        "zapkey_b2b",
        "propequity",
        "propstack",
        "hfc_banking",
        "rera_developer",
        "ogd_india",
        "state_igr",
        "mock_deed",
    }
    assert expected_connectors.issubset(set(available.keys()))

    # Verify instantiation of each connector
    for conn_type in expected_connectors:
        config = ConnectorConfig(
            source_id=f"test_{conn_type}",
            source_code=conn_type,
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        instance = ConnectorRegistry.create(conn_type, config)
        assert instance is not None
        assert instance.config.source_code == conn_type


# ----------------------------------------------------------------------
# 2. Credential Handling & Missing Environment Variable Protection
# ----------------------------------------------------------------------

def test_missing_credentials_raise_authentication_error():
    """Verify that connectors fail fast with AuthenticationError when credentials are missing."""
    # Ensure environment variables are unset for the test
    old_pe = os.environ.pop("PROPEQUITY_API_KEY", None)
    old_zk = os.environ.pop("ZAPKEY_API_KEY", None)

    try:
        pe_config = ConnectorConfig(
            source_id="src_pe",
            source_code="propequity",
            base_url="https://api.propequity.in",
            allow_test_endpoints=True,
        )
        pe_conn = PropEquityConnector(pe_config)
        with pytest.raises(AuthenticationError) as exc_info:
            pe_conn._get_api_key()
        assert "PROPEQUITY_API_KEY" in str(exc_info.value)

        zk_config = ConnectorConfig(
            source_id="src_zk",
            source_code="zapkey_b2b",
            base_url="https://api.zapkey.com",
            allow_test_endpoints=True,
        )
        zk_conn = ZapkeyB2BConnector(zk_config)
        with pytest.raises(AuthenticationError) as exc_info:
            zk_conn._get_api_key()
        assert "ZAPKEY_API_KEY" in str(exc_info.value)

    finally:
        if old_pe:
            os.environ["PROPEQUITY_API_KEY"] = old_pe
        if old_zk:
            os.environ["ZAPKEY_API_KEY"] = old_zk


# ----------------------------------------------------------------------
# 3. Provider Activation & Monitoring Board API Tests
# ----------------------------------------------------------------------

def test_get_providers_status_board(client: TestClient, admin_headers):
    """Test the real-time provider activation and connectivity monitoring board."""
    response = client.get("/api/v1/acquisition/providers/status", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_providers"] == 8
    # Commercial providers must be reported as BLOCKED when commercial agreements/credentials are pending
    providers = data["providers"]
    codes = [p["source_code"] for p in providers]
    assert "propequity" in codes
    assert "zapkey_b2b" in codes
    assert "mock_deed" in codes

    # PropEquity without environment key must report CONFIG_MISSING and BLOCKED
    if not os.environ.get("PROPEQUITY_API_KEY"):
        pe_status = next(p for p in providers if p["source_code"] == "propequity")
        assert pe_status["connection_status"] == "CONFIG_MISSING"
        assert pe_status["commercial_status"] == "BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED"
        assert pe_status["is_healthy"] is False

    # Mock connector is always active for sandbox testing
    mock_status = next(p for p in providers if p["source_code"] == "mock_deed")
    assert mock_status["connection_status"] == "MOCK_ACTIVE"
    assert mock_status["commercial_status"] == "SANDBOX_ACTIVE"
    assert mock_status["is_healthy"] is True


# ----------------------------------------------------------------------
# 4. Ingestion Job Status Tracking Tests
# ----------------------------------------------------------------------

def test_list_and_get_ingestion_jobs(client: TestClient, admin_headers, db_session):
    """Verify listing and retrieving ingestion job history."""
    from app.models.data_source import DataSourceModel, IngestionJobModel

    # Seed an ingestion job
    source = DataSourceModel(
        source_code="TEST_MONITOR_SRC",
        source_name="Test Monitor Source",
        provider_name="Test Provider",
        legal_authorization_basis="Testing tracking",
    )
    db_session.add(source)
    db_session.commit()

    job = IngestionJobModel(
        source_id=source.id,
        status="COMPLETED",
        trigger_mode="MANUAL_ADMIN",
        records_fetched=150,
        records_staged=150,
        records_normalized=148,
        records_rejected=2,
        records_duplicate=0,
    )
    db_session.add(job)
    db_session.commit()

    # List jobs
    list_res = client.get("/api/v1/acquisition/jobs", headers=admin_headers)
    assert list_res.status_code == status.HTTP_200_OK
    jobs_data = list_res.json()
    assert jobs_data["total"] >= 1
    job_ids = [j["id"] for j in jobs_data["items"]]
    assert job.id in job_ids

    # Get single job
    get_res = client.get(f"/api/v1/acquisition/jobs/{job.id}", headers=admin_headers)
    assert get_res.status_code == status.HTTP_200_OK
    single_job = get_res.json()
    assert single_job["records_fetched"] == 150
    assert single_job["records_normalized"] == 148
    assert single_job["status"] == "COMPLETED"


# ----------------------------------------------------------------------
# 5. Data Governance & Licensing Attribution Tests
# ----------------------------------------------------------------------

def test_source_attribution_and_metadata_preservation(db_session):
    """Verify that every imported transaction preserves source attribution and verification evidence."""
    dataset = DatasetMetadataModel(
        name="Gov_Attribution_Dataset_2026",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Ingested from PropEquity API",
        file_format="api_stream",
        original_filename="propequity_stream",
        file_hash_sha256="d"*64,
    )
    db_session.add(dataset)
    db_session.commit()

    norm_tx = NormalizedTransactionRecord(
        transaction_id="tx-pe-001",
        source_id="propequity",
        source_reference="PE-MUM-2026-BK1-8842",
        original_record_hash="a"*64,
        registration_reference="BK1/8842/2026",
        fingerprint_hash="b"*64,
        state="Maharashtra",
        district="Mumbai",
        sub_district="Andheri",
        locality="Lokhandwala Complex",
        postal_code="400053",
        project_name="Oberoi Springs",
        unit_number="1204",
        property_type="High-Rise Apartment",
        transaction_type="RESALE",
        registration_date=datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1100.0,
        built_up_area_sqft=1350.0,
        super_built_up_area_sqft=1450.0,
        original_area_value=1100.0,
        original_area_unit="sqft",
        acquisition_timestamp=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        transaction_amount=24500000.0,
        price_per_sqft=22272.73,
        guideline_rate_per_sqft=19500.0,
        deviation_from_guideline_pct=14.2,
        latitude=19.1368,
        longitude=72.8273,
        coordinate_precision_digits=4,
        sro_office="SRO-ANDHERI-01",
        raw_payload={"test": "record"},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="PROV_AUDITOR")
    outcome, tx = verifier.verify_and_route_record(dataset=dataset, norm_tx=norm_tx, row_index=1)

    assert outcome == "VERIFIED"
    assert tx is not None
    assert tx.data_source == "propequity"
    assert tx.is_verified_deed is True
    assert tx.fingerprint_hash == "b"*64

    # Check evidence record
    evidence = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert evidence is not None
    assert evidence.source_origin == "propequity"
    assert evidence.source_document_ref == "BK1/8842/2026"
    assert evidence.original_record_hash == "a"*64
    assert evidence.verification_evidence_details["is_ml_eligible"] is True


# ----------------------------------------------------------------------
# 6. Mock Data Quarantine from Certified Empirical ML Dataset
# ----------------------------------------------------------------------

def test_mock_records_strictly_prohibited_from_empirical_dataset(db_session):
    """Verify that mock/simulation records are explicitly flagged with is_verified_deed=False."""
    dataset = DatasetMetadataModel(
        name="Mock_Simulation_Dataset",
        source_type="synthetic_benchmark",
        license_type="commercial_restricted",
        data_source_provenance="Simulated mock adapter",
        file_format="api_stream",
        original_filename="mock_stream",
        file_hash_sha256="e"*64,
    )
    db_session.add(dataset)
    db_session.commit()

    mock_norm_tx = NormalizedTransactionRecord(
        transaction_id="tx-mock-001",
        source_id="mock_deed",
        source_reference="MOCK-SIM-001",
        original_record_hash="c"*64,
        registration_reference="MOCK-REG-999",
        fingerprint_hash="d"*64,
        state="Karnataka",
        district="Bengaluru",
        locality="Whitefield",
        postal_code="560066",
        project_name="Prestige Mock Tower",
        unit_number="501",
        property_type="High-Rise Apartment",
        registration_date=datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1200.0,
        super_built_up_area_sqft=1500.0,
        original_area_value=1200.0,
        original_area_unit="sqft",
        acquisition_timestamp=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        transaction_amount=12000000.0,
        price_per_sqft=10000.0,
        guideline_rate_per_sqft=8000.0,
        deviation_from_guideline_pct=25.0,
        latitude=12.9698,
        longitude=77.7499,
        coordinate_precision_digits=4,
        sro_office="SRO-KR-PURAM",
        raw_payload={"mock": True},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="PROV_AUDITOR")
    outcome, tx = verifier.verify_and_route_record(dataset=dataset, norm_tx=mock_norm_tx, row_index=1)

    assert outcome == "VERIFIED"
    assert tx is not None
    # Crucial security check: must NOT be marked as a verified empirical deed!
    assert tx.is_verified_deed is False

    evidence = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert evidence.verification_status == "PROVISIONAL_NON_ML"
    assert evidence.verification_evidence_details["is_ml_eligible"] is False
