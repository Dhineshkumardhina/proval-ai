"""Pydantic schemas for institutional data quality, governance surveillance, and dashboard monitoring."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class GovernanceMetricCard(BaseModel):
    label: str
    value: int
    category: str  # e.g., 'INGESTED', 'NORMALIZED', 'VALIDATED', 'VERIFIED', 'SYNTHETIC', 'DUPLICATE', 'REJECTED', 'QUARANTINED', 'PENDING'
    description: str


class SourceDistributionItem(BaseModel):
    source_id: str
    source_name: str
    provider_name: str
    authorization_status: str
    total_records: int
    verified_empirical_count: int
    is_active: bool


class GeographicDistributionItem(BaseModel):
    state: str
    city_count: int
    record_count: int
    percentage: float


class CityDistributionItem(BaseModel):
    city: str
    record_count: int
    percentage: float
    locality_count: int


class MissingDataStatisticItem(BaseModel):
    field_name: str
    missing_count: int
    missing_percentage: float
    impact_level: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'


class IngestionJobStatusItem(BaseModel):
    job_id: str
    source_id: str
    status: str
    trigger_mode: str
    records_fetched: int
    records_normalized: int
    records_rejected: int
    records_duplicate: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class QuarantinedRecordReviewItem(BaseModel):
    id: str
    dataset_id: str
    row_index: int
    quarantine_code: str
    quarantine_reason: str
    anomaly_score: float
    anomalous_fields: List[str]
    resolution_status: str
    created_at: datetime


class DataQualityMethodology(BaseModel):
    overall_score: float
    completeness_score: float
    validity_score: float
    uniqueness_score: float
    consistency_score: float
    formula_description: str
    weights: Dict[str, float]
    verification_disclaimer: Optional[str] = None


class MLReadinessGateSummary(BaseModel):
    is_gated: bool
    empirical_records_count: int
    empirical_records_threshold: int
    calibration_holdout_count: int
    calibration_holdout_threshold: int
    status_label: str
    gate_reason: str


class InstitutionalGovernanceDashboardResponse(BaseModel):
    """Institutional enterprise monitoring payload combining metrics, datasets, sources, quality scores, and audit trails."""

    model_config = ConfigDict(populate_by_name=True)

    # 1. High-level metric counts
    total_ingested_transactions: int
    successfully_normalized_records: int
    validated_records: int
    verified_empirical_deeds: int
    synthetic_and_mock_records: int
    duplicate_records: int
    rejected_records: int
    quarantined_records: int
    records_awaiting_verification: int
    verification_rate_pct: float = Field(default=0.0)
    total_localities_covered: int = Field(default=0)

    # 2. Quality scoring
    data_quality_score: float
    quality_methodology: DataQualityMethodology

    # 3. Distributions
    source_wise_distribution: List[SourceDistributionItem]
    geographic_distribution: List[GeographicDistributionItem]
    city_wise_distribution: List[CityDistributionItem] = Field(default_factory=list)
    missing_data_statistics: List[MissingDataStatisticItem]

    # 4. Jobs & Freshness
    latest_ingestion_jobs: List[IngestionJobStatusItem]
    data_freshness_timestamp: Optional[datetime] = None
    latest_acquisition_date: Optional[datetime] = None

    # 5. ML Readiness Gate
    ml_readiness_gate: MLReadinessGateSummary

    # 6. Governance & Versions
    active_dataset_count: int
    approved_dataset_count: int
    dataset_version_history_count: int

    # 7. User Role & Permissions Context
    user_role: str
    can_approve_datasets: bool
    can_export_ml: bool

