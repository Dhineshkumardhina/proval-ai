"""Pydantic schemas for statistical uncertainty quantification, split conformal prediction, and calibration gates."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubgroupCoverageMetric(BaseModel):
    """Empirical coverage and interval width audit across geographic, size, and property-type strata."""

    subgroupCategory: str = Field(..., validation_alias="subgroupCategory", serialization_alias="subgroupCategory")
    subgroupValue: str = Field(..., validation_alias="subgroupValue", serialization_alias="subgroupValue")
    sampleSize: int = Field(..., validation_alias="sampleSize", serialization_alias="sampleSize")
    nominalCoverage: float = Field(..., validation_alias="nominalCoverage", serialization_alias="nominalCoverage")
    empiricalCoverage: float = Field(..., validation_alias="empiricalCoverage", serialization_alias="empiricalCoverage")
    meanIntervalWidth: float = Field(..., validation_alias="meanIntervalWidth", serialization_alias="meanIntervalWidth")
    isUnderCovered: bool = Field(..., validation_alias="isUnderCovered", serialization_alias="isUnderCovered")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CalibrationGateAuditResponse(BaseModel):
    """Audit response for conformal calibration prerequisites."""

    canCalibrate: bool = Field(..., validation_alias="canCalibrate", serialization_alias="canCalibrate")
    status: str
    activeModelAvailable: bool = Field(..., validation_alias="activeModelAvailable", serialization_alias="activeModelAvailable")
    activeModelVersion: Optional[str] = Field(default=None, validation_alias="activeModelVersion", serialization_alias="activeModelVersion")
    calibrationRecordsCount: int = Field(..., validation_alias="calibrationRecordsCount", serialization_alias="calibrationRecordsCount")
    minimumRequiredCalibrationRecords: int = Field(default=100, validation_alias="minimumRequiredCalibrationRecords", serialization_alias="minimumRequiredCalibrationRecords")
    isSyntheticData: bool = Field(..., validation_alias="isSyntheticData", serialization_alias="isSyntheticData")
    isDatasetDisjointFromTraining: bool = Field(..., validation_alias="isDatasetDisjointFromTraining", serialization_alias="isDatasetDisjointFromTraining")
    blockingIssues: List[str] = Field(default_factory=list, validation_alias="blockingIssues", serialization_alias="blockingIssues")
    governanceNotice: str = Field(..., validation_alias="governanceNotice", serialization_alias="governanceNotice")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class UncertaintyStatusResponse(BaseModel):
    """Runtime uncertainty status and calibration availability."""

    isCalibrated: bool = Field(..., validation_alias="isCalibrated", serialization_alias="isCalibrated")
    calibrationStatus: str = Field(..., validation_alias="calibrationStatus", serialization_alias="calibrationStatus")
    activeModelVersion: Optional[str] = Field(default=None, validation_alias="activeModelVersion", serialization_alias="activeModelVersion")
    supportedCoverageLevels: List[float] = Field(default=[0.90, 0.95], validation_alias="supportedCoverageLevels", serialization_alias="supportedCoverageLevels")
    calibrationRecordsCount: int = Field(..., validation_alias="calibrationRecordsCount", serialization_alias="calibrationRecordsCount")
    blockingReasons: List[str] = Field(default_factory=list, validation_alias="blockingReasons", serialization_alias="blockingReasons")
    governanceNotice: str = Field(..., validation_alias="governanceNotice", serialization_alias="governanceNotice")
    conceptualTaxonomy: Dict[str, str] = Field(..., validation_alias="conceptualTaxonomy", serialization_alias="conceptualTaxonomy")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class UncertaintyPredictionRequest(BaseModel):
    """Valuation request with requested nominal conformal coverage level."""

    city: str
    locality: str
    propertyType: str = Field(..., validation_alias="propertyType", serialization_alias="propertyType")
    carpetAreaSqFt: float = Field(..., ge=50, le=100000, validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: Optional[float] = Field(default=None, validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    floorNo: Optional[int] = Field(default=None, validation_alias="floorNo", serialization_alias="floorNo")
    totalFloors: Optional[int] = Field(default=None, validation_alias="totalFloors", serialization_alias="totalFloors")
    guidelineRatePerSqFt: Optional[float] = Field(default=None, validation_alias="guidelineRatePerSqFt", serialization_alias="guidelineRatePerSqFt")
    ageYears: Optional[int] = Field(default=None, validation_alias="ageYears", serialization_alias="ageYears")
    transactionQuarter: Optional[str] = Field(default=None, validation_alias="transactionQuarter", serialization_alias="transactionQuarter")
    nominalCoverage: float = Field(default=0.90, description="Nominal coverage level: 0.90 (90%) or 0.95 (95%)", validation_alias="nominalCoverage", serialization_alias="nominalCoverage")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class UncertaintyPredictionResponse(BaseModel):
    """Valuation point estimate paired with statistically calibrated conformal prediction intervals (or transparent uncalibrated fallback)."""

    status: str  # "CALIBRATED" or "UNCERTAINTY_NOT_CALIBRATED"
    isCalibrated: bool = Field(..., validation_alias="isCalibrated", serialization_alias="isCalibrated")
    pointEstimate: float = Field(..., validation_alias="pointEstimate", serialization_alias="pointEstimate")
    pointEstimatePerSqFt: float = Field(..., validation_alias="pointEstimatePerSqFt", serialization_alias="pointEstimatePerSqFt")
    nominalCoverage: float = Field(..., validation_alias="nominalCoverage", serialization_alias="nominalCoverage")
    lowerBound: Optional[float] = Field(default=None, validation_alias="lowerBound", serialization_alias="lowerBound")
    upperBound: Optional[float] = Field(default=None, validation_alias="upperBound", serialization_alias="upperBound")
    intervalWidth: Optional[float] = Field(default=None, validation_alias="intervalWidth", serialization_alias="intervalWidth")
    relativeIntervalWidthPct: Optional[float] = Field(default=None, validation_alias="relativeIntervalWidthPct", serialization_alias="relativeIntervalWidthPct")
    empiricalCoverage: Optional[float] = Field(default=None, validation_alias="empiricalCoverage", serialization_alias="empiricalCoverage")
    modelVersion: Optional[str] = Field(default=None, validation_alias="modelVersion", serialization_alias="modelVersion")
    calibrationVersion: Optional[str] = Field(default=None, validation_alias="calibrationVersion", serialization_alias="calibrationVersion")
    ruleConsistencyScore: float = Field(..., validation_alias="ruleConsistencyScore", serialization_alias="ruleConsistencyScore")
    dataCompletenessScore: float = Field(..., validation_alias="dataCompletenessScore", serialization_alias="dataCompletenessScore")
    evidenceCoverageTier: str = Field(..., validation_alias="evidenceCoverageTier", serialization_alias="evidenceCoverageTier")
    governanceDisclaimer: str = Field(..., validation_alias="governanceDisclaimer", serialization_alias="governanceDisclaimer")
    blockingReasons: Optional[List[str]] = Field(default=None, validation_alias="blockingReasons", serialization_alias="blockingReasons")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

