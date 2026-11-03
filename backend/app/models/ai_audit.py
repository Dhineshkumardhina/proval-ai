"""SQLAlchemy model for AI Underwriter audit logs (Phase 2G).

Tracks every AI-assisted underwriter consultation for DPDP Act 2023 compliance,
governance, and institutional credit auditability.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base


class AIAuditLogModel(Base):
    """Immutable audit trail for all AI Underwriting assistance requests."""

    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=True, index=True)
    model_name = Column(String(64), nullable=False)
    provider = Column(String(32), nullable=False)  # "gemini" or "deterministic_fallback"
    pii_redacted_count = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    response_tokens = Column(Integer, default=0)
    status = Column(String(32), nullable=False)  # "success", "fallback", "error"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

