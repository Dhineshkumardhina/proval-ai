"""Automated tests for Statistical Uncertainty Quantification & Split Conformal Prediction (Phase 2F).

Covers:
1. Conformal nonconformity score calculation.
2. Calibration quantiles with finite-sample rank adjustment.
3. Configurable coverage levels (90% and 95%).
4. Prediction interval construction and bounds checking.
5. Geographic and subgroup coverage evaluation.
6. Strict calibration gate (missing model, synthetic data, insufficient sample size, leakage).
7. Refusal to manufacture prediction intervals when calibration is unavailable.
8. Conceptual taxonomy separation (Rule consistency vs Conformal intervals).
9. FastAPI uncertainty API endpoints integration.
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.ml_model import MLModelRegistryModel
from app.models.uncertainty import CalibrationArtifactModel
from app.ml.conformal import (
    compute_nonconformity_scores,
    calculate_conformal_quantile,
    generate_prediction_interval,
    evaluate_subgroup_coverage,
    calibrate_conformal_model,
)
from app.ml.calibration_gate import evaluate_calibration_gate, MINIMUM_CALIBRATION_RECORDS
from app.ml.uncertainty_service import uncertainty_service, CONCEPTUAL_TAXONOMY
from app.schemas.uncertainty import UncertaintyPredictionRequest


def test_conformal_score_calculation():
    """Verify nonconformity score computation s_i = |y_i - y_pred_i|."""
    y_true = np.array([10000000.0, 15000000.0, 8000000.0])
    y_pred = np.array([9500000.0, 16000000.0, 8000000.0])

    scores = compute_nonconformity_scores(y_true, y_pred)
    assert len(scores) == 3
    assert np.allclose(scores, [500000.0, 1000000.0, 0.0])


def test_calibration_quantiles_finite_sample_rank_adjustment():
    """Verify finite-sample adjusted conformal quantile calculation: ceil((n+1)(1-alpha))/n."""
    np.random.seed(42)
    scores = np.sort(np.random.uniform(100000, 2000000, 100))

    # 90% coverage on n=100: rank = ceil(101 * 0.90) = ceil(90.9) = 91
    q_90, p_90, guaranteed_90 = calculate_conformal_quantile(scores, 0.90)
    assert guaranteed_90 is True
    assert p_90 == 0.91
    assert q_90 == scores[90]  # 0-indexed 90th element (91st order statistic)

    # 95% coverage on n=100: rank = ceil(101 * 0.95) = ceil(95.95) = 96
    q_95, p_95, guaranteed_95 = calculate_conformal_quantile(scores, 0.95)
    assert guaranteed_95 is True
    assert p_95 == 0.96
    assert q_95 > q_90

    # Test small sample size limitation: n = 10 cannot guarantee 95% coverage
    small_scores = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    q_small, _, guaranteed_small = calculate_conformal_quantile(small_scores, 0.95)
    assert guaranteed_small is False


def test_prediction_interval_construction():
    """Verify lower bound, upper bound, interval width, and relative width calculations."""
    point_estimate = 15000000.0  # ₹1.5 Cr
    quantile_q = 1500000.0       # ₹15 Lakhs

    lower, upper, width, rel_width = generate_prediction_interval(point_estimate, quantile_q)
    assert lower == 13500000.0
    assert upper == 16500000.0
    assert width == 3000000.0
    assert rel_width == 20.0  # (3M / 15M) * 100

    # Ensure lower bound is non-negative when quantile exceeds point estimate
    lower_bounded, _, _, _ = generate_prediction_interval(500000.0, 800000.0)
    assert lower_bounded == 0.0


def test_subgroup_coverage_evaluation():
    """Verify subgroup conditional coverage analysis across micro-markets, types, and sizes."""
    np.random.seed(42)
    n = 40
    cal_data = {
        "carpet_area_sqft": np.random.uniform(600, 2500, n),
        "city": ["Bengaluru"] * n,
        "locality": ["Whitefield"] * 20 + ["Indiranagar"] * 20,
        "property_type": ["High-Rise Apartment"] * 30 + ["Gated Villa"] * 10,
        "transaction_quarter": ["2024-Q1"] * 20 + ["2024-Q2"] * 20,
    }
    cal_df = pd.DataFrame(cal_data)
    scores = np.random.uniform(50000, 1000000, n)
    quantiles = {0.90: float(np.quantile(scores, 0.91)), 0.95: float(np.quantile(scores, 0.96))}

    subgroup_metrics = evaluate_subgroup_coverage(cal_df, scores, quantiles)
    assert len(subgroup_metrics) > 0

    categories = {m.subgroupCategory for m in subgroup_metrics}
    assert "locality" in categories
    assert "area_tier" in categories
    assert "property_type" in categories

    for m in subgroup_metrics:
        assert 0.0 <= m.empiricalCoverage <= 1.0
        assert m.meanIntervalWidth > 0
        assert isinstance(m.isUnderCovered, bool)


def test_calibration_gate_blocks_when_no_active_model(db_session):
    """Verify calibration gate blocks execution when no validated ML model is in registry."""
    # Clear any active model in test db
    db_session.query(MLModelRegistryModel).delete()
    db_session.commit()

    gate = evaluate_calibration_gate(db_session)
    assert gate.canCalibrate is False
    assert gate.status == "UNCERTAINTY_NOT_CALIBRATED"
    assert gate.activeModelAvailable is False
    assert any("MISSING_VALIDATED_MODEL" in issue for issue in gate.blockingIssues)


def test_calibration_gate_rejects_synthetic_calibration_dataset(db_session):
    """Verify calibration gate rejects synthetic or demo datasets."""
    # Create mock active model
    model = MLModelRegistryModel(
        version="v1.0.test-mock",
        algorithm="CatBoostRegressor",
        status="ACTIVE",
        is_production_ready=True,
        feature_names=["carpet_area_sqft"],
    )
    synth_dataset = DatasetMetadataModel(
        name="Synthetic Demo Calibration Set",
        description="Synthetic demonstration records",
        source_type="synthetic_demo",
        data_source_provenance="Synthetic test data",
        file_format="csv",
        original_filename="synth_cal.csv",
        file_hash_sha256="synth_hash",
        total_rows=150,
        valid_rows=150,
        status="COMPLETED",
    )
    db_session.add(model)
    db_session.add(synth_dataset)
    db_session.commit()

    gate = evaluate_calibration_gate(db_session, synth_dataset.id)
    assert gate.canCalibrate is False
    assert gate.isSyntheticData is True
    assert any("DISQUALIFIED_CALIBRATION_PROVENANCE" in issue for issue in gate.blockingIssues)


def test_calibration_gate_rejects_insufficient_sample_size(db_session):
    """Verify calibration gate rejects datasets with fewer than 100 records."""
    model = MLModelRegistryModel(
        version="v1.0.test-size",
        algorithm="CatBoostRegressor",
        status="ACTIVE",
        is_production_ready=True,
        feature_names=["carpet_area_sqft"],
    )
    dataset = DatasetMetadataModel(
        name="Small Genuine Calibration Set",
        source_type="licensed_vendor",
        file_format="csv",
        original_filename="small_cal.csv",
        file_hash_sha256="small_hash",
        total_rows=14,
        valid_rows=14,
        status="COMPLETED",
    )
    db_session.add(model)
    db_session.add(dataset)
    db_session.commit()

    # Add 14 records
    for i in range(14):
        tx = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i,
            fingerprint_hash=f"cal_fp_{i}",
            city="Bengaluru",
            locality="Whitefield",
            project_name=f"Project_{i}",
            property_type="High-Rise Apartment",
            transaction_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
            transaction_quarter="2024-Q2",
            carpet_area_sqft=1200.0,
            transaction_price=12000000.0,
            price_per_sqft=10000.0,
            is_verified_deed=True,
            is_asking_price=False,
            raw_data={},
        )
        db_session.add(tx)
    db_session.commit()

    gate = evaluate_calibration_gate(db_session, dataset.id)
    assert gate.canCalibrate is False
    assert gate.calibrationRecordsCount == 14
    assert gate.minimumRequiredCalibrationRecords == MINIMUM_CALIBRATION_RECORDS
    assert any("INSUFFICIENT_CALIBRATION_SAMPLE" in issue for issue in gate.blockingIssues)


def test_calibration_gate_detects_training_calibration_leakage(db_session):
    """Verify calibration gate blocks datasets that overlap with the training set."""
    dataset = DatasetMetadataModel(
        name="Shared Dataset",
        source_type="licensed_vendor",
        file_format="csv",
        original_filename="shared.csv",
        file_hash_sha256="shared_hash",
        total_rows=200,
        valid_rows=200,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.commit()

    model = MLModelRegistryModel(
        version="v1.0.test-leakage",
        dataset_id=dataset.id,  # Trained on this exact dataset!
        algorithm="CatBoostRegressor",
        status="ACTIVE",
        is_production_ready=True,
        feature_names=["carpet_area_sqft"],
    )
    db_session.add(model)
    db_session.commit()

    gate = evaluate_calibration_gate(db_session, dataset.id)
    assert gate.canCalibrate is False
    assert gate.isDatasetDisjointFromTraining is False
    assert any("DATASET_LEAKAGE" in issue for issue in gate.blockingIssues)


def test_uncertainty_service_refuses_to_manufacture_bounds_when_uncalibrated(db_session):
    """Verify predict_with_uncertainty withholds prediction intervals when calibration is unavailable."""
    # Ensure no active ML model
    db_session.query(MLModelRegistryModel).delete()
    db_session.commit()

    req = UncertaintyPredictionRequest(
        city="Bengaluru",
        locality="Whitefield",
        propertyType="High-Rise Apartment",
        carpetAreaSqFt=1200.0,
        nominalCoverage=0.95,
    )
    resp = uncertainty_service.predict_with_uncertainty(db_session, req)

    assert resp.status == "UNCERTAINTY_NOT_CALIBRATED"
    assert resp.isCalibrated is False
    assert resp.pointEstimate > 0
    # Crucial: Bounds MUST be None, never fabricated!
    assert resp.lowerBound is None
    assert resp.upperBound is None
    assert resp.intervalWidth is None
    assert resp.relativeIntervalWidthPct is None
    assert resp.empiricalCoverage is None
    assert resp.evidenceCoverageTier == "PROVISIONAL_RULE_BASED"
    # Conceptual taxonomy separation
    assert resp.ruleConsistencyScore > 0  # Heuristic score exists
    assert resp.dataCompletenessScore > 0  # Data completeness exists
    assert "UNCALIBRATED" in resp.governanceDisclaimer
    assert len(resp.blockingReasons) > 0


def test_conceptual_taxonomy_definitions():
    """Verify all 5 uncertainty concepts are defined and distinct."""
    assert "rule_consistency_score" in CONCEPTUAL_TAXONOMY
    assert "data_completeness_score" in CONCEPTUAL_TAXONOMY
    assert "evidence_coverage" in CONCEPTUAL_TAXONOMY
    assert "ml_prediction_uncertainty" in CONCEPTUAL_TAXONOMY
    assert "calibrated_prediction_interval" in CONCEPTUAL_TAXONOMY

    # Verify rule consistency is explicitly declared as NOT a probability
    assert "NOT a probability" in CONCEPTUAL_TAXONOMY["rule_consistency_score"]


def test_api_uncertainty_status_endpoint(client):
    """Verify GET /api/v1/ml/uncertainty/status returns transparent uncalibrated status."""
    resp = client.get("/api/v1/ml/uncertainty/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "isCalibrated" in data
    assert "calibrationStatus" in data
    assert data["calibrationStatus"] == "UNCERTAINTY_NOT_CALIBRATED"
    assert data["supportedCoverageLevels"] == [0.90, 0.95]
    assert "conceptualTaxonomy" in data
    assert len(data["blockingReasons"]) > 0


def test_api_uncertainty_predict_withholds_bounds(client):
    """Verify POST /api/v1/ml/uncertainty/predict withholds intervals and provides honest fallback."""
    payload = {
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1400.0,
        "floorNo": 8,
        "totalFloors": 16,
        "guidelineRatePerSqFt": 7500.0,
        "nominalCoverage": 0.90,
    }
    resp = client.post("/api/v1/ml/uncertainty/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UNCERTAINTY_NOT_CALIBRATED"
    assert data["isCalibrated"] is False
    assert data["pointEstimate"] > 0
    assert data["lowerBound"] is None
    assert data["upperBound"] is None
    assert data["intervalWidth"] is None
    assert "UNCALIBRATED" in data["governanceDisclaimer"]
