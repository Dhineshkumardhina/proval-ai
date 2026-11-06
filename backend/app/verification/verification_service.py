"""Service coordinating record verification, quarantine routing, and provenance certification."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
)
from app.models.verification import (
    QuarantinedRecordModel,
    VerificationEvidenceModel,
    TransactionLifecycleState,
)
from app.normalization.models import NormalizedTransactionRecord
from app.verification.anomaly_detector import TransactionAnomalyDetector
from app.verification.duplicate_detector import compute_deterministic_deed_hash, calculate_property_similarity

logger = logging.getLogger("propval.verification")


class VerificationEngine:
    """Evaluates normalized records against empirical authenticity and anomaly rules."""

    def __init__(self, db: Session, verifier_id: str = "SYSTEM_VERIFIER"):
        self.db = db
        self.verifier_id = verifier_id

    def verify_and_route_record(
        self,
        dataset: DatasetMetadataModel,
        norm_tx: NormalizedTransactionRecord,
        row_index: int,
    ) -> Tuple[str, Optional[Any]]:
        """Transition normalized record into VERIFIED, QUARANTINED, or DUPLICATE.

        Returns:
            (status_string, saved_model_instance)
        """
        # 1. Deterministic SRO Duplicate Defense
        existing_tx = (
            self.db.query(ImportedTransactionModel)
            .filter(ImportedTransactionModel.fingerprint_hash == norm_tx.fingerprint_hash)
            .first()
        )
        if existing_tx:
            dup = DuplicateRecordModel(
                dataset_id=dataset.id,
                row_index=row_index,
                fingerprint_hash=norm_tx.fingerprint_hash,
                matched_transaction_id=existing_tx.id,
                raw_data=norm_tx.raw_payload,
            )
            self.db.add(dup)
            return "DUPLICATE", dup

        # 2. Anomaly & Outlier Inspection
        verdict = TransactionAnomalyDetector.inspect(norm_tx.model_dump(mode="json"))
        if verdict.is_anomalous:
            # Route to Quarantine
            quarantine = QuarantinedRecordModel(
                dataset_id=dataset.id,
                row_index=row_index,
                quarantine_code=verdict.quarantine_code or "ANOMALY_DETECTED",
                quarantine_reason=verdict.quarantine_reason or "Statistical / physical anomaly flagged",
                anomaly_score=verdict.anomaly_score,
                anomalous_fields=verdict.anomalous_fields,
                raw_payload=norm_tx.raw_payload,
                resolution_status="PENDING_REVIEW",
            )
            self.db.add(quarantine)
            return "QUARANTINED", quarantine

        # 3. Source Authenticity & ML Eligibility Check
        # Synthetic demos, test harness, or mock adapters CANNOT be verified as empirical deeds
        is_empirical = True
        src_tag = f"{(norm_tx.source_id or '')}|{(norm_tx.source_reference or '')}|{(dataset.source_type or '')}".upper()
        if "MOCK" in src_tag or "SRC_E2E" in src_tag or "TEST" in src_tag or "SIMULATION" in src_tag or dataset.source_type == "synthetic_benchmark":
            is_empirical = False

        # 4. Save to Imported Transactions as VERIFIED
        tx = ImportedTransactionModel(
            dataset_id=dataset.id,
            row_index=row_index,
            fingerprint_hash=norm_tx.fingerprint_hash,
            city=norm_tx.district,
            locality=norm_tx.locality,
            sub_market=norm_tx.sub_district,
            pincode=norm_tx.postal_code,
            project_name=norm_tx.project_name,
            unit_number=norm_tx.unit_number,
            property_type=norm_tx.property_type,
            transaction_type=norm_tx.transaction_type,
            transaction_date=norm_tx.registration_date,
            transaction_quarter=norm_tx.transaction_quarter,
            carpet_area_sqft=norm_tx.carpet_area_sqft,
            built_up_area_sqft=norm_tx.built_up_area_sqft,
            super_built_up_area_sqft=norm_tx.super_built_up_area_sqft,
            transaction_price=norm_tx.transaction_amount,
            price_per_sqft=norm_tx.price_per_sqft,
            guideline_rate_per_sqft=norm_tx.guideline_rate_per_sqft,
            deviation_from_guideline_pct=norm_tx.deviation_from_guideline_pct,
            latitude=norm_tx.latitude,
            longitude=norm_tx.longitude,
            original_latitude=norm_tx.original_latitude,
            original_longitude=norm_tx.original_longitude,
            precision_digits=norm_tx.coordinate_precision_digits,
            survey_number=norm_tx.cadastral.survey_number if norm_tx.cadastral else None,
            village_name=norm_tx.cadastral.revenue_village if norm_tx.cadastral else None,
            taluka_tehsil=norm_tx.sub_district,
            sro_jurisdiction_code=norm_tx.sro_office,
            cadastral_parcel_id=f"{norm_tx.state[:2].upper()}-{norm_tx.district[:3].upper()}-{norm_tx.cadastral.survey_number}" if (norm_tx.cadastral and norm_tx.cadastral.survey_number) else None,
            spatial_accuracy_tier="PARCEL_SURVEY_RECORDED" if (norm_tx.cadastral and norm_tx.cadastral.survey_number) else "COORDINATE_BOUNDED",
            is_verified_deed=is_empirical,
            is_asking_price=False,
            data_source=norm_tx.source_id,
            raw_data=norm_tx.raw_payload,
        )
        self.db.add(tx)
        self.db.flush()

        # 5. Persist Cryptographic Verification Evidence
        canonical_norm_str = json.dumps(
            norm_tx.model_dump(mode="json", exclude={"raw_payload"}),
            sort_keys=True,
            separators=(",", ":"),
        )
        norm_hash = hashlib.sha256(canonical_norm_str.encode("utf-8")).hexdigest()

        evidence = VerificationEvidenceModel(
            transaction_id=tx.id,
            verification_status=TransactionLifecycleState.VERIFIED if is_empirical else "PROVISIONAL_NON_ML",
            verifier_id=self.verifier_id,
            verifier_method="B2B_SRO_ATTESTATION" if is_empirical else "TEST_HARNESS_SIMULATION",
            source_origin=norm_tx.source_id,
            source_document_ref=norm_tx.registration_reference,
            original_record_hash=norm_tx.original_record_hash,
            normalized_record_hash=norm_hash,
            dataset_version=norm_tx.dataset_version,
            verification_evidence_details={
                "fingerprint_hash": norm_tx.fingerprint_hash,
                "sro_office": norm_tx.sro_office,
                "price_per_sqft": norm_tx.price_per_sqft,
                "guideline_deviation": norm_tx.deviation_from_guideline_pct,
                "is_ml_eligible": is_empirical,
            },
        )
        self.db.add(evidence)
        self.db.flush()

        return "VERIFIED", tx

