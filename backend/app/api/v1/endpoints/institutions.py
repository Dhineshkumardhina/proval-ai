"""API endpoints for Institutional Partner Tenancy, Onboarding, and Credit Policy (Phase 5B)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_roles,
    enforce_tenant_isolation,
    UserSession,
    ROLE_ADMIN,
    ROLE_INSTITUTION_ADMIN,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_COMPLIANCE_AUDITOR,
)
from app.schemas.institution import (
    CasePolicyEvaluationRequest,
    InstitutionAPIKeyResponse,
    InstitutionCreate,
    InstitutionListResponse,
    InstitutionPolicyResponse,
    InstitutionPolicyUpdate,
    InstitutionResponse,
    InstitutionUpdate,
    InstitutionalPilotDashboardResponse,
    PilotAgreementDraftUpload,
    PilotAgreementExecute,
    PilotAgreementResponse,
    PolicyComplianceResult,
)
from app.services import institution_service

router = APIRouter()


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard New Institution",
    description="Register a new institutional partner tenant (HFC, NBFC, Bank) with isolated configuration and policy.",
)
def onboard_institution(
    inst_in: InstitutionCreate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    """Onboard new institutional partner."""
    return institution_service.create_institution(
        db=db,
        inst_in=inst_in,
        actor_id=user.username,
        actor_role=user.role,
    )


@router.get(
    "",
    response_model=InstitutionListResponse,
    summary="List Institutions",
    description="Retrieve paginated list of institutional partners.",
)
def list_institutions(
    status: Optional[str] = Query(default=None, description="Filter by status (e.g. ACTIVE, ONBOARDING)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """List institutions. Tenant users only receive their own institution."""
    if user.institution_id and user.role != ROLE_ADMIN:
        inst = institution_service.get_institution(db=db, institution_id=user.institution_id)
        items = [inst] if inst else []
        return InstitutionListResponse(items=items, total=len(items))

    items, total = institution_service.list_institutions(
        db=db,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return InstitutionListResponse(items=items, total=total)


@router.get(
    "/pilot-dashboard",
    response_model=InstitutionalPilotDashboardResponse,
    summary="Institutional Pilot Dashboard",
    description="Retrieve live institutional pilot statistics, partner authorization status, and safety metrics.",
)
def get_pilot_dashboard(
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve institutional pilot dashboard metrics based on real database records."""
    return institution_service.get_pilot_dashboard(db=db)


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get Institution Details",
    description="Retrieve institution tenant profile, branch list, and configuration.",
)
def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve institution by ID."""
    enforce_tenant_isolation(user, institution_id)
    inst = institution_service.get_institution(db=db, institution_id=institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution '{institution_id}' not found.",
        )
    return inst


@router.patch(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update Institution",
    description="Update operational parameters, contact info, domains, or branch registry.",
)
def update_institution(
    institution_id: str,
    update_in: InstitutionUpdate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Update institution details."""
    enforce_tenant_isolation(user, institution_id)
    updated = institution_service.update_institution(
        db=db,
        institution_id=institution_id,
        update_in=update_in,
        actor_id=user.username,
        actor_role=user.role,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution '{institution_id}' not found.",
        )
    return updated


@router.get(
    "/{institution_id}/policy",
    response_model=InstitutionPolicyResponse,
    summary="Get Institution Credit Policy",
    description="Retrieve institution-specific credit underwriting rules, tolerances, and approval hierarchy.",
)
def get_institution_policy(
    institution_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Get institution credit policy."""
    enforce_tenant_isolation(user, institution_id)
    policy = institution_service.get_institution_policy(db=db, institution_id=institution_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy for institution '{institution_id}' not found.",
        )
    return policy


@router.put(
    "/{institution_id}/policy",
    response_model=InstitutionPolicyResponse,
    summary="Update Institution Credit Policy",
    description="Update institution-specific credit policy parameters, LTV caps, CIBIL thresholds, and approval tiers.",
)
def update_institution_policy(
    institution_id: str,
    policy_in: InstitutionPolicyUpdate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Update institution policy configuration."""
    enforce_tenant_isolation(user, institution_id)
    updated = institution_service.update_institution_policy(
        db=db,
        institution_id=institution_id,
        policy_in=policy_in,
        actor_id=user.username,
        actor_role=user.role,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy for institution '{institution_id}' not found.",
        )
    return updated


@router.post(
    "/{institution_id}/policy/evaluate",
    response_model=PolicyComplianceResult,
    summary="Evaluate Case Policy Compliance",
    description="Evaluate loan case parameters against institution-specific underwriting rules and determine approval hierarchy tier.",
)
def evaluate_case_policy(
    institution_id: str,
    eval_req: CasePolicyEvaluationRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Evaluate case parameters against institution policy."""
    enforce_tenant_isolation(user, institution_id)
    inst = db.query(institution_service.InstitutionModel).filter(institution_service.InstitutionModel.id == institution_id).first()
    if not inst or not inst.policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution or policy for '{institution_id}' not found.",
        )
    return institution_service.evaluate_case_policy_compliance(policy=inst.policy, req=eval_req)


@router.post(
    "/{institution_id}/api-keys",
    response_model=InstitutionAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate / Rotate Partner API Key",
    description="Generate a secure cryptographic API key for B2B Loan Origination System (LOS) integration. Key is returned once.",
)
def rotate_api_key(
    institution_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Generate or rotate partner API key."""
    enforce_tenant_isolation(user, institution_id)
    return institution_service.generate_institution_api_key(
        db=db,
        institution_id=institution_id,
        actor_id=user.username,
        actor_role=user.role,
    )


@router.post(
    "/{institution_id}/agreements/draft",
    response_model=PilotAgreementResponse,
    summary="Upload Pilot Agreement Draft",
    description="Register draft institutional agreement documentation without marking legally executed.",
)
def upload_agreement_draft(
    institution_id: str,
    draft_in: PilotAgreementDraftUpload,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Upload draft agreement documentation."""
    enforce_tenant_isolation(user, institution_id)
    return institution_service.upload_pilot_agreement_draft(
        db=db,
        institution_id=institution_id,
        draft_in=draft_in,
        actor_id=user.username,
        actor_role=user.role,
    )


@router.post(
    "/{institution_id}/agreements/execute",
    response_model=PilotAgreementResponse,
    summary="Execute Institutional Pilot Agreement",
    description="Record legally executed pilot agreement and DPA with verified authorization and approved operational scope.",
)
def execute_pilot_agreement(
    institution_id: str,
    exec_in: PilotAgreementExecute,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Formally execute institutional pilot agreement."""
    enforce_tenant_isolation(user, institution_id)
    return institution_service.execute_pilot_agreement(
        db=db,
        institution_id=institution_id,
        exec_in=exec_in,
        actor_id=user.username,
        actor_role=user.role,
    )


@router.get(
    "/{institution_id}/agreements",
    response_model=PilotAgreementResponse,
    summary="Get Pilot Agreement & Authorization Status",
    description="Retrieve full institutional pilot agreement details, DPA status, authorized participants, and operational scope.",
)
def get_pilot_agreement(
    institution_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve agreement details."""
    enforce_tenant_isolation(user, institution_id)
    return institution_service.get_pilot_agreement(db=db, institution_id=institution_id)


@router.post(
    "/{institution_id}/suspend",
    response_model=InstitutionResponse,
    summary="Suspend Institutional Partner",
    description="Suspend an institution and revoke all active pilot operations and case creation capabilities.",
)
def suspend_institution(
    institution_id: str,
    reason: str = Query(default="Administrative suspension", description="Reason for suspension"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_INSTITUTION_ADMIN])),
):
    """Suspend an institution."""
    enforce_tenant_isolation(user, institution_id)
    return institution_service.suspend_institution(
        db=db,
        institution_id=institution_id,
        reason=reason,
        actor_id=user.username,
        actor_role=user.role,
    )

