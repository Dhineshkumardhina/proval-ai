"""Pydantic schemas for valuation case management and lifecycle operations."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.valuation import ValuationResponse

CaseStatusType = Literal[
    "READY_FOR_APPROVAL",
    "REVIEW_REQUIRED",
    "HIGH_ALERT",
    "APPROVED",
    "REJECTED",
]

PropertyTypeLiteral = Literal[
    "High-Rise Apartment",
    "Gated Villa",
    "Independent Floor",
    "Commercial SCO",
]

MetroCityLiteral = Literal[
    "Bengaluru",
    "Mumbai",
    "Delhi-NCR",
    "Hyderabad",
    "Pune",
    "Chennai",
]


class ValuationCaseCreate(BaseModel):
    """Schema for creating a new valuation file."""

    borrowerName: str = Field(..., min_length=2, max_length=255, validation_alias="borrowerName", serialization_alias="borrowerName")
    coBorrowerName: Optional[str] = Field(default=None, max_length=255, validation_alias="coBorrowerName", serialization_alias="coBorrowerName")
    cibilScore: int = Field(default=750, ge=300, le=900, validation_alias="cibilScore", serialization_alias="cibilScore")
    loanRequested: float = Field(..., gt=0, validation_alias="loanRequested", serialization_alias="loanRequested")
    declaredAgreementValue: float = Field(..., gt=0, validation_alias="declaredAgreementValue", serialization_alias="declaredAgreementValue")

    propertyType: str = Field(default="High-Rise Apartment", validation_alias="propertyType", serialization_alias="propertyType")
    unitAddress: str = Field(..., validation_alias="unitAddress", serialization_alias="unitAddress")
    projectName: str = Field(..., validation_alias="projectName", serialization_alias="projectName")
    locality: str = Field(default="Central Corridor", validation_alias="locality", serialization_alias="locality")
    city: str = Field(default="Bengaluru", validation_alias="city", serialization_alias="city")
    pincode: str = Field(default="560001", validation_alias="pincode", serialization_alias="pincode")
    branch: str = Field(default="Main Lending Branch", validation_alias="branch", serialization_alias="branch")

    carpetAreaSqFt: float = Field(..., gt=0, validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: float = Field(..., ge=0, validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    floorNo: int = Field(default=1, ge=0, le=200, validation_alias="floorNo", serialization_alias="floorNo")
    totalFloors: int = Field(default=1, ge=1, le=200, validation_alias="totalFloors", serialization_alias="totalFloors")
    ageYears: int = Field(default=0, ge=0, le=150, validation_alias="ageYears", serialization_alias="ageYears")
    roadWidthFt: float = Field(default=30.0, ge=0, validation_alias="roadWidthFt", serialization_alias="roadWidthFt")

    circleRatePerSqFt: Optional[float] = Field(default=None, ge=0, validation_alias="circleRatePerSqFt", serialization_alias="circleRatePerSqFt")
    baseMarketRatePerSqFt: Optional[float] = Field(default=None, ge=0, validation_alias="baseMarketRatePerSqFt", serialization_alias="baseMarketRatePerSqFt")
    floorRiseFactor: Optional[float] = Field(default=None, validation_alias="floorRiseFactor", serialization_alias="floorRiseFactor")
    roadWidthFactor: Optional[float] = Field(default=250.0, validation_alias="roadWidthFactor", serialization_alias="roadWidthFactor")
    amenitiesPremium: Optional[float] = Field(default=400.0, validation_alias="amenitiesPremium", serialization_alias="amenitiesPremium")
    structuralDepreciation: Optional[float] = Field(default=80.0, validation_alias="structuralDepreciation", serialization_alias="structuralDepreciation")

    underwriterHaircutPct: float = Field(default=0.0, ge=-90.0, le=50.0, validation_alias="underwriterHaircutPct", serialization_alias="underwriterHaircutPct")
    distressDiscountPct: float = Field(default=18.0, ge=5.0, le=50.0, validation_alias="distressDiscountPct", serialization_alias="distressDiscountPct")
    ltvRatioPct: float = Field(default=75.0, ge=30.0, le=90.0, validation_alias="ltvRatioPct", serialization_alias="ltvRatioPct")
    legalRiskPenaltyPct: float = Field(default=0.0, ge=0.0, le=100.0, validation_alias="legalRiskPenaltyPct", serialization_alias="legalRiskPenaltyPct")
    assignedUnderwriter: str = Field(default="V. Sundaram (Sr. Underwriter)", validation_alias="assignedUnderwriter", serialization_alias="assignedUnderwriter")

    reraRegistration: Optional[str] = Field(default="", validation_alias="reraRegistration", serialization_alias="reraRegistration")
    bbmpPlanApprovalNo: Optional[str] = Field(default="", validation_alias="bbmpPlanApprovalNo", serialization_alias="bbmpPlanApprovalNo")
    titleChainYears: int = Field(default=30, validation_alias="titleChainYears", serialization_alias="titleChainYears")
    encumbranceStatus: str = Field(default="NIL_ENCUMBRANCE", validation_alias="encumbranceStatus", serialization_alias="encumbranceStatus")

    comparables: Optional[List[Dict[str, Any]]] = Field(default_factory=list, validation_alias="comparables", serialization_alias="comparables")
    documentFields: Optional[List[Dict[str, Any]]] = Field(default_factory=list, validation_alias="documentFields", serialization_alias="documentFields")
    surveyPhotos: Optional[List[Dict[str, Any]]] = Field(default_factory=list, validation_alias="surveyPhotos", serialization_alias="surveyPhotos")
    auditNotes: Optional[List[str]] = Field(default_factory=list, validation_alias="auditNotes", serialization_alias="auditNotes")
    dataSource: str = Field(default="synthetic-demo", validation_alias="dataSource", serialization_alias="dataSource")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ValuationCaseUpdate(BaseModel):
    """Schema for updating underwriter parameters or property fields on an existing case."""

    borrowerName: Optional[str] = Field(default=None, min_length=2, max_length=255, validation_alias="borrowerName", serialization_alias="borrowerName")
    coBorrowerName: Optional[str] = Field(default=None, max_length=255, validation_alias="coBorrowerName", serialization_alias="coBorrowerName")
    cibilScore: Optional[int] = Field(default=None, ge=300, le=900, validation_alias="cibilScore", serialization_alias="cibilScore")
    loanRequested: Optional[float] = Field(default=None, gt=0, validation_alias="loanRequested", serialization_alias="loanRequested")
    declaredAgreementValue: Optional[float] = Field(default=None, gt=0, validation_alias="declaredAgreementValue", serialization_alias="declaredAgreementValue")

    carpetAreaSqFt: Optional[float] = Field(default=None, gt=0, validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: Optional[float] = Field(default=None, ge=0, validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    circleRatePerSqFt: Optional[float] = Field(default=None, ge=0, validation_alias="circleRatePerSqFt", serialization_alias="circleRatePerSqFt")
    baseMarketRatePerSqFt: Optional[float] = Field(default=None, ge=0, validation_alias="baseMarketRatePerSqFt", serialization_alias="baseMarketRatePerSqFt")
    floorRiseFactor: Optional[float] = Field(default=None, validation_alias="floorRiseFactor", serialization_alias="floorRiseFactor")
    roadWidthFactor: Optional[float] = Field(default=None, validation_alias="roadWidthFactor", serialization_alias="roadWidthFactor")
    amenitiesPremium: Optional[float] = Field(default=None, validation_alias="amenitiesPremium", serialization_alias="amenitiesPremium")
    structuralDepreciation: Optional[float] = Field(default=None, validation_alias="structuralDepreciation", serialization_alias="structuralDepreciation")

    underwriterHaircutPct: Optional[float] = Field(default=None, ge=-90.0, le=50.0, validation_alias="underwriterHaircutPct", serialization_alias="underwriterHaircutPct")
    distressDiscountPct: Optional[float] = Field(default=None, ge=5.0, le=50.0, validation_alias="distressDiscountPct", serialization_alias="distressDiscountPct")
    ltvRatioPct: Optional[float] = Field(default=None, ge=30.0, le=90.0, validation_alias="ltvRatioPct", serialization_alias="ltvRatioPct")
    legalRiskPenaltyPct: Optional[float] = Field(default=None, ge=0.0, le=100.0, validation_alias="legalRiskPenaltyPct", serialization_alias="legalRiskPenaltyPct")

    status: Optional[str] = Field(default=None, validation_alias="status", serialization_alias="status")
    statusLabel: Optional[str] = Field(default=None, validation_alias="statusLabel", serialization_alias="statusLabel")
    assignedUnderwriter: Optional[str] = Field(default=None, validation_alias="assignedUnderwriter", serialization_alias="assignedUnderwriter")
    auditNotes: Optional[List[str]] = Field(default=None, validation_alias="auditNotes", serialization_alias="auditNotes")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CaseStatusUpdate(BaseModel):
    """Schema for changing workflow status and appending an audit note."""

    status: str = Field(..., description="Target status (APPROVED, REVIEW_REQUIRED, etc.)")
    auditNote: Optional[str] = Field(default=None, validation_alias="auditNote", serialization_alias="auditNote")

    model_config = ConfigDict(populate_by_name=True)


class ValuationCaseResponse(BaseModel):
    """Complete institutional valuation case representation matching React frontend contract."""

    id: str
    dataSource: str = Field(default="synthetic-demo", validation_alias="dataSource", serialization_alias="dataSource")
    applicationNo: str = Field(..., validation_alias="applicationNo", serialization_alias="applicationNo")
    borrowerName: str = Field(..., validation_alias="borrowerName", serialization_alias="borrowerName")
    coBorrowerName: Optional[str] = Field(default=None, validation_alias="coBorrowerName", serialization_alias="coBorrowerName")
    cibilScore: int = Field(default=750, validation_alias="cibilScore", serialization_alias="cibilScore")
    loanRequested: float = Field(..., validation_alias="loanRequested", serialization_alias="loanRequested")
    declaredAgreementValue: float = Field(..., validation_alias="declaredAgreementValue", serialization_alias="declaredAgreementValue")
    propertyType: str = Field(default="High-Rise Apartment", validation_alias="propertyType", serialization_alias="propertyType")
    unitAddress: str = Field(..., validation_alias="unitAddress", serialization_alias="unitAddress")
    projectName: str = Field(..., validation_alias="projectName", serialization_alias="projectName")
    locality: str = Field(..., validation_alias="locality", serialization_alias="locality")
    city: str = Field(..., validation_alias="city", serialization_alias="city")
    pincode: str = Field(..., validation_alias="pincode", serialization_alias="pincode")
    branch: str = Field(..., validation_alias="branch", serialization_alias="branch")

    carpetAreaSqFt: float = Field(..., validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: float = Field(..., validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    floorNo: int = Field(default=1, validation_alias="floorNo", serialization_alias="floorNo")
    totalFloors: int = Field(default=1, validation_alias="totalFloors", serialization_alias="totalFloors")
    ageYears: int = Field(default=0, validation_alias="ageYears", serialization_alias="ageYears")
    roadWidthFt: float = Field(default=30.0, validation_alias="roadWidthFt", serialization_alias="roadWidthFt")

    circleRatePerSqFt: float = Field(..., validation_alias="circleRatePerSqFt", serialization_alias="circleRatePerSqFt")
    baseMarketRatePerSqFt: float = Field(..., validation_alias="baseMarketRatePerSqFt", serialization_alias="baseMarketRatePerSqFt")
    floorRiseFactor: float = Field(default=0.0, validation_alias="floorRiseFactor", serialization_alias="floorRiseFactor")
    roadWidthFactor: float = Field(default=0.0, validation_alias="roadWidthFactor", serialization_alias="roadWidthFactor")
    amenitiesPremium: float = Field(default=0.0, validation_alias="amenitiesPremium", serialization_alias="amenitiesPremium")
    structuralDepreciation: float = Field(default=0.0, validation_alias="structuralDepreciation", serialization_alias="structuralDepreciation")

    status: str = Field(default="READY_FOR_APPROVAL", validation_alias="status", serialization_alias="status")
    statusLabel: str = Field(default="Ready for Approval", validation_alias="statusLabel", serialization_alias="statusLabel")
    underwriterHaircutPct: float = Field(default=0.0, validation_alias="underwriterHaircutPct", serialization_alias="underwriterHaircutPct")
    distressDiscountPct: float = Field(default=17.0, validation_alias="distressDiscountPct", serialization_alias="distressDiscountPct")
    ltvRatioPct: float = Field(default=75.0, validation_alias="ltvRatioPct", serialization_alias="ltvRatioPct")
    legalRiskPenaltyPct: float = Field(default=0.0, validation_alias="legalRiskPenaltyPct", serialization_alias="legalRiskPenaltyPct")
    assignedUnderwriter: str = Field(..., validation_alias="assignedUnderwriter", serialization_alias="assignedUnderwriter")

    createdAt: str = Field(..., validation_alias="createdAt", serialization_alias="createdAt")
    lastUpdated: str = Field(..., validation_alias="lastUpdated", serialization_alias="lastUpdated")
    reraRegistration: str = Field(default="", validation_alias="reraRegistration", serialization_alias="reraRegistration")
    bbmpPlanApprovalNo: str = Field(default="", validation_alias="bbmpPlanApprovalNo", serialization_alias="bbmpPlanApprovalNo")
    titleChainYears: int = Field(default=30, validation_alias="titleChainYears", serialization_alias="titleChainYears")
    encumbranceStatus: str = Field(default="NIL_ENCUMBRANCE", validation_alias="encumbranceStatus", serialization_alias="encumbranceStatus")

    comparables: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="comparables", serialization_alias="comparables")
    documentFields: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="documentFields", serialization_alias="documentFields")
    surveyPhotos: List[Dict[str, Any]] = Field(default_factory=list, validation_alias="surveyPhotos", serialization_alias="surveyPhotos")
    auditNotes: List[str] = Field(default_factory=list, validation_alias="auditNotes", serialization_alias="auditNotes")

    # Optional latest calculated valuation
    latestValuation: Optional[ValuationResponse] = Field(default=None, validation_alias="latestValuation", serialization_alias="latestValuation")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ValuationCaseListResponse(BaseModel):
    """Paginated collection of valuation cases."""

    items: List[ValuationCaseResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(populate_by_name=True)

