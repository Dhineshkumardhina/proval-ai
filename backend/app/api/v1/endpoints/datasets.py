"""Datasets and Real Estate Transaction Ingestion API endpoints."""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_roles,
    UserSession,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
)
from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
    DataQualityReportModel,
)
from app.schemas.dataset import (
    DatasetResponse,
    ImportedTransactionResponse,
    RejectedRecordResponse,
    DuplicateRecordResponse,
    DataQualityReportResponse,
    MLPreparationResponse,
)
from app.services import ingestion_service, ml_preprocessing, audit_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=DataQualityReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Ingest Transaction Dataset (CSV / Excel)",
    description="Ingest property transaction records with automatic column mapping, currency/area unit normalization, duplicate detection, and quality audit.",
)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV or Excel (.xlsx, .xls) file"),
    name: Optional[str] = Form(None, description="Dataset display name"),
    description: Optional[str] = Form(None, description="Dataset description"),
    sourceType: str = Form(default="user_upload", description="Source classification"),
    licenseType: str = Form(default="commercial_restricted", description="Licensing classification"),
    provenance: Optional[str] = Form(None, description="Detailed source provenance documentation"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    """Upload and ingest a real estate dataset."""
    # Path traversal & null byte injection protection
    raw_name = file.filename or "uploaded_dataset.csv"
    if "\x00" in raw_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious filename rejected: null byte detected.",
        )
    import re
    cleaned_name = os.path.basename(raw_name.replace("\\", "/"))
    filename = re.sub(r"[^a-zA-Z0-9_\-\. ]", "_", cleaned_name)

    # File extension whitelist guard
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}",
        )

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Size limit guard (25MB)
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum upload limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # MIME validation and Magic Bytes guard
    if ext == ".xlsx" and not contents.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MIME validation failure: File format does not match valid Excel (.xlsx) OpenXML archive.",
        )
    elif ext == ".xls" and not contents.startswith(b"\xd0\xcf\x11\xe0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MIME validation failure: File format does not match valid Excel 97-2004 (.xls) compound binary.",
        )
    elif ext == ".csv":
        if b"\x00" in contents[:4096]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MIME validation failure: CSV file contains invalid null byte binary data.",
            )
        try:
            contents[:4096].decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MIME validation failure: CSV file contains invalid non-text binary data.",
            )

    try:
        metadata = {
            "name": name or filename,
            "description": description or f"Imported transaction file {filename}",
            "sourceType": sourceType,
            "licenseType": licenseType,
            "provenance": provenance or f"Uploaded by {user.name} ({user.role})",
        }

        dataset, report = ingestion_service.ingest_dataset(
            db=db,
            file_bytes=contents,
            filename=filename,
            metadata=metadata,
        )

        validity_pct = round((report.valid_records / max(1, report.total_records)) * 100.0, 1)

        # Record dataset ingestion event in tamper-evident audit trail
        audit_service.record_audit_event(
            db=db,
            event_type=audit_service.EVENT_DATASET_INGESTED,
            actor_id=user.username,
            actor_role=user.role,
            case_id=None,
            payload={
                "datasetId": dataset.id,
                "datasetName": dataset.name,
                "filename": filename,
                "totalRecords": report.total_records,
                "validRecords": report.valid_records,
                "rejectedRecords": report.rejected_records,
                "sourceType": dataset.source_type,
                "licenseType": dataset.license_type,
            },
        )

        return DataQualityReportResponse(
            datasetId=dataset.id,
            datasetName=dataset.name,
            totalRecords=report.total_records,
            validRecords=report.valid_records,
            rejectedRecords=report.rejected_records,
            duplicateRecords=report.duplicate_records,
            validityRatePct=validity_pct,
            missingValuePercentages=report.missing_value_percentages,
            geographicDistribution=report.geographic_distribution,
            propertyTypeDistribution=report.property_type_distribution,
            priceMetrics=report.price_metrics,
            temporalDistribution=report.temporal_distribution,
            meetsMlCriteria=report.meets_ml_criteria,
            readinessSummary=report.readiness_summary,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dataset ingestion failed: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[DatasetResponse],
    summary="List Ingested Datasets",
    description="Retrieve all cataloged property datasets with row counts and status.",
)
def list_datasets(
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """List datasets."""
    datasets = db.query(DatasetMetadataModel).order_by(desc(DatasetMetadataModel.created_at)).all()
    results = []
    for d in datasets:
        results.append(
            DatasetResponse(
                id=d.id,
                name=d.name,
                description=d.description,
                sourceType=d.source_type,
                licenseType=d.license_type,
                dataSourceProvenance=d.data_source_provenance,
                fileFormat=d.file_format,
                originalFilename=d.original_filename,
                fileHashSha256=d.file_hash_sha256,
                totalRows=d.total_rows,
                validRows=d.valid_rows,
                rejectedRows=d.rejected_rows,
                duplicateRows=d.duplicate_rows,
                status=d.status,
                isUsableForMl=d.is_usable_for_ml,
                createdAt=d.created_at,
            )
        )
    return results


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get Dataset Details",
)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Get single dataset metadata."""
    d = db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == dataset_id).first()
    if not d:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return DatasetResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        sourceType=d.source_type,
        licenseType=d.license_type,
        dataSourceProvenance=d.data_source_provenance,
        fileFormat=d.file_format,
        originalFilename=d.original_filename,
        fileHashSha256=d.file_hash_sha256,
        totalRows=d.total_rows,
        validRows=d.valid_rows,
        rejectedRows=d.rejected_rows,
        duplicateRows=d.duplicate_rows,
        status=d.status,
        isUsableForMl=d.is_usable_for_ml,
        createdAt=d.created_at,
    )


@router.get(
    "/{dataset_id}/records",
    response_model=List[ImportedTransactionResponse],
    summary="Get Valid Normalized Transactions",
)
def get_dataset_records(
    dataset_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve normalized valid records from dataset."""
    records = (
        db.query(ImportedTransactionModel)
        .filter(ImportedTransactionModel.dataset_id == dataset_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        ImportedTransactionResponse(
            id=r.id,
            datasetId=r.dataset_id,
            rowIndex=r.row_index,
            city=r.city,
            locality=r.locality,
            subMarket=r.sub_market,
            pincode=r.pincode,
            projectName=r.project_name,
            unitNumber=r.unit_number,
            propertyType=r.property_type,
            transactionType=r.transaction_type,
            transactionDate=r.transaction_date,
            transactionQuarter=r.transaction_quarter,
            carpetAreaSqFt=r.carpet_area_sqft,
            superBuiltUpAreaSqFt=r.super_built_up_area_sqft,
            floorNo=r.floor_no,
            totalFloors=r.total_floors,
            transactionPrice=r.transaction_price,
            pricePerSqFt=r.price_per_sqft,
            guidelineRatePerSqFt=r.guideline_rate_per_sqft,
            deviationFromGuidelinePct=r.deviation_from_guideline_pct,
            latitude=r.latitude,
            longitude=r.longitude,
            isVerifiedDeed=r.is_verified_deed,
            dataSource=r.data_source,
        )
        for r in records
    ]


@router.get(
    "/{dataset_id}/rejected",
    response_model=List[RejectedRecordResponse],
    summary="Get Rejected Records with Failure Reasons",
)
def get_rejected_records(
    dataset_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve rejected records with diagnostic failure codes."""
    records = (
        db.query(RejectedRecordModel)
        .filter(RejectedRecordModel.dataset_id == dataset_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        RejectedRecordResponse(
            id=r.id,
            datasetId=r.dataset_id,
            rowIndex=r.row_index,
            rejectionReason=r.rejection_reason,
            rejectionCode=r.rejection_code,
            rawData=r.raw_data,
            createdAt=r.created_at,
        )
        for r in records
    ]


@router.get(
    "/{dataset_id}/duplicates",
    response_model=List[DuplicateRecordResponse],
    summary="Get Flagged Duplicate Records",
)
def get_duplicate_records(
    dataset_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve duplicate records flagged by fingerprint hashing."""
    records = (
        db.query(DuplicateRecordModel)
        .filter(DuplicateRecordModel.dataset_id == dataset_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        DuplicateRecordResponse(
            id=r.id,
            datasetId=r.dataset_id,
            rowIndex=r.row_index,
            fingerprintHash=r.fingerprint_hash,
            matchedTransactionId=r.matched_transaction_id,
            rawData=r.raw_data,
            createdAt=r.created_at,
        )
        for r in records
    ]


@router.get(
    "/{dataset_id}/readiness",
    response_model=DataQualityReportResponse,
    summary="Get Dataset Quality & ML Readiness Assessment",
)
def get_dataset_readiness(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Retrieve data quality and readiness report."""
    report = (
        db.query(DataQualityReportModel)
        .filter(DataQualityReportModel.dataset_id == dataset_id)
        .order_by(desc(DataQualityReportModel.created_at))
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail=f"No quality report found for dataset '{dataset_id}'.")

    dataset = db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == dataset_id).first()
    validity_pct = round((report.valid_records / max(1, report.total_records)) * 100.0, 1)

    return DataQualityReportResponse(
        datasetId=dataset_id,
        datasetName=dataset.name if dataset else "Dataset",
        totalRecords=report.total_records,
        validRecords=report.valid_records,
        rejectedRecords=report.rejected_records,
        duplicateRecords=report.duplicate_records,
        validityRatePct=validity_pct,
        missingValuePercentages=report.missing_value_percentages,
        geographicDistribution=report.geographic_distribution,
        propertyTypeDistribution=report.property_type_distribution,
        priceMetrics=report.price_metrics,
        temporalDistribution=report.temporal_distribution,
        meetsMlCriteria=report.meets_ml_criteria,
        readinessSummary=report.readiness_summary,
    )


@router.post(
    "/{dataset_id}/prepare-ml",
    response_model=MLPreparationResponse,
    summary="Execute Preprocessing & Out-of-Time Train/Val/Test Split",
    description="Partition dataset into temporal Out-of-Time (OOT) train/validation/test sets and spatial clusters preventing data leakage.",
)
def prepare_ml_dataset(
    dataset_id: str,
    trainRatio: float = Query(default=0.70, ge=0.5, le=0.9),
    valRatio: float = Query(default=0.15, ge=0.05, le=0.3),
    testRatio: float = Query(default=0.15, ge=0.05, le=0.3),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    """Execute ML preparation partitioning."""
    return ml_preprocessing.prepare_ml_split(
        db=db,
        dataset_id=dataset_id,
        train_ratio=trainRatio,
        val_ratio=valRatio,
        test_ratio=testRatio,
    )

