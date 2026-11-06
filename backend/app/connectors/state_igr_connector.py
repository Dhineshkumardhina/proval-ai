"""Connector for Authorized State Registration Department (IGR) SRO Portals.

Connects to authorized State Registration Department e-Search and electronic SRO conveyance
registries under formal government department MoU / digital certificate integration.

Classification: CLASS_A_API / CLASS_C_INSTITUTIONAL
Jurisdiction: State Government Registration & Stamps Departments (e.g., IGR Maharashtra, Kaveri Karnataka).
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


class StateRegistrationDepartmentConnector(BaseDataConnector):
    """Authorized G2B connector for State Registration Department (IGR) APIs."""

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

    def _get_credentials(self) -> Dict[str, str]:
        if self.config.license_expiration:
            now = datetime.now(timezone.utc)
            exp = self.config.license_expiration
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                raise ExpiredCredentialError(
                    f"State IGR credentials/MoU expired on {exp.isoformat()}.",
                    provider="state_igr",
                    expired_at=exp.isoformat(),
                )

        env_var = self.config.auth_token_env_var or "IGR_CLIENT_TOKEN"
        token = SecretManagerService.get_secret(
            key_or_name=self.config.secret_manager_key or env_var,
            fallback_env_var=env_var,
        ) or self.config.custom_headers.get("x-igr-token")

        dept_id = SecretManagerService.get_secret(
            key_or_name="IGR_DEPARTMENT_ID",
            fallback_env_var="IGR_DEPARTMENT_ID",
        ) or self.config.custom_headers.get("x-igr-dept-id")

        if not token:
            raise AuthenticationError(
                f"Missing IGR credentials: Environment variable '{env_var}' is not configured."
            )
        return {"token": token, "dept_id": dept_id or "INSTITUTIONAL_VALUER"}

    def _build_auth_headers(self) -> Dict[str, str]:
        creds = self._get_credentials()
        return {
            "x-igr-token": creds["token"],
            "x-igr-dept-id": creds["dept_id"],
            "Accept": "application/json",
            "User-Agent": "PropVal-AI-Acquisition/1.0 (State IGR G2B Gateway)",
        }

    async def authenticate(self) -> bool:
        headers = self._build_auth_headers()
        try:
            res = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/auth/certificate-verify",
                headers=headers,
            )
            return res.get("status") in ("authenticated", "authorized", "valid", "ok")
        except Exception as e:
            raise AuthenticationError(f"State IGR certificate authentication failed: {e}")

    async def test_connection(self) -> ConnectorHealthStatus:
        start_time = datetime.now(timezone.utc)
        try:
            headers = self._build_auth_headers()
            res = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/gateway/status",
                headers=headers,
            )
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=res.get("status") in ("ok", "operational", "healthy"),
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                message="Successfully reached State Registration Department (IGR) SRO Gateway.",
            )
        except Exception as e:
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=500,
                message=f"State IGR SRO gateway test failed: {str(e)}",
            )

    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
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
                params["registered_since"] = cursor.last_sync_timestamp.isoformat()
            if cursor.last_record_id:
                params["last_deed_sequence"] = cursor.last_record_id

            response_data = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/sro/registered-deeds",
                headers=headers,
                params=params,
            )

            if not isinstance(response_data, dict):
                raise InvalidResponseError(f"State IGR response is not a valid JSON dictionary: {type(response_data)}")

            records = response_data.get("deeds") or response_data.get("records") or []
            if not isinstance(records, list):
                raise InvalidResponseError("State IGR response deeds must be an array.")
            pagination = response_data.get("pagination") or {}
            if "has_more" in pagination:
                has_more = bool(pagination["has_more"])
            else:
                has_more = len(records) == page_size and len(records) > 0

            last_id = records[-1].get("deed_sequence") or records[-1].get("id") if records else cursor.last_record_id

            next_cursor = SyncCursor(
                page=page + 1,
                page_size=page_size,
                last_record_id=str(last_id) if last_id else None,
                last_sync_timestamp=get_utc_now(),
            )

            batch_id = f"batch-igr-{uuid.uuid4().hex[:12]}"
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
        return {
            "provider_name": "State Registration & Stamps Department (IGR Gateway)",
            "source_code": self.config.source_code,
            "access_tier": "CLASS_A_API",
            "source_category": "STATE_REGISTRATION_DEPT",
            "jurisdiction": "State Government SRO Registration Jurisdictions",
            "license_type": "Authorized G2B Institutional API Agreement & Digital Certificate",
            "permitted_purposes": [
                "DATA_INGESTION",
                "VALUATION_ESTIMATION",
                "MARKET_INTELLIGENCE",
                "MODEL_TRAINING",
            ],
            "retention_restrictions": {
                "max_retention_days": 365,
                "raw_deed_redistribution_allowed": False,
            },
            "provenance_statement": (
                "Data ingested via official State Registration Department (IGR) SRO digital certificate gateway. "
                "Certified statutory Index-II conveyance records."
            ),
        }

