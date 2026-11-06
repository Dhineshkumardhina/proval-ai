"""Mock / Test Connector for testing acquisition pipelines without external API credentials.

Labels clearly indicate this is a MOCK adapter for test automation only,
not a real connection to any government or commercial registry.
"""

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
from app.connectors.exceptions import AuthenticationError


class MockDeedConnector(BaseDataConnector):
    """MOCK / TEST ONLY adapter simulating authorized deed feed responses for unit/integration tests."""

    def __init__(self, config: ConnectorConfig, simulated_records: Optional[List[Dict[str, Any]]] = None):
        super().__init__(config)
        self.simulated_records = simulated_records if simulated_records is not None else self._generate_default_test_records()
        self.should_fail_auth = False
        self.should_timeout = False

    def _generate_default_test_records(self) -> List[Dict[str, Any]]:
        """Generate deterministic mock records with realistic Indian property attributes."""
        records = []
        uid_prefix = uuid.uuid4().hex[:6].upper()
        for i in range(1, 25):
            records.append({
                "source_record_id": f"MOCK-SRO-BLR-{uid_prefix}-{i:04d}",
                "registration_number": f"DOC-{uid_prefix}-{i:04d}/2024",
                "registration_date": f"2024-{(i%12)+1:02d}-15",
                "transaction_amount": 12500000 + (i * 250000),
                "property_type": "High-Rise Apartment",
                "state": "Karnataka",
                "district": "Bengaluru Urban",
                "sub_district": "Shivajinagar",
                "locality": "Whitefield",
                "project_name": f"Sobha Test Residency Unit {i}",
                "unit_number": f"B-{i:02d}",
                "carpet_area_sqft": 1250.0 + (i * 20.0),
                "guideline_rate_per_sqft": 8500.0,
                "latitude": 12.9698 + (i * 0.0001),
                "longitude": 77.7499 + (i * 0.0001),
                "sro_office": "Shivajinagar SRO",
                "deed_type": "Sale Deed",
                "is_verified": True,
            })
        return records

    async def authenticate(self) -> bool:
        if self.should_fail_auth:
            raise AuthenticationError("MOCK AUTH FAILURE: Simulated invalid API token.")
        return True

    async def test_connection(self) -> ConnectorHealthStatus:
        if self.should_fail_auth:
            return ConnectorHealthStatus(
                is_healthy=False,
                source_code=self.config.source_code,
                latency_ms=1.5,
                status_code=401,
                message="MOCK AUTH FAILURE: Unauthorized",
            )
        return ConnectorHealthStatus(
            is_healthy=True,
            source_code=self.config.source_code,
            latency_ms=2.0,
            status_code=200,
            message="MOCK CONNECTOR: Healthy test connection (Simulated Environment).",
        )

    async def fetch_incremental(
        self,
        cursor: SyncCursor,
    ) -> AsyncGenerator[RawBatchPayload, None]:
        if self.should_fail_auth:
            raise AuthenticationError("MOCK AUTH FAILURE: Simulated invalid API token.")

        current_page = cursor.page
        page_size = cursor.page_size

        while True:
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size

            batch_records = self.simulated_records[start_idx:end_idx]
            has_more = end_idx < len(self.simulated_records)

            next_cursor = None
            if has_more:
                next_cursor = SyncCursor(
                    last_sync_timestamp=cursor.last_sync_timestamp,
                    last_record_id=batch_records[-1].get("source_record_id") if batch_records else None,
                    page=current_page + 1,
                    page_size=page_size,
                )

            batch_id = f"MOCK-BATCH-{uuid.uuid4().hex[:8]}"
            checksum = self.calculate_payload_hash(batch_records)

            yield RawBatchPayload(
                batch_id=batch_id,
                source_code=self.config.source_code,
                record_count=len(batch_records),
                payload_checksum_sha256=checksum,
                raw_records=batch_records,
                fetched_at=get_utc_now(),
                next_cursor=next_cursor,
                has_more=has_more,
            )

            if not has_more or len(batch_records) == 0:
                break

            current_page += 1

    def extract_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_code": self.config.source_code,
            "provider_name": "PropVal AI Test Harness (Mock Provider)",
            "access_tier": "CLASS_F_MOCK",
            "coverage_states": ["Karnataka"],
            "coverage_cities": ["Bengaluru"],
            "data_classification": "Simulated Synthetic Test Deeds",
            "legal_basis": "Internal Testing & Simulation Only (Not Real SRO Data)",
            "pii_handling": "Synthetically generated test fixtures",
        }

