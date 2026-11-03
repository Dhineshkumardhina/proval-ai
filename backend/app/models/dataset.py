"""Database models for datasets, transaction ingestion, and data quality tracking."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class DatasetMetadataModel(Base):
    """Metadata catalog for imported property transaction datasets."""

    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Provenance & Licensing
    source_type = Column(
        String(64),
        nullable=False,
        default="user_upload",
        # Options: user_upload, government_open_data, academic_research, commercial_license, synthetic_benchmark
    )
    license_type = Column(
        String(64),
        nullable=False,
        default="commercial_restricted",
        # Options: commercial_restricted, cc_by_4_0, open_government_license, synthetic_demo
    )
    data_source_provenance = Column(String(255), nullable=False, default="Uploaded by authorized institutional underwriter")

    file_format = Column(String(16), nullable=False)  # csv, xlsx, xls
    original_filename = Column(String(255), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)

    # Summary Counts
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)

    # Processing State
    status = Column(String(32), default="COMPLETED")  # PENDING, INGESTING, COMPLETED, FAILED
    is_usable_for_ml = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    transactions = relationship("ImportedTransactionModel", back_populates="dataset", cascade="all, delete-orphan")
    rejected_records = relationship("RejectedRecordModel", back_populates="dataset", cascade="all, delete-orphan")
    duplicates = relationship("DuplicateRecordModel", back_populates="dataset", cascade="all, delete-orphan")
    quality_reports = relationship("DataQualityReportModel", back_populates="dataset", cascade="all, delete-orphan")


class ImportedTransactionModel(Base):
    """Cleaned, validated, and normalized property transaction deed record."""

    __tablename__ = "imported_transactions"
    __table_args__ = (
        Index("ix_imported_tx_verified_asking", "is_verified_deed", "is_asking_price"),
        Index("ix_imported_tx_city_locality", "city", "locality"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    fingerprint_hash = Column(String(64), nullable=False, index=True)

    # Geographic & Project Identification
    city = Column(String(64), nullable=False, index=True)
    locality = Column(String(128), nullable=False, index=True)
    sub_market = Column(String(128), nullable=True)
    pincode = Column(String(16), nullable=True, index=True)
    project_name = Column(String(255), nullable=False, index=True)
    unit_number = Column(String(64), nullable=True)

    # Physical Attributes (Normalized to standard units)
    property_type = Column(String(64), nullable=False, default="High-Rise Apartment")
    transaction_type = Column(String(32), default="REGISTRATION")  # REGISTRATION, RESALE, NEW_SALE
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    transaction_quarter = Column(String(16), nullable=False, index=True)  # e.g. 2024-Q3

    carpet_area_sqft = Column(Float, nullable=False)
    super_built_up_area_sqft = Column(Float, nullable=True)
    floor_no = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    age_years = Column(Integer, nullable=True)

    # Financial Metrics (Normalized to INR)
    transaction_price = Column(Float, nullable=False)
    price_per_sqft = Column(Float, nullable=False, index=True)
    guideline_rate_per_sqft = Column(Float, nullable=True)
    deviation_from_guideline_pct = Column(Float, nullable=True)

    # Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Data Quality Flags
    is_verified_deed = Column(Boolean, default=True)
    is_asking_price = Column(Boolean, default=False)
    data_source = Column(String(64), nullable=False, default="imported-deed")

    # Original Raw Upload Data
    raw_data = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    dataset = relationship("DatasetMetadataModel", back_populates="transactions")


class RejectedRecordModel(Base):
    """Raw uploaded rows rejected during ingestion with audit failure reasons."""

    __tablename__ = "rejected_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    rejection_reason = Column(String(500), nullable=False)
    rejection_code = Column(String(64), nullable=False, index=True)
    # Rejection Codes: MISSING_PRICE, INVALID_AREA, IMPOSSIBLE_DATE, OUT_OF_BOUNDS_COORDINATES,
    # EXTREME_PRICE_OUTLIER, INCONSISTENT_LOCATION, INVALID_CURRENCY_FORMAT, CORRUPT_ROW

    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    dataset = relationship("DatasetMetadataModel", back_populates="rejected_records")


class DuplicateRecordModel(Base):
    """Rows flagged as duplicate property transaction deeds."""

    __tablename__ = "duplicate_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    fingerprint_hash = Column(String(64), nullable=False, index=True)
    matched_transaction_id = Column(String(36), nullable=True)

    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    dataset = relationship("DatasetMetadataModel", back_populates="duplicates")


class DataQualityReportModel(Base):
    """Computed statistical data quality metrics and ML readiness audit report."""

    __tablename__ = "data_quality_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)

    total_records = Column(Integer, nullable=False)
    valid_records = Column(Integer, nullable=False)
    rejected_records = Column(Integer, nullable=False)
    duplicate_records = Column(Integer, nullable=False)

    # Detailed distributions stored as structured JSON
    missing_value_percentages = Column(JSON, nullable=False)
    geographic_distribution = Column(JSON, nullable=False)
    property_type_distribution = Column(JSON, nullable=False)
    price_metrics = Column(JSON, nullable=False)
    temporal_distribution = Column(JSON, nullable=False)

    # ML Readiness Verdict
    meets_ml_criteria = Column(Boolean, default=False)
    readiness_summary = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    dataset = relationship("DatasetMetadataModel", back_populates="quality_reports")

