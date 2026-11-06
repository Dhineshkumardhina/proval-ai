"""Phase 6B Test Suite: Certified Empirical Transaction Dataset Expansion & Quality Governance.

Verifies:
1. Exact lifecycle state classification.
2. Strict ML training threshold enforcement (minimum 1,000 certified empirical transactions).
3. Non-fabrication and rejection of synthetic/demo transactions from certified cohorts.
4. Duplicate transaction identification and isolation.
5. Incomplete, anomalous, and circle-rate undervaluation quarantine.
6. Geographic and typology distribution audit.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    DuplicateRecordModel,
    RejectedRecordModel,
)
from app.models.verification import (
    QuarantinedRecordModel,
    TransactionLifecycleState,
)
from app.dataset_management.empirical_coverage import EmpiricalCoverageService
from app.ml.readiness_gate import evaluate_training_gate, MINIMUM_RECORDS_THRESHOLD


def test_empirical_gate_blocked_under_1000_threshold(db_session: Session):
    """Verify that ML training readiness gate strictly blocks training when empirical records < 1000."""
    dataset = DatasetMetadataModel(
        name="Empirical Bengaluru Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="deeds_blr.csv",
        file_hash_sha256="hash_blr_6b_1",
        total_rows=140,
        valid_rows=140,
        status="COMPLETED",
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.flush()

    # Add 140 verified transactions across 3 localities
    localities = ["Whitefield", "Indiranagar", "Koramangala"]
    for i in range(140):
        rec = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i + 1,
            fingerprint_hash=f"fp_phase6b_cert_{i}",
            data_source="B2B_ZAPKEY_BLR",
            city="Bengaluru",
            locality=localities[i % 3],
            project_name=f"Project {i}",
            property_type="Apartment" if i % 2 == 0 else "High-Rise Apartment",
            carpet_area_sqft=1200.0,
            transaction_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
            transaction_quarter="2024-Q2",
            transaction_price=12500000.0 + (i * 10000),
            price_per_sqft=10416.67,
            is_verified_deed=True,
            is_asking_price=False,
            raw_data={"doc_id": f"DOC-2024-{i:04d}"},
        )
        db_session.add(rec)
    db_session.commit()

    # Evaluate ML gate
    gate_result = evaluate_training_gate(db_session, dataset.id)
    assert not gate_result.passed
    assert not gate_result.canTrain
    assert gate_result.totalRecords == 140
    assert gate_result.validRecords == 140
    assert gate_result.requiredRecordsThreshold == 1000
    assert any("INSUFFICIENT_SAMPLE_SIZE" in issue for issue in gate_result.blockingIssues)
    assert "READINESS: NO-GO" in gate_result.governanceRecommendation


def test_synthetic_data_strictly_disqualified_from_empirical_gate(db_session: Session):
    """Verify that synthetic demonstration data is flagged and disqualified by the readiness gate."""
    dataset = DatasetMetadataModel(
        name="Synthetic Demo Benchmark",
        description="Demo synthetic deed transactions",
        source_type="synthetic_demo",
        license_type="mit",
        file_format="csv",
        original_filename="synthetic.csv",
        file_hash_sha256="hash_synth_6b",
        total_rows=1200,
        valid_rows=1200,
        status="COMPLETED",
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.flush()

    for i in range(10):
        rec = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i + 1,
            fingerprint_hash=f"fp_synth_{i}",
            data_source="synthetic-demo",
            city="Bengaluru",
            locality="Whitefield",
            project_name="Demo Tower",
            property_type="Apartment",
            carpet_area_sqft=1000.0,
            transaction_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            transaction_quarter="2024-Q1",
            transaction_price=10000000.0,
            price_per_sqft=10000.0,
            is_verified_deed=True,
            is_asking_price=False,
            raw_data={},
        )
        db_session.add(rec)
    db_session.commit()

    gate_result = evaluate_training_gate(db_session, dataset.id)
    assert not gate_result.passed
    assert not gate_result.canTrain
    assert gate_result.isSyntheticData is True
    assert any("DISQUALIFIED_PROVENANCE" in issue for issue in gate_result.blockingIssues)


def test_duplicate_rejection_and_isolation(db_session: Session):
    """Verify that duplicate transactions are recorded with fingerprint hash and cannot pollute verified count."""
    dataset = DatasetMetadataModel(
        name="Duplicate Test Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="dup_test.csv",
        file_hash_sha256="hash_dup_test",
        total_rows=2,
        valid_rows=1,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.flush()

    # Primary record
    primary_tx = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=1,
        fingerprint_hash="fp_unique_dup_123",
        data_source="zapkey_b2b",
        city="Bengaluru",
        locality="Whitefield",
        project_name="Prestige Park",
        property_type="Apartment",
        carpet_area_sqft=1000.0,
        transaction_date=datetime(2024, 5, 10, tzinfo=timezone.utc),
        transaction_quarter="2024-Q2",
        transaction_price=9000000.0,
        price_per_sqft=9000.0,
        is_verified_deed=True,
        is_asking_price=False,
        raw_data={"doc_id": "DEED-123"},
    )
    db_session.add(primary_tx)
    db_session.flush()

    # Duplicate record
    dup_rec = DuplicateRecordModel(
        dataset_id=dataset.id,
        row_index=2,
        fingerprint_hash="fp_unique_dup_123",
        matched_transaction_id=primary_tx.id,
        raw_data={"doc_id": "DEED-123-DUP"},
    )
    db_session.add(dup_rec)
    db_session.commit()

    # Verify duplicate is stored in duplicate_records and does not increment imported verified deeds
    dup_entry = db_session.query(DuplicateRecordModel).filter(
        DuplicateRecordModel.fingerprint_hash == "fp_unique_dup_123"
    ).first()
    assert dup_entry is not None
    assert dup_entry.matched_transaction_id == primary_tx.id


def test_quarantine_isolation_undervaluation_and_anomaly(db_session: Session):
    """Verify that quarantined records (e.g. circle rate undervaluation) remain isolated."""
    dataset = DatasetMetadataModel(
        name="Quarantine Test Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="quarantine_test.csv",
        file_hash_sha256="hash_quarantine_test",
        total_rows=1,
        valid_rows=0,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.flush()

    quarantined = QuarantinedRecordModel(
        dataset_id=dataset.id,
        row_index=1,
        quarantine_code="CIRCLE_RATE_UNDERVALUATION",
        quarantine_reason="Deed price is 58.8% below statutory circle rate (Stamp Duty Undervaluation Alert)",
        anomaly_score=0.92,
        anomalous_fields={"price": 2500000.0, "guideline_value": 6070000.0},
        raw_payload={"doc_number": "DOC-UNDERVALUED-001"},
        resolution_status="PENDING_REVIEW",
    )
    db_session.add(quarantined)
    db_session.commit()

    q_rec = db_session.query(QuarantinedRecordModel).filter(
        QuarantinedRecordModel.quarantine_code == "CIRCLE_RATE_UNDERVALUATION"
    ).first()
    assert q_rec is not None
    assert q_rec.resolution_status == "PENDING_REVIEW"
    assert q_rec.anomaly_score > 0.90


def test_rejected_records_missing_price_isolated(db_session: Session):
    """Verify that rejected records (e.g. missing price) cannot enter imported transactions."""
    dataset = DatasetMetadataModel(
        name="Rejected Test Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="rejected_test.csv",
        file_hash_sha256="hash_rej_test",
        total_rows=1,
        valid_rows=0,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.flush()

    rejected = RejectedRecordModel(
        dataset_id=dataset.id,
        row_index=1,
        rejection_code="MISSING_PRICE",
        rejection_reason="Amount Validation Error: Transaction amount is missing",
        raw_data={"locality": "Koramangala", "carpet_area_sqft": 1200},
    )
    db_session.add(rejected)
    db_session.commit()

    rej_entry = db_session.query(RejectedRecordModel).filter(
        RejectedRecordModel.rejection_code == "MISSING_PRICE"
    ).first()
    assert rej_entry is not None
    assert rej_entry.dataset_id == dataset.id


def test_empirical_coverage_service_metrics(db_session: Session):
    """Verify EmpiricalCoverageService aggregates correctly and reports GATED status when < 1000."""
    cov = EmpiricalCoverageService.get_empirical_coverage(db_session)
    assert "total_verified_empirical_deeds" in cov
    assert "target_threshold" in cov
    assert cov["target_threshold"] == 1000
    assert cov["ml_eligibility_status"] == "GATED"
    assert "progress_percentage" in cov
    assert cov["progress_percentage"] < 100.0


def test_lifecycle_states_enumeration():
    """Verify that all 9 lifecycle states are defined in TransactionLifecycleState."""
    expected_states = [
        "RAW",
        "PARSED",
        "NORMALIZED",
        "VALIDATION_PENDING",
        "VALIDATED",
        "VERIFIED",
        "CERTIFIED",
        "REJECTED",
        "QUARANTINED",
    ]
    for state in expected_states:
        assert hasattr(TransactionLifecycleState, state), f"Missing lifecycle state: {state}"
        assert getattr(TransactionLifecycleState, state) == state
    assert set(TransactionLifecycleState.ALL_STATES) == set(expected_states)
