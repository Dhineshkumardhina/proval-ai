"""Pydantic schemas for datasets, transaction ingestion, and ML readiness."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DatasetResponse(BaseModel):
    """Dataset metadata catalog item."""

    id: str
    name: str
    description: Optional[str] = None
    sourceType: str = Field(..., validation_alias="sourceType", serialization_alias="sourceType")
    licenseType: str = Field(..., validation_alias="licenseType", serialization_alias="licenseType")
    dataSourceProvenance: str = Field(..., validation_alias="dataSourceProvenance", serialization_alias="dataSourceProvenance")
    fileFormat: str = Field(..., validation_alias="fileFormat", serialization_alias="fileFormat")
    originalFilename: str = Field(..., validation_alias="originalFilename", serialization_alias="originalFilename")
    fileHashSha256: str = Field(..., validation_alias="fileHashSha256", serialization_alias="fileHashSha256")
    totalRows: int = Field(..., validation_alias="totalRows", serialization_alias="totalRows")
    validRows: int = Field(..., validation_alias="validRows", serialization_alias="validRows")
    rejectedRows: int = Field(..., validation_alias="rejectedRows", serialization_alias="rejectedRows")
    duplicateRows: int = Field(..., validation_alias="duplicateRows", serialization_alias="duplicateRows")
    status: str
    isUsableForMl: bool = Field(..., validation_alias="isUsableForMl", serialization_alias="isUsableForMl")
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ImportedTransactionResponse(BaseModel):
    """Normalized property transaction record."""

    id: str
    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    rowIndex: int = Field(..., validation_alias="rowIndex", serialization_alias="rowIndex")
    city: str
    locality: str
    subMarket: Optional[str] = Field(default=None, validation_alias="subMarket", serialization_alias="subMarket")
    pincode: Optional[str] = None
    projectName: str = Field(..., validation_alias="projectName", serialization_alias="projectName")
    unitNumber: Optional[str] = Field(default=None, validation_alias="unitNumber", serialization_alias="unitNumber")
    propertyType: str = Field(..., validation_alias="propertyType", serialization_alias="propertyType")
    transactionType: str = Field(default="REGISTRATION", validation_alias="transactionType", serialization_alias="transactionType")
    transactionDate: datetime = Field(..., validation_alias="transactionDate", serialization_alias="transactionDate")
    transactionQuarter: str = Field(..., validation_alias="transactionQuarter", serialization_alias="transactionQuarter")
    carpetAreaSqFt: float = Field(..., validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: Optional[float] = Field(default=None, validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    floorNo: Optional[int] = Field(default=None, validation_alias="floorNo", serialization_alias="floorNo")
    totalFloors: Optional[int] = Field(default=None, validation_alias="totalFloors", serialization_alias="totalFloors")
    transactionPrice: float = Field(..., validation_alias="transactionPrice", serialization_alias="transactionPrice")
    pricePerSqFt: float = Field(..., validation_alias="pricePerSqFt", serialization_alias="pricePerSqFt")
    guidelineRatePerSqFt: Optional[float] = Field(default=None, validation_alias="guidelineRatePerSqFt", serialization_alias="guidelineRatePerSqFt")
    deviationFromGuidelinePct: Optional[float] = Field(default=None, validation_alias="deviationFromGuidelinePct", serialization_alias="deviationFromGuidelinePct")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    isVerifiedDeed: bool = Field(default=True, validation_alias="isVerifiedDeed", serialization_alias="isVerifiedDeed")
    dataSource: str = Field(default="imported-deed", validation_alias="dataSource", serialization_alias="dataSource")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RejectedRecordResponse(BaseModel):
    """Audit record for rejected row with diagnostic reason."""

    id: str
    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    rowIndex: int = Field(..., validation_alias="rowIndex", serialization_alias="rowIndex")
    rejectionReason: str = Field(..., validation_alias="rejectionReason", serialization_alias="rejectionReason")
    rejectionCode: str = Field(..., validation_alias="rejectionCode", serialization_alias="rejectionCode")
    rawData: Dict[str, Any] = Field(..., validation_alias="rawData", serialization_alias="rawData")
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DuplicateRecordResponse(BaseModel):
    """Record flagged as duplicate transaction."""

    id: str
    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    rowIndex: int = Field(..., validation_alias="rowIndex", serialization_alias="rowIndex")
    fingerprintHash: str = Field(..., validation_alias="fingerprintHash", serialization_alias="fingerprintHash")
    matchedTransactionId: Optional[str] = Field(default=None, validation_alias="matchedTransactionId", serialization_alias="matchedTransactionId")
    rawData: Dict[str, Any] = Field(..., validation_alias="rawData", serialization_alias="rawData")
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DataQualityReportResponse(BaseModel):
    """Statistical data quality distribution report."""

    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    datasetName: str = Field(..., validation_alias="datasetName", serialization_alias="datasetName")
    totalRecords: int = Field(..., validation_alias="totalRecords", serialization_alias="totalRecords")
    validRecords: int = Field(..., validation_alias="validRecords", serialization_alias="validRecords")
    rejectedRecords: int = Field(..., validation_alias="rejectedRecords", serialization_alias="rejectedRecords")
    duplicateRecords: int = Field(..., validation_alias="duplicateRecords", serialization_alias="duplicateRecords")
    validityRatePct: float = Field(..., validation_alias="validityRatePct", serialization_alias="validityRatePct")
    missingValuePercentages: Dict[str, float] = Field(..., validation_alias="missingValuePercentages", serialization_alias="missingValuePercentages")
    geographicDistribution: Dict[str, int] = Field(..., validation_alias="geographicDistribution", serialization_alias="geographicDistribution")
    propertyTypeDistribution: Dict[str, int] = Field(..., validation_alias="propertyTypeDistribution", serialization_alias="propertyTypeDistribution")
    priceMetrics: Dict[str, float] = Field(..., validation_alias="priceMetrics", serialization_alias="priceMetrics")
    temporalDistribution: Dict[str, int] = Field(..., validation_alias="temporalDistribution", serialization_alias="temporalDistribution")
    meetsMlCriteria: bool = Field(..., validation_alias="meetsMlCriteria", serialization_alias="meetsMlCriteria")
    readinessSummary: str = Field(..., validation_alias="readinessSummary", serialization_alias="readinessSummary")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLPreparationResponse(BaseModel):
    """Result of train/validation/test split with leakage prevention."""

    datasetId: str = Field(..., validation_alias="datasetId", serialization_alias="datasetId")
    totalUsableRecords: int = Field(..., validation_alias="totalUsableRecords", serialization_alias="totalUsableRecords")
    trainRecords: int = Field(..., validation_alias="trainRecords", serialization_alias="trainRecords")
    validationRecords: int = Field(..., validation_alias="validationRecords", serialization_alias="validationRecords")
    testRecords: int = Field(..., validation_alias="testRecords", serialization_alias="testRecords")
    temporalSplit: Dict[str, str] = Field(..., validation_alias="temporalSplit", serialization_alias="temporalSplit")
    spatialClusters: List[str] = Field(..., validation_alias="spatialClusters", serialization_alias="spatialClusters")
    selectedFeatures: List[str] = Field(..., validation_alias="selectedFeatures", serialization_alias="selectedFeatures")
    targetVariable: str = Field(..., validation_alias="targetVariable", serialization_alias="targetVariable")
    isLeakageGuarded: bool = Field(default=True, validation_alias="isLeakageGuarded", serialization_alias="isLeakageGuarded")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

