"""Pydantic schemas for valuation calculation and appraisal responses."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class AttributionFactor(BaseModel):
    """Individual factor attribution in the valuation scorecard."""

    factor: str
    impactPerSqFt: float = Field(..., serialization_alias="impactPerSqFt", validation_alias="impactPerSqFt")
    description: str
    category: Literal["positive", "negative", "neutral"]

    model_config = ConfigDict(populate_by_name=True)


class ValuationInputParams(BaseModel):
    """Input parameters for institutional property valuation."""

    carpetAreaSqFt: float = Field(
        ...,
        description="RERA carpet area in square feet",
        validation_alias="carpetAreaSqFt",
        serialization_alias="carpetAreaSqFt",
    )
    superBuiltUpAreaSqFt: float = Field(
        default=0.0,
        description="Super built-up area in square feet",
        validation_alias="superBuiltUpAreaSqFt",
        serialization_alias="superBuiltUpAreaSqFt",
    )
    baseMarketRatePerSqFt: float = Field(
        ...,
        description="Base market rate per square foot",
        validation_alias="baseMarketRatePerSqFt",
        serialization_alias="baseMarketRatePerSqFt",
    )
    circleRatePerSqFt: float = Field(
        default=0.0,
        description="Government SRO Circle Rate / Ready Reckoner guideline rate",
        validation_alias="circleRatePerSqFt",
        serialization_alias="circleRatePerSqFt",
    )
    floorRiseFactor: float = Field(
        default=0.0,
        description="Floor rise adjustment in ₹/sq ft",
        validation_alias="floorRiseFactor",
        serialization_alias="floorRiseFactor",
    )
    roadWidthFactor: float = Field(
        default=0.0,
        description="Road width adjustment in ₹/sq ft",
        validation_alias="roadWidthFactor",
        serialization_alias="roadWidthFactor",
    )
    amenitiesPremium: float = Field(
        default=0.0,
        description="Gated amenities premium in ₹/sq ft",
        validation_alias="amenitiesPremium",
        serialization_alias="amenitiesPremium",
    )
    structuralDepreciation: float = Field(
        default=0.0,
        description="Age / depreciation adjustment in ₹/sq ft",
        validation_alias="structuralDepreciation",
        serialization_alias="structuralDepreciation",
    )
    underwriterHaircutPct: float = Field(
        default=0.0,
        description="Underwriter risk hair-cut percentage (-90% to +50%)",
        validation_alias="underwriterHaircutPct",
        serialization_alias="underwriterHaircutPct",
    )
    distressDiscountPct: float = Field(
        default=17.0,
        description="Forced sale liquidation discount percentage (5% to 50%)",
        validation_alias="distressDiscountPct",
        serialization_alias="distressDiscountPct",
    )
    ltvRatioPct: float = Field(
        default=75.0,
        description="Loan-to-Value regulatory ratio cap (30% to 90%)",
        validation_alias="ltvRatioPct",
        serialization_alias="ltvRatioPct",
    )
    legalRiskPenaltyPct: float = Field(
        default=0.0,
        description="Title discrepancy / legal penalty percentage (0% to 100%)",
        validation_alias="legalRiskPenaltyPct",
        serialization_alias="legalRiskPenaltyPct",
    )

    # Optional metadata
    caseId: Optional[str] = Field(
        default=None,
        validation_alias="caseId",
        serialization_alias="caseId",
    )
    propertyId: Optional[str] = Field(
        default=None,
        validation_alias="propertyId",
        serialization_alias="propertyId",
    )
    applicationNo: Optional[str] = Field(
        default=None,
        validation_alias="applicationNo",
        serialization_alias="applicationNo",
    )
    dataSource: Optional[str] = Field(
        default="synthetic-demo",
        validation_alias="dataSource",
        serialization_alias="dataSource",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


class ValuationResponse(BaseModel):
    """Institutional valuation result response matching React frontend contract."""

    carpetAreaSqFt: float
    superBuiltUpAreaSqFt: float
    unadjustedRatePerSqFt: float
    ruleAdjustedRatePerSqFt: float
    aiAdjustedRatePerSqFt: float  # Backward-compatible alias for existing frontend components
    circleRatePerSqFt: float
    grossMarketValue: int
    netAssessedValue: int
    distressLiquidationValue: int
    maxSanctionAmount: int
    deviationFromCircleRatePct: float
    confidenceScorePct: float
    riskTier: Literal["LOW_RISK", "MODERATE_RISK", "HIGH_ALERT"]
    attributionBreakdown: List[AttributionFactor]

    # Engine and Credibility Metadata
    engineVersion: str = "0.2.0"
    engineType: str = "provisional rule-based estimation"
    dataSource: str = "synthetic-demo"
    isProvisional: bool = True
    calculatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )

