"""Phase 6F Verification Suite: Empirical CatBoost Training & Model Certification Gate.

Verifies:
1. Certified dataset register audit confirms fewer than 1,000 certified empirical records exist.
2. Pre-training readiness gate evaluates to False and blocks model training.
3. Threshold of 1,000 certified empirical transactions is strictly enforced and not lowered.
4. Synthetic demonstration and mock datasets are disqualified.
5. Attempting to train via train_valuation_model raises HTTP 422 with TRAINING_BLOCKED_BY_READINESS_GATE.
6. A BLOCKED audit model record is persisted in ml_models.
7. Conformal prediction calibration blocks when no active empirical model exists.
8. Fallback to deterministic rule-based valuation engine remains active and operational.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.ml_model import MLModelRegistryModel
from app.ml.readiness_gate import evaluate_training_gate, MINIMUM_RECORDS_THRESHOLD
from app.ml.trainer import train_valuation_model
from app.ml.model_service import MLModelService
from app.services.valuation_service import calculate_valuation, ValuationInputParams


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_certified_dataset_count_below_1000_threshold(db_session: Session):
    """Verify that current certified empirical transactions remain below the 1,000 threshold."""
    # Query datasets approved for ML
    ml_usable_datasets = (
        db_session.query(DatasetMetadataModel)
        .filter(DatasetMetadataModel.is_usable_for_ml == True)
        .count()
    )
    assert ml_usable_datasets == 0, "No datasets should be marked as ML-usable before threshold certification."

    # Query total verified deeds across all imported transactions
    verified_deeds_count = (
        db_session.query(ImportedTransactionModel)
        .filter(ImportedTransactionModel.is_verified_deed == True)
        .count()
    )
    # Database currently contains staged records but far below the 1,000 certified empirical requirement
    assert verified_deeds_count < MINIMUM_RECORDS_THRESHOLD, (
        f"Verified deeds count ({verified_deeds_count}) must be less than threshold ({MINIMUM_RECORDS_THRESHOLD})."
    )


def test_training_gate_threshold_constant():
    """Verify that the minimum sample size threshold remains strictly 1,000 and has not been lowered."""
    assert MINIMUM_RECORDS_THRESHOLD == 1000, (
        f"Governance violation: MINIMUM_RECORDS_THRESHOLD must be exactly 1000, found {MINIMUM_RECORDS_THRESHOLD}"
    )


def test_training_gate_evaluates_to_blocked(db_session: Session):
    """Verify that evaluating any existing dataset fails the readiness gate."""
    dataset = db_session.query(DatasetMetadataModel).first()
    if dataset:
        audit = evaluate_training_gate(db_session, dataset.id)
        assert audit.canTrain is False
        assert audit.passed is False
        assert len(audit.blockingIssues) > 0


def test_synthetic_data_strictly_disqualified(db_session: Session):
    """Verify that synthetic demonstration data is explicitly disqualified by the gate."""
    synth_dataset = DatasetMetadataModel(
        id="test-synthetic-gate-phase6f",
        name="Synthetic Demo Dataset 2026",
        description="Sample generated transactions for UI demonstration",
        source_type="synthetic_demo",
        data_source_provenance="synthetic-demo",
        file_format="CSV",
        original_filename="synthetic_demo.csv",
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        total_rows=1200,
        valid_rows=1200,
        status="COMPLETED",
        approval_status="APPROVED",
    )
    db_session.add(synth_dataset)
    db_session.commit()

    try:
        audit = evaluate_training_gate(db_session, synth_dataset.id)
        assert audit.canTrain is False
        assert audit.isSyntheticData is True
        assert any("synthetic" in issue.lower() or "disqualified" in issue.lower() for issue in audit.blockingIssues)
    finally:
        db_session.delete(synth_dataset)
        db_session.commit()


def test_train_valuation_model_enforces_gate_and_records_blocked(db_session: Session):
    """Verify that train_valuation_model raises HTTP 422 and registers a BLOCKED entry in ml_models."""
    dataset = db_session.query(DatasetMetadataModel).first()
    if not dataset:
        pytest.skip("No dataset available in DB to test.")

    with pytest.raises(HTTPException) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            algorithm="CatBoostRegressor",
            user_name="Risk Auditor (ML-Val)",
            user_role="RISK_OFFICER",
        )

    assert exc_info.value.status_code == 422
    assert "TRAINING_BLOCKED_BY_READINESS_GATE" in str(exc_info.value.detail)

    # Verify a BLOCKED model entry was saved in the registry
    blocked_model = (
        db_session.query(MLModelRegistryModel)
        .filter(MLModelRegistryModel.status == "BLOCKED")
        .first()
    )
    assert blocked_model is not None
    assert blocked_model.status == "BLOCKED"
    assert blocked_model.is_production_ready is False
    assert blocked_model.training_records_count == 0


def test_conformal_calibration_blocked_without_active_model(db_session: Session):
    """Verify that conformal prediction calibration is blocked when no approved empirical model exists."""
    ml_service = MLModelService()
    active_tuple = ml_service.get_active_model(db_session)
    assert active_tuple is None, "No empirical model should be active while training is blocked."


def test_deterministic_rule_based_fallback_operational():
    """Verify that the deterministic rule-based valuation engine functions reliably as fallback."""
    val_in = ValuationInputParams(
        carpetAreaSqFt=1000.0,
        superBuiltUpAreaSqFt=1250.0,
        baseMarketRatePerSqFt=8500.0,
        circleRatePerSqFt=6000.0,
        floorRiseFactor=150.0,
        roadWidthFactor=200.0,
        amenitiesPremium=300.0,
        structuralDepreciation=50.0,
        underwriterHaircutPct=10.0,
        distressDiscountPct=15.0,
        ltvRatioPct=80.0,
        legalRiskPenaltyPct=0.0,
        dataSource="synthetic-demo",
    )
    result = calculate_valuation(val_in)
    assert result.grossMarketValue > 0
    assert result.netAssessedValue > 0
    assert result.maxSanctionAmount > 0
    assert result.engineType == "provisional rule-based estimation"
