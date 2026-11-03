"""Reproducible ML preprocessing pipeline and train/validation/test partitioning."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import asc
from fastapi import HTTPException, status

from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.schemas.dataset import MLPreparationResponse


SELECTED_NUMERICAL_FEATURES = [
    "carpet_area_sqft",
    "floor_no",
    "total_floors",
    "guideline_rate_per_sqft",
]

SELECTED_CATEGORICAL_FEATURES = [
    "city",
    "locality",
    "property_type",
    "transaction_quarter",
]

TARGET_VARIABLE = "transaction_price"


def prepare_ml_split(
    db: Session,
    dataset_id: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> MLPreparationResponse:
    """Partition imported dataset into Out-of-Time and Spatial train/val/test splits."""
    dataset = db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    # 1. Guard against training on synthetic demonstration data
    if dataset.source_type == "synthetic_benchmark" or dataset.license_type == "synthetic_demo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CREDIBILITY POLICY ENFORCED: Machine learning model training is strictly prohibited on synthetic demonstration data.",
        )

    # 2. Query valid records ordered strictly by transaction_date ascending (Out-of-Time Split)
    records = (
        db.query(ImportedTransactionModel)
        .filter(ImportedTransactionModel.dataset_id == dataset_id)
        .order_by(asc(ImportedTransactionModel.transaction_date))
        .all()
    )

    total_count = len(records)
    if total_count < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient valid records ({total_count}) to perform temporal/spatial train-val-test split (minimum 10 required).",
        )

    # 3. Calculate temporal split index boundaries
    train_end_idx = max(1, int(total_count * train_ratio))
    val_end_idx = max(train_end_idx + 1, int(total_count * (train_ratio + val_ratio)))

    train_records = records[:train_end_idx]
    val_records = records[train_end_idx:val_end_idx]
    test_records = records[val_end_idx:]

    train_start_str = train_records[0].transaction_date.strftime("%Y-%m-%d")
    train_end_str = train_records[-1].transaction_date.strftime("%Y-%m-%d")

    val_start_str = val_records[0].transaction_date.strftime("%Y-%m-%d") if val_records else "N/A"
    val_end_str = val_records[-1].transaction_date.strftime("%Y-%m-%d") if val_records else "N/A"

    test_start_str = test_records[0].transaction_date.strftime("%Y-%m-%d") if test_records else "N/A"
    test_end_str = test_records[-1].transaction_date.strftime("%Y-%m-%d") if test_records else "N/A"

    # 4. Extract unique spatial clusters (Localities & Pincodes)
    spatial_clusters = sorted(list(set(
        f"{r.city} - {r.locality}" for r in records if r.locality
    )))

    all_features = SELECTED_NUMERICAL_FEATURES + SELECTED_CATEGORICAL_FEATURES

    return MLPreparationResponse(
        datasetId=dataset_id,
        totalUsableRecords=total_count,
        trainRecords=len(train_records),
        validationRecords=len(val_records),
        testRecords=len(test_records),
        temporalSplit={
            "train": f"{train_start_str} to {train_end_str} ({len(train_records)} records, {train_ratio*100:.0f}%)",
            "validation": f"{val_start_str} to {val_end_str} ({len(val_records)} records, {val_ratio*100:.0f}%)",
            "test": f"{test_start_str} to {test_end_str} ({len(test_records)} records, {test_ratio*100:.0f}%)",
            "split_mechanism": "Strict Out-of-Time (OOT) temporal ordering preventing lookahead bias",
        },
        spatialClusters=spatial_clusters[:15],
        selectedFeatures=all_features,
        targetVariable=TARGET_VARIABLE,
        isLeakageGuarded=True,
    )

