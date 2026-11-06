"""Service for dataset versioning, snapshot integrity, version diffs, and ML export."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
)
from app.models.verification import QuarantinedRecordModel
from app.models.dataset_version import DatasetVersionModel
from app.schemas.dataset_version import (
    DatasetComparisonResponse,
    MLExportManifest,
)
from app.services.audit_service import record_audit_event, EVENT_DATASET_INGESTED, EVENT_ADMIN_ACTION

logger = logging.getLogger("propval.dataset_management")


class DatasetVersionService:
    """Manages immutable snapshots, cryptographic checksums, version diffs, and ML export."""

    def __init__(self, db: Session):
        self.db = db

    def compute_dataset_checksum(self, transaction_fingerprints: List[str]) -> str:
        """Compute deterministic Merkle-style root hash from sorted transaction fingerprints."""
        sorted_fps = sorted(transaction_fingerprints)
        concatenated = "|".join(sorted_fps)
        return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

    def create_version_snapshot(
        self,
        dataset_id: str,
        semver_tag: str,
        version_title: str,
        created_by: str,
        description: Optional[str] = None,
    ) -> DatasetVersionModel:
        """Snapshot current dataset state into an immutable DatasetVersionModel."""
        dataset = self.db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dataset '{dataset_id}' not found.")

        # Guard against duplicate semver tag for this dataset
        existing = (
            self.db.query(DatasetVersionModel)
            .filter(
                DatasetVersionModel.dataset_id == dataset_id,
                DatasetVersionModel.semver_tag == semver_tag,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version '{semver_tag}' already exists for dataset '{dataset_id}'. Dataset versions are immutable.",
            )

        # Collect verified transactions
        transactions = (
            self.db.query(ImportedTransactionModel)
            .filter(ImportedTransactionModel.dataset_id == dataset_id)
            .all()
        )
        verified_count = sum(1 for tx in transactions if tx.is_verified_deed and not tx.is_asking_price)
        rejected_count = (
            self.db.query(RejectedRecordModel)
            .filter(RejectedRecordModel.dataset_id == dataset_id)
            .count()
        )
        duplicate_count = (
            self.db.query(DuplicateRecordModel)
            .filter(DuplicateRecordModel.dataset_id == dataset_id)
            .count()
        )
        quarantined_count = (
            self.db.query(QuarantinedRecordModel)
            .filter(QuarantinedRecordModel.dataset_id == dataset_id)
            .count()
        )

        # Compute distributions
        geo_dist: Dict[str, int] = {}
        prop_dist: Dict[str, int] = {}
        source_dist: Dict[str, int] = {}
        fingerprints: List[str] = []
        included_tx_ids: List[str] = []

        for tx in transactions:
            geo_dist[tx.city] = geo_dist.get(tx.city, 0) + 1
            prop_dist[tx.property_type] = prop_dist.get(tx.property_type, 0) + 1
            source_dist[tx.data_source] = source_dist.get(tx.data_source, 0) + 1
            fingerprints.append(tx.fingerprint_hash)
            included_tx_ids.append(tx.id)

        checksum = self.compute_dataset_checksum(fingerprints)
        is_ml = verified_count >= 1000 and dataset.source_type != "synthetic_benchmark"

        version = DatasetVersionModel(
            dataset_id=dataset_id,
            semver_tag=semver_tag,
            version_title=version_title,
            description=description,
            total_records=len(transactions) + rejected_count + duplicate_count + quarantined_count,
            verified_records=verified_count,
            rejected_records=rejected_count,
            duplicate_records=duplicate_count,
            quarantined_records=quarantined_count,
            dataset_checksum_sha256=checksum,
            geographic_distribution=geo_dist,
            property_type_distribution=prop_dist,
            source_distribution=source_dist,
            validation_summary={
                "valid_records": verified_count,
                "rejection_rate_pct": round((rejected_count / max(1, len(transactions))) * 100, 2),
                "is_ml_ready": is_ml,
            },
            included_transaction_ids=included_tx_ids,
            created_by=created_by,
            approval_status="DRAFT",
            is_ml_eligible=is_ml,
        )
        self.db.add(version)

        # Record tamper-evident audit event
        record_audit_event(
            db=self.db,
            event_type=EVENT_ADMIN_ACTION,
            actor_id=created_by,
            actor_role="SENIOR_UNDERWRITER",
            payload={
                "action": "CREATE_DATASET_VERSION_SNAPSHOT",
                "dataset_id": dataset_id,
                "semver_tag": semver_tag,
                "dataset_checksum_sha256": checksum,
                "verified_records": verified_count,
                "is_ml_eligible": is_ml,
            },
        )

        self.db.commit()
        self.db.refresh(version)
        return version

    def approve_dataset_version(
        self,
        version_id: str,
        approval_status: str,
        approver_id: str,
        notes: Optional[str] = None,
    ) -> DatasetVersionModel:
        """Approve or deprecate a dataset version (Role-gated: Admin / Chief Underwriter)."""
        version = self.db.query(DatasetVersionModel).filter(DatasetVersionModel.id == version_id).first()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset version not found.")

        version.approval_status = approval_status
        version.approved_by = approver_id
        version.approved_at = datetime.now(timezone.utc)

        record_audit_event(
            db=self.db,
            event_type=EVENT_ADMIN_ACTION,
            actor_id=approver_id,
            actor_role="ADMIN",
            payload={
                "action": "APPROVE_DATASET_VERSION",
                "version_id": version.id,
                "semver_tag": version.semver_tag,
                "approval_status": approval_status,
                "notes": notes,
            },
        )
        self.db.commit()
        self.db.refresh(version)
        return version

    def compare_versions(self, version_a_id: str, version_b_id: str) -> DatasetComparisonResponse:
        """Compute exact record and distributional differential between two dataset snapshots."""
        ver_a = self.db.query(DatasetVersionModel).filter(DatasetVersionModel.id == version_a_id).first()
        ver_b = self.db.query(DatasetVersionModel).filter(DatasetVersionModel.id == version_b_id).first()

        if not ver_a or not ver_b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both dataset versions not found.")

        set_a: Set[str] = set(ver_a.included_transaction_ids or [])
        set_b: Set[str] = set(ver_b.included_transaction_ids or [])

        added = set_b - set_a
        removed = set_a - set_b
        common = set_a.intersection(set_b)

        # Geographic changes
        geo_changes: Dict[str, int] = {}
        all_cities = set(ver_a.geographic_distribution.keys()).union(set(ver_b.geographic_distribution.keys()))
        for c in all_cities:
            cnt_a = ver_a.geographic_distribution.get(c, 0)
            cnt_b = ver_b.geographic_distribution.get(c, 0)
            if cnt_a != cnt_b:
                geo_changes[c] = cnt_b - cnt_a

        return DatasetComparisonResponse(
            source_version=ver_a.semver_tag,
            target_version=ver_b.semver_tag,
            source_dataset_id=ver_a.dataset_id,
            target_dataset_id=ver_b.dataset_id,
            added_record_count=len(added),
            removed_record_count=len(removed),
            common_record_count=len(common),
            newly_verified_records=ver_b.verified_records - ver_a.verified_records,
            newly_rejected_records=ver_b.rejected_records - ver_a.rejected_records,
            newly_duplicate_records=ver_b.duplicate_records - ver_a.duplicate_records,
            newly_quarantined_records=ver_b.quarantined_records - ver_a.quarantined_records,
            geographic_changes=geo_changes,
            quality_metric_changes={
                "checksum_changed": ver_a.dataset_checksum_sha256 != ver_b.dataset_checksum_sha256,
                "ml_eligibility_changed": ver_a.is_ml_eligible != ver_b.is_ml_eligible,
            },
            comparison_summary=(
                f"Compared {ver_a.semver_tag} -> {ver_b.semver_tag}: +{len(added)} added, -{len(removed)} removed, "
                f"net change of {ver_b.verified_records - ver_a.verified_records} verified empirical records."
            ),
        )

    def export_ml_training_manifest(
        self,
        version_id: str,
        user_id: str = "SYSTEM",
        user_role: str = "ADMIN",
    ) -> MLExportManifest:
        """Export ML-ready empirical training records strictly respecting governance and readiness gates."""
        version = self.db.query(DatasetVersionModel).filter(DatasetVersionModel.id == version_id).first()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset version not found.")

        parent_dataset = self.db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == version.dataset_id).first()

        from app.services.audit_service import (
            EVENT_DATASET_EXPORT_ACCESSED,
            EVENT_DATASET_EXPORT_BLOCKED,
        )

        # Objective 9: Prevent unauthorized dataset exports
        # Gate 1: Check Version Approval Status
        if version.approval_status != "APPROVED":
            record_audit_event(
                db=self.db,
                event_type=EVENT_DATASET_EXPORT_BLOCKED,
                actor_id=user_id,
                actor_role=user_role,
                payload={
                    "version_id": version.id,
                    "semver_tag": version.semver_tag,
                    "reason": f"Dataset version approval status is '{version.approval_status}' (must be 'APPROVED')",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Institutional Export Blocked: Dataset version '{version.semver_tag}' is in "
                    f"'{version.approval_status}' state. Only 'APPROVED' dataset versions can be exported."
                ),
            )

        # Gate 2: Check Parent Dataset Approval Status
        if parent_dataset and parent_dataset.approval_status != "APPROVED":
            record_audit_event(
                db=self.db,
                event_type=EVENT_DATASET_EXPORT_BLOCKED,
                actor_id=user_id,
                actor_role=user_role,
                payload={
                    "version_id": version.id,
                    "dataset_id": parent_dataset.id,
                    "reason": f"Parent dataset approval status is '{parent_dataset.approval_status}' (must be 'APPROVED')",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Institutional Export Blocked: Parent dataset '{parent_dataset.name}' has approval status "
                    f"'{parent_dataset.approval_status}'. Both parent dataset and version snapshot must be approved."
                ),
            )

        # Gate 3: Explicit ML Licensing & Purpose Limitation (Phase 4B-7B)
        from app.services.policy_service import DataPolicyService
        if parent_dataset:
            is_ml_authorized, purpose_reason = DataPolicyService.verify_dataset_and_source_for_ml(
                db=self.db,
                dataset=parent_dataset,
                version=version,
                required_purpose="MODEL_TRAINING",
            )
            if not is_ml_authorized:
                record_audit_event(
                    db=self.db,
                    event_type=EVENT_DATASET_EXPORT_BLOCKED,
                    actor_id=user_id,
                    actor_role=user_role,
                    payload={
                        "version_id": version.id,
                        "dataset_id": parent_dataset.id,
                        "reason": purpose_reason,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Institutional Export Blocked by Licensing Policy: {purpose_reason}",
                )

        # Gate 4: Invariant - Minimum 1,000 Verified Empirical Deed Transactions
        if not version.is_ml_eligible and version.verified_records < 1000:
            record_audit_event(
                db=self.db,
                event_type=EVENT_DATASET_EXPORT_BLOCKED,
                actor_id=user_id,
                actor_role=user_role,
                payload={
                    "version_id": version.id,
                    "semver_tag": version.semver_tag,
                    "verified_records": version.verified_records,
                    "reason": "Insufficient verified empirical records (< 1,000 threshold)",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"ML Export Gated: Version '{version.semver_tag}' has {version.verified_records} verified records. "
                    f"A minimum of 1,000 verified empirical deed transactions is required."
                ),
            )

        # Retrieve verified transactions in this version snapshot
        tx_ids = version.included_transaction_ids or []
        transactions = (
            self.db.query(ImportedTransactionModel)
            .filter(
                ImportedTransactionModel.id.in_(tx_ids),
                ImportedTransactionModel.is_verified_deed == True,
                ImportedTransactionModel.is_asking_price == False,
            )
            .order_by(ImportedTransactionModel.transaction_date.asc())
            .all()
        )

        records_payload = []
        for tx in transactions:
            records_payload.append({
                "transaction_id": tx.id,
                "registration_date": tx.transaction_date.isoformat(),
                "transaction_quarter": tx.transaction_quarter,
                "city": tx.city,
                "locality": tx.locality,
                "property_type": tx.property_type,
                "carpet_area_sqft": tx.carpet_area_sqft,
                "transaction_price": tx.transaction_price,
                "price_per_sqft": tx.price_per_sqft,
                "guideline_rate_per_sqft": tx.guideline_rate_per_sqft,
                "latitude": tx.latitude,
                "longitude": tx.longitude,
                "fingerprint_hash": tx.fingerprint_hash,
            })

        feature_cols = [
            "carpet_area_sqft", "guideline_rate_per_sqft", "city",
            "locality", "property_type", "transaction_quarter"
        ]

        # Record successful authorized export audit event (Objective 10)
        record_audit_event(
            db=self.db,
            event_type=EVENT_DATASET_EXPORT_ACCESSED,
            actor_id=user_id,
            actor_role=user_role,
            payload={
                "version_id": version.id,
                "semver_tag": version.semver_tag,
                "dataset_checksum_sha256": version.dataset_checksum_sha256,
                "eligible_record_count": len(records_payload),
            },
        )
        self.db.commit()

        return MLExportManifest(
            dataset_version_id=version.id,
            semver_tag=version.semver_tag,
            export_timestamp=datetime.now(timezone.utc),
            eligible_record_count=len(records_payload),
            checksum_sha256=version.dataset_checksum_sha256,
            feature_columns=feature_cols,
            target_column="transaction_price",
            temporal_split_summary={
                "train_pct": 70,
                "val_pct": 15,
                "test_pct": 15,
                "first_deed": records_payload[0]["registration_date"] if records_payload else None,
                "last_deed": records_payload[-1]["registration_date"] if records_payload else None,
            },
            records=records_payload,
        )

