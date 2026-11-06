"""Pydantic schemas for data sources, connector health, secret management, and ingestion jobs."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


def get_utc_now():
    return datetime.now(timezone.utc)


class DataSourceBase(BaseModel):
    source_code: str = Field(..., max_length=64)
    source_name: str = Field(..., max_length=255)
    provider_name: str = Field(..., max_length=255)
    access_tier: str = Field(default="CLASS_C_INSTITUTIONAL", max_length=32)
    source_category: Optional[str] = Field(default="LICENSED_PROVIDER", max_length=64)
    authorization_status: str = Field(
        default="AUTHORIZATION_PENDING",
        pattern=r"^(DOCUMENTED_AND_AUTHORIZED|AUTHORIZATION_PENDING|SANDBOX_ONLY|TEST_ONLY|EXPIRED|REVOKED|BLOCKED)$",
    )
    legal_authorization_basis: str
    license_number: Optional[str] = None
    agreement_reference: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    permitted_purposes: Optional[List[str]] = None
    retention_restrictions: Optional[Dict[str, Any]] = None
    commercial_terms_summary: Optional[str] = None
    data_owner: str = Field(default="Institutional Data Officer", max_length=128)
    compliance_reviewer: Optional[str] = None
    api_base_url: Optional[str] = None
    auth_secret_env_var: str = Field(default="ZAPKEY_API_KEY", max_length=128)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    is_active: bool = True

    # Phase 6A Extended Configuration Fields
    provider_identifier: Optional[str] = None
    api_endpoint: Optional[str] = None
    authentication_method: Optional[str] = Field(default="API_KEY")
    secret_manager_key: Optional[str] = None
    request_timeout_seconds: Optional[int] = Field(default=30, ge=2, le=120)
    retry_policy: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff_factor": 1.5, "circuit_breaker_threshold": 5}
    )
    permitted_data_categories: Optional[List[str]] = Field(
        default_factory=lambda: ["RESIDENTIAL_DEEDS"]
    )


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceStatusUpdateRequest(BaseModel):
    authorization_status: str = Field(
        ...,
        pattern=r"^(DOCUMENTED_AND_AUTHORIZED|AUTHORIZATION_PENDING|SANDBOX_ONLY|TEST_ONLY|EXPIRED|REVOKED|BLOCKED)$",
    )
    status_change_reason: str = Field(..., min_length=5, max_length=1000)
    compliance_reviewer: Optional[str] = None


class DataSourceResponse(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status_updated_by: Optional[str] = None
    status_change_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TriggerAcquisitionRequest(BaseModel):
    source_id: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=500)
    max_batches: int = Field(default=5, ge=1, le=20)
    target_dataset_name: Optional[str] = None


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: str
    trigger_mode: str
    records_fetched: int
    records_staged: int
    records_normalized: int
    records_rejected: int
    records_duplicate: int
    error_summary: Optional[str] = None
    audit_event_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class IngestionJobListResponse(BaseModel):
    items: List[IngestionJobResponse]
    total: int


class ConnectorTestResponse(BaseModel):
    is_healthy: bool
    source_code: str
    latency_ms: float
    status_code: int
    message: str


class ProviderConnectionStatus(BaseModel):
    """Institutional monitoring state for an external property data provider."""
    source_code: str
    provider_name: str
    access_tier: str
    source_category: str
    auth_secret_env_var: str
    env_var_configured: bool
    connection_status: str  # CONNECTED, AUTHENTICATION_FAILED, UNREACHABLE, CONFIG_MISSING, MOCK_ACTIVE
    commercial_status: str  # BLOCKED_COMMERCIAL_AGREEMENT_REQUIRED, SANDBOX_ACTIVE, DOCUMENTED_AND_AUTHORIZED
    classification: str = Field(default="BLOCKED")  # IMPLEMENTED, CONFIGURED, AUTHENTICATED, LIVE, BLOCKED
    is_healthy: bool
    latency_ms: Optional[float] = None
    last_checked_at: datetime = Field(default_factory=get_utc_now)
    message: str
    secret_manager_bound: bool = False
    circuit_breaker_state: Optional[str] = "CLOSED"
    license_reference: Optional[str] = None
    license_valid_until: Optional[datetime] = None
    masked_credential: Optional[str] = "[NOT_CONFIGURED]"


class ProviderStatusBoardResponse(BaseModel):
    """Real-time provider activation and connectivity monitoring dashboard."""
    providers: List[ProviderConnectionStatus]
    total_providers: int
    live_providers_count: int
    blocked_providers_count: int
    timestamp: datetime = Field(default_factory=get_utc_now)


class RotateSecretRequest(BaseModel):
    new_secret: str = Field(..., min_length=8, max_length=512)
    reason: str = Field(..., min_length=5, max_length=500)


class SecretRotationResponse(BaseModel):
    source_id: str
    source_code: str
    secret_key_reference: str
    masked_secret: str
    fingerprint_sha256_prefix: str
    rotation_timestamp: datetime
    status: str
