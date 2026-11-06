"""Connector for Authorized Real Estate Developer & RERA Project Transaction Records.

Ingests primary developer direct allotments, builder-buyer agreements, and RERA-registered project
conveyances under developer data authorization agreements.

Classification: CLASS_B_BULK / CLASS_C_INSTITUTIONAL
Jurisdiction: RERA-Approved Urban Real Estate Projects.
"""

import os
import re
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


class RERADeveloperConnector(BaseDataConnector):
    """Connector for authorized real estate developer primary sales and RERA registrations."""

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
                    f"RERA developer feed credentials/agreement expired on {exp.isoformat()}.",
                    provider="rera_developer",
                    expired_at=exp.isoformat(),
                )

        env_var = self.config.auth_token_env_var or "RERA_DEVELOPER_API_KEY"
        key = SecretManagerService.get_secret(
            key_or_name=self.config.secret_manager_key or env_var,
            fallback_env_var=env_var,
        )
        if not key:
            key = self.config.custom_headers.get("x-developer-token") or self.config.custom_headers.get("Authorization")
        if not key:
            raise AuthenticationError(
                f"Missing API credentials: Environment variable '{env_var}' is not configured."
            )
        return key

    def _build_auth_headers(self) -> Dict[str, str]:
        key = self._get_api_key()
        return {
            "x-developer-key": key,
            "Accept": "application/json",
            "User-Agent": "PropVal-AI-Acquisition/1.0 (RERA Developer Feed)",
        }

    @staticmethod
    def validate_rera_registration_number(rera_num: Optional[str]) -> bool:
        """Validate format of Indian RERA project registration numbers across key states.

        Examples:
        - MahaRERA: P51800001234
        - Karnataka RERA: PRM/KA/RERA/1251/310/PR/170915/000123
        - UP RERA: UPRERAPRJ12345
        - HRERA: 123 of 2017
        """
        if not rera_num:
            return False
        clean = rera_num.strip()
        patterns = [
            r"^P\d{11}$",                                   # MahaRERA
            r"^PRM/KA/RERA/\d+/\d+/PR/\d+/\d+$",            # Karnataka RERA
            r"^UPRERAPRJ\d+$",                               # UP RERA
            r"^\d+\s+of\s+\d{4}$",                          # HRERA
            r"^[A-Z0-9\/\-\_]{8,40}$",                       # Generalized RERA format
        ]
        return any(re.match(pat, clean, re.IGNORECASE) for pat in patterns)

    async def authenticate(self) -> bool:
        headers = self._build_auth_headers()
        try:
            res = await self.http_client.request(
                method="GET",
                endpoint="/v1/developer/auth/verify",
                headers=headers,
            )
            return res.get("status") in ("authenticated", "authorized", "active", "ok")
        except Exception as e:
            raise AuthenticationError(f"RERA Developer authentication failed: {e}")

    async def test_connection(self) -> ConnectorHealthStatus:
        start_time = datetime.now(timezone.utc)
        try:
            headers = self._build_auth_headers()
            res = await self.http_client.request(
                method="GET",
                endpoint="/v1/developer/health",
                headers=headers,
            )
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=res.get("status") in ("ok", "healthy"),
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=200,
                message="Successfully reached Developer RERA Gateway.",
            )
        except Exception as e:
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=round(elapsed_ms, 2),
                status_code=500,
                message=f"RERA Developer connectivity test failed: {str(e)}",
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
                "page_size": page_size,
            }
            if cursor.last_sync_timestamp:
                params["updated_after"] = cursor.last_sync_timestamp.isoformat()

            response_data = await self.http_client.request(
                method="GET",
                endpoint="/v1/developer/project-transactions",
                headers=headers,
                params=params,
            )

            if not isinstance(response_data, dict):
                raise InvalidResponseError(f"RERA developer feed response is not a valid JSON dictionary: {type(response_data)}")

            records = response_data.get("allotments") or response_data.get("transactions") or []
            if not isinstance(records, list):
                raise InvalidResponseError("RERA developer feed response records must be an array.")
            pagination = response_data.get("pagination") or {}
            if "has_more" in pagination:
                has_more = bool(pagination["has_more"])
            else:
                has_more = len(records) == page_size and len(records) > 0

            last_id = records[-1].get("allotment_id") or records[-1].get("id") if records else cursor.last_record_id

            next_cursor = SyncCursor(
                page=page + 1,
                page_size=page_size,
                last_record_id=str(last_id) if last_id else None,
                last_sync_timestamp=get_utc_now(),
            )

            batch_id = f"batch-rera-{uuid.uuid4().hex[:12]}"
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
            "provider_name": "RERA-Registered Developer Project Consortium",
            "source_code": self.config.source_code,
            "access_tier": "CLASS_B_BULK",
            "source_category": "DEVELOPER_DIRECT",
            "jurisdiction": "RERA Authorized Residential & Commercial Projects",
            "license_type": "Authorized Developer Allotment Data Feed",
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
                "Data ingested from RERA registered developer primary sales records. "
                "Verified against statutory state Real Estate Regulatory Authority project filings."
            ),
        }

