"""Database models for property data sources, connectors, ingestion jobs, and raw staging."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
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


class SourceAuthorizationStatus:
    """Rigorous institutional source authorization lifecycle classifications."""
    DOCUMENTED_AND_AUTHORIZED = "DOCUMENTED_AND_AUTHORIZED"
    AUTHORIZATION_PENDING = "AUTHORIZATION_PENDING"
    SANDBOX_ONLY = "SANDBOX_ONLY"
    TEST_ONLY = "TEST_ONLY"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    BLOCKED = "BLOCKED"

    ALL_STATUSES = {
        DOCUMENTED_AND_AUTHORIZED,
        AUTHORIZATION_PENDING,
        SANDBOX_ONLY,
        TEST_ONLY,
        EXPIRED,
        REVOKED,
        BLOCKED,
    }

    # Only DOCUMENTED_AND_AUTHORIZED sources are allowed into live production ingestion
    PRODUCTION_PERMITTED = {DOCUMENTED_AND_AUTHORIZED}


class DataSourceModel(Base):
    """Catalog of authorized external property data providers and G2B gateways."""

    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_code = Column(String(64), unique=True, nullable=False, index=True)
    source_name = Column(String(255), nullable=False)
    provider_name = Column(String(255), nullable=False)
    access_tier = Column(String(32), nullable=False, default="CLASS_C_INSTITUTIONAL")
    source_category = Column(String(64), nullable=True, default="LICENSED_PROVIDER")
    # Categories: LICENSED_PROVIDER, DATA_AGGREGATOR, HOUSING_FINANCE, DEVELOPER_DIRECT, GOVERNMENT_OPEN_DATA, STATE_REGISTRATION_DEPT, AUTHENTICATED_UPLOAD
    # Tiers: CLASS_A_API, CLASS_B_BULK, CLASS_C_INSTITUTIONAL, CLASS_D_MANUAL, CLASS_E_PUBLIC, CLASS_F_MOCK

    # Institutional Authorization & Status Tracking (Phase 4B-1)
    authorization_status = Column(
        String(32),
        default=SourceAuthorizationStatus.AUTHORIZATION_PENDING,
        nullable=False,
        index=True,
    )
    legal_authorization_basis = Column(Text, nullable=False)
    license_number = Column(String(128), nullable=True)
    agreement_reference = Column(String(128), nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # Usage Terms & DPDP Purpose Limitation
    permitted_purposes = Column(
        JSON,
        nullable=True,
        default=lambda: ["DATA_INGESTION", "VALUATION_ESTIMATION", "MARKET_INTELLIGENCE"],
    )
    # e.g., ["VALUATION_ESTIMATION", "MARKET_INTELLIGENCE", "MODEL_TRAINING"]
    retention_restrictions = Column(
        JSON,
        nullable=True,
        default=lambda: {"max_retention_days": 90, "raw_deed_redistribution_allowed": False},
    )
    # e.g., {"max_retention_days": 365, "raw_deed_redistribution_allowed": False}
    commercial_terms_summary = Column(Text, nullable=True)

    # Institutional Ownership & Governance
    data_owner = Column(String(128), default="Institutional Data Officer", nullable=False)
    compliance_reviewer = Column(String(128), nullable=True)
    status_updated_by = Column(String(128), nullable=True)
    status_change_reason = Column(Text, nullable=True)

    # API Configuration (Never plaintext secrets!)
    api_base_url = Column(String(512), nullable=True)
    auth_secret_env_var = Column(String(128), default="ZAPKEY_API_KEY", nullable=False)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Phase 6A Extended Configuration
    provider_identifier = Column(String(64), nullable=True)
    api_endpoint = Column(String(512), nullable=True)
    authentication_method = Column(String(64), default="API_KEY", nullable=True)
    secret_manager_key = Column(String(255), nullable=True)
    request_timeout_seconds = Column(Integer, default=30, nullable=True)
    retry_policy = Column(JSON, default=lambda: {"max_retries": 3, "backoff_factor": 1.5, "circuit_breaker_threshold": 5}, nullable=True)
    permitted_data_categories = Column(JSON, default=lambda: ["RESIDENTIAL_DEEDS"], nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    ingestion_jobs = relationship("IngestionJobModel", back_populates="source", cascade="all, delete-orphan")
    raw_staged_records = relationship("RawTransactionStagingModel", back_populates="source", cascade="all, delete-orphan")


class IngestionJobModel(Base):
    """Audit and execution state for automated or manual connector ingestion runs."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        Index("ix_ingestion_jobs_source_status", "source_id", "status"),
        Index("ix_ingestion_jobs_started_at", "started_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="PENDING", nullable=False)
    # States: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

    trigger_mode = Column(String(32), default="MANUAL_ADMIN", nullable=False)
    # Triggers: MANUAL_ADMIN, SCHEDULED_CRON, WEBHOOK

    cursor_state = Column(JSON, nullable=True)
    
    records_fetched = Column(Integer, default=0, nullable=False)
    records_staged = Column(Integer, default=0, nullable=False)
    records_normalized = Column(Integer, default=0, nullable=False)
    records_rejected = Column(Integer, default=0, nullable=False)
    records_duplicate = Column(Integer, default=0, nullable=False)

    error_summary = Column(Text, nullable=True)
    audit_event_id = Column(String(36), nullable=True)

    started_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    source = relationship("DataSourceModel", back_populates="ingestion_jobs")
    raw_records = relationship("RawTransactionStagingModel", back_populates="job", cascade="all, delete-orphan")


class RawTransactionStagingModel(Base):
    """Immutable staging buffer storing raw retrieved payloads before normalization."""

    __tablename__ = "raw_transaction_staging"
    __table_args__ = (
        Index("ix_raw_staging_job_row", "job_id", "row_index"),
        Index("ix_raw_staging_payload_hash", "payload_hash_sha256"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    
    payload_hash_sha256 = Column(String(64), nullable=False)
    raw_payload = Column(JSON, nullable=False)
    pii_scrub_status = Column(String(32), default="PENDING", nullable=False)
    # PII Status: PENDING, CLEANSED, FLAGGED_QUARANTINED

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    job = relationship("IngestionJobModel", back_populates="raw_records")
    source = relationship("DataSourceModel", back_populates="raw_staged_records")

