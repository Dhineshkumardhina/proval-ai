"""SQLAlchemy model for ML model registry and metadata tracking."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class MLModelRegistryModel(Base):
    """Model registry tracking trained ML valuation models, versions, and governance gates."""

    __tablename__ = "ml_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(String(64), unique=True, nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    algorithm = Column(String(64), nullable=False)  # "CatBoostRegressor", "RandomForestRegressor", etc.
    hyperparameters = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)  # {"mae": float, "rmse": float, "mape": float, "r2": float}
    benchmark_comparisons = Column(JSON, nullable=True)  # comparisons against Median, LinearRegression, RF
    feature_names = Column(JSON, nullable=False)
    target_variable = Column(String(64), default="transaction_price")
    status = Column(String(32), default="CANDIDATE")  # "ACTIVE", "CANDIDATE", "BLOCKED", "DEPRECATED"
    artifact_path = Column(String(256), nullable=True)
    is_production_ready = Column(Boolean, default=False)
    training_records_count = Column(Integer, default=0)
    test_records_count = Column(Integer, default=0)
    readiness_gate_audit = Column(JSON, nullable=True)
    trained_by = Column(String(128), default="Automated Training Pipeline")
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    dataset = relationship("DatasetMetadataModel")

