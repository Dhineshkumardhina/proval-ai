"""Pydantic schemas for Machine Learning valuation, training gate, benchmarks, and SHAP explainability."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SHAPFeatureContribution(BaseModel):
    """SHAP (SHapley Additive exPlanations) single feature contribution."""

    feature: str
    featureValue: Any = Field(..., validation_alias="featureValue", serialization_alias="featureValue")
    shapValue: float = Field(..., validation_alias="shapValue", serialization_alias="shapValue")
    impactDirection: str = Field(..., validation_alias="impactDirection", serialization_alias="impactDirection")
    impactDescription: str = Field(..., validation_alias="impactDescription", serialization_alias="impactDescription")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLTrainingGateAuditResponse(BaseModel):
    """Rigorous pre-training gate evaluation ensuring zero training on unverified/synthetic data."""

    passed: bool
    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    totalRecords: int = Field(..., validation_alias="totalRecords", serialization_alias="totalRecords")
    validRecords: int = Field(..., validation_alias="validRecords", serialization_alias="validRecords")
    requiredRecordsThreshold: int = Field(default=1000, validation_alias="requiredRecordsThreshold", serialization_alias="requiredRecordsThreshold")
    isSyntheticData: bool = Field(..., validation_alias="isSyntheticData", serialization_alias="isSyntheticData")
    verifiedDeedRatio: float = Field(..., validation_alias="verifiedDeedRatio", serialization_alias="verifiedDeedRatio")
    geographicCoverage: Dict[str, int] = Field(..., validation_alias="geographicCoverage", serialization_alias="geographicCoverage")
    propertyTypeDistribution: Dict[str, int] = Field(..., validation_alias="propertyTypeDistribution", serialization_alias="propertyTypeDistribution")
    priceSanityVerified: bool = Field(..., validation_alias="priceSanityVerified", serialization_alias="priceSanityVerified")
    blockingIssues: List[str] = Field(default_factory=list, validation_alias="blockingIssues", serialization_alias="blockingIssues")
    canTrain: bool = Field(..., validation_alias="canTrain", serialization_alias="canTrain")
    governanceRecommendation: str = Field(..., validation_alias="governanceRecommendation", serialization_alias="governanceRecommendation")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLModelStatusResponse(BaseModel):
    """Real-time ML subsystem status and readiness."""

    isMlActive: bool = Field(..., validation_alias="isMlActive", serialization_alias="isMlActive")
    activeModelVersion: Optional[str] = Field(default=None, validation_alias="activeModelVersion", serialization_alias="activeModelVersion")
    engineType: str = Field(..., validation_alias="engineType", serialization_alias="engineType")
    trainingGateStatus: str = Field(..., validation_alias="trainingGateStatus", serialization_alias="trainingGateStatus")
    totalVerifiedRecordsAvailable: int = Field(..., validation_alias="totalVerifiedRecordsAvailable", serialization_alias="totalVerifiedRecordsAvailable")
    requiredRecordsThreshold: int = Field(default=1000, validation_alias="requiredRecordsThreshold", serialization_alias="requiredRecordsThreshold")
    datasetReadinessSummary: str = Field(..., validation_alias="datasetReadinessSummary", serialization_alias="datasetReadinessSummary")
    governanceNotice: str = Field(..., validation_alias="governanceNotice", serialization_alias="governanceNotice")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLModelSummaryResponse(BaseModel):
    """Metadata catalog entry for trained or candidate ML model."""

    id: str
    version: str
    algorithm: str
    datasetId: Optional[str] = Field(default=None, validation_alias="datasetId", serialization_alias="datasetId")
    metrics: Optional[Dict[str, Any]] = None
    benchmarkComparisons: Optional[Dict[str, Any]] = Field(default=None, validation_alias="benchmarkComparisons", serialization_alias="benchmarkComparisons")
    featureNames: List[str] = Field(..., validation_alias="featureNames", serialization_alias="featureNames")
    status: str
    isProductionReady: bool = Field(..., validation_alias="isProductionReady", serialization_alias="isProductionReady")
    trainingRecordsCount: int = Field(..., validation_alias="trainingRecordsCount", serialization_alias="trainingRecordsCount")
    testRecordsCount: int = Field(..., validation_alias="testRecordsCount", serialization_alias="testRecordsCount")
    trainedAt: datetime = Field(..., validation_alias="trainedAt", serialization_alias="trainedAt")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLTrainingRequest(BaseModel):
    """Request payload to initiate ML model training on an ingested dataset."""

    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    algorithm: str = Field(default="CatBoostRegressor", description="Algorithm to train: CatBoostRegressor, RandomForest, LinearRegression")
    hyperparameters: Optional[Dict[str, Any]] = None
    targetVariable: str = Field(default="transaction_price", validation_alias="targetVariable", serialization_alias="targetVariable")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLPredictionRequest(BaseModel):
    """Property feature vector for valuation estimation."""

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
    modelVersion: Optional[str] = Field(default=None, validation_alias="modelVersion", serialization_alias="modelVersion")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLPredictionResponse(BaseModel):
    """Valuation result generated by ML model or transparent fallback."""

    engineType: str = Field(..., validation_alias="engineType", serialization_alias="engineType")
    modelVersion: Optional[str] = Field(default=None, validation_alias="modelVersion", serialization_alias="modelVersion")
    estimatedPrice: float = Field(..., validation_alias="estimatedPrice", serialization_alias="estimatedPrice")
    estimatedPricePerSqFt: float = Field(..., validation_alias="estimatedPricePerSqFt", serialization_alias="estimatedPricePerSqFt")
    confidenceScore: float = Field(..., validation_alias="confidenceScore", serialization_alias="confidenceScore")
    isMlPrediction: bool = Field(..., validation_alias="isMlPrediction", serialization_alias="isMlPrediction")
    fallbackReason: Optional[str] = Field(default=None, validation_alias="fallbackReason", serialization_alias="fallbackReason")
    shapBaseValue: Optional[float] = Field(default=None, validation_alias="shapBaseValue", serialization_alias="shapBaseValue")
    shapContributions: Optional[List[SHAPFeatureContribution]] = Field(default=None, validation_alias="shapContributions", serialization_alias="shapContributions")
    governanceDisclaimer: str = Field(..., validation_alias="governanceDisclaimer", serialization_alias="governanceDisclaimer")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

