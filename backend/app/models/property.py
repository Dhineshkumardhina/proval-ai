"""Property record database models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class PropertyRecord(Base):
    """Property asset record and physical architectural parameters."""

    __tablename__ = "properties"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    application_no = Column(String(64), unique=True, index=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    unit_address = Column(String(500), nullable=False)
    locality = Column(String(128), index=True, nullable=False)
    city = Column(String(64), index=True, nullable=False)
    pincode = Column(String(16), index=True, nullable=False)
    property_type = Column(String(64), nullable=False, default="High-Rise Apartment")

    # Dimensions
    carpet_area_sqft = Column(Float, nullable=False)
    super_built_up_area_sqft = Column(Float, nullable=False)
    floor_no = Column(Integer, default=1)
    total_floors = Column(Integer, default=1)
    age_years = Column(Integer, default=0)
    road_width_ft = Column(Float, default=30.0)

    # Base pricing & physical scorecard adjustments
    circle_rate_per_sqft = Column(Float, nullable=False, default=0.0)
    base_market_rate_per_sqft = Column(Float, nullable=False, default=0.0)
    floor_rise_factor = Column(Float, default=0.0)
    road_width_factor = Column(Float, default=0.0)
    amenities_premium = Column(Float, default=0.0)
    structural_depreciation = Column(Float, default=0.0)

    # Provenance metadata
    data_source = Column(String(64), nullable=False, default="synthetic-demo")

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )

    # Relationships
    valuation_cases = relationship("ValuationCaseModel", back_populates="property", cascade="all, delete-orphan")
    institution = relationship("InstitutionModel", backref="properties")

