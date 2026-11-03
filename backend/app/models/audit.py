"""SQLAlchemy model for Tamper-Evident SHA-256 Audit Trail (Phase 2H).

Implements a secure cryptographic hash chain for institutional model governance,
underwriting accountability, and regulatory audit compliance.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base


class AuditEventModel(Base):
    """Immutable audit record within a cryptographic SHA-256 hash chain."""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    sequence_number = Column(Integer, unique=True, index=True, nullable=False)
    event_type = Column(String(64), index=True, nullable=False)
    actor_id = Column(String(64), index=True, nullable=False)
    actor_role = Column(String(64), nullable=False, default="SYSTEM")
    case_id = Column(String(64), index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)

