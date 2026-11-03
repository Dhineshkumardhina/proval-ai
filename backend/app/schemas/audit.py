"""Pydantic schemas for Tamper-Evident SHA-256 Audit Trail (Phase 2H)."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """Structured representation of an individual audit block in the hash chain."""

    id: int
    event_id: str
    sequence_number: int
    event_type: str
    actor_id: str
    actor_role: str
    case_id: Optional[str] = None
    timestamp: datetime
    payload: Dict[str, Any]
    prev_hash: str
    current_hash: str


class AuditEventListResponse(BaseModel):
    """Paginated list of audit events."""

    items: List[AuditEventResponse]
    total: int
    limit: int
    offset: int


class AuditVerificationReport(BaseModel):
    """Cryptographic audit verification report examining the entire SHA-256 hash chain."""

    is_valid: bool = Field(..., description="True if every hash and previous-hash relationship is intact")
    total_events: int = Field(..., description="Total audit events inspected")
    verified_events: int = Field(..., description="Number of events successfully recomputed and validated")
    genesis_hash: str = Field(..., description="Previous hash anchor for event #1")
    latest_hash: str = Field(..., description="Current hash of the most recent block")
    broken_index: Optional[int] = Field(None, description="Sequence number where verification failed, if any")
    broken_event_id: Optional[str] = Field(None, description="Event ID where failure was detected, if any")
    error_type: Optional[str] = Field(
        None,
        description="Failure taxonomy: HASH_MISMATCH, PREV_HASH_MISMATCH, SEQUENCE_GAP, or None",
    )
    details: str = Field(..., description="Detailed verification explanation")
    security_boundary_notice: str = Field(..., description="Advisory documentation on DBA rewrite boundaries")
    verified_at: str = Field(..., description="Verification execution timestamp (UTC)")

    @property
    def tampered(self) -> bool:
        return not self.is_valid

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class AuditSummaryResponse(BaseModel):
    """High-level status of the audit chain for surveillance dashboards."""

    total_events: int
    latest_sequence_number: int
    latest_event_id: Optional[str] = None
    latest_event_type: Optional[str] = None
    latest_timestamp: Optional[str] = None
    latest_hash: str
    is_chain_intact: bool
    event_counts_by_type: Dict[str, int]

