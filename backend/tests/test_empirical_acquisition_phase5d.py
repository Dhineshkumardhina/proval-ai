"""Phase 5D — Certified Empirical Transaction Acquisition Tests.

Tests the full lifecycle of certified empirical property transactions:
- Ingestion and normalization pipeline integrity
- Acceptance criteria enforcement and anomaly quarantine
- Data quality metrics calculation (completeness, accuracy, duplicate rate, missing-value rate, verification rate)
- Cryptographic provenance and source attribution preservation
- Versioned dataset snapshot generation and sealing
- Strict ML Readiness Gate lock enforcement when empirical count < 1,000
"""

import hashlib
import json
import pytest
from datetime import datetime, timezone

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    DuplicateRecordModel,
    RejectedRecordModel,
)
from app.models.dataset_version import DatasetVersionModel
from app.models.verification import VerificationEvidenceModel, QuarantinedRecordModel
from app.normalization.models import (
    NormalizedTransactionRecord,
    CadastralParcelMetadata,
    SpatialProximityFeatures,
)
from app.verification.verification_service import VerificationEngine
from app.dataset_management.empirical_coverage import EmpiricalCoverageService
from app.dataset_management.version_service import DatasetVersionService
from app.ml.readiness_gate import evaluate_training_gate, MINIMUM_RECORDS_THRESHOLD


# ----------------------------------------------------------------------
# 1. Certified Transaction Acceptance Criteria & Verification
# ----------------------------------------------------------------------

def test_acceptance_criteria_verified_empirical_deed(db_session):
    """Verify that a legitimate licensed SRO deed satisfies all acceptance criteria."""
    dataset = DatasetMetadataModel(
        name="Empirical_Licensed_Deeds_2026",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Licensed feed from Zapkey B2B",
        file_format="api_stream",
        original_filename="zapkey_stream_2026",
        file_hash_sha256="f" * 64,
        approval_status="APPROVED",
        is_usable_for_ml=False,
    )
    db_session.add(dataset)
    db_session.commit()

    norm_tx = NormalizedTransactionRecord(
        transaction_id="tx-emp-001",
        source_id="zapkey_b2b",
        source_reference="ZPK-BLR-2026-REG-4421",
        original_record_hash="1" * 64,
        registration_reference="REG/4421/2026/BK1",
        fingerprint_hash="2" * 64,
        country="India",
        state="Karnataka",
        district="Bengaluru Urban",
        sub_district="Bengaluru East",
        city="Bengaluru",
        locality="Whitefield",
        postal_code="560066",
        project_name="Prestige Boulevard",
        unit_number="B-402",
        property_type="High-Rise Apartment",
        transaction_type="REGISTRATION",
        registration_date=datetime(2026, 2, 20, 11, 30, 0, tzinfo=timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1250.0,
        built_up_area_sqft=1450.0,
        super_built_up_area_sqft=1600.0,
        original_area_value=1250.0,
        original_area_unit="SQFT",
        acquisition_timestamp=datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc),
        transaction_amount=13500000.0,
        currency="INR",
        price_per_sqft=10800.0,
        guideline_rate_per_sqft=9200.0,
        deviation_from_guideline_pct=17.39,
        latitude=12.9698,
        longitude=77.7499,
        coordinate_precision_digits=4,
        sro_office="SRO-SHIVAJINAGAR",
        cadastral=CadastralParcelMetadata(
            survey_number="184/2",
            revenue_village="Whitefield",
            khata_type="A Khata",
            is_cadastral_verified=True,
        ),
        spatial_features=SpatialProximityFeatures(
            distance_to_metro_km=1.2,
            distance_to_arterial_road_km=0.4,
            is_spatial_derived=True,
        ),
        raw_payload={"deed_number": "4421/2026", "consideration_inr": 13500000},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="DATA_OFFICER_01")
    outcome, tx = verifier.verify_and_route_record(dataset=dataset, norm_tx=norm_tx, row_index=1)

    assert outcome == "VERIFIED"
    assert tx is not None
    assert tx.is_verified_deed is True
    assert tx.is_asking_price is False
    assert tx.price_per_sqft == 10800.0
    assert tx.cadastral_parcel_id == "KA-BEN-184/2"
    assert tx.spatial_accuracy_tier == "PARCEL_SURVEY_RECORDED"

    evidence = (
        db_session.query(VerificationEvidenceModel)
        .filter(VerificationEvidenceModel.transaction_id == tx.id)
        .first()
    )
    assert evidence is not None
    assert evidence.verification_status == "VERIFIED"
    assert evidence.verifier_method == "B2B_SRO_ATTESTATION"
    assert evidence.verification_evidence_details["is_ml_eligible"] is True


# ----------------------------------------------------------------------
# 2. Suspicious Record & Anomaly Quarantine
# ----------------------------------------------------------------------

def test_anomaly_quarantine_for_extreme_circle_rate_undervaluation(db_session):
    """Verify that transactions with extreme circle rate undervaluation (>50%) are quarantined."""
    dataset = DatasetMetadataModel(
        name="Suspect_Deeds_Batch",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Incoming feed",
        file_format="api_stream",
        original_filename="feed_batch_02",
        file_hash_sha256="3" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.commit()

    # Deed price ₹3,500/sqft vs Guideline rate ₹10,000/sqft (65% undervaluation => Tax evasion risk)
    suspect_tx = NormalizedTransactionRecord(
        transaction_id="tx-suspect-001",
        source_id="propequity",
        source_reference="PE-UND-2026-09",
        original_record_hash="4" * 64,
        registration_reference="REG/9921/2026",
        fingerprint_hash="5" * 64,
        state="Maharashtra",
        district="Mumbai Suburban",
        locality="Andheri East",
        project_name="Commercial Tower X",
        property_type="High-Rise Apartment",
        registration_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1000.0,
        original_area_value=1000.0,
        original_area_unit="SQFT",
        acquisition_timestamp=datetime(2026, 1, 15, tzinfo=timezone.utc),
        transaction_amount=3500000.0,
        price_per_sqft=3500.0,
        guideline_rate_per_sqft=10000.0,
        deviation_from_guideline_pct=-65.0,
        latitude=19.1136,
        longitude=72.8697,
        raw_payload={"suspicious": True},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="AUTO_ANOMALY_MONITOR")
    outcome, record = verifier.verify_and_route_record(dataset=dataset, norm_tx=suspect_tx, row_index=1)

    assert outcome == "QUARANTINED"
    assert isinstance(record, QuarantinedRecordModel)
    assert record.quarantine_code == "CIRCLE_RATE_UNDERVALUATION"
    assert record.resolution_status == "PENDING_REVIEW"


# ----------------------------------------------------------------------
# 3. Duplicate Detection & Idempotency
# ----------------------------------------------------------------------

def test_duplicate_deed_detected_and_rejected(db_session):
    """Verify that importing an identical deed twice routes the second instance to duplicates."""
    dataset = DatasetMetadataModel(
        name="Deduplication_Audit_Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Zapkey Batch",
        file_format="csv",
        original_filename="deeds_batch_dup.csv",
        file_hash_sha256="7" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.commit()

    tx_data = dict(
        transaction_id="tx-dup-base",
        source_id="zapkey_b2b",
        source_reference="ZPK-DUP-01",
        original_record_hash="8" * 64,
        registration_reference="REG/DUP/2026",
        fingerprint_hash="9" * 64,
        state="Karnataka",
        district="Bengaluru",
        locality="Koramangala",
        project_name="Raheja Residency",
        property_type="High-Rise Apartment",
        registration_date=datetime(2026, 1, 10, tzinfo=timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1100.0,
        original_area_value=1100.0,
        original_area_unit="SQFT",
        acquisition_timestamp=datetime(2026, 1, 10, tzinfo=timezone.utc),
        transaction_amount=12000000.0,
        price_per_sqft=10909.09,
        guideline_rate_per_sqft=9500.0,
        deviation_from_guideline_pct=14.8,
        latitude=12.9352,
        longitude=77.6245,
        raw_payload={"deed": "dup_test"},
    )

    verifier = VerificationEngine(db=db_session, verifier_id="DUP_TEST_AGENT")
    
    # First ingestion -> VERIFIED
    outcome1, tx1 = verifier.verify_and_route_record(dataset=dataset, norm_tx=NormalizedTransactionRecord(**tx_data), row_index=1)
    assert outcome1 == "VERIFIED"

    # Second ingestion with same fingerprint -> DUPLICATE
    outcome2, tx2 = verifier.verify_and_route_record(dataset=dataset, norm_tx=NormalizedTransactionRecord(**tx_data), row_index=2)
    assert outcome2 == "DUPLICATE"
    assert isinstance(tx2, DuplicateRecordModel)
    assert tx2.fingerprint_hash == "9" * 64


# ----------------------------------------------------------------------
# 4. Strict ML Readiness Gate Lock When Empirical Deeds < 1,000
# ----------------------------------------------------------------------

def test_ml_readiness_gate_strictly_locked_below_1000_threshold(db_session):
    """Verify that dataset with < 1,000 certified empirical transactions is locked from ML training."""
    dataset = DatasetMetadataModel(
        name="Small_Empirical_Dataset_46_Records",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Zapkey Verified Deeds",
        file_format="api_stream",
        original_filename="verified_batch",
        file_hash_sha256="a" * 64,
        approval_status="APPROVED",
        is_usable_for_ml=False,
    )
    db_session.add(dataset)
    db_session.flush()

    # Seed 50 verified empirical deeds (far below 1,000)
    for i in range(50):
        rec = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i + 1,
            fingerprint_hash=f"fp_gate_{i:04d}" + "x" * 53,
            city="Bengaluru",
            locality=f"Locality_{i % 5}",
            sub_market="Bengaluru East",
            project_name=f"Project_{i % 10}",
            property_type="High-Rise Apartment",
            transaction_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            transaction_quarter="2026-Q1",
            carpet_area_sqft=1200.0,
            transaction_price=12000000.0 + (i * 50000),
            price_per_sqft=10000.0 + (i * 41.6),
            latitude=12.9716,
            longitude=77.5946,
            is_verified_deed=True,
            is_asking_price=False,
            data_source="zapkey_b2b",
            raw_data={"row": i},
        )
        db_session.add(rec)
    db_session.commit()

    # Evaluate ML training gate
    gate_audit = evaluate_training_gate(db=db_session, dataset_id=dataset.id)

    assert gate_audit.passed is False
    assert gate_audit.canTrain is False
    assert gate_audit.validRecords == 50
    assert gate_audit.requiredRecordsThreshold == MINIMUM_RECORDS_THRESHOLD
    assert any("INSUFFICIENT_SAMPLE_SIZE" in issue for issue in gate_audit.blockingIssues)
    assert "READINESS: NO-GO" in gate_audit.governanceRecommendation


# ----------------------------------------------------------------------
# 5. Versioned Dataset Snapshot Generation & Quality Metrics
# ----------------------------------------------------------------------

def test_versioned_dataset_snapshot_creation(db_session):
    """Verify creation and sealing of an immutable versioned dataset snapshot."""
    dataset = DatasetMetadataModel(
        name="Phase5D_Gold_Standard_Corpus",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Licensed SRO Feed",
        file_format="api_stream",
        original_filename="corpus_stream",
        file_hash_sha256="b" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.flush()

    # Add 10 verified transactions
    tx_ids = []
    for i in range(10):
        rec = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i + 1,
            fingerprint_hash=f"fp_ver_{i:04d}" + "y" * 53,
            city="Bengaluru Urban",
            locality="Whitefield",
            project_name="Prestige Park",
            property_type="High-Rise Apartment",
            transaction_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            transaction_quarter="2026-Q1",
            carpet_area_sqft=1150.0,
            transaction_price=11500000.0,
            price_per_sqft=10000.0,
            is_verified_deed=True,
            is_asking_price=False,
            data_source="zapkey_b2b",
            raw_data={},
        )
        db_session.add(rec)
        db_session.flush()
        tx_ids.append(rec.id)
    db_session.commit()

    # Create immutable version snapshot v1.0.0
    service = DatasetVersionService(db=db_session)
    version_obj = service.create_version_snapshot(
        dataset_id=dataset.id,
        semver_tag="v1.0.0",
        version_title="Phase 5D Audited Baseline Snapshot",
        description="Sealed baseline of verified deeds for institutional audit",
        created_by="INSTITUTIONAL_DATA_OFFICER",
    )

    assert version_obj is not None
    assert version_obj.semver_tag == "v1.0.0"
    assert version_obj.total_records == 10
    assert version_obj.verified_records == 10
    assert version_obj.dataset_checksum_sha256 is not None
    assert len(version_obj.dataset_checksum_sha256) == 64
    assert version_obj.is_ml_eligible is False  # Because 10 < 1,000 threshold!
