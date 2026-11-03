"""Reproducible model training pipeline with strict training gate enforcement and artifact persistence."""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dataset import ImportedTransactionModel, DatasetMetadataModel
from app.models.ml_model import MLModelRegistryModel
from app.ml.readiness_gate import evaluate_training_gate
from app.ml.preprocessing import (
    extract_features_from_records,
    split_oot_temporal,
    ALL_FEATURE_NAMES,
    TARGET_VARIABLE,
)
from app.ml.benchmarks import evaluate_benchmarks

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts", "models")


def train_valuation_model(
    db: Session,
    dataset_id: str,
    algorithm: str = "CatBoostRegressor",
    user_name: str = "Automated Pipeline",
) -> MLModelRegistryModel:
    """Execute training pipeline strictly gated by Phase 2D readiness evaluation.

    If readiness gate fails (e.g. sample size < 1,000 or synthetic provenance):
    - Aborts execution with HTTP 422
    - Refuses to train models or fabricate metrics
    - Persists audit trail of why training was blocked
    """
    # 1. Evaluate Strict Pre-Training Gate
    gate_audit = evaluate_training_gate(db, dataset_id)

    if not gate_audit.canTrain:
        # Create an audit record in ml_models table recording the blocked attempt
        blocked_model = MLModelRegistryModel(
            version=f"BLOCKED-{int(time.time())}",
            dataset_id=dataset_id,
            algorithm=algorithm,
            hyperparameters={"blocked": True},
            metrics=None,
            benchmark_comparisons=None,
            feature_names=ALL_FEATURE_NAMES,
            target_variable=TARGET_VARIABLE,
            status="BLOCKED",
            artifact_path=None,
            is_production_ready=False,
            training_records_count=0,
            test_records_count=0,
            readiness_gate_audit=gate_audit.model_dump(by_alias=True),
            trained_by=user_name,
            trained_at=datetime.now(timezone.utc),
        )
        db.add(blocked_model)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "TRAINING_BLOCKED_BY_READINESS_GATE",
                "message": "Dataset does not meet the mandatory criteria for training a production-quality ML valuation model.",
                "datasetId": dataset_id,
                "validRecords": gate_audit.validRecords,
                "requiredRecords": gate_audit.requiredRecordsThreshold,
                "blockingIssues": gate_audit.blockingIssues,
                "governanceRecommendation": gate_audit.governanceRecommendation,
            },
        )

    # 2. Load Valid Ingested Transactions
    records = (
        db.query(ImportedTransactionModel)
        .filter(ImportedTransactionModel.dataset_id == dataset_id)
        .all()
    )

    df = extract_features_from_records(records)

    # 3. Partition Data using Out-of-Time Temporal Split (Zero Leakage)
    train_df, val_df, test_df, date_meta = split_oot_temporal(df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

    # 4. Train Models & Benchmark Suite
    benchmarks, cb_model = evaluate_benchmarks(train_df, test_df)

    # 5. Model Versioning & Artifact Persistence
    version_str = f"v1.0.{int(time.time())}"
    model_dir = os.path.join(ARTIFACTS_DIR, version_str)
    os.makedirs(model_dir, exist_ok=True)

    artifact_path = os.path.join(model_dir, "catboost_valuation.cbm")
    cb_model.save_model(artifact_path)

    metadata_path = os.path.join(model_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": version_str,
            "algorithm": algorithm,
            "dataset_id": dataset_id,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "benchmarks": benchmarks,
            "features": ALL_FEATURE_NAMES,
            "target": TARGET_VARIABLE,
            "temporal_metadata": date_meta,
        }, f, indent=2)

    # 6. Deactivate older models if any
    db.query(MLModelRegistryModel).filter(MLModelRegistryModel.status == "ACTIVE").update({"status": "DEPRECATED"})

    # 7. Persist New Approved Model in Registry
    new_model = MLModelRegistryModel(
        version=version_str,
        dataset_id=dataset_id,
        algorithm=algorithm,
        hyperparameters={"iterations": 300, "learning_rate": 0.05, "depth": 6, "loss_function": "RMSE"},
        metrics=benchmarks["models"]["CatBoost"],
        benchmark_comparisons=benchmarks,
        feature_names=ALL_FEATURE_NAMES,
        target_variable=TARGET_VARIABLE,
        status="ACTIVE",
        artifact_path=artifact_path,
        is_production_ready=True,
        training_records_count=len(train_df),
        test_records_count=len(test_df),
        readiness_gate_audit=gate_audit.model_dump(by_alias=True),
        trained_by=user_name,
        trained_at=datetime.now(timezone.utc),
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)

    return new_model

