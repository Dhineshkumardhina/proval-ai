"""Feature engineering, categorical encoding, and Out-of-Time temporal splitting."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.dataset import ImportedTransactionModel


FEATURE_NAMES_NUMERIC = [
    "carpet_area_sqft",
    "floor_no",
    "total_floors",
    "floor_ratio",
    "guideline_rate_per_sqft",
    "age_years",
]

FEATURE_NAMES_CATEGORICAL = [
    "city",
    "locality",
    "property_type",
    "transaction_quarter",
]

ALL_FEATURE_NAMES = FEATURE_NAMES_NUMERIC + FEATURE_NAMES_CATEGORICAL
TARGET_VARIABLE = "transaction_price"


def extract_features_from_records(records: List[ImportedTransactionModel]) -> pd.DataFrame:
    """Extract and engineer features from ORM records into a clean DataFrame."""
    rows = []
    for r in records:
        carpet = float(r.carpet_area_sqft) if r.carpet_area_sqft else 1000.0
        fl_no = float(r.floor_no) if r.floor_no is not None else 1.0
        tot_fl = float(r.total_floors) if r.total_floors is not None else max(fl_no, 4.0)
        fl_ratio = round(fl_no / max(1.0, tot_fl), 3)
        gl_rate = float(r.guideline_rate_per_sqft) if r.guideline_rate_per_sqft else 7000.0
        age = float(r.age_years) if r.age_years is not None else 2.0
        price = float(r.transaction_price) if r.transaction_price else 0.0

        rows.append({
            "carpet_area_sqft": carpet,
            "floor_no": fl_no,
            "total_floors": tot_fl,
            "floor_ratio": fl_ratio,
            "guideline_rate_per_sqft": gl_rate,
            "age_years": age,
            "city": str(r.city or "Bengaluru"),
            "locality": str(r.locality or "General"),
            "property_type": str(r.property_type or "High-Rise Apartment"),
            "transaction_quarter": str(r.transaction_quarter or "2024-Q1"),
            "transaction_date": r.transaction_date,
            "transaction_price": price,
        })

    df = pd.DataFrame(rows)
    return df


def split_oot_temporal(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    """Strict Out-of-Time (OOT) temporal partitioning to eliminate future lookahead leakage."""
    if len(df) == 0:
        empty = pd.DataFrame(columns=df.columns)
        return empty, empty, empty, {}

    df_sorted = df.sort_values(by="transaction_date", ascending=True).reset_index(drop=True)
    n = len(df_sorted)

    train_end = max(1, int(n * train_ratio))
    val_end = max(train_end + 1, int(n * (train_ratio + val_ratio)))
    if val_end >= n and n >= 3:
        val_end = n - 1

    train_df = df_sorted.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df_sorted.iloc[train_end:val_end].copy().reset_index(drop=True)
    test_df = df_sorted.iloc[val_end:].copy().reset_index(drop=True)

    date_metadata = {
        "train": f"{train_df['transaction_date'].min().strftime('%Y-%m-%d')} to {train_df['transaction_date'].max().strftime('%Y-%m-%d')} ({len(train_df)} records)",
        "validation": f"{val_df['transaction_date'].min().strftime('%Y-%m-%d')} to {val_df['transaction_date'].max().strftime('%Y-%m-%d')} ({len(val_df)} records)" if len(val_df) > 0 else "None",
        "test": f"{test_df['transaction_date'].min().strftime('%Y-%m-%d')} to {test_df['transaction_date'].max().strftime('%Y-%m-%d')} ({len(test_df)} records)" if len(test_df) > 0 else "None",
        "leakage_guard": "Strict Out-of-Time temporal ordering verified: Train <= Val <= Test",
    }

    return train_df, val_df, test_df, date_metadata


def build_feature_vector(
    city: str,
    locality: str,
    property_type: str,
    carpet_area_sqft: float,
    floor_no: Optional[int] = None,
    total_floors: Optional[int] = None,
    guideline_rate_per_sqft: Optional[float] = None,
    age_years: Optional[int] = None,
    transaction_quarter: Optional[str] = None,
) -> pd.DataFrame:
    """Build a single row DataFrame matching training features for real-time inference."""
    fl_no = float(floor_no) if floor_no is not None else 1.0
    tot_fl = float(total_floors) if total_floors is not None else max(fl_no, 4.0)
    fl_ratio = round(fl_no / max(1.0, tot_fl), 3)
    gl_rate = float(guideline_rate_per_sqft) if guideline_rate_per_sqft else 7000.0
    age = float(age_years) if age_years is not None else 2.0
    quarter = transaction_quarter or "2024-Q4"

    row = {
        "carpet_area_sqft": float(carpet_area_sqft),
        "floor_no": fl_no,
        "total_floors": tot_fl,
        "floor_ratio": fl_ratio,
        "guideline_rate_per_sqft": gl_rate,
        "age_years": age,
        "city": str(city),
        "locality": str(locality),
        "property_type": str(property_type),
        "transaction_quarter": str(quarter),
    }

    return pd.DataFrame([row])

