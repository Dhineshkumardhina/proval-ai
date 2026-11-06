"""Connector for Zapkey B2B Real Estate Transaction Intelligence API.

Zapkey is an accredited commercial property data provider in India delivering
digitized, geocoded, Index-II SRO registered deed transactions.

Classification: CLASS_C_INSTITUTIONAL / CLASS_A_API
Jurisdiction: Maharashtra (Mumbai, Pune) and Karnataka (Bengaluru Urban).
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

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


class ZapkeyB2BConnector(BaseDataConnector):
    """Authorized B2B connector for Zapkey Real Estate Transaction API."""

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
                    f"Zapkey API credentials/license expired on {exp.isoformat()}.",
                    provider="zapkey_b2b",
                    expired_at=exp.isoformat(),
                )

        env_var = self.config.auth_token_env_var or "ZAPKEY_API_KEY"
        key = SecretManagerService.get_secret(
            key_or_name=self.config.secret_manager_key or env_var,
            fallback_env_var=env_var,
        )
        if not key:
            key = self.config.custom_headers.get("x-api-key")
        if not key:
            raise AuthenticationError(
                f"Missing API credentials: Environment variable '{env_var}' is not configured."
            )
        return key

    def _build_auth_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self._get_api_key(),
            "Accept": "application/json",
            "User-Agent": "PropVal-AI-Acquisition/1.0",
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
            return res.get("status") == "authenticated"
        except Exception as e:
            raise AuthenticationError(f"Zapkey authentication verification failed: {e}")

    async def test_connection(self) -> ConnectorHealthStatus:
        """Perform a lightweight health check against Zapkey ping endpoint."""
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
                is_healthy=res.get("status") in ("ok", "healthy"),
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                message="Successfully reached Zapkey API gateway.",
            )
        except Exception as e:
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=500,
                message=str(e),
            )

    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
        """Fetch transactions incrementally with cursor/page synchronization."""
        headers = self._build_auth_headers()
        current_page = cursor.page

        while True:
            params: Dict[str, Any] = {
                "page": current_page,
                "limit": cursor.page_size,
            }
            if cursor.last_sync_timestamp:
                params["since"] = cursor.last_sync_timestamp.isoformat()

            response_data = await self.http_client.request(
                method="GET",
                endpoint="/v1/transactions",
                headers=headers,
                params=params,
            )

            if not isinstance(response_data, dict):
                raise InvalidResponseError(f"Zapkey response is not a valid JSON dictionary: {type(response_data)}")

            records = response_data.get("data")
            if records is None or not isinstance(records, list):
                raise InvalidResponseError("Zapkey response missing valid 'data' array.")
            has_more = bool(response_data.get("has_more", False))
            total = response_data.get("total", len(records))

            batch_id = f"BATCH-{self.config.source_code}-{uuid.uuid4().hex[:8]}"
            checksum = self.calculate_payload_hash(records)

            next_cur = None
            if has_more:
                next_cur = SyncCursor(
                    last_sync_timestamp=cursor.last_sync_timestamp,
                    last_record_id=records[-1].get("id") if records else None,
                    page=current_page + 1,
                    page_size=cursor.page_size,
                )

            yield RawBatchPayload(
                batch_id=batch_id,
                source_code=self.config.source_code,
                record_count=len(records),
                payload_checksum_sha256=checksum,
                raw_records=records,
                fetched_at=get_utc_now(),
                next_cursor=next_cur,
                has_more=has_more,
            )

            if not has_more or len(records) == 0:
                break

            current_page += 1

    def extract_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_code": self.config.source_code,
            "provider_name": "Zapkey Technologies Pvt Ltd",
            "access_tier": "CLASS_C_INSTITUTIONAL",
            "coverage_states": ["Karnataka", "Maharashtra"],
            "coverage_cities": ["Bengaluru", "Mumbai", "Pune", "Thane"],
            "data_classification": "Registered Index-II Empirical Deeds",
            "legal_basis": "Commercial B2B License Agreement / Authorized SRO Aggregation",
            "pii_handling": "Pre-scrubbed by provider / Sanitized on ingestion",
        }

