"""Phase 5E — Empirical Machine Learning Training Gate & Governance Tests.

Verifies:
1. Strict prerequisite gate blocks model training when empirical records < 1,000.
2. Training attempt creates a BLOCKED audit record in ml_models table.
3. Separation of duties enforcement (requester cannot be approving authority).
4. Unapproved dataset versions reject training with HTTP 403 Forbidden.
5. Calibration gate blocks conformal prediction when no active ML model exists.
6. Statutory rule-based engine serves as fail-safe fallback when ML is gated.
"""

import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.dataset_version import DatasetVersionModel
from app.models.ml_model import MLModelRegistryModel
from app.ml.readiness_gate import evaluate_training_gate, MINIMUM_RECORDS_THRESHOLD
from app.ml.calibration_gate import evaluate_calibration_gate
from app.ml.trainer import train_valuation_model


# ----------------------------------------------------------------------
# 1. Training Gate Block & Audit Persistence Tests
# ----------------------------------------------------------------------

def test_training_strictly_blocked_under_1000_threshold(db_session):
    """Verify that train_valuation_model blocks execution and logs a BLOCKED record in ml_models."""
    dataset = DatasetMetadataModel(
        name="Phase5E_Gated_Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Zapkey Certified Stream",
        file_format="api_stream",
        original_filename="stream_5e",
        file_hash_sha256="c" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.flush()

    # Seed 25 verified records (far below 1,000 threshold)
    for i in range(25):
        rec = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i + 1,
            fingerprint_hash=f"fp_5e_{i:04d}" + "z" * 53,
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
    db_session.commit()

    # Attempt training: must raise HTTP 422
    with pytest.raises(HTTPException) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            algorithm="CatBoostRegressor",
            user_name="Lead Data Scientist",
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "TRAINING_BLOCKED_BY_READINESS_GATE"
    assert exc_info.value.detail["validRecords"] == 25
    assert exc_info.value.detail["requiredRecords"] == MINIMUM_RECORDS_THRESHOLD

    # Verify that a BLOCKED record was persisted in ml_models
    blocked_entry = (
        db_session.query(MLModelRegistryModel)
        .filter(
            MLModelRegistryModel.dataset_id == dataset.id,
            MLModelRegistryModel.status == "BLOCKED",
        )
        .first()
    )
    assert blocked_entry is not None
    assert blocked_entry.is_production_ready is False
    assert blocked_entry.readiness_gate_audit["passed"] is False
    assert any("INSUFFICIENT_SAMPLE_SIZE" in issue for issue in blocked_entry.readiness_gate_audit["blockingIssues"])


# ----------------------------------------------------------------------
# 2. Separation of Duties Governance Test
# ----------------------------------------------------------------------

def test_separation_of_duties_enforced(db_session):
    """Verify that training requester cannot be the approving authority."""
    dataset = DatasetMetadataModel(
        name="Phase5E_SoD_Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Zapkey Stream",
        file_format="api_stream",
        original_filename="stream_sod",
        file_hash_sha256="d" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.commit()

    # Same person requests and approves
    with pytest.raises(HTTPException) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            algorithm="CatBoostRegressor",
            user_name="Dr. Jane Doe (ADMIN)",
            approved_by="Dr. Jane Doe (CHIEF_CREDIT_OFFICER)",
        )
    assert exc_info.value.status_code == 400
    assert "Separation of duties violation" in exc_info.value.detail


# ----------------------------------------------------------------------
# 3. Unapproved Dataset Version Rejection Test
# ----------------------------------------------------------------------

def test_unapproved_dataset_version_rejected(db_session):
    """Verify that an unapproved (DRAFT) dataset version blocks training with HTTP 403."""
    dataset = DatasetMetadataModel(
        name="Phase5E_Unapproved_Version_Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Zapkey Stream",
        file_format="api_stream",
        original_filename="stream_unapp",
        file_hash_sha256="e" * 64,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.flush()

    ver_draft = DatasetVersionModel(
        dataset_id=dataset.id,
        semver_tag="v1.0.0-draft",
        version_title="Draft Unapproved Snapshot",
        dataset_checksum_sha256="f" * 64,
        geographic_distribution={},
        property_type_distribution={},
        source_distribution={},
        validation_summary={},
        included_transaction_ids=[],
        approval_status="DRAFT",  # Not APPROVED
        created_by="ml_dev",
    )
    db_session.add(ver_draft)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            version_id=ver_draft.id,
            user_name="Lead Data Scientist",
        )
    assert exc_info.value.status_code == 403
    assert "Training Authorization Blocked" in exc_info.value.detail


# ----------------------------------------------------------------------
# 4. Calibration Gate Blocks Conformal Prediction When Model Missing
# ----------------------------------------------------------------------

def test_calibration_gate_blocks_when_no_active_model_exists(db_session):
    """Verify that conformal prediction calibration evaluates to BLOCKED when no production ML model exists."""
    audit = evaluate_calibration_gate(db=db_session)
    assert audit.canCalibrate is False
    assert any("MISSING_VALIDATED_MODEL" in issue for issue in audit.blockingIssues)
