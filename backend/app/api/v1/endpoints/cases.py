"""Valuation Case lifecycle and Underwriting API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.institution import InstitutionModel
from app.core.security import (
    get_current_user,
    require_roles,
    enforce_tenant_isolation,
    UserSession,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_ADMIN,
    ROLE_INSTITUTION_ADMIN,
)
from app.schemas.case import (
    ValuationCaseCreate,
    ValuationCaseUpdate,
    CaseStatusUpdate,
    ValuationCaseResponse,
    ValuationCaseListResponse,
)
from app.services import case_service, audit_service

router = APIRouter()


@router.get(
    "",
    response_model=ValuationCaseListResponse,
    summary="List Valuation Cases",
    description="Retrieve paginated valuation cases with optional city, status, and search filters.",
)
def list_cases(
    city: Optional[str] = Query(default=None, description="Filter by Indian Metro City"),
    status: Optional[str] = Query(default=None, description="Filter by Workflow Status"),
    search: Optional[str] = Query(default=None, description="Search borrower, applicationNo, project"),
    institution_id: Optional[str] = Query(default=None, description="Filter by Institution Tenant"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve list of cases with tenant isolation."""
    effective_inst_id = user.institution_id or institution_id
    if effective_inst_id:
        inst = db.query(InstitutionModel).filter(InstitutionModel.id == effective_inst_id).first()
        if inst:
            if inst.status == "SUSPENDED":
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=f"Institution '{inst.code}' is SUSPENDED. Pilot case access is blocked.",
                )
            if inst.status not in ["APPROVED_FOR_PILOT", "ACTIVE"] and user.role != ROLE_ADMIN:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=f"Institution '{inst.code}' (status: {inst.status}) is not authorized for pilot operations. Status must be APPROVED_FOR_PILOT.",
                )

    items, total = case_service.list_cases(
        db=db,
        city=city,
        status=status,
        search=search,
        institution_id=effective_inst_id,
        limit=limit,
        offset=offset,
    )
    return ValuationCaseListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ValuationCaseResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create Valuation Case",
    description="Intake a new collateral file, calculate baseline valuation estimate, and save to database.",
)
def create_case(
    case_in: ValuationCaseCreate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_CREDIT_UNDERWRITER, ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Create a new valuation case."""
    if user.institution_id:
        case_in.institutionId = user.institution_id

    target_inst_id = case_in.institutionId
    if target_inst_id:
        inst = db.query(InstitutionModel).filter(InstitutionModel.id == target_inst_id).first()
        if inst:
            if inst.status == "SUSPENDED":
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=f"Institution '{inst.code}' is SUSPENDED. Cannot create pilot cases.",
                )
            if inst.status not in ["APPROVED_FOR_PILOT", "ACTIVE"] and user.role != ROLE_ADMIN:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=f"Institution '{inst.code}' (status: {inst.status}) is not authorized for pilot operations. Status must be APPROVED_FOR_PILOT.",
                )

    created = case_service.create_case(db=db, case_in=case_in)
    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_CASE_CREATED,
        actor_id=user.username,
        actor_role=user.role,
        case_id=created.id,
        payload={
            "case_id": created.id,
            "city": created.city,
            "projectName": created.projectName,
            "loanRequested": created.loanRequested,
            "carpetAreaSqFt": created.carpetAreaSqFt,
        },
    )
    return created


@router.get(
    "/{case_id}",
    response_model=ValuationCaseResponse,
    summary="Get Valuation Case",
    description="Retrieve full valuation case including property attributes, comparables, and latest calculation result.",
)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Get single valuation case by ID."""
    case = case_service.get_case_by_id(db=db, case_id=case_id)
    if not case:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )
    enforce_tenant_isolation(user, case.institutionId)
    return case


@router.put(
    "/{case_id}",
    response_model=ValuationCaseResponse,
    summary="Update Valuation Case",
    description="Update underwriter adjustments, recalculate valuation estimate, and save result.",
)
def update_case(
    case_id: str,
    case_in: ValuationCaseUpdate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_CREDIT_UNDERWRITER, ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    """Update case parameters and re-estimate."""
    existing = case_service.get_case_by_id(db=db, case_id=case_id)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )
    enforce_tenant_isolation(user, existing.institutionId)

    # Finalized case protection: Approved or Rejected cases cannot be modified by non-admin underwriters
    if existing.status in ["APPROVED", "REJECTED"] and user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation case '{case_id}' is finalized ({existing.status}) and locked against alterations. Administrative clearance is required to reopen.",
        )

    # Privilege escalation guard: Only Senior Underwriters, Risk Committee, and Admins can alter status
    if case_in.status is not None and user.role not in [ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_ADMIN]:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied: Credit Underwriters cannot modify case workflow status. Use authorized status transition endpoints.",
        )

    updated = case_service.update_case(db=db, case_id=case_id, case_in=case_in)
    if not updated:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )
    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_UNDERWRITER_PARAM_CHANGED,
        actor_id=user.username,
        actor_role=user.role,
        case_id=case_id,
        payload=case_in.model_dump(exclude_unset=True),
    )
    return updated


@router.patch(
    "/{case_id}/status",
    response_model=ValuationCaseResponse,
    summary="Transition Case Status",
    description="Transition case status (e.g. APPROVED, REVIEW_REQUIRED) and record audit ledger entry.",
)
def update_case_status(
    case_id: str,
    status_in: CaseStatusUpdate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_RISK_COMMITTEE_MEMBER, ROLE_ADMIN])),
):
    """Update workflow status."""
    existing = case_service.get_case_by_id(db=db, case_id=case_id)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )
    enforce_tenant_isolation(user, existing.institutionId)

    updated = case_service.update_case_status(
        db=db,
        case_id=case_id,
        new_status=status_in.status,
        audit_note=status_in.auditNote,
        human_sign_off_by=status_in.humanSignOffBy,
        human_sign_off_notes=status_in.humanSignOffNotes,
        actor_role=user.role,
    )
    if not updated:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )

    evt_type = (
        audit_service.EVENT_CASE_APPROVED
        if status_in.status == "APPROVED"
        else (
            audit_service.EVENT_CASE_REJECTED
            if status_in.status == "REJECTED"
            else audit_service.EVENT_CASE_STATUS_CHANGED
        )
    )
    audit_service.record_audit_event(
        db=db,
        event_type=evt_type,
        actor_id=user.username,
        actor_role=user.role,
        case_id=case_id,
        payload={
            "new_status": status_in.status,
            "audit_note": status_in.auditNote or "",
        },
    )
    return updated


@router.delete(
    "/{case_id}",
    summary="Delete Valuation Case",
    description="Remove a valuation case and cascade associated records. Restricted to institutional Administrators.",
)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    """Delete case with mandatory immutable audit event recording."""
    case = case_service.get_case_by_id(db=db, case_id=case_id)
    if not case:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )
    enforce_tenant_isolation(user, case.institutionId)

    # Record audit event BEFORE deletion so action is permanently traceable
    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_ADMIN_ACTION,
        actor_id=user.username,
        actor_role=user.role,
        case_id=case_id,
        payload={
            "action": "CASE_DELETED",
            "case_id": case_id,
            "borrower_name": case.borrowerName,
            "application_no": case.applicationNo,
            "deleted_by": user.username,
            "role": user.role,
        },
    )

    deleted = case_service.delete_case(db=db, case_id=case_id)
    if not deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' could not be deleted.",
        )
    return {"message": "Valuation case deleted successfully", "id": case_id}
