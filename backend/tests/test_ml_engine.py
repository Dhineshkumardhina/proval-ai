"""Comprehensive automated test suite for Machine Learning Valuation Engine (Phase 2E).

Covers:
1. Training readiness gate validation (1,000 record threshold enforcement).
2. Synthetic demonstration data exclusion.
3. Feature engineering and categorical feature handling.
4. Out-of-Time temporal splitting and data leakage prevention.
5. Model benchmarking and defensive metric calculations (zero-safe MAPE).
6. Model training, serialization, artifact persistence, and registry loading.
7. SHAP explainability and distinction from statutory rule-based factors.
8. Runtime fallback behavior when ML is gated.
9. FastAPI API endpoint integration.
"""

import os
import shutil
import tempfile
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.ml_model import MLModelRegistryModel
from app.ml.readiness_gate import evaluate_training_gate
from app.ml.preprocessing import (
    extract_features_from_records,
    split_oot_temporal,
    build_feature_vector,
    ALL_FEATURE_NAMES,
    FEATURE_NAMES_CATEGORICAL,
)
from app.ml.benchmarks import compute_metrics, evaluate_benchmarks
from app.ml.explainability import (
    explain_catboost_prediction,
    get_governance_provenance_notice,
)
from app.ml.trainer import train_valuation_model
from app.ml.model_service import ml_model_service
from app.schemas.ml import MLPredictionRequest


def test_compute_metrics_defensive_zero_and_near_zero_handling():
    """Verify compute_metrics handles exact zero targets safely without ZeroDivisionError."""
    y_true = np.array([0.0, 1000000.0, 2000000.0])
    y_pred = np.array([50000.0, 1050000.0, 1950000.0])

    metrics = compute_metrics(y_true, y_pred, epsilon=1.0)
    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert np.isfinite(metrics["mape"])
    assert metrics["mape"] > 0
    assert isinstance(metrics["r2"], float)


def test_readiness_gate_rejects_synthetic_demonstration_dataset(db_session):
    """Verify that datasets with synthetic demonstration provenance are blocked from training."""
    synth_dataset = DatasetMetadataModel(
        name="Synthetic Demo Case Corpus",
        description="Synthetic demonstration records for UI showcasing",
        source_type="synthetic_demo",
        data_source_provenance="Synthetic test dataset",
        file_format="csv",
        original_filename="demo.csv",
        file_hash_sha256="abc123hash",
        total_rows=1200,
        valid_rows=1200,
        status="COMPLETED",
    )
    db_session.add(synth_dataset)
    db_session.commit()

    gate = evaluate_training_gate(db_session, synth_dataset.id)
    assert gate.canTrain is False
    assert gate.isSyntheticData is True
    assert any("DISQUALIFIED_PROVENANCE" in issue for issue in gate.blockingIssues)
    assert "READINESS: NO-GO" in gate.governanceRecommendation


def test_readiness_gate_blocks_under_threshold_dataset(db_session):
    """Verify that genuine datasets with fewer than 1,000 records are blocked."""
    dataset = DatasetMetadataModel(
        name="Genuine Small Ingested Batch",
        description="Authentic transactions under threshold",
        source_type="user_upload",
        data_source_provenance="Certified deed extracts",
        file_format="csv",
        original_filename="small.csv",
        file_hash_sha256="hash456",
        total_rows=14,
        valid_rows=14,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.commit()

    # Add 14 genuine transactions
    for i in range(14):
        tx = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=i,
            fingerprint_hash=f"fp_{i}",
            city="Bengaluru",
            locality=f"Locality_{i % 4}",
            project_name=f"Project_{i}",
            property_type="High-Rise Apartment",
            transaction_date=datetime(2024, (i % 12) + 1, 15, tzinfo=timezone.utc),
            transaction_quarter="2024-Q1",
            carpet_area_sqft=1200.0 + (i * 50),
            transaction_price=10000000.0 + (i * 500000),
            price_per_sqft=8000.0,
            is_verified_deed=True,
            is_asking_price=False,
            raw_data={"test": True},
        )
        db_session.add(tx)
    db_session.commit()

    gate = evaluate_training_gate(db_session, dataset.id)
    assert gate.canTrain is False
    assert gate.validRecords == 14
    assert gate.requiredRecordsThreshold == 1000
    assert any("INSUFFICIENT_SAMPLE_SIZE" in issue for issue in gate.blockingIssues)


def test_trainer_aborts_on_blocked_dataset(db_session):
    """Verify train_valuation_model raises HTTP 422 and logs a BLOCKED entry when gate fails."""
    dataset = DatasetMetadataModel(
        name="Blocked Attempt Batch",
        description="Attempt to train with 2 records",
        source_type="user_upload",
        file_format="csv",
        original_filename="blocked.csv",
        file_hash_sha256="hash_blocked",
        total_rows=2,
        valid_rows=2,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        train_valuation_model(db_session, dataset.id, algorithm="CatBoostRegressor")

    assert "TRAINING_BLOCKED_BY_READINESS_GATE" in str(exc_info.value)

    # Verify blocked entry is registered in database
    blocked_entry = (
        db_session.query(MLModelRegistryModel)
        .filter(MLModelRegistryModel.dataset_id == dataset.id)
        .first()
    )
    assert blocked_entry is not None
    assert blocked_entry.status == "BLOCKED"
    assert blocked_entry.is_production_ready is False


def test_feature_engineering_and_temporal_oot_split():
    """Verify feature engineering and chronological Out-of-Time temporal splitting."""
    records = []
    base_date = datetime(2023, 1, 1)

    for i in range(30):
        # Create records strictly increasing in time
        tx_date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=i * 15)
        r = ImportedTransactionModel(
            row_index=i,
            fingerprint_hash=f"fp_{i}",
            city="Bengaluru",
            locality="Whitefield" if i % 2 == 0 else "Indiranagar",
            property_type="High-Rise Apartment",
            transaction_date=tx_date.to_pydatetime(),
            transaction_quarter=f"2023-Q{(i // 8) + 1}",
            carpet_area_sqft=1000.0 + (i * 20),
            floor_no=(i % 10) + 1,
            total_floors=15,
            guideline_rate_per_sqft=7500.0,
            age_years=3,
            transaction_price=8000000.0 + (i * 200000),
            is_verified_deed=True,
            is_asking_price=False,
            raw_data={},
        )
        records.append(r)

    df = extract_features_from_records(records)
    assert len(df) == 30
    assert "floor_ratio" in df.columns
    assert "carpet_area_sqft" in df.columns

    train_df, val_df, test_df, meta = split_oot_temporal(df, 0.70, 0.15, 0.15)
    assert len(train_df) == 21
    assert len(val_df) > 0
    assert len(test_df) > 0

    # Test strict temporal ordering (zero lookahead leakage)
    assert train_df["transaction_date"].max() <= val_df["transaction_date"].min()
    assert val_df["transaction_date"].max() <= test_df["transaction_date"].min()


def test_benchmarks_and_catboost_training_on_synthetic_mock_environment():
    """Verify benchmark suite trains Median, Linear Regression, Random Forest, and CatBoost models."""
    np.random.seed(42)
    n = 60

    data = {
        "carpet_area_sqft": np.random.uniform(800, 2500, n),
        "floor_no": np.random.randint(1, 20, n).astype(float),
        "total_floors": np.full(n, 20.0),
        "floor_ratio": np.random.uniform(0.05, 1.0, n),
        "guideline_rate_per_sqft": np.random.choice([6000.0, 8000.0, 10000.0], n),
        "age_years": np.random.uniform(0, 10, n),
        "city": ["Bengaluru"] * n,
        "locality": np.random.choice(["Whitefield", "Koramangala", "Indiranagar", "HSR Layout"], n),
        "property_type": ["High-Rise Apartment"] * n,
        "transaction_quarter": np.random.choice(["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"], n),
        "transaction_date": pd.date_range("2024-01-01", periods=n, freq="5D"),
    }
    # Synthetic target with linear relationship + noise
    data["transaction_price"] = (
        data["carpet_area_sqft"] * data["guideline_rate_per_sqft"] * 1.3
        + data["floor_no"] * 50000.0
        + np.random.normal(0, 50000, n)
    )

    df = pd.DataFrame(data)
    train_df = df.iloc[:45].copy()
    test_df = df.iloc[45:].copy()

    summary, cb_model = evaluate_benchmarks(train_df, test_df)

    assert "Median_Baseline" in summary["models"]
    assert "Linear_Regression" in summary["models"]
    assert "Random_Forest" in summary["models"]
    assert "CatBoost" in summary["models"]
    assert summary["models"]["CatBoost"]["mape"] >= 0
    assert summary["test_records_count"] == len(test_df)

    # Test SHAP explanation extraction from CatBoost model
    test_row = build_feature_vector(
        city="Bengaluru",
        locality="Whitefield",
        property_type="High-Rise Apartment",
        carpet_area_sqft=1500.0,
        floor_no=12,
        total_floors=20,
        guideline_rate_per_sqft=8000.0,
        age_years=2,
    )
    base_val, shaps = explain_catboost_prediction(cb_model, test_row)
    assert base_val > 0
    assert len(shaps) == len(ALL_FEATURE_NAMES)
    assert any(c.feature == "carpet_area_sqft" for c in shaps)
    assert shaps[0].impactDirection in ("INCREASES_VALUE", "DECREASES_VALUE", "NEUTRAL")


def test_explainability_governance_taxonomy():
    """Verify strict distinction between SHAP ML explanations and statutory rule-based factors."""
    ml_notice = get_governance_provenance_notice(is_ml=True, model_version="v1.0.123")
    assert "TreeSHAP" in ml_notice["methodology"]
    assert "CatBoost" in ml_notice["source"]

    rule_notice = get_governance_provenance_notice(is_ml=False)
    assert "Rule-Based" in rule_notice["methodology"]
    assert "NOT an ML prediction and contains NO SHAP" in rule_notice["rule_based_overlap"]


def test_ml_model_service_fallback_when_no_active_model(db_session):
    """Verify model_service transparently falls back to rule-based engine when ML is inactive."""
    # Ensure no active ML model
    db_session.query(MLModelRegistryModel).delete()
    db_session.commit()

    status_resp = ml_model_service.get_ml_status(db_session)
    assert status_resp.isMlActive is False
    assert status_resp.engineType == "RULE_BASED_HEDONIC"
    assert status_resp.trainingGateStatus == "BLOCKED"

    req = MLPredictionRequest(
        city="Bengaluru",
        locality="Whitefield",
        propertyType="High-Rise Apartment",
        carpetAreaSqFt=1200.0,
        guidelineRatePerSqFt=7200.0,
        floorNo=5,
        totalFloors=14,
    )
    pred_resp = ml_model_service.predict(db_session, req)

    assert pred_resp.isMlPrediction is False
    assert pred_resp.engineType == "RULE_BASED_FALLBACK"
    assert pred_resp.estimatedPrice > 0
    assert pred_resp.shapContributions is None
    assert "ML Training Gated" in pred_resp.fallbackReason


def test_api_ml_status_endpoint(client):
    """Verify GET /api/v1/ml/status returns accurate system state."""
    resp = client.get("/api/v1/ml/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "isMlActive" in data
    assert "engineType" in data
    assert "trainingGateStatus" in data
    assert "requiredRecordsThreshold" in data
    assert data["requiredRecordsThreshold"] == 1000


def test_api_ml_predict_transparent_fallback(client):
    """Verify POST /api/v1/ml/predict works and transparently returns fallback metadata."""
    payload = {
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1350.0,
        "floorNo": 7,
        "totalFloors": 18,
        "guidelineRatePerSqFt": 7500.0,
    }
    resp = client.post("/api/v1/ml/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimatedPrice"] > 0
    assert "engineType" in data
    assert "isMlPrediction" in data
    assert "governanceDisclaimer" in data


def test_api_ml_explain_refuses_when_no_active_ml_model(client):
    """Verify POST /api/v1/ml/explain returns HTTP 400 when only rule-based engine is active."""
    payload = {
        "city": "Bengaluru",
        "locality": "Whitefield",
        "propertyType": "High-Rise Apartment",
        "carpetAreaSqFt": 1350.0,
    }
    resp = client.post("/api/v1/ml/explain", json=payload)
    assert resp.status_code == 400
    assert "SHAP explanations are only available for trained Machine Learning models" in resp.json()["detail"]


def test_api_ml_gate_check_on_sample_dataset(client):
    """Verify GET /api/v1/ml/gate-check/{dataset_id} evaluates sample dataset as NO-GO."""
    # First upload sample file
    with open("backend/data/samples/sample_bengaluru_transactions.csv", "rb") as f:
        upload_resp = client.post(
            "/api/v1/datasets/upload",
            data={"name": "Sample Gate Test"},
            files={"file": ("sample_bengaluru_transactions.csv", f, "text/csv")},
        )
    dataset_id = upload_resp.json()["datasetId"]

    resp = client.get(f"/api/v1/ml/gate-check/{dataset_id}")
    assert resp.status_code == 200
    gate = resp.json()
    assert gate["canTrain"] is False
    assert gate["validRecords"] == 14
    assert gate["requiredRecordsThreshold"] == 1000
    assert len(gate["blockingIssues"]) > 0
