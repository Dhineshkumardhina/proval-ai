"""Test suite for Phase 4B-2 Privacy Engineering.

Verifies:
1. PII detection and redaction for PAN, Aadhaar, mobile phones, email addresses, and personal party names.
2. Safe preservation of legitimate property identifiers (Survey No, CTS No, Flat No, PIN code, Coordinates).
3. Pre-persistence PII scrubbing in connector acquisition jobs, staging, rejections, and quarantine.
4. Retention policy enforcement and purge of expired raw staging payloads with SHA-256 integrity retention.
5. DPDP Section 12 Right to Erasure workflow and audit trail.
6. Logging redaction for PII, tokens, and sensitive parameters.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.logging import redact_sensitive_text
from app.models.data_source import DataSourceModel, RawTransactionStagingModel
from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
)
from app.models.audit import AuditEventModel
from app.models.verification import QuarantinedRecordModel
from app.services.privacy_service import (
    redact_pii,
    scrub_raw_payload_dict,
    anonymize_staged_payload_for_retention,
    SAFE_PROPERTY_KEYS,
)
from app.services.acquisition_service import AcquisitionOrchestrator
from app.connectors.mock_connector import MockDeedConnector
from app.connectors.base import ConnectorConfig
from app.services.audit_service import (
    EVENT_PII_DETECTED_AND_SCRUBBED,
    EVENT_RAW_STAGING_RETENTION_PURGE,
    EVENT_DATASET_RECORD_ERASURE,
)


@pytest.fixture
def db_session():
    """Create isolated clean test session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# 1. PII Detection and Scrubbing Unit Tests
# ---------------------------------------------------------------------------

def test_detect_and_redact_pan():
    raw_text = "Transaction conducted by taxpayer with PAN ABCDE1234F at SRO Jayanagar."
    cleansed, count, types = redact_pii(raw_text)
    assert count == 1
    assert "PAN" in types
    assert "[REDACTED_PAN]" in cleansed
    assert "ABCDE1234F" not in cleansed


def test_detect_and_redact_aadhaar():
    raw_text = "Deed executed by seller holding Aadhaar 2345 6789 0123 on 2026-03-15."
    cleansed, count, types = redact_pii(raw_text)
    assert count == 1
    assert "AADHAAR" in types
    assert "[REDACTED_AADHAAR]" in cleansed
    assert "2345 6789 0123" not in cleansed


def test_detect_and_redact_phone():
    raw_text = "Contact broker directly at +91 9876543210 or 8765432109 for keys."
    cleansed, count, types = redact_pii(raw_text)
    assert count >= 1
    assert "PHONE" in types
    assert "[REDACTED_PHONE]" in cleansed
    assert "9876543210" not in cleansed


def test_detect_and_redact_email():
    raw_text = "Forward execution deed copy to purchaser.officer@domain.co.in."
    cleansed, count, types = redact_pii(raw_text)
    assert count == 1
    assert "EMAIL" in types
    assert "[REDACTED_EMAIL]" in cleansed
    assert "purchaser.officer@domain.co.in" not in cleansed


def test_detect_and_redact_labeled_and_honorific_names():
    raw_text = "Borrower: Ramesh Kumar signed before Mr. Rajesh Sharma."
    cleansed, count, types = redact_pii(raw_text)
    assert count >= 2
    assert "[REDACTED_NAME]" in cleansed
    assert "Ramesh Kumar" not in cleansed
    assert "Rajesh Sharma" not in cleansed


# ---------------------------------------------------------------------------
# 2. Property Identifier Preservation Tests (Zero Destruction)
# ---------------------------------------------------------------------------

def test_property_identifiers_preserved_during_scrubbing():
    """Ensure Survey No, CTS No, Flat No, PIN code, and coordinates are not destroyed."""
    payload = {
        "unit_number": "Flat 402, Block B",
        "survey_number": "Sy. No. 124/2A",
        "cts_number": "CTS 809/1",
        "pincode": "560001",
        "locality": "Indiranagar",
        "carpet_area_sqft": 1450.5,
        "transaction_amount": 18500000.0,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "buyer_name": "Vikram Malhotra",
        "buyer_pan": "ABCDE1234F",
        "party_contact": "+91 9876543210",
        "party_email": "vikram.m@domain.in",
    }

    cleansed, total_redactions, detected_types = scrub_raw_payload_dict(payload)

    # Legitimate property identifiers must be strictly preserved
    assert cleansed["unit_number"] == "Flat 402, Block B"
    assert cleansed["survey_number"] == "Sy. No. 124/2A"
    assert cleansed["cts_number"] == "CTS 809/1"
    assert cleansed["pincode"] == "560001"
    assert cleansed["locality"] == "Indiranagar"
    assert cleansed["carpet_area_sqft"] == 1450.5
    assert cleansed["transaction_amount"] == 18500000.0
    assert cleansed["latitude"] == 12.9716
    assert cleansed["longitude"] == 77.5946

    # Personal identifiable entities must be redacted
    assert cleansed["buyer_name"] == "[REDACTED_PERSONAL_NAME]"
    assert cleansed["buyer_pan"] == "[REDACTED_PAN]"
    assert cleansed["party_contact"] == "[REDACTED_PHONE]"
    assert cleansed["party_email"] == "[REDACTED_EMAIL]"
    assert total_redactions >= 4
    assert "PAN" in detected_types
    assert "PHONE" in detected_types
    assert "EMAIL" in detected_types


# ---------------------------------------------------------------------------
# 3. Pipeline Ingestion & Pre-Staging Scrubbing Integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pre_staging_pii_scrubbing_in_acquisition(db_session: Session):
    """Verify that connector responses are scrubbed before persistence in staging and rejections."""
    # Create test data source with unique code
    import uuid
    uid = uuid.uuid4().hex[:6]
    src = DataSourceModel(
        source_code=f"TEST_PII_SCRUB_{uid}",
        source_name="Test PII Scrubbing Feed",
        provider_name="Test Provider",
        access_tier="CLASS_F_MOCK",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="Institutional Research Sandbox License",
        license_number=f"LIC-TEST-{uid}",
        data_owner="Data Compliance Officer",
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    # Prepare connector returning payload with embedded PII
    raw_records = [
        {
            "registration_number": "DOC-PII-001",
            "registration_date": "2026-01-15",
            "transaction_amount": 12500000,
            "carpet_area_sqft": 1200,
            "state": "Karnataka",
            "district": "Bengaluru Urban",
            "locality": "Koramangala",
            "pincode": "560034",
            "buyer_name": "Suresh Raina",
            "buyer_pan": "ABCDE1234F",
            "seller_contact": "+91 9845012345",
        },
        {
            # Invalid record to test rejection staging
            "registration_number": "DOC-PII-002",
            "registration_date": "2026-01-16",
            "transaction_amount": None,  # Will fail normalization
            "carpet_area_sqft": 1000,
            "vendor_name": "Mahesh Bhupathi",
            "vendor_aadhaar": "2345 6789 0123",
        }
    ]

    cfg = ConnectorConfig(
        source_id=src.id,
        source_code=src.source_code,
        base_url="https://mock.propval.internal",
    )
    mock_conn = MockDeedConnector(config=cfg, simulated_records=raw_records)
    orchestrator = AcquisitionOrchestrator(db=db_session)

    job = await orchestrator.execute_acquisition_job(
        source_id=src.id,
        connector=mock_conn,
        target_dataset_name="PII_Scrub_Test_Dataset",
    )

    assert job.status == "COMPLETED"

    # Verify Raw Staging has NO unredacted PII
    staged_records = (
        db_session.query(RawTransactionStagingModel)
        .filter(RawTransactionStagingModel.job_id == job.id)
        .all()
    )
    assert len(staged_records) == 2
    for s in staged_records:
        payload_str = json.dumps(s.raw_payload)
        assert "ABCDE1234F" not in payload_str
        assert "9845012345" not in payload_str
        assert "2345 6789 0123" not in payload_str
        assert "Suresh Raina" not in payload_str
        assert "Mahesh Bhupathi" not in payload_str

    # Verify Rejection table has NO unredacted PII
    rejections = (
        db_session.query(RejectedRecordModel)
        .filter(RejectedRecordModel.dataset_id.in_(
            db_session.query(DatasetMetadataModel.id).filter(DatasetMetadataModel.name == "PII_Scrub_Test_Dataset")
        ))
        .all()
    )
    assert len(rejections) >= 1
    for r in rejections:
        rej_str = json.dumps(r.raw_data)
        assert "2345 6789 0123" not in rej_str
        assert "Mahesh Bhupathi" not in rej_str

    # Verify privacy audit event was logged
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == EVENT_PII_DETECTED_AND_SCRUBBED)
        .order_by(AuditEventModel.timestamp.desc())
        .first()
    )
    assert audit_ev is not None
    payload_data = json.loads(audit_ev.payload_json) if isinstance(audit_ev.payload_json, str) else audit_ev.payload_json
    assert payload_data.get("job_id") == job.id
    assert payload_data.get("total_redactions") > 0


# ---------------------------------------------------------------------------
# 4. Raw Staging Retention Purge and DPDP Right to Erasure
# ---------------------------------------------------------------------------

def test_raw_staging_retention_purge(db_session: Session):
    """Verify raw staging payloads past retention window are purged while keeping hashes."""
    orchestrator = AcquisitionOrchestrator(db=db_session)

    # Insert an expired staging record directly
    old_date = datetime.now(timezone.utc) - timedelta(days=120)
    old_staged = RawTransactionStagingModel(
        job_id="test-job-expired",
        source_id="test-src-expired",
        row_index=1,
        created_at=old_date,
        payload_hash_sha256="abc123canonicalhash",
        raw_payload={
            "property_type": "Apartment",
            "carpet_area_sqft": 1100.0,
            "transaction_amount": 9500000.0,
            "locality": "Whitefield",
            "temporary_transient_data": "must_be_deleted",
        },
        pii_scrub_status="CLEANSED",
    )
    db_session.add(old_staged)
    db_session.commit()
    db_session.refresh(old_staged)

    # Execute retention purge for records older than 90 days
    purged_count = orchestrator.purge_expired_raw_staging(
        retention_days=90,
        actor_id="TEST_COMPLIANCE_RUNNER",
    )
    assert purged_count >= 1

    db_session.refresh(old_staged)
    assert old_staged.pii_scrub_status == "PURGED"
    assert old_staged.raw_payload.get("_retention_purged") is True
    assert "temporary_transient_data" not in old_staged.raw_payload
    # Crucially, hash is kept intact for non-repudiation
    assert old_staged.payload_hash_sha256 == "abc123canonicalhash"

    # Verify purge audit event recorded
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == EVENT_RAW_STAGING_RETENTION_PURGE)
        .order_by(AuditEventModel.timestamp.desc())
        .first()
    )
    assert audit_ev is not None


def test_dpdp_section12_record_erasure(db_session: Session):
    """Verify DPDP Act Section 12 record erasure workflow."""
    orchestrator = AcquisitionOrchestrator(db=db_session)

    # Create dummy dataset and transaction
    dataset = DatasetMetadataModel(
        name="Erasure_Test_Dataset",
        source_type="user_upload",
        file_format="csv",
        original_filename="erasure_test.csv",
        file_hash_sha256="dummy_hash_for_erasure_test",
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    tx = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=1,
        fingerprint_hash="fingerprint_to_erase",
        city="Bengaluru",
        locality="Indiranagar",
        project_name="Indira Enclave",
        property_type="Apartment",
        transaction_date=datetime.now(timezone.utc),
        transaction_quarter="2026Q1",
        carpet_area_sqft=1200.0,
        transaction_price=10000000.0,
        price_per_sqft=8333.33,
        raw_data={"unit": "Flat 101"},
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    tx_id = tx.id

    # Create associated duplicate record
    dup = DuplicateRecordModel(
        dataset_id=dataset.id,
        row_index=2,
        fingerprint_hash="fingerprint_to_erase",
        matched_transaction_id=tx_id,
        raw_data={"buyer": "Confidential Party"},
    )
    db_session.add(dup)
    db_session.commit()

    # Execute DPDP Section 12 Erasure
    success = orchestrator.erase_transaction_record(
        transaction_id=tx_id,
        reason="Data Principal DPDP Section 12 Right to Erasure Request",
        actor_id="DATA_PROTECTION_OFFICER",
    )
    assert success is True

    # Record should no longer be present in active valuation transactions
    tx_check = db_session.query(ImportedTransactionModel).filter(ImportedTransactionModel.id == tx_id).first()
    assert tx_check is None

    # Duplicate raw data should be erased
    db_session.refresh(dup)
    assert dup.raw_data.get("_erased") is True

    # Audit event should be recorded
    audit_ev = (
        db_session.query(AuditEventModel)
        .filter(AuditEventModel.event_type == EVENT_DATASET_RECORD_ERASURE)
        .order_by(AuditEventModel.timestamp.desc())
        .first()
    )
    assert audit_ev is not None
    payload = json.loads(audit_ev.payload_json) if isinstance(audit_ev.payload_json, str) else audit_ev.payload_json
    assert payload.get("transaction_id") == tx_id


# ---------------------------------------------------------------------------
# 5. Logging Redaction Tests
# ---------------------------------------------------------------------------

def test_logger_redacts_credentials_and_pii():
    """Verify that logging filter catches PAN, Aadhaar, email, phone, and auth tokens."""
    sample_log = (
        "User auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.abc; "
        "Taxpayer PAN: ABCDE1234F; "
        "Aadhaar: 2345 6789 0123; "
        "Phone: 9876543210; "
        "Email: admin@bank.gov.in"
    )

    redacted = redact_sensitive_text(sample_log)
    assert "Bearer [REDACTED]" in redacted
    assert "[REDACTED_PAN]" in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "ABCDE1234F" not in redacted
    assert "2345 6789 0123" not in redacted
    assert "9876543210" not in redacted
    assert "admin@bank.gov.in" not in redacted
