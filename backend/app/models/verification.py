"""Database models for property transaction verification states, anomalies, and quarantine."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
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


class TransactionLifecycleState:
    """Rigorous state lifecycle for property transaction records."""
    RAW = "RAW"
    PARSED = "PARSED"
    NORMALIZED = "NORMALIZED"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATED = "VALIDATED"
    VERIFIED = "VERIFIED"
    CERTIFIED = "CERTIFIED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"

    ALL_STATES = [
        RAW,
        PARSED,
        NORMALIZED,
        VALIDATION_PENDING,
        VALIDATED,
        VERIFIED,
        CERTIFIED,
        REJECTED,
        QUARANTINED,
    ]


class QuarantinedRecordModel(Base):
    """Suspicious records held in quarantine pending underwriter review."""

    __tablename__ = "quarantined_records"
    __table_args__ = (
        Index("ix_quarantined_records_dataset_code", "dataset_id", "quarantine_code"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    quarantine_code = Column(String(64), nullable=False, index=True)
    quarantine_reason = Column(String(500), nullable=False)
    anomaly_score = Column(Float, default=0.0, nullable=False)
    
    # Forensic context
    anomalous_fields = Column(JSON, nullable=False)  # List of suspicious fields
    raw_payload = Column(JSON, nullable=False)
    
    # Resolution status
    resolution_status = Column(String(32), default="PENDING_REVIEW", nullable=False)
    # Status: PENDING_REVIEW, RESOLVED_VERIFIED, RESOLVED_REJECTED
    reviewed_by = Column(String(128), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class VerificationEvidenceModel(Base):
    """Cryptographic verification evidence and provenance audit trail for individual transactions."""

    __tablename__ = "verification_evidence"
    __table_args__ = (
        Index("ix_verification_evidence_status", "verification_status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), ForeignKey("imported_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    verification_status = Column(String(32), default=TransactionLifecycleState.VERIFIED, nullable=False)
    verifier_id = Column(String(128), nullable=False)  # e.g., 'SYSTEM_AUTO_VERIFIER' or underwriter username
    verifier_method = Column(String(64), nullable=False)  # SRO_INDEX_II_MATCH, B2B_DIGITAL_ATTESTATION, MANUAL_INSPECTION
    
    source_origin = Column(String(128), nullable=False)
    source_document_ref = Column(String(255), nullable=False)
    original_record_hash = Column(String(64), nullable=False)
    normalized_record_hash = Column(String(64), nullable=False)
    dataset_version = Column(String(32), nullable=True)

    verification_evidence_details = Column(JSON, nullable=False)
    verified_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

