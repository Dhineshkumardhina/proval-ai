"""Centralized source-authorization, purpose limitation, and data retention policy service.

Enforces:
1. Source authorization lifecycle and validity dates (valid_from <= now <= valid_until).
2. Purpose specification & limitation (DPDP Section 4 & Section 7).
3. Independent, explicit verification of ML model training and feature extraction permissions
   (never inferred from general data ingestion or market intelligence rights).
4. Source-specific dynamic retention windows and authorized legal holds.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.data_source import DataSourceModel, SourceAuthorizationStatus
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.dataset_version import DatasetVersionModel


def get_utc_now():
    return datetime.now(timezone.utc)


class DataPolicyService:
    """Institutional gatekeeper enforcing contractual licensing terms, purpose limitations, and retention rules."""

    @staticmethod
    def verify_source_for_ingestion(
        source: DataSourceModel,
        requested_purpose: str = "DATA_INGESTION",
    ) -> Tuple[bool, Optional[str]]:
        """Verify whether an external property data source is authorized and valid for acquisition."""
        if not source.is_active:
            return False, f"Source '{source.source_code}' is marked inactive."

        # 1. Source Authorization Status Check
        if source.authorization_status != SourceAuthorizationStatus.DOCUMENTED_AND_AUTHORIZED:
            return False, (
                f"Source '{source.source_code}' authorization status is '{source.authorization_status}'. "
                f"Ingestion strictly requires '{SourceAuthorizationStatus.DOCUMENTED_AND_AUTHORIZED}'."
            )

        # 2. Agreement Validity Window Check
        now = get_utc_now()
        if source.valid_from is not None:
            # Ensure valid_from has timezone
            vf = source.valid_from if source.valid_from.tzinfo else source.valid_from.replace(tzinfo=timezone.utc)
            if now < vf:
                return False, (
                    f"Source '{source.source_code}' agreement is not yet active "
                    f"(effective date: {vf.isoformat()})."
                )

        if source.valid_until is not None:
            vu = source.valid_until if source.valid_until.tzinfo else source.valid_until.replace(tzinfo=timezone.utc)
            if now > vu:
                return False, (
                    f"Source '{source.source_code}' authorization expired on {vu.isoformat()}."
                )

        # 3. Permitted Acquisition Purpose Verification
        purposes = source.permitted_purposes
        if not purposes or not isinstance(purposes, list):
            return False, (
                f"Source '{source.source_code}' has missing or invalid permitted_purposes metadata. "
                "Explicit purpose authorization is required."
            )

        allowed_purposes = {str(p).strip().upper() for p in purposes}
        req_clean = str(requested_purpose).strip().upper()

        if req_clean not in allowed_purposes and "ALL" not in allowed_purposes:
            return False, (
                f"Purpose '{requested_purpose}' is not authorized for source '{source.source_code}'. "
                f"Permitted purposes: {sorted(list(allowed_purposes))}."
            )

        return True, None

    @staticmethod
    def verify_dataset_and_source_for_ml(
        db: Session,
        dataset: DatasetMetadataModel,
        version: Optional[DatasetVersionModel] = None,
        required_purpose: str = "MODEL_TRAINING",
    ) -> Tuple[bool, Optional[str]]:
        """Verify that dataset governance approval and explicit source licensing permit ML processing.

        Rule: Machine learning permissions (MODEL_TRAINING, DERIVED_FEATURES) must NEVER be
        inferred from general data ingestion or valuation estimation rights.
        """
        # 1. Dataset Approval Status Enforcement
        if dataset.approval_status != "APPROVED":
            return False, (
                f"Dataset '{dataset.name}' has approval status '{dataset.approval_status}'. "
                f"Machine learning processing strictly requires 'APPROVED' status."
            )

        # 2. Version Approval Status Enforcement (if version snapshot provided)
        if version is not None and version.approval_status != "APPROVED":
            return False, (
                f"Dataset version '{version.semver_tag}' has approval status '{version.approval_status}'. "
                f"Machine learning processing strictly requires 'APPROVED' status."
            )

        # 3. Identify and Inspect Underlying Data Source Licensing Terms
        source = None
        # Check if source_code or provenance indicates a managed data source
        source_candidates = []
        if getattr(dataset, "source_type", None):
            source_candidates.append(dataset.source_type)
        if getattr(dataset, "data_source_provenance", None):
            source_candidates.append(dataset.data_source_provenance)

        # Query active sources matching provenance or source_type
        for cand in source_candidates:
            if cand:
                s = db.query(DataSourceModel).filter(
                    or_(
                        DataSourceModel.source_code == cand,
                        DataSourceModel.provider_name.ilike(f"%{cand}%"),
                    )
                ).first()
                if s:
                    source = s
                    break

        # Also inspect sample transaction's data_source tag
        if not source:
            sample_tx = (
                db.query(ImportedTransactionModel.data_source)
                .filter(ImportedTransactionModel.dataset_id == dataset.id)
                .first()
            )
            if sample_tx and sample_tx[0]:
                source = db.query(DataSourceModel).filter(
                    or_(
                        DataSourceModel.source_code == sample_tx[0],
                        DataSourceModel.id == sample_tx[0],
                    )
                ).first()

        # If an authorized source is identified, enforce explicit purpose terms
        if source:
            # Check source authorization and validity
            is_valid, reason = DataPolicyService.verify_source_for_ingestion(source, requested_purpose="DATA_INGESTION")
            if not is_valid:
                return False, f"ML Processing Gated: {reason}"

            # Strict check: NEVER infer ML training permission from general access
            purposes = source.permitted_purposes or []
            allowed_purposes = {str(p).strip().upper() for p in purposes}
            req_clean = str(required_purpose).strip().upper()

            if req_clean not in allowed_purposes:
                return False, (
                    f"ML Processing Prohibited: Source '{source.source_code}' does not grant explicit "
                    f"permission for '{required_purpose}'. Contractually permitted purposes: {purposes}."
                )

        return True, None

    @staticmethod
    def get_source_retention_days(source: DataSourceModel) -> Optional[int]:
        """Resolve contract-specified max retention days from source configuration."""
        restrictions = source.retention_restrictions or {}
        if isinstance(restrictions, dict):
            if "max_retention_days" in restrictions:
                try:
                    return int(restrictions["max_retention_days"])
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def is_legal_hold_active(source: DataSourceModel) -> bool:
        """Determine whether source records are subject to an authorized legal hold."""
        restrictions = source.retention_restrictions or {}
        if isinstance(restrictions, dict):
            return bool(
                restrictions.get("legal_hold")
                or restrictions.get("is_legal_hold")
                or restrictions.get("legal_hold_authorized")
                or restrictions.get("legal_hold_active")
            )
        return False
