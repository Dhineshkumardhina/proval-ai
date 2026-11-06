"""Comprehensive verification, quarantine, anomaly, and provenance tests."""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel, DuplicateRecordModel, RejectedRecordModel
from app.models.verification import (
    QuarantinedRecordModel,
    VerificationEvidenceModel,
    TransactionLifecycleState,
)
from app.normalization.engine import PropertyNormalizationEngine
from app.verification.duplicate_detector import compute_deterministic_deed_hash, calculate_property_similarity
from app.verification.anomaly_detector import TransactionAnomalyDetector
from app.verification.verification_service import VerificationEngine


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_dataset(db_session: Session):
    ds = DatasetMetadataModel(
        name=f"Verification_Test_Dataset_{uuid.uuid4().hex[:6]}",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Test Harness SRO Provider",
        file_format="api_stream",
        original_filename="stream",
        file_hash_sha256=uuid.uuid4().hex,
        status="INGESTING",
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


# =========================================================================
# 1. Deterministic SRO Deed Hashing & Fuzzy Duplicate Scoring
# =========================================================================

def test_deterministic_deed_hashing():
    """Verify identical SRO attributes produce identical canonical SHA-256 hashes."""
    h1 = compute_deterministic_deed_hash(
        state="Karnataka",
        district="Bengaluru Urban",
        sro_office="Shivajinagar",
        registration_year="2024",
        registration_number="DOC-1234/2024",
        unit_number="Flat 402",
    )
    h2 = compute_deterministic_deed_hash(
        state="  karnataka  ",
        district="bengaluru urban",
        sro_office="SHIVAJINAGAR",
        registration_year="2024",
        registration_number="doc-1234/2024",
        unit_number="flat 402",
    )
    assert h1 == h2
    assert len(h1) == 64


def test_fuzzy_duplicate_candidate_detection():
    """Verify fuzzy similarity scoring identifies close suspect candidates without auto-merging."""
    rec_a = {
        "project_name": "Prestige Lakeside Habitat",
        "locality": "Whitefield",
        "carpet_area_sqft": 1450.0,
        "transaction_price": 18500000.0,
    }
    rec_b = {
        "project_name": "Prestige Lakeside Habitat Phase 1",
        "locality": "Whitefield Kadugodi",
        "carpet_area_sqft": 1455.0,  # ~0.3% difference
        "transaction_price": 18500000.0,  # Identical
    }
    score, reasons = calculate_property_similarity(rec_a, rec_b)
    assert score >= 0.70
    assert any("Identical consideration amount" in r for r in reasons)


# =========================================================================
# 2. Anomaly Detection & Quarantine Routing
# =========================================================================

def test_anomaly_detection_extreme_rate_outlier():
    """Verify impossible price-per-sqft triggers quarantine anomaly verdict."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 450000000.0,  # ₹45 Cr for 1000 sqft -> ₹450,000/sqft (Extravagant outlier)
    }
    verdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert "RATE_OUTLIER_ANOMALY" in verdict.quarantine_code
    assert verdict.anomaly_score >= 0.4


def test_anomaly_detection_undervaluation_vs_guideline():
    """Verify deed transacted below 50% of statutory circle rate flags undervaluation alert."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 4000000.0,  # ₹4,000/sqft
        "guideline_rate_per_sqft": 9000.0,  # Circle rate is ₹9,000/sqft (55% undervaluation)
    }
    verdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert "CIRCLE_RATE_UNDERVALUATION" in verdict.quarantine_code


# =========================================================================
# 3. Verification Engine Lifecycle & Provenance Audit
# =========================================================================

def test_verification_routing_quarantine(db_session: Session, mock_dataset: DatasetMetadataModel):
    """Verify anomalous record is routed to QuarantinedRecordModel and does not enter ML transactions."""
    engine = PropertyNormalizationEngine(source_id="src-test", source_code="ZAP_TEST")
    verifier = VerificationEngine(db_session, verifier_id="TEST_VERIFIER")

    # Record with severe undervaluation anomaly
    raw = {
        "registration_number": f"ANOM-{uuid.uuid4().hex[:6]}",
        "registration_date": "2024-06-15",
        "price": 3500000.0,  # ₹3,500/sqft
        "area": 1000.0,
        "guideline_rate_per_sqft": 8500.0,
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "locality": "Whitefield",
    }
    norm_tx, err = engine.normalize_record(raw, row_index=10)
    assert err is None

    outcome, saved = verifier.verify_and_route_record(mock_dataset, norm_tx, row_index=10)
    db_session.commit()

    assert outcome == "QUARANTINED"
    assert isinstance(saved, QuarantinedRecordModel)
    assert saved.resolution_status == "PENDING_REVIEW"
    assert "CIRCLE_RATE_UNDERVALUATION" in saved.quarantine_code


def test_verification_evidence_provenance_link(db_session: Session, mock_dataset: DatasetMetadataModel):
    """Verify clean record enters VERIFIED state and creates immutable VerificationEvidenceModel."""
    engine = PropertyNormalizationEngine(source_id="ZAPKEY_COMMERCIAL_FEED", source_code="ZAP_CLEAN")
    verifier = VerificationEngine(db_session, verifier_id="SENIOR_UNDERWRITER_AUTO")

    raw = {
        "registration_number": f"CLEAN-{uuid.uuid4().hex[:6]}",
        "registration_date": "2024-07-20",
        "price": 12500000.0,  # ₹12,500/sqft
        "area": 1000.0,
        "guideline_rate_per_sqft": 11000.0,
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "locality": "Whitefield",
        "sro_office": "Shivajinagar SRO",
        "is_verified": True,
    }
    norm_tx, err = engine.normalize_record(raw, row_index=11, dataset_version="v2.1.0")
    assert err is None

    outcome, saved = verifier.verify_and_route_record(mock_dataset, norm_tx, row_index=11)
    db_session.commit()

    assert outcome == "VERIFIED"
    assert isinstance(saved, ImportedTransactionModel)
    assert saved.is_verified_deed is True

    # Confirm cryptographic verification evidence was recorded
    ev = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == saved.id)
        .first()
    )
    assert ev is not None
    assert ev.verification_status == TransactionLifecycleState.VERIFIED
    assert ev.verifier_id == "SENIOR_UNDERWRITER_AUTO"
    assert ev.dataset_version == "v2.1.0"
    assert len(ev.original_record_hash) == 64
    assert len(ev.normalized_record_hash) == 64

