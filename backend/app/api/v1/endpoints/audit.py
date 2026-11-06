"""FastAPI endpoints for Tamper-Evident SHA-256 Audit Trail & Model Governance (Phase 2H)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_roles,
    UserSession,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_COMPLIANCE_AUDITOR,
    ROLE_ADMIN,
)
from app.schemas.audit import (
    AuditEventResponse,
    AuditEventListResponse,
    AuditVerificationReport,
    AuditSummaryResponse,
)
from app.services import audit_service

router = APIRouter()


@router.get(
    "/events",
    response_model=AuditEventListResponse,
    summary="List Audit Trail Events",
    description="Retrieve paginated cryptographic audit blocks with optional caseId and eventType filtering.",
)
def list_events(
    case_id: Optional[str] = Query(default=None, description="Filter by valuation case ID"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_COMPLIANCE_AUDITOR, ROLE_ADMIN])),
) -> AuditEventListResponse:
    """Retrieve audit events."""
    items, total = audit_service.list_audit_events(
        db=db,
        limit=limit,
        offset=offset,
        case_id=case_id,
        event_type=event_type,
    )
    return AuditEventListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/events/{event_id}",
    response_model=AuditEventResponse,
    summary="Get Audit Event Block Detail",
    description="Retrieve a single audit block including its previous hash, payload, and cryptographic current hash.",
)
def get_event_by_id(
    event_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_COMPLIANCE_AUDITOR, ROLE_ADMIN])),
) -> AuditEventResponse:
    """Retrieve a single audit block."""
    items, _ = audit_service.list_audit_events(db=db, limit=1, offset=0)
    # Search specifically for event_id
    from app.models.audit import AuditEventModel
    import json

    e = db.query(AuditEventModel).filter(AuditEventModel.event_id == event_id).first()
    if not e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit block '{event_id}' not found.",
        )

    try:
        payload_dict = json.loads(e.payload_json)
    except Exception:
        payload_dict = {"raw": e.payload_json}

    return AuditEventResponse(
        id=e.id,
        event_id=e.event_id,
        sequence_number=e.sequence_number,
        event_type=e.event_type,
        actor_id=e.actor_id,
        actor_role=e.actor_role,
        case_id=e.case_id,
        timestamp=e.timestamp,
        payload=payload_dict,
        prev_hash=e.prev_hash,
        current_hash=e.current_hash,
    )


@router.post(
    "/verify",
    response_model=AuditVerificationReport,
    summary="Verify Cryptographic Hash Chain Integrity",
    description="Recalculates SHA-256 hashes for all sequential blocks and verifies previous-hash continuity.",
)
def verify_audit_trail(
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_COMPLIANCE_AUDITOR, ROLE_ADMIN])),
) -> AuditVerificationReport:
    """Execute cryptographic verification of the complete hash chain."""
    return audit_service.verify_audit_chain(db)


@router.get(
    "/summary",
    response_model=AuditSummaryResponse,
    summary="Audit Trail Status Summary",
    description="Returns high-level statistics, latest block hash, and chain integrity status.",
)
def get_audit_summary(
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_COMPLIANCE_AUDITOR, ROLE_ADMIN])),
) -> AuditSummaryResponse:
    """Retrieve audit surveillance summary."""
    return audit_service.get_audit_summary(db)


@router.post(
    "/anchor/epoch",
    summary="Anchor Audit Sequence into Merkle Root Epoch",
    description="Calculates a cryptographic Merkle root hash over sequential audit blocks with simulated RFC 3161 proof.",
)
def create_anchor_epoch(
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    """Anchor audit blocks into an immutable epoch record."""
    epoch = audit_service.ExternalAuditAnchorService.anchor_epoch(db=db, actor_id=user.username)
    return {
        "id": epoch.id,
        "epoch_number": epoch.epoch_number,
        "merkle_root_hash": epoch.merkle_root_hash,
        "start_sequence": epoch.start_sequence,
        "end_sequence": epoch.end_sequence,
        "event_count": epoch.event_count,
        "anchor_manifest": epoch.anchor_manifest,
        "anchor_token": epoch.anchor_token,
        "anchored_at": epoch.anchored_at,
    }


@router.get(
    "/anchor/epochs",
    summary="List Anchored Merkle Root Epochs",
)
def list_anchor_epochs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_COMPLIANCE_AUDITOR, ROLE_ADMIN])),
):
    """Retrieve historical Merkle root anchoring epochs."""
    epochs = audit_service.ExternalAuditAnchorService.list_anchors(db=db, limit=limit, offset=offset)
    return [
        {
            "id": ep.id,
            "epoch_number": ep.epoch_number,
            "merkle_root_hash": ep.merkle_root_hash,
            "start_sequence": ep.start_sequence,
            "end_sequence": ep.end_sequence,
            "event_count": ep.event_count,
            "anchor_manifest": ep.anchor_manifest,
            "anchor_token": ep.anchor_token,
            "anchored_at": ep.anchored_at,
        }
        for ep in epochs
    ]


