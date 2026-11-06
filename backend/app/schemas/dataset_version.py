"""Pydantic schemas for dataset versions, snapshots, comparisons, and ML export."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DatasetVersionCreate(BaseModel):
    dataset_id: str
    semver_tag: str = Field(..., pattern=r"^v\d+\.\d+\.\d+$")  # e.g. v1.0.0
    version_title: str = Field(..., max_length=255)
    description: Optional[str] = None


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    semver_tag: str
    version_title: str
    description: Optional[str] = None
    total_records: int
    verified_records: int
    rejected_records: int
    duplicate_records: int
    quarantined_records: int
    dataset_checksum_sha256: str
    geographic_distribution: Dict[str, int]
    property_type_distribution: Dict[str, int]
    source_distribution: Dict[str, int]
    validation_summary: Dict[str, Any]
    created_by: str
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    is_ml_eligible: bool
    created_at: datetime


class DatasetVersionApprovalRequest(BaseModel):
    approval_status: str = Field(..., pattern=r"^(APPROVED|DEPRECATED)$")
    approval_notes: Optional[str] = None


class DatasetComparisonResponse(BaseModel):
    source_version: str
    target_version: str
    source_dataset_id: str
    target_dataset_id: str
    added_record_count: int
    removed_record_count: int
    common_record_count: int
    newly_verified_records: int
    newly_rejected_records: int
    newly_duplicate_records: int
    newly_quarantined_records: int
    geographic_changes: Dict[str, int]
    quality_metric_changes: Dict[str, Any]
    comparison_summary: str


class MLExportManifest(BaseModel):
    dataset_version_id: str
    semver_tag: str
    export_timestamp: datetime
    eligible_record_count: int
    checksum_sha256: str
    feature_columns: List[str]
    target_column: str
    temporal_split_summary: Dict[str, Any]
    records: List[Dict[str, Any]]

