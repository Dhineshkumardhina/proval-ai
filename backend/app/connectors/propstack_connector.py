"""Connector for PropStack Commercial & Residential Real Estate Intelligence API.

PropStack is an accredited Indian real estate data aggregator tracking registered Index-II
deeds, municipal approvals, and commercial lease/sale transactions across Mumbai MMR, Pune,
and Bengaluru.

Classification: CLASS_C_INSTITUTIONAL / CLASS_A_API
Jurisdiction: Western & Southern India (MMR, Pune, Bengaluru).
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.connectors.base import (
    BaseDataConnector,
    ConnectorConfig,
    ConnectorHealthStatus,
    RawBatchPayload,
    SyncCursor,
    get_utc_now,
)
from app.connectors.exceptions import AuthenticationError, ExpiredCredentialError, InvalidResponseError
from app.connectors.http_client import ResilientHTTPClient
from app.services.secret_manager import SecretManagerService


class PropStackConnector(BaseDataConnector):
    """Authorized B2B connector for PropStack Real Estate Transaction API."""

    def __init__(self, config: ConnectorConfig, http_client: Optional[ResilientHTTPClient] = None):
        super().__init__(config)
        self.http_client = http_client or ResilientHTTPClient(
            base_url=config.base_url,
            timeout_seconds=config.timeout_seconds,
            connect_timeout_seconds=config.connect_timeout_seconds,
            max_retries=config.max_retries,
            backoff_factor=config.backoff_factor,
            rate_limit_per_minute=config.rate_limit_per_minute,
            allow_test_endpoints=config.allow_test_endpoints,
            verify_ssl=config.verify_ssl,
            circuit_breaker_enabled=config.circuit_breaker_enabled,
            circuit_breaker_failure_threshold=config.circuit_breaker_failure_threshold,
            circuit_breaker_recovery_timeout_seconds=config.circuit_breaker_recovery_timeout_seconds,
            circuit_breaker_name=config.source_code,
        )

    def _get_api_key(self) -> str:
        """Resolve API Key strictly from SecretManager, environment variable, or custom headers."""
        if self.config.license_expiration:
            now = datetime.now(timezone.utc)
            exp = self.config.license_expiration
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                raise ExpiredCredentialError(
                    f"PropStack API credentials/license expired on {exp.isoformat()}.",
                    provider="propstack",
                    expired_at=exp.isoformat(),
                )

        env_var = self.config.auth_token_env_var or "PROPSTACK_API_KEY"
        key = SecretManagerService.get_secret(
            key_or_name=self.config.secret_manager_key or env_var,
            fallback_env_var=env_var,
        )
        if not key:
            key = self.config.custom_headers.get("x-api-key") or self.config.custom_headers.get("Authorization")
        if not key:
            raise AuthenticationError(
                f"Missing API credentials: Environment variable '{env_var}' is not configured."
            )
        return key

    def _build_auth_headers(self) -> Dict[str, str]:
        key = self._get_api_key()
        return {
            "x-propstack-key": key,
            "Accept": "application/json",
            "User-Agent": "PropVal-AI-Acquisition/1.0 (PropStack Client)",
        }

    async def authenticate(self) -> bool:
        """Validate that the configured API key is valid and responsive."""
        headers = self._build_auth_headers()
        try:
            res = await self.http_client.request(
                method="GET",
                endpoint="/v1/auth/verify",
                headers=headers,
            )
            return res.get("status") in ("authenticated", "ok", "valid")
        except Exception as e:
            raise AuthenticationError(f"PropStack authentication verification failed: {e}")

    async def test_connection(self) -> ConnectorHealthStatus:
        """Perform a lightweight health check against PropStack endpoint."""
        start_time = datetime.now(timezone.utc)
        try:
            headers = self._build_auth_headers()
            res = await self.http_client.request(
                method="GET",
                endpoint="/v1/health",
                headers=headers,
            )
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=res.get("status") in ("ok", "healthy", "up"),
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                message="Successfully reached PropStack API gateway.",
            )
        except Exception as e:
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=500,
                message=f"PropStack connection test failed: {str(e)}",
            )

    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
        """Stream paginated batches of registered deeds from PropStack."""
        headers = self._build_auth_headers()
        page = cursor.page
        page_size = cursor.page_size
        has_more = True

        while has_more:
            params: Dict[str, Any] = {
                "page": page,
                "limit": page_size,
            }
            if cursor.last_sync_timestamp:
                params["since"] = cursor.last_sync_timestamp.isoformat()
            if cursor.last_record_id:
                params["starting_after"] = cursor.last_record_id

            response_data = await self.http_client.request(
                method="GET",
                endpoint="/v1/deeds/stream",
                headers=headers,
                params=params,
            )

            if not isinstance(response_data, dict):
                raise InvalidResponseError(f"PropStack response is not a valid JSON dictionary: {type(response_data)}")

            records = response_data.get("deeds") or response_data.get("data") or []
            if not isinstance(records, list):
                raise InvalidResponseError("PropStack response deeds must be an array.")
            pagination = response_data.get("pagination") or {}
            if "has_more" in pagination:
                has_more = bool(pagination["has_more"])
            else:
                has_more = len(records) == page_size and len(records) > 0

            last_id = records[-1].get("deed_id") or records[-1].get("id") if records else cursor.last_record_id

            next_cursor = SyncCursor(
                page=page + 1,
                page_size=page_size,
                last_record_id=str(last_id) if last_id else None,
                last_sync_timestamp=get_utc_now(),
            )

            batch_id = f"batch-propstack-{uuid.uuid4().hex[:12]}"
            payload_hash = self.calculate_payload_hash(records)

            yield RawBatchPayload(
                batch_id=batch_id,
                source_code=self.config.source_code,
                record_count=len(records),
                payload_checksum_sha256=payload_hash,
                raw_records=records,
                fetched_at=get_utc_now(),
                next_cursor=next_cursor,
                has_more=has_more,
            )

            page += 1

    def extract_source_metadata(self) -> Dict[str, Any]:
        """Return legal licensing terms, SRO jurisdiction, and provenance metadata."""
        return {
            "provider_name": "PropStack Real Estate Technologies",
            "source_code": self.config.source_code,
            "access_tier": "CLASS_C_INSTITUTIONAL",
            "source_category": "DATA_AGGREGATOR",
            "jurisdiction": "Maharashtra (Mumbai, Pune) & Karnataka (Bengaluru)",
            "license_type": "Commercial Data Aggregation License",
            "permitted_purposes": [
                "DATA_INGESTION",
                "VALUATION_ESTIMATION",
                "MARKET_INTELLIGENCE",
                "MODEL_TRAINING",
            ],
            "retention_restrictions": {
                "max_retention_days": 180,
                "raw_deed_redistribution_allowed": False,
            },
            "provenance_statement": (
                "Data ingested via PropStack API under enterprise aggregation license. "
                "Derived from digitized State Registration Department Index-II registers."
            ),
        }

