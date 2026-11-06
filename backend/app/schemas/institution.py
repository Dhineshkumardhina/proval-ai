"""Pydantic schemas for institutional multi-tenancy and credit policy (Phase 5B)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

InstitutionTypeLiteral = Literal["HFC", "NBFC", "BANK", "VALUATION_FIRM", "VALUATION_AGENCY", "FINTECH"]
InstitutionStatusLiteral = Literal[
    "INVITED",
    "ONBOARDING",
    "DOCUMENTATION_PENDING",
    "UNDER_REVIEW",
    "APPROVED_FOR_PILOT",
    "ACTIVE",
    "SUSPENDED",
    "REJECTED",
    "CLOSED",
    "INACTIVE",
]
AgreementStatusLiteral = Literal["PENDING", "DRAFT", "UNDER_REVIEW", "EXECUTED", "EXPIRED"]
PilotAuthorizationStatusLiteral = Literal["UNAUTHORIZED", "PENDING_REVIEW", "AUTHORIZED", "SUSPENDED", "REVOKED"]


class BranchConfig(BaseModel):
    """Institutional branch office configuration."""
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(..., min_length=2, max_length=32, validation_alias="code", serialization_alias="code")
    name: str = Field(..., min_length=2, max_length=128, validation_alias="name", serialization_alias="name")
    city: str = Field(..., validation_alias="city", serialization_alias="city")
    state: str = Field(default="Karnataka", validation_alias="state", serialization_alias="state")
    tier: str = Field(default="METRO", validation_alias="tier", serialization_alias="tier")  # METRO, TIER_1, TIER_2, TIER_3


class ApprovalTierConfig(BaseModel):
    """Institutional loan sanction approval tier threshold."""
    model_config = ConfigDict(populate_by_name=True)

    tier: int = Field(..., ge=1, le=5, validation_alias="tier", serialization_alias="tier")
    maxAmount: float = Field(..., gt=0, validation_alias="maxAmount", serialization_alias="maxAmount")
    roleRequired: str = Field(..., validation_alias="roleRequired", serialization_alias="roleRequired")
    label: str = Field(..., validation_alias="label", serialization_alias="label")


class InstitutionPolicyBase(BaseModel):
    """Base policy configuration fields."""
    model_config = ConfigDict(populate_by_name=True)

    maxLtvPct: float = Field(default=75.0, ge=10.0, le=95.0, validation_alias="maxLtvPct", serialization_alias="maxLtvPct")
    defaultDistressDiscountPct: float = Field(default=17.0, ge=0.0, le=50.0, validation_alias="defaultDistressDiscountPct", serialization_alias="defaultDistressDiscountPct")
    maxUnderwriterHaircutPct: float = Field(default=25.0, ge=0.0, le=50.0, validation_alias="maxUnderwriterHaircutPct", serialization_alias="maxUnderwriterHaircutPct")
    circleRateTolerancePct: float = Field(default=20.0, ge=0.0, le=100.0, validation_alias="circleRateTolerancePct", serialization_alias="circleRateTolerancePct")
    minCibilScore: int = Field(default=700, ge=300, le=900, validation_alias="minCibilScore", serialization_alias="minCibilScore")
    mandatoryTitleSearchYears: int = Field(default=30, ge=1, le=60, validation_alias="mandatoryTitleSearchYears", serialization_alias="mandatoryTitleSearchYears")
    requireReraForOngoing: bool = Field(default=True, validation_alias="requireReraForOngoing", serialization_alias="requireReraForOngoing")
    requireNilEncumbrance: bool = Field(default=True, validation_alias="requireNilEncumbrance", serialization_alias="requireNilEncumbrance")
    approvalHierarchy: List[ApprovalTierConfig] = Field(
        default_factory=lambda: [
            ApprovalTierConfig(tier=1, maxAmount=5000000.0, roleRequired="CREDIT_UNDERWRITER", label="Branch Credit Underwriter"),
            ApprovalTierConfig(tier=2, maxAmount=20000000.0, roleRequired="SENIOR_UNDERWRITER", label="Senior Underwriter / Cluster Head"),
            ApprovalTierConfig(tier=3, maxAmount=999999999.0, roleRequired="RISK_COMMITTEE_MEMBER", label="Credit Risk & Audit Committee"),
        ],
        validation_alias="approvalHierarchy",
        serialization_alias="approvalHierarchy",
    )
    auditRequirements: Dict[str, Any] = Field(
        default_factory=lambda: {
            "require_geo_tagged_photos": True,
            "require_two_comparables": True,
            "strict_chain_hash_validation": True,
        },
        validation_alias="auditRequirements",
        serialization_alias="auditRequirements",
    )


class InstitutionPolicyCreate(InstitutionPolicyBase):
    pass


class InstitutionPolicyUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    maxLtvPct: Optional[float] = Field(default=None, ge=10.0, le=95.0, validation_alias="maxLtvPct", serialization_alias="maxLtvPct")
    defaultDistressDiscountPct: Optional[float] = Field(default=None, ge=0.0, le=50.0, validation_alias="defaultDistressDiscountPct", serialization_alias="defaultDistressDiscountPct")
    maxUnderwriterHaircutPct: Optional[float] = Field(default=None, ge=0.0, le=50.0, validation_alias="maxUnderwriterHaircutPct", serialization_alias="maxUnderwriterHaircutPct")
    circleRateTolerancePct: Optional[float] = Field(default=None, ge=0.0, le=100.0, validation_alias="circleRateTolerancePct", serialization_alias="circleRateTolerancePct")
    minCibilScore: Optional[int] = Field(default=None, ge=300, le=900, validation_alias="minCibilScore", serialization_alias="minCibilScore")
    mandatoryTitleSearchYears: Optional[int] = Field(default=None, ge=1, le=60, validation_alias="mandatoryTitleSearchYears", serialization_alias="mandatoryTitleSearchYears")
    requireReraForOngoing: Optional[bool] = Field(default=None, validation_alias="requireReraForOngoing", serialization_alias="requireReraForOngoing")
    requireNilEncumbrance: Optional[bool] = Field(default=None, validation_alias="requireNilEncumbrance", serialization_alias="requireNilEncumbrance")
    approvalHierarchy: Optional[List[ApprovalTierConfig]] = Field(default=None, validation_alias="approvalHierarchy", serialization_alias="approvalHierarchy")
    auditRequirements: Optional[Dict[str, Any]] = Field(default=None, validation_alias="auditRequirements", serialization_alias="auditRequirements")


class InstitutionPolicyResponse(InstitutionPolicyBase):
    id: str
    institutionId: str = Field(..., validation_alias="institutionId", serialization_alias="institutionId")
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")
    updatedAt: datetime = Field(..., validation_alias="updatedAt", serialization_alias="updatedAt")


class InstitutionCreate(BaseModel):
    """Schema for onboarding a new institutional partner."""
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[A-Z0-9_\-]+$", validation_alias="code", serialization_alias="code")
    name: str = Field(..., min_length=3, max_length=255, validation_alias="name", serialization_alias="name")
    institutionType: InstitutionTypeLiteral = Field(default="HFC", validation_alias="institutionType", serialization_alias="institutionType")
    status: Optional[InstitutionStatusLiteral] = Field(default="ACTIVE", validation_alias="status", serialization_alias="status")
    primaryContactEmail: str = Field(..., min_length=5, max_length=255, validation_alias="primaryContactEmail", serialization_alias="primaryContactEmail")
    primaryContactName: Optional[str] = Field(default="", max_length=128, validation_alias="primaryContactName", serialization_alias="primaryContactName")
    primaryContactPhone: Optional[str] = Field(default="", max_length=32, validation_alias="primaryContactPhone", serialization_alias="primaryContactPhone")
    cinOrRegistrationNo: Optional[str] = Field(default="", max_length=128, validation_alias="cinOrRegistrationNo", serialization_alias="cinOrRegistrationNo")
    rbiNhbRegistrationNo: Optional[str] = Field(default="", max_length=128, validation_alias="rbiNhbRegistrationNo", serialization_alias="rbiNhbRegistrationNo")
    registeredOfficeAddress: Optional[str] = Field(default="", validation_alias="registeredOfficeAddress", serialization_alias="registeredOfficeAddress")
    branches: Optional[List[BranchConfig]] = Field(default_factory=list, validation_alias="branches", serialization_alias="branches")
    authorizedDomains: Optional[List[str]] = Field(default_factory=list, validation_alias="authorizedDomains", serialization_alias="authorizedDomains")
    retentionPeriodYears: Optional[int] = Field(default=8, ge=5, le=30, validation_alias="retentionPeriodYears", serialization_alias="retentionPeriodYears")
    policy: Optional[InstitutionPolicyCreate] = Field(default=None, validation_alias="policy", serialization_alias="policy")


class InstitutionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, min_length=3, max_length=255, validation_alias="name", serialization_alias="name")
    status: Optional[InstitutionStatusLiteral] = Field(default=None, validation_alias="status", serialization_alias="status")
    primaryContactEmail: Optional[str] = Field(default=None, validation_alias="primaryContactEmail", serialization_alias="primaryContactEmail")
    primaryContactName: Optional[str] = Field(default=None, validation_alias="primaryContactName", serialization_alias="primaryContactName")
    primaryContactPhone: Optional[str] = Field(default=None, validation_alias="primaryContactPhone", serialization_alias="primaryContactPhone")
    registeredOfficeAddress: Optional[str] = Field(default=None, validation_alias="registeredOfficeAddress", serialization_alias="registeredOfficeAddress")
    branches: Optional[List[BranchConfig]] = Field(default=None, validation_alias="branches", serialization_alias="branches")
    authorizedDomains: Optional[List[str]] = Field(default=None, validation_alias="authorizedDomains", serialization_alias="authorizedDomains")
    retentionPeriodYears: Optional[int] = Field(default=None, ge=5, le=30, validation_alias="retentionPeriodYears", serialization_alias="retentionPeriodYears")
    webhookUrl: Optional[str] = Field(default=None, validation_alias="webhookUrl", serialization_alias="webhookUrl")


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    code: str
    name: str
    institutionType: str = Field(..., validation_alias="institutionType", serialization_alias="institutionType")
    status: str
    cinOrRegistrationNo: str = Field(default="", validation_alias="cinOrRegistrationNo", serialization_alias="cinOrRegistrationNo")
    rbiNhbRegistrationNo: str = Field(default="", validation_alias="rbiNhbRegistrationNo", serialization_alias="rbiNhbRegistrationNo")
    primaryContactName: str = Field(default="", validation_alias="primaryContactName", serialization_alias="primaryContactName")
    primaryContactEmail: str = Field(..., validation_alias="primaryContactEmail", serialization_alias="primaryContactEmail")
    primaryContactPhone: str = Field(default="", validation_alias="primaryContactPhone", serialization_alias="primaryContactPhone")
    registeredOfficeAddress: str = Field(default="", validation_alias="registeredOfficeAddress", serialization_alias="registeredOfficeAddress")
    branches: List[BranchConfig] = Field(default_factory=list)
    authorizedDomains: List[str] = Field(default_factory=list, validation_alias="authorizedDomains", serialization_alias="authorizedDomains")
    retentionPeriodYears: int = Field(default=8, validation_alias="retentionPeriodYears", serialization_alias="retentionPeriodYears")
    apiKeyPrefix: Optional[str] = Field(default=None, validation_alias="apiKeyPrefix", serialization_alias="apiKeyPrefix")
    webhookUrl: Optional[str] = Field(default=None, validation_alias="webhookUrl", serialization_alias="webhookUrl")

    # Phase 7B: Pilot Authorization & Legal Agreements
    agreementStatus: str = Field(default="PENDING", validation_alias="agreementStatus", serialization_alias="agreementStatus")
    agreementReference: str = Field(default="", validation_alias="agreementReference", serialization_alias="agreementReference")
    agreementSignedDate: Optional[datetime] = Field(default=None, validation_alias="agreementSignedDate", serialization_alias="agreementSignedDate")
    agreementSignatoryName: str = Field(default="", validation_alias="agreementSignatoryName", serialization_alias="agreementSignatoryName")
    agreementSignatoryTitle: str = Field(default="", validation_alias="agreementSignatoryTitle", serialization_alias="agreementSignatoryTitle")
    agreementEvidenceUrl: str = Field(default="", validation_alias="agreementEvidenceUrl", serialization_alias="agreementEvidenceUrl")

    dpaStatus: str = Field(default="PENDING", validation_alias="dpaStatus", serialization_alias="dpaStatus")
    dpaReference: str = Field(default="", validation_alias="dpaReference", serialization_alias="dpaReference")
    dpaSignedDate: Optional[datetime] = Field(default=None, validation_alias="dpaSignedDate", serialization_alias="dpaSignedDate")
    dpaSignatoryName: str = Field(default="", validation_alias="dpaSignatoryName", serialization_alias="dpaSignatoryName")

    pilotAuthorizationStatus: str = Field(default="UNAUTHORIZED", validation_alias="pilotAuthorizationStatus", serialization_alias="pilotAuthorizationStatus")
    pilotCommencementDate: Optional[datetime] = Field(default=None, validation_alias="pilotCommencementDate", serialization_alias="pilotCommencementDate")
    pilotExpiryDate: Optional[datetime] = Field(default=None, validation_alias="pilotExpiryDate", serialization_alias="pilotExpiryDate")
    authorizedPilotParticipants: List[str] = Field(default_factory=list, validation_alias="authorizedPilotParticipants", serialization_alias="authorizedPilotParticipants")
    approvedDataCategories: List[str] = Field(default_factory=list, validation_alias="approvedDataCategories", serialization_alias="approvedDataCategories")
    permittedPurposes: List[str] = Field(default_factory=list, validation_alias="permittedPurposes", serialization_alias="permittedPurposes")
    approvedOperationalScope: Dict[str, Any] = Field(default_factory=dict, validation_alias="approvedOperationalScope", serialization_alias="approvedOperationalScope")
    approvalEvidenceReference: str = Field(default="", validation_alias="approvalEvidenceReference", serialization_alias="approvalEvidenceReference")
    isPilotApproved: bool = Field(default=False, validation_alias="isPilotApproved", serialization_alias="isPilotApproved")

    policy: Optional[InstitutionPolicyResponse] = None
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")
    updatedAt: datetime = Field(..., validation_alias="updatedAt", serialization_alias="updatedAt")


class InstitutionListResponse(BaseModel):
    items: List[InstitutionResponse]
    total: int


class InstitutionAPIKeyResponse(BaseModel):
    """Returned once upon key creation; raw key cannot be retrieved afterwards."""
    model_config = ConfigDict(populate_by_name=True)

    institutionId: str = Field(..., validation_alias="institutionId", serialization_alias="institutionId")
    institutionCode: str = Field(..., validation_alias="institutionCode", serialization_alias="institutionCode")
    apiKey: str = Field(..., validation_alias="apiKey", serialization_alias="apiKey")
    prefix: str
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")


class CasePolicyEvaluationRequest(BaseModel):
    """Case parameters for policy compliance verification."""
    model_config = ConfigDict(populate_by_name=True)

    loanRequested: float = Field(..., gt=0, validation_alias="loanRequested", serialization_alias="loanRequested")
    declaredAgreementValue: float = Field(..., gt=0, validation_alias="declaredAgreementValue", serialization_alias="declaredAgreementValue")
    cibilScore: int = Field(default=750, ge=300, le=900, validation_alias="cibilScore", serialization_alias="cibilScore")
    ltvRatioPct: float = Field(default=75.0, ge=0.0, le=100.0, validation_alias="ltvRatioPct", serialization_alias="ltvRatioPct")
    underwriterHaircutPct: float = Field(default=0.0, ge=0.0, le=100.0, validation_alias="underwriterHaircutPct", serialization_alias="underwriterHaircutPct")
    titleChainYears: int = Field(default=30, ge=0, validation_alias="titleChainYears", serialization_alias="titleChainYears")
    encumbranceStatus: str = Field(default="NIL_ENCUMBRANCE", validation_alias="encumbranceStatus", serialization_alias="encumbranceStatus")
    reraRegistration: Optional[str] = Field(default="", validation_alias="reraRegistration", serialization_alias="reraRegistration")


class PolicyComplianceResult(BaseModel):
    """Institutional credit underwriting compliance evaluation report."""
    model_config = ConfigDict(populate_by_name=True)

    isCompliant: bool = Field(..., validation_alias="isCompliant", serialization_alias="isCompliant")
    requiredApprovalTier: int = Field(..., validation_alias="requiredApprovalTier", serialization_alias="requiredApprovalTier")
    requiredRole: str = Field(..., validation_alias="requiredRole", serialization_alias="requiredRole")
    tierLabel: str = Field(..., validation_alias="tierLabel", serialization_alias="tierLabel")
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# Phase 7B: Structured Mechanism for Pilot Agreements & Pilot Authorization
class PilotAgreementDraftUpload(BaseModel):
    """Register draft pilot documentation (does NOT legally execute)."""
    model_config = ConfigDict(populate_by_name=True)

    agreementReference: str = Field(..., min_length=3, max_length=128, validation_alias="agreementReference", serialization_alias="agreementReference")
    evidenceUrl: str = Field(..., min_length=5, max_length=500, validation_alias="evidenceUrl", serialization_alias="evidenceUrl")
    dpaReference: Optional[str] = Field(default="", max_length=128, validation_alias="dpaReference", serialization_alias="dpaReference")
    notes: Optional[str] = Field(default="", max_length=1000, validation_alias="notes", serialization_alias="notes")


class PilotAgreementExecute(BaseModel):
    """Formal institutional pilot agreement execution with verified legal authority."""
    model_config = ConfigDict(populate_by_name=True)

    agreementReference: str = Field(..., min_length=3, max_length=128, validation_alias="agreementReference", serialization_alias="agreementReference")
    agreementSignatoryName: str = Field(..., min_length=2, max_length=128, validation_alias="agreementSignatoryName", serialization_alias="agreementSignatoryName")
    agreementSignatoryTitle: str = Field(..., min_length=2, max_length=128, validation_alias="agreementSignatoryTitle", serialization_alias="agreementSignatoryTitle")
    agreementSignedDate: datetime = Field(..., validation_alias="agreementSignedDate", serialization_alias="agreementSignedDate")
    agreementEvidenceUrl: str = Field(..., min_length=5, max_length=500, validation_alias="agreementEvidenceUrl", serialization_alias="agreementEvidenceUrl")

    dpaReference: str = Field(..., min_length=3, max_length=128, validation_alias="dpaReference", serialization_alias="dpaReference")
    dpaSignatoryName: str = Field(..., min_length=2, max_length=128, validation_alias="dpaSignatoryName", serialization_alias="dpaSignatoryName")
    dpaSignedDate: datetime = Field(..., validation_alias="dpaSignedDate", serialization_alias="dpaSignedDate")

    pilotCommencementDate: datetime = Field(..., validation_alias="pilotCommencementDate", serialization_alias="pilotCommencementDate")
    pilotExpiryDate: datetime = Field(..., validation_alias="pilotExpiryDate", serialization_alias="pilotExpiryDate")

    authorizedPilotParticipants: List[str] = Field(..., min_length=1, validation_alias="authorizedPilotParticipants", serialization_alias="authorizedPilotParticipants")
    approvedDataCategories: List[str] = Field(..., min_length=1, validation_alias="approvedDataCategories", serialization_alias="approvedDataCategories")
    permittedPurposes: List[str] = Field(..., min_length=1, validation_alias="permittedPurposes", serialization_alias="permittedPurposes")
    approvedOperationalScope: Dict[str, Any] = Field(default_factory=dict, validation_alias="approvedOperationalScope", serialization_alias="approvedOperationalScope")
    approvalEvidenceReference: str = Field(..., min_length=3, max_length=255, validation_alias="approvalEvidenceReference", serialization_alias="approvalEvidenceReference")


class PilotAgreementResponse(BaseModel):
    """Detailed institutional pilot agreement and authorization status."""
    model_config = ConfigDict(populate_by_name=True)

    institutionId: str = Field(..., validation_alias="institutionId", serialization_alias="institutionId")
    institutionCode: str = Field(..., validation_alias="institutionCode", serialization_alias="institutionCode")
    institutionName: str = Field(..., validation_alias="institutionName", serialization_alias="institutionName")
    status: str
    isPilotApproved: bool = Field(..., validation_alias="isPilotApproved", serialization_alias="isPilotApproved")

    agreementStatus: str = Field(..., validation_alias="agreementStatus", serialization_alias="agreementStatus")
    agreementReference: str = Field(..., validation_alias="agreementReference", serialization_alias="agreementReference")
    agreementSignedDate: Optional[datetime] = Field(default=None, validation_alias="agreementSignedDate", serialization_alias="agreementSignedDate")
    agreementSignatoryName: str = Field(..., validation_alias="agreementSignatoryName", serialization_alias="agreementSignatoryName")
    agreementSignatoryTitle: str = Field(..., validation_alias="agreementSignatoryTitle", serialization_alias="agreementSignatoryTitle")
    agreementEvidenceUrl: str = Field(..., validation_alias="agreementEvidenceUrl", serialization_alias="agreementEvidenceUrl")

    dpaStatus: str = Field(..., validation_alias="dpaStatus", serialization_alias="dpaStatus")
    dpaReference: str = Field(..., validation_alias="dpaReference", serialization_alias="dpaReference")
    dpaSignedDate: Optional[datetime] = Field(default=None, validation_alias="dpaSignedDate", serialization_alias="dpaSignedDate")
    dpaSignatoryName: str = Field(..., validation_alias="dpaSignatoryName", serialization_alias="dpaSignatoryName")

    pilotAuthorizationStatus: str = Field(..., validation_alias="pilotAuthorizationStatus", serialization_alias="pilotAuthorizationStatus")
    pilotCommencementDate: Optional[datetime] = Field(default=None, validation_alias="pilotCommencementDate", serialization_alias="pilotCommencementDate")
    pilotExpiryDate: Optional[datetime] = Field(default=None, validation_alias="pilotExpiryDate", serialization_alias="pilotExpiryDate")

    authorizedPilotParticipants: List[str] = Field(default_factory=list, validation_alias="authorizedPilotParticipants", serialization_alias="authorizedPilotParticipants")
    approvedDataCategories: List[str] = Field(default_factory=list, validation_alias="approvedDataCategories", serialization_alias="approvedDataCategories")
    permittedPurposes: List[str] = Field(default_factory=list, validation_alias="permittedPurposes", serialization_alias="permittedPurposes")
    approvedOperationalScope: Dict[str, Any] = Field(default_factory=dict, validation_alias="approvedOperationalScope", serialization_alias="approvedOperationalScope")
    approvalEvidenceReference: str = Field(..., validation_alias="approvalEvidenceReference", serialization_alias="approvalEvidenceReference")


class ValuationDivergenceStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    meanDivergencePct: float = Field(..., validation_alias="meanDivergencePct", serialization_alias="meanDivergencePct")
    exceeding15PctCount: int = Field(..., validation_alias="exceeding15PctCount", serialization_alias="exceeding15PctCount")
    maxDivergencePct: float = Field(..., validation_alias="maxDivergencePct", serialization_alias="maxDivergencePct")


class AuditChainStatusSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    isValid: bool = Field(..., validation_alias="isValid", serialization_alias="isValid")
    totalEvents: int = Field(..., validation_alias="totalEvents", serialization_alias="totalEvents")
    latestHash: Optional[str] = Field(default=None, validation_alias="latestHash", serialization_alias="latestHash")


class DataProvenanceStatusSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    certifiedDeeds: int = Field(..., validation_alias="certifiedDeeds", serialization_alias="certifiedDeeds")
    verifiedDeeds: int = Field(..., validation_alias="verifiedDeeds", serialization_alias="verifiedDeeds")
    mlGateStatus: str = Field(..., validation_alias="mlGateStatus", serialization_alias="mlGateStatus")
    activeValuationEngine: str = Field(..., validation_alias="activeValuationEngine", serialization_alias="activeValuationEngine")


class InstitutionalPilotDashboardResponse(BaseModel):
    """Metrics for the Institutional Pilot Dashboard matching Section 7 requirements."""
    model_config = ConfigDict(populate_by_name=True)

    totalRegisteredInstitutions: int = Field(..., validation_alias="totalRegisteredInstitutions", serialization_alias="totalRegisteredInstitutions")
    institutionsApprovedForPilot: int = Field(..., validation_alias="institutionsApprovedForPilot", serialization_alias="institutionsApprovedForPilot")
    pendingOnboardingApprovals: int = Field(..., validation_alias="pendingOnboardingApprovals", serialization_alias="pendingOnboardingApprovals")
    activePilotUsers: int = Field(..., validation_alias="activePilotUsers", serialization_alias="activePilotUsers")
    totalPilotValuationCases: int = Field(..., validation_alias="totalPilotValuationCases", serialization_alias="totalPilotValuationCases")
    pendingHumanReviews: int = Field(..., validation_alias="pendingHumanReviews", serialization_alias="pendingHumanReviews")
    highAlertCases: int = Field(..., validation_alias="highAlertCases", serialization_alias="highAlertCases")
    valuationDivergenceStats: ValuationDivergenceStats = Field(..., validation_alias="valuationDivergenceStats", serialization_alias="valuationDivergenceStats")
    auditChainVerificationStatus: AuditChainStatusSummary = Field(..., validation_alias="auditChainVerificationStatus", serialization_alias="auditChainVerificationStatus")
    dataProvenanceStatus: DataProvenanceStatusSummary = Field(..., validation_alias="dataProvenanceStatus", serialization_alias="dataProvenanceStatus")


