"""Connector for Open Government Data (OGD) Platform India (data.gov.in).

Ingests published government real estate, municipal guideline rates, and public registry
statistics published on the National Open Government Data Portal (data.gov.in).

Classification: CLASS_E_PUBLIC
Jurisdiction: Government of India / National OGD Platform.
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


class OpenGovernmentDataConnector(BaseDataConnector):
    """Authorized connector for Open Government Data Platform India (data.gov.in)."""

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
        if self.config.license_expiration:
            now = datetime.now(timezone.utc)
            exp = self.config.license_expiration
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                raise ExpiredCredentialError(
                    f"Open Government Data API key expired on {exp.isoformat()}.",
                    provider="ogd_india",
                    expired_at=exp.isoformat(),
                )

        env_var = self.config.auth_token_env_var or "DATA_GOV_IN_API_KEY"
        key = SecretManagerService.get_secret(
            key_or_name=self.config.secret_manager_key or env_var,
            fallback_env_var=env_var,
        )
        if not key:
            key = self.config.custom_headers.get("api-key")
        if not key:
            raise AuthenticationError(
                f"Missing API credentials: Environment variable '{env_var}' is not configured."
            )
        return key

    async def authenticate(self) -> bool:
        """Validate OGD API Key against public data.gov.in ping endpoint."""
        api_key = self._get_api_key()
        try:
            res = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/ping",
                params={"api-key": api_key, "format": "json"},
            )
            return res.get("status") in ("ok", "success", "authenticated")
        except Exception as e:
            raise AuthenticationError(f"data.gov.in authentication verification failed: {e}")

    async def test_connection(self) -> ConnectorHealthStatus:
        start_time = datetime.now(timezone.utc)
        try:
            api_key = self._get_api_key()
            res = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/health",
                params={"api-key": api_key, "format": "json"},
            )
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=res.get("status") in ("ok", "healthy", "success"),
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                message="Successfully reached National Open Government Data Portal (data.gov.in).",
            )
        except Exception as e:
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=500,
                message=f"data.gov.in connection test failed: {str(e)}",
            )

    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
        api_key = self._get_api_key()
        page = cursor.page
        page_size = cursor.page_size
        offset = (page - 1) * page_size
        has_more = True

        while has_more:
            params: Dict[str, Any] = {
                "api-key": api_key,
                "format": "json",
                "offset": offset,
                "limit": page_size,
            }

            response_data = await self.http_client.request(
                method="GET",
                endpoint="/resource/real-estate-transactions",
                params=params,
            )

            if not isinstance(response_data, dict):
                raise InvalidResponseError(f"OGD India response is not a valid JSON dictionary: {type(response_data)}")

            records = response_data.get("records") or response_data.get("data") or []
            if not isinstance(records, list):
                raise InvalidResponseError("OGD India response records must be an array.")
            total_records = response_data.get("total", 0)
            has_more = (offset + len(records)) < total_records and len(records) > 0

            next_cursor = SyncCursor(
                page=page + 1,
                page_size=page_size,
                last_record_id=str(offset + len(records)),
                last_sync_timestamp=get_utc_now(),
            )

            batch_id = f"batch-ogd-{uuid.uuid4().hex[:12]}"
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

            offset += page_size
            page += 1

    def extract_source_metadata(self) -> Dict[str, Any]:
        return {
            "provider_name": "Open Government Data (OGD) Platform India",
            "source_code": self.config.source_code,
            "access_tier": "CLASS_E_PUBLIC",
            "source_category": "GOVERNMENT_OPEN_DATA",
            "jurisdiction": "National / Government of India",
            "license_type": "National Data Sharing and Accessibility Policy (NDSAP)",
            "permitted_purposes": [
                "DATA_INGESTION",
                "VALUATION_ESTIMATION",
                "MARKET_INTELLIGENCE",
                "MODEL_TRAINING",
            ],
            "retention_restrictions": {
                "max_retention_days": 365,
                "raw_deed_redistribution_allowed": True,
            },
            "provenance_statement": (
                "Data ingested from the official Open Government Data Platform India (data.gov.in) "
                "under the National Data Sharing and Accessibility Policy (NDSAP)."
            ),
        }

