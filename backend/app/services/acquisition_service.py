"""Acquisition orchestrator managing job lifecycle, staging, duplicate defense, and provenance."""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.connectors.base import BaseDataConnector, RawBatchPayload, SyncCursor, get_utc_now
from app.connectors.exceptions import ConnectorError
from app.models.data_source import DataSourceModel, IngestionJobModel, RawTransactionStagingModel
from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    DuplicateRecordModel,
    RejectedRecordModel,
)
from app.models.verification import QuarantinedRecordModel
from app.normalization.engine import PropertyNormalizationEngine
from app.verification.verification_service import VerificationEngine
from app.services.audit_service import (
    record_audit_event,
    EVENT_DATASET_INGESTED,
    EVENT_PII_DETECTED_AND_SCRUBBED,
    EVENT_RAW_STAGING_RETENTION_PURGE,
    EVENT_DATASET_RECORD_ERASURE,
)
from app.services.privacy_service import scrub_raw_payload_dict, anonymize_staged_payload_for_retention

logger = logging.getLogger("propval.acquisition")


class AcquisitionOrchestrator:
    """Coordinates data acquisition from connectors into staging, normalization, and datasets."""

    def __init__(self, db: Session):
        self.db = db

    def compute_sro_deed_fingerprint(
        self,
        state: str,
        district: str,
        sro_office: str,
        reg_number: str,
        reg_year: str,
        unit_number: Optional[str] = None,
    ) -> str:
        """Calculate deterministic SHA-256 fingerprint for an Indian registered deed."""
        canonical_str = (
            f"{state.strip().upper()}|{district.strip().upper()}|"
            f"{sro_office.strip().upper()}|{reg_year.strip()}|"
            f"{reg_number.strip().upper()}|{(unit_number or '').strip().upper()}"
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    async def execute_acquisition_job(
        self,
        source_id: str,
        connector: BaseDataConnector,
        cursor: Optional[SyncCursor] = None,
        target_dataset_name: Optional[str] = None,
        max_batches: int = 10,
    ) -> IngestionJobModel:
        """Run a fully managed acquisition execution with staging, normalization, and duplicate guards."""
        source = self.db.query(DataSourceModel).filter(DataSourceModel.id == source_id).first()
        if not source:
            raise ConnectorError(f"Data source with id '{source_id}' does not exist.")

        # Objective 2 & Security Requirement: Enforce Source Authorization, Validity, and Purpose Licensing
        from app.models.data_source import SourceAuthorizationStatus
        from app.services.policy_service import DataPolicyService
        from app.services.audit_service import EVENT_SOURCE_PURPOSE_BLOCKED

        is_authorized, block_reason = DataPolicyService.verify_source_for_ingestion(
            source=source,
            requested_purpose="DATA_INGESTION",
        )
        if not is_authorized:
            # Allow CLASS_F_MOCK or TEST_ONLY strictly when source is explicitly tagged as TEST_ONLY
            is_test_override = (
                source.authorization_status in (SourceAuthorizationStatus.TEST_ONLY, SourceAuthorizationStatus.SANDBOX_ONLY)
                and "MOCK" in (source.access_tier or "").upper()
            )
            if not is_test_override:
                record_audit_event(
                    db=self.db,
                    event_type=EVENT_SOURCE_PURPOSE_BLOCKED,
                    actor_id="ACQUISITION_SYSTEM",
                    actor_role="SYSTEM",
                    payload={
                        "source_id": source.id,
                        "source_code": source.source_code,
                        "reason": block_reason,
                    },
                )
                self.db.commit()
                raise ConnectorError(f"Institutional Ingestion Blocked: {block_reason}")

        cursor = cursor or SyncCursor(page=1, page_size=100)

        # 1. Initialize Ingestion Job
        job = IngestionJobModel(
            source_id=source.id,
            status="RUNNING",
            trigger_mode="MANUAL_ADMIN",
            cursor_state=cursor.model_dump(mode="json"),
            started_at=get_utc_now(),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        try:
            # 2. Authenticate
            await connector.authenticate()

            # 3. Retrieve or create target Dataset
            dataset_name = target_dataset_name or f"Acquisition_{source.source_code}_{job.started_at.strftime('%Y%m%d_%H%M')}"
            dataset = DatasetMetadataModel(
                name=dataset_name,
                description=f"Automated acquisition from {source.source_name}",
                source_type="commercial_license" if "CLASS_C" in source.access_tier else "user_upload",
                license_type="commercial_restricted",
                data_source_provenance=f"Ingested via {connector.__class__.__name__} from {source.provider_name}",
                file_format="api_stream",
                original_filename=f"{source.source_code}_stream",
                file_hash_sha256=hashlib.sha256(job.id.encode()).hexdigest(),
                status="INGESTING",
                approval_status="UNDER_REVIEW",
                data_owner=source.data_owner or "Institutional Data Officer",
            )
            self.db.add(dataset)
            self.db.commit()
            self.db.refresh(dataset)

            batches_processed = 0
            total_fetched = 0
            total_staged = 0
            total_normalized = 0
            total_rejected = 0
            total_duplicate = 0
            total_pii_redacted = 0

            norm_engine = PropertyNormalizationEngine(source_id=source.source_code, source_code=source.source_code)
            verification_engine = VerificationEngine(db=self.db, verifier_id="ACQUISITION_SYSTEM")

            # 4. Stream batches from connector
            async for batch in connector.fetch_incremental(cursor):
                batches_processed += 1
                total_fetched += batch.record_count

                # Stage raw batch with pre-staging privacy scrubbing
                for row_idx, raw_record in enumerate(batch.raw_records):
                    # DPDP Act Pre-Staging PII Scrubbing
                    cleansed_record, pii_count, detected_pii = scrub_raw_payload_dict(raw_record)
                    if pii_count > 0:
                        total_pii_redacted += pii_count

                    staged = RawTransactionStagingModel(
                        job_id=job.id,
                        source_id=source.id,
                        row_index=total_staged + 1,
                        payload_hash_sha256=hashlib.sha256(
                            json.dumps(cleansed_record, sort_keys=True).encode()
                        ).hexdigest(),
                        raw_payload=cleansed_record,
                        pii_scrub_status="CLEANSED",
                    )
                    self.db.add(staged)
                    total_staged += 1

                    # Process through Normalization & Verification Pipeline using cleansed payload
                    res = self._process_record(
                        dataset=dataset,
                        record=cleansed_record,
                        row_index=total_staged,
                        source_code=source.source_code,
                        norm_engine=norm_engine,
                        verification_engine=verification_engine,
                    )
                    if res == "VERIFIED" or res == "NORMALIZED":
                        total_normalized += 1
                    elif res == "DUPLICATE":
                        total_duplicate += 1
                    else:
                        total_rejected += 1

                self.db.commit()

                if batch.next_cursor:
                    job.cursor_state = batch.next_cursor.model_dump(mode="json")
                if not batch.has_more or batches_processed >= max_batches:
                    break

            # If PII was detected and sanitized during ingestion, emit explicit privacy audit event
            if total_pii_redacted > 0:
                record_audit_event(
                    db=self.db,
                    event_type=EVENT_PII_DETECTED_AND_SCRUBBED,
                    actor_id="ACQUISITION_SYSTEM",
                    actor_role="SYSTEM",
                    payload={
                        "job_id": job.id,
                        "source_id": source.id,
                        "source_code": source.source_code,
                        "total_redactions": total_pii_redacted,
                        "records_scanned": total_staged,
                    },
                )

            # 5. Finalize Job and Dataset
            job.records_fetched = total_fetched
            job.records_staged = total_staged
            job.records_normalized = total_normalized
            job.records_rejected = total_rejected
            job.records_duplicate = total_duplicate
            job.status = "COMPLETED"
            job.completed_at = get_utc_now()

            dataset.total_rows = total_staged
            dataset.valid_rows = total_normalized
            dataset.rejected_rows = total_rejected
            dataset.duplicate_rows = total_duplicate
            dataset.status = "COMPLETED"
            dataset.is_usable_for_ml = total_normalized >= 1000

            # 6. Record Audit Event
            audit_ev = record_audit_event(
                db=self.db,
                event_type=EVENT_DATASET_INGESTED,
                actor_id="ACQUISITION_SYSTEM",
                actor_role="ADMIN",
                payload={
                    "job_id": job.id,
                    "dataset_id": dataset.id,
                    "source_id": source.id,
                    "source_code": source.source_code,
                    "records_fetched": total_fetched,
                    "records_normalized": total_normalized,
                    "records_duplicate": total_duplicate,
                    "records_rejected": total_rejected,
                },
            )
            job.audit_event_id = audit_ev.id

            self.db.commit()
            self.db.refresh(job)
            return job

        except Exception as e:
            self.db.rollback()
            job.status = "FAILED"
            job.error_summary = str(e)
            job.completed_at = get_utc_now()
            self.db.commit()
            logger.error(f"Acquisition job '{job.id}' failed: {e}")
            raise

    def _process_record(
        self,
        dataset: DatasetMetadataModel,
        record: Dict[str, Any],
        row_index: int,
        source_code: str,
        norm_engine: PropertyNormalizationEngine,
        verification_engine: VerificationEngine,
    ) -> str:
        """Normalize, validate, and verify a single transaction deed record."""
        norm_tx, err = norm_engine.normalize_record(record, row_index=row_index)
        if norm_tx is None:
            code = "INVALID_RECORD"
            if "Amount" in (err or ""):
                code = "MISSING_PRICE"
            elif "Area" in (err or ""):
                code = "INVALID_AREA"
            elif "Date" in (err or ""):
                code = "IMPOSSIBLE_DATE"

            rej = RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=row_index,
                rejection_reason=err or "Normalization failure",
                rejection_code=code,
                raw_data=record,
            )
            self.db.add(rej)
            return "REJECTED"

        status_outcome, _ = verification_engine.verify_and_route_record(
            dataset=dataset,
            norm_tx=norm_tx,
            row_index=row_index,
        )
        return status_outcome

    def purge_expired_raw_staging(
        self,
        retention_days: Optional[int] = None,
        actor_id: str = "SYSTEM_RETENTION_WORKER",
        source_id: Optional[str] = None,
    ) -> int:
        """Purge raw staging payloads respecting source-specific retention policies and authorized legal holds.

        If retention_days is explicitly provided (for backward compatibility), applies it across matching records.
        Otherwise, inspects each source's configured retention_restrictions['max_retention_days'].
        """
        from datetime import timedelta
        from app.services.policy_service import DataPolicyService
        from app.services.audit_service import (
            EVENT_RAW_STAGING_RETENTION_PURGE,
            EVENT_RETENTION_LEGAL_HOLD_APPLIED,
        )

        sources_query = self.db.query(DataSourceModel)
        if source_id:
            sources_query = sources_query.filter(DataSourceModel.id == source_id)
        sources = sources_query.all()

        total_purged = 0
        now_dt = get_utc_now()

        # 1. Purge per source based on source-specific retention policy
        for src in sources:
            # Check legal hold
            if DataPolicyService.is_legal_hold_active(src):
                record_audit_event(
                    db=self.db,
                    event_type=EVENT_RETENTION_LEGAL_HOLD_APPLIED,
                    actor_id=actor_id,
                    actor_role="DPO",
                    payload={
                        "source_id": src.id,
                        "source_code": src.source_code,
                        "message": f"Source '{src.source_code}' is under authorized legal hold. Staging records retained without purging.",
                    },
                )
                self.db.commit()
                continue

            # Determine retention days
            if retention_days is not None:
                src_days = retention_days
            else:
                src_days = DataPolicyService.get_source_retention_days(src) or 90

            cutoff_dt = now_dt - timedelta(days=src_days)
            records = (
                self.db.query(RawTransactionStagingModel)
                .filter(
                    RawTransactionStagingModel.source_id == src.id,
                    RawTransactionStagingModel.created_at < cutoff_dt,
                    RawTransactionStagingModel.pii_scrub_status != "PURGED",
                    RawTransactionStagingModel.pii_scrub_status != "ERASED_UNDER_DPDP",
                )
                .all()
            )

            src_purged = 0
            for r in records:
                r.raw_payload = anonymize_staged_payload_for_retention(r.raw_payload or {})
                r.pii_scrub_status = "PURGED"
                src_purged += 1

            if src_purged > 0:
                record_audit_event(
                    db=self.db,
                    event_type=EVENT_RAW_STAGING_RETENTION_PURGE,
                    actor_id=actor_id,
                    actor_role="ADMIN",
                    payload={
                        "source_id": src.id,
                        "source_code": src.source_code,
                        "retention_days": src_days,
                        "records_purged": src_purged,
                        "cutoff_timestamp": cutoff_dt.isoformat(),
                    },
                )
                self.db.commit()
                total_purged += src_purged

        # 2. Also handle any staging records with unspecified/orphan source_id
        effective_orphan_days = retention_days or 90
        orphan_cutoff = now_dt - timedelta(days=effective_orphan_days)
        orphan_records = (
            self.db.query(RawTransactionStagingModel)
            .filter(
                RawTransactionStagingModel.source_id.notin_([s.id for s in sources]) if sources else True,
                RawTransactionStagingModel.created_at < orphan_cutoff,
                RawTransactionStagingModel.pii_scrub_status != "PURGED",
                RawTransactionStagingModel.pii_scrub_status != "ERASED_UNDER_DPDP",
            )
            .all()
        )
        orphan_purged = 0
        for r in orphan_records:
            r.raw_payload = anonymize_staged_payload_for_retention(r.raw_payload or {})
            r.pii_scrub_status = "PURGED"
            orphan_purged += 1

        if orphan_purged > 0:
            record_audit_event(
                db=self.db,
                event_type=EVENT_RAW_STAGING_RETENTION_PURGE,
                actor_id=actor_id,
                actor_role="ADMIN",
                payload={
                    "retention_days": effective_orphan_days,
                    "records_purged": orphan_purged,
                    "cutoff_timestamp": orphan_cutoff.isoformat(),
                },
            )
            self.db.commit()
            total_purged += orphan_purged

        return total_purged

    def erase_transaction_record(
        self,
        transaction_id: str,
        reason: str,
        actor_id: str = "COMPLIANCE_OFFICER",
    ) -> bool:
        """Execute DPDP Section 12 Right to Erasure on a specific transaction record.

        Delegates to centralized TransactionErasureService across all storage tiers:
        imported transactions, duplicates, quarantine, raw staging, and version snapshots.
        """
        from app.services.erasure_service import TransactionErasureService
        result = TransactionErasureService.execute_erasure(
            db=self.db,
            transaction_id=transaction_id,
            reason=reason,
            actor_id=actor_id,
        )
        return result.get("success", False)

