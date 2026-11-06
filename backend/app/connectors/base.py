"""Base abstractions, data models, and protocols for PropVal AI data connectors."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field


def get_utc_now():
    return datetime.now(timezone.utc)


class ConnectorConfig(BaseModel):
    """Configuration for data source connector execution."""

    source_id: str
    source_code: str
    base_url: str

    # Extended Fields for Phase 6A Commercial Readiness
    provider_identifier: Optional[str] = None
    api_endpoint: Optional[str] = None
    authentication_method: str = Field(default="API_KEY")  # API_KEY, BEARER_TOKEN, PARTNER_HEADER, MUTUAL_TLS, MOCK_SANDBOX
    secret_manager_key: Optional[str] = None

    timeout_seconds: int = Field(default=30, ge=2, le=120)
    connect_timeout_seconds: float = Field(default=5.0, ge=0.5, le=30.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    backoff_factor: float = Field(default=1.5, ge=1.0, le=5.0)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)

    # Circuit Breaker Configuration
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, le=50)
    circuit_breaker_recovery_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)

    # Licensing & Data Governance Requirements
    permitted_data_categories: List[str] = Field(
        default_factory=lambda: ["RESIDENTIAL_DEEDS", "INDEX_II_RECORDS"]
    )
    license_reference: Optional[str] = None
    license_expiration: Optional[datetime] = None
    data_retention_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {"max_retention_days": 90, "raw_deed_redistribution_allowed": False}
    )

    auth_token_env_var: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    allow_test_endpoints: bool = False
    verify_ssl: bool = True

    def model_post_init(self, __context: Any) -> None:
        """Ensure provider_identifier and api_endpoint sync with source_code and base_url."""
        if not self.provider_identifier:
            self.provider_identifier = self.source_code
        if not self.api_endpoint:
            self.api_endpoint = self.base_url


class SyncCursor(BaseModel):
    """Cursor tracking high-water marks for incremental synchronization."""

    last_sync_timestamp: Optional[datetime] = None
    last_record_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)


class RawBatchPayload(BaseModel):
    """Staged batch of raw retrieved records with cryptographic checksum."""

    batch_id: str
    source_code: str
    record_count: int
    payload_checksum_sha256: str
    raw_records: List[Dict[str, Any]]
    fetched_at: datetime
    next_cursor: Optional[SyncCursor] = None
    has_more: bool = False


class ConnectorHealthStatus(BaseModel):
    """Health check outcome for a data connector."""

    is_healthy: bool
    source_code: str
    latency_ms: float
    status_code: int
    message: str
    timestamp: datetime = Field(default_factory=get_utc_now)


class BaseDataConnector(ABC):
    """Abstract Base Class for all authorized PropVal AI property data connectors."""

    def __init__(self, config: ConnectorConfig):
        self.config = config

    @abstractmethod
    async def authenticate(self) -> bool:
        """Verify or establish authorized credentials."""
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectorHealthStatus:
        """Validate connectivity and responsiveness."""
        pass

    @abstractmethod
    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
        """Asynchronously stream paginated batches of raw transaction records."""
        pass

    @abstractmethod
    def extract_source_metadata(self) -> Dict[str, Any]:
        """Return legal licensing terms, SRO jurisdiction, and provenance metadata."""
        pass

    @staticmethod
    def calculate_payload_hash(records: List[Dict[str, Any]]) -> str:
        """Compute deterministic SHA-256 hash of raw record payload."""
        canonical_str = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

