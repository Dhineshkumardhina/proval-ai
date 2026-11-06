"""Database model for immutable institutional dataset versions and snapshots."""

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


class DatasetVersionModel(Base):
    """Immutable snapshot version of an empirical property transaction dataset."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        Index("ix_dataset_versions_dataset_semver", "dataset_id", "semver_tag", unique=True),
        Index("ix_dataset_versions_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    semver_tag = Column(String(32), nullable=False)  # e.g., 'v1.0.0', 'v1.1.0'
    version_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Snapshot Metrics & Counts
    total_records = Column(Integer, default=0, nullable=False)
    verified_records = Column(Integer, default=0, nullable=False)
    rejected_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)
    quarantined_records = Column(Integer, default=0, nullable=False)

    # Cryptographic Checksum (Merkle root / hash of sorted transaction IDs & hashes)
    dataset_checksum_sha256 = Column(String(64), nullable=False)

    # Distributions & Diagnostics
    geographic_distribution = Column(JSON, nullable=False)
    property_type_distribution = Column(JSON, nullable=False)
    source_distribution = Column(JSON, nullable=False)
    validation_summary = Column(JSON, nullable=False)

    # Transaction Fingerprint Manifest (List of transaction IDs/hashes locked in this snapshot)
    included_transaction_ids = Column(JSON, nullable=False)

    # Governance & Approval
    created_by = Column(String(128), nullable=False)
    approval_status = Column(String(32), default="DRAFT", nullable=False)  # DRAFT, APPROVED, DEPRECATED
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    is_ml_eligible = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    dataset = relationship("DatasetMetadataModel")

