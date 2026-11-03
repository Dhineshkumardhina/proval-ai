"""SQLAlchemy model for conformal calibration artifacts and uncertainty quantification registry."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class CalibrationArtifactModel(Base):
    """Stores split conformal calibration quantiles and subgroup empirical coverage metrics."""

    __tablename__ = "conformal_calibrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version = Column(String(64), nullable=False, index=True)
    calibration_dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    calibration_records_count = Column(Integer, default=0)
    coverage_levels = Column(JSON, nullable=False)  # [0.90, 0.95]
    quantiles = Column(JSON, nullable=False)  # {"0.90": float, "0.95": float}
    mean_interval_width = Column(JSON, nullable=True)  # {"0.90": float, "0.95": float}
    subgroup_coverage = Column(JSON, nullable=True)  # geographic, property type, size tier breakdowns
    status = Column(String(32), default="ACTIVE")  # "ACTIVE", "BLOCKED", "DEPRECATED"
    calibration_gate_audit = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("DatasetMetadataModel")

