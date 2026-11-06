"""FastAPI endpoints for Institutional Data Quality and Governance Surveillance Dashboard."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.security import (
    require_roles,
    UserSession,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
    ROLE_COMPLIANCE_AUDITOR,
    ROLE_ADMIN,
)
from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
    DataQualityReportModel,
)
from app.models.dataset_version import DatasetVersionModel
from app.models.data_source import DataSourceModel, IngestionJobModel
from app.models.verification import (
    QuarantinedRecordModel,
    VerificationEvidenceModel,
    TransactionLifecycleState,
)
from app.schemas.governance_dashboard import (
    InstitutionalGovernanceDashboardResponse,
    SourceDistributionItem,
    GeographicDistributionItem,
    CityDistributionItem,
    MissingDataStatisticItem,
    IngestionJobStatusItem,
    QuarantinedRecordReviewItem,
    DataQualityMethodology,
    MLReadinessGateSummary,
)

router = APIRouter()


@router.get(
    "/metrics",
    response_model=InstitutionalGovernanceDashboardResponse,
    summary="Get Institutional Governance & Data Quality Dashboard Metrics",
    description="Aggregated real-time metrics for data quality, verification tiers, source authorization, and ML gating.",
)
def get_governance_metrics(
    db: Session = Depends(get_db),
    user: UserSession = Depends(
        require_roles([
            ROLE_CREDIT_UNDERWRITER,
            ROLE_SENIOR_UNDERWRITER,
            ROLE_RISK_COMMITTEE_MEMBER,
            ROLE_COMPLIANCE_AUDITOR,
            ROLE_ADMIN,
        ])
    ),
):
    """Compile aggregated data quality and governance metrics strictly enforcing RBAC."""
    # 1. High-level transaction counts
    total_valid_tx = db.query(func.count(ImportedTransactionModel.id)).scalar() or 0
    total_rejected = db.query(func.count(RejectedRecordModel.id)).scalar() or 0
    total_duplicates = db.query(func.count(DuplicateRecordModel.id)).scalar() or 0
    total_quarantined = db.query(func.count(QuarantinedRecordModel.id)).scalar() or 0

    # Total ingested transactions across all pipelines
    total_ingested = total_valid_tx + total_rejected + total_duplicates + total_quarantined

    # Empirical vs Synthetic
    verified_empirical = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter(ImportedTransactionModel.is_verified_deed == True)
        .filter(ImportedTransactionModel.data_source != "synthetic-demo")
        .scalar()
        or 0
    )

    synthetic_records = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter(
            (ImportedTransactionModel.data_source == "synthetic-demo")
            | (ImportedTransactionModel.data_source == "synthetic_benchmark")
        )
        .scalar()
        or 0
    )

    # Validated records
    validated_records = total_valid_tx
    successfully_normalized = total_valid_tx

    # Awaiting verification
    awaiting_verification = max(0, total_valid_tx - verified_empirical - synthetic_records)

    # 2. Source-wise distribution
    sources = db.query(DataSourceModel).all()
    source_items: List[SourceDistributionItem] = []
    for s in sources:
        # Match data source by code or id in transactions
        src_tx_count = (
            db.query(func.count(ImportedTransactionModel.id))
            .filter(
                (ImportedTransactionModel.data_source == s.source_code)
                | (ImportedTransactionModel.data_source == s.source_name)
            )
            .scalar()
            or 0
        )
        src_emp_count = (
            db.query(func.count(ImportedTransactionModel.id))
            .filter(
                (ImportedTransactionModel.data_source == s.source_code)
                | (ImportedTransactionModel.data_source == s.source_name)
            )
            .filter(ImportedTransactionModel.is_verified_deed == True)
            .scalar()
            or 0
        )
        source_items.append(
            SourceDistributionItem(
                source_id=s.id,
                source_name=s.source_name,
                provider_name=s.provider_name,
                authorization_status=s.authorization_status,
                total_records=src_tx_count,
                verified_empirical_count=src_emp_count,
                is_active=s.is_active,
            )
        )

    # Fallback default if no sources configured yet
    if not source_items:
        source_items.append(
            SourceDistributionItem(
                source_id="src-syn-01",
                source_name="Synthetic Demonstration Deed Store",
                provider_name="PropVal Sandbox Generator",
                authorization_status="SANDBOX_ONLY",
                total_records=synthetic_records or total_valid_tx,
                verified_empirical_count=0,
                is_active=True,
            )
        )

    # 3. Geographic distribution
    geo_group = (
        db.query(
            ImportedTransactionModel.city,
            func.count(ImportedTransactionModel.id).label("cnt")
        )
        .group_by(ImportedTransactionModel.city)
        .all()
    )
    geo_items: List[GeographicDistributionItem] = []
    for city, count in geo_group:
        pct = round((count / max(1, total_valid_tx)) * 100.0, 1)
        geo_items.append(
            GeographicDistributionItem(
                state="India",
                city_count=1,
                record_count=count,
                percentage=pct,
            )
        )
    if not geo_items and total_valid_tx == 0:
        geo_items = [
            GeographicDistributionItem(state="Karnataka", city_count=1, record_count=0, percentage=0.0),
            GeographicDistributionItem(state="Maharashtra", city_count=1, record_count=0, percentage=0.0),
        ]

    # City-Wise Distribution & Locality Coverage (Phase 4C)
    city_items: List[CityDistributionItem] = []
    city_group = (
        db.query(
            ImportedTransactionModel.city,
            func.count(ImportedTransactionModel.id).label("record_count"),
            func.count(func.distinct(ImportedTransactionModel.locality)).label("locality_count"),
        )
        .group_by(ImportedTransactionModel.city)
        .order_by(desc("record_count"))
        .all()
    )
    for c_name, r_count, l_count in city_group:
        c_pct = round((r_count / max(1, total_valid_tx)) * 100.0, 1)
        city_items.append(
            CityDistributionItem(
                city=c_name,
                record_count=r_count,
                percentage=c_pct,
                locality_count=l_count,
            )
        )

    total_localities = db.query(func.count(func.distinct(ImportedTransactionModel.locality))).scalar() or 0
    verification_rate = round((verified_empirical / max(1, total_ingested)) * 100.0, 1) if total_ingested > 0 else 0.0

    # 4. Ingestion jobs
    jobs = db.query(IngestionJobModel).order_by(desc(IngestionJobModel.started_at)).limit(5).all()
    job_items: List[IngestionJobStatusItem] = []
    for j in jobs:
        job_items.append(
            IngestionJobStatusItem(
                job_id=j.id,
                source_id=j.source_id,
                status=j.status,
                trigger_mode=j.trigger_mode,
                records_fetched=j.records_fetched,
                records_normalized=j.records_normalized,
                records_rejected=j.records_rejected,
                records_duplicate=j.records_duplicate,
                started_at=j.started_at,
                completed_at=j.completed_at,
            )
        )

    # 5. Missing Data Statistics
    # Calculate missing coordinates, guideline rate, sub_market, pincode
    missing_coords = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter((ImportedTransactionModel.latitude == None) | (ImportedTransactionModel.longitude == None))
        .scalar()
        or 0
    )
    missing_guideline = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter(ImportedTransactionModel.guideline_rate_per_sqft == None)
        .scalar()
        or 0
    )
    missing_pincode = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter(ImportedTransactionModel.pincode == None)
        .scalar()
        or 0
    )
    missing_submarket = (
        db.query(func.count(ImportedTransactionModel.id))
        .filter(ImportedTransactionModel.sub_market == None)
        .scalar()
        or 0
    )

    denom = max(1, total_valid_tx)
    missing_stats = [
        MissingDataStatisticItem(
            field_name="Coordinates (Lat/Lon)",
            missing_count=missing_coords,
            missing_percentage=round((missing_coords / denom) * 100.0, 1),
            impact_level="HIGH",
        ),
        MissingDataStatisticItem(
            field_name="Guideline Rate (Circle Rate)",
            missing_count=missing_guideline,
            missing_percentage=round((missing_guideline / denom) * 100.0, 1),
            impact_level="HIGH",
        ),
        MissingDataStatisticItem(
            field_name="Sub-Market / Micro-Market",
            missing_count=missing_submarket,
            missing_percentage=round((missing_submarket / denom) * 100.0, 1),
            impact_level="MEDIUM",
        ),
        MissingDataStatisticItem(
            field_name="Postal PIN Code",
            missing_count=missing_pincode,
            missing_percentage=round((missing_pincode / denom) * 100.0, 1),
            impact_level="LOW",
        ),
    ]

    # 6. Data Quality Score and Methodology (Phase 4B-7 Corrected Formulation)
    # Completeness (40%): non-missing rates across mandatory fields
    # Validity (30%): (1 - rejected / total_ingested)
    # Uniqueness (20%): (1 - duplicates / total_ingested)
    # Consistency (10%): (1 - quarantined / total_ingested)
    if total_ingested == 0:
        completeness_score = 0.0
        validity_score = 0.0
        uniqueness_score = 0.0
        consistency_score = 0.0
        overall_score = 0.0
    else:
        validity_ratio = (total_ingested - total_rejected) / total_ingested
        uniqueness_ratio = (total_ingested - total_duplicates) / total_ingested
        consistency_ratio = (total_ingested - total_quarantined) / total_ingested
        avg_completeness = (
            1.0 - (sum(m.missing_percentage for m in missing_stats) / (len(missing_stats) * 100.0))
        ) if total_valid_tx > 0 else 0.0

        completeness_score = round(max(0.0, min(100.0, avg_completeness * 100.0)), 1)
        validity_score = round(max(0.0, min(100.0, validity_ratio * 100.0)), 1)
        uniqueness_score = round(max(0.0, min(100.0, uniqueness_ratio * 100.0)), 1)
        consistency_score = round(max(0.0, min(100.0, consistency_ratio * 100.0)), 1)

        overall_score = round(
            (completeness_score * 0.40)
            + (validity_score * 0.30)
            + (uniqueness_score * 0.20)
            + (consistency_score * 0.10),
            1,
        )

    methodology = DataQualityMethodology(
        overall_score=overall_score,
        completeness_score=completeness_score,
        validity_score=validity_score,
        uniqueness_score=uniqueness_score,
        consistency_score=consistency_score,
        formula_description="PropVal AI Internal Institutional Data Quality Index (Weighted Arithmetic Mean: Completeness 40% + Validity 30% + Uniqueness 20% + Consistency 10%)",
        weights={
            "completeness": 0.40,
            "validity": 0.30,
            "uniqueness": 0.20,
            "consistency": 0.10,
        },
        verification_disclaimer=(
            "A high data quality score certifies syntactic integrity and structural completeness; "
            "it does NOT constitute certified empirical deed verification."
        ),
    )

    # 7. ML Readiness Gate Summary
    ml_gated = verified_empirical < 1000
    ml_gate = MLReadinessGateSummary(
        is_gated=ml_gated,
        empirical_records_count=verified_empirical,
        empirical_records_threshold=1000,
        calibration_holdout_count=0,
        calibration_holdout_threshold=100,
        status_label="GATED (Pending Empirical Cohort)" if ml_gated else "ELIGIBLE",
        gate_reason=(
            f"Verification invariant: Requires ≥ 1,000 empirical deeds (Current: {verified_empirical}). "
            "Synthetic and unverified records are barred from training."
        ),
    )

    # 8. Freshness & Acquisition Dates
    latest_tx = (
        db.query(ImportedTransactionModel)
        .order_by(desc(ImportedTransactionModel.created_at))
        .first()
    )
    latest_freshness = latest_tx.created_at if latest_tx else None
    latest_acq = latest_tx.transaction_date if latest_tx else None

    # 9. Datasets & Version History
    active_datasets = db.query(func.count(DatasetMetadataModel.id)).scalar() or 0
    approved_datasets = (
        db.query(func.count(DatasetMetadataModel.id))
        .filter(DatasetMetadataModel.approval_status == "APPROVED")
        .scalar()
        or 0
    )
    version_count = db.query(func.count(DatasetVersionModel.id)).scalar() or 0

    # User Permissions Context
    can_approve = user.role in [ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN]
    can_export = user.role in [ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN]

    return InstitutionalGovernanceDashboardResponse(
        total_ingested_transactions=total_ingested,
        successfully_normalized_records=successfully_normalized,
        validated_records=validated_records,
        verified_empirical_deeds=verified_empirical,
        synthetic_and_mock_records=synthetic_records,
        duplicate_records=total_duplicates,
        rejected_records=total_rejected,
        quarantined_records=total_quarantined,
        records_awaiting_verification=awaiting_verification,
        verification_rate_pct=verification_rate,
        total_localities_covered=total_localities,
        data_quality_score=overall_score,
        quality_methodology=methodology,
        source_wise_distribution=source_items,
        geographic_distribution=geo_items,
        city_wise_distribution=city_items,
        missing_data_statistics=missing_stats,
        latest_ingestion_jobs=job_items,
        data_freshness_timestamp=latest_freshness,
        latest_acquisition_date=latest_acq,
        ml_readiness_gate=ml_gate,
        active_dataset_count=active_datasets,
        approved_dataset_count=approved_datasets,
        dataset_version_history_count=version_count,
        user_role=user.role,
        can_approve_datasets=can_approve,
        can_export_ml=can_export,
    )


@router.get(
    "/quarantine",
    response_model=List[QuarantinedRecordReviewItem],
    summary="List Quarantined Records for Underwriter Review",
)
def list_quarantined_records(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(
        require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_COMPLIANCE_AUDITOR])
    ),
):
    """Retrieve isolated anomalous records held in quarantine for forensic underwriter review."""
    # Ensure limit and offset are integers when invoked directly in unit tests
    limit_val = int(limit) if not isinstance(limit, int) else limit
    offset_val = int(offset) if not isinstance(offset, int) else offset

    records = (
        db.query(QuarantinedRecordModel)
        .order_by(desc(QuarantinedRecordModel.created_at))
        .offset(offset_val)
        .limit(limit_val)
        .all()
    )
    results: List[QuarantinedRecordReviewItem] = []
    for r in records:
        anom_fields = r.anomalous_fields if isinstance(r.anomalous_fields, list) else []
        results.append(
            QuarantinedRecordReviewItem(
                id=r.id,
                dataset_id=r.dataset_id,
                row_index=r.row_index,
                quarantine_code=r.quarantine_code,
                quarantine_reason=r.quarantine_reason,
                anomaly_score=r.anomaly_score,
                anomalous_fields=anom_fields,
                resolution_status=r.resolution_status,
                created_at=r.created_at,
            )
        )
    return results


@router.post(
    "/quarantine/{quarantine_id}/resolve",
    summary="Resolve Quarantined Record (Forensic Underwriter Action)",
)
def resolve_quarantined_record(
    quarantine_id: str,
    action: str = Query(..., description="Action: RESOLVED_VERIFIED or RESOLVED_REJECTED"),
    notes: str = Query(..., description="Forensic review notes justifying the resolution"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(
        require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_COMPLIANCE_AUDITOR])
    ),
):
    """Forensic underwriter resolution of quarantined anomalous records."""
    quar = db.query(QuarantinedRecordModel).filter(QuarantinedRecordModel.id == quarantine_id).first()
    if not quar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarantined record not found.")

    if action not in ("RESOLVED_VERIFIED", "RESOLVED_REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'RESOLVED_VERIFIED' or 'RESOLVED_REJECTED'.",
        )

    quar.resolution_status = action
    quar.reviewed_by = user.username
    quar.reviewed_at = get_utc_now()
    quar.resolution_notes = notes

    record_audit_event(
        db=db,
        event_type="QUARANTINE_RECORD_RESOLVED",
        actor_id=user.username,
        actor_role=user.role,
        payload={
            "quarantine_id": quar.id,
            "dataset_id": quar.dataset_id,
            "action": action,
            "notes": notes,
        },
    )

    db.commit()
    db.refresh(quar)
    return {
        "id": quar.id,
        "resolution_status": quar.resolution_status,
        "reviewed_by": quar.reviewed_by,
        "reviewed_at": quar.reviewed_at,
        "resolution_notes": quar.resolution_notes,
    }


@router.get(
    "/erasure-requests",
    summary="List Formal DPDP Right to Erasure Requests",
)
def list_erasure_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(
        require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN, ROLE_COMPLIANCE_AUDITOR])
    ),
):
    """Retrieve historical log of formal DPDP erasure requests and execution status."""
    from app.services.erasure_service import TransactionErasureService
    records = TransactionErasureService.list_erasure_requests(db=db, limit=limit, offset=offset)
    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "dataset_id": r.dataset_id,
            "requester_id": r.requester_id,
            "requester_role": r.requester_role,
            "reason": r.reason,
            "status": r.status,
            "records_erased_summary": r.records_erased_summary,
            "legal_backup_disclaimer": r.legal_backup_disclaimer,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        }
        for r in records
    ]

