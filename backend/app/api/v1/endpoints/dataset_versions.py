"""API endpoints for dataset versions, snapshots, comparisons, and ML training exports."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import (
    require_roles,
    UserSession,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
)
from app.models.dataset_version import DatasetVersionModel
from app.schemas.dataset_version import (
    DatasetVersionCreate,
    DatasetVersionResponse,
    DatasetVersionApprovalRequest,
    DatasetComparisonResponse,
    MLExportManifest,
)
from app.dataset_management.version_service import DatasetVersionService

router = APIRouter()


@router.get(
    "/versions",
    response_model=List[DatasetVersionResponse],
    summary="List Dataset Versions",
)
def list_dataset_versions(
    dataset_id: Optional[str] = Query(None, description="Filter by parent dataset ID"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    query = db.query(DatasetVersionModel)
    if dataset_id:
        query = query.filter(DatasetVersionModel.dataset_id == dataset_id)
    return query.order_by(desc(DatasetVersionModel.created_at)).all()


@router.post(
    "/versions",
    response_model=DatasetVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Immutable Dataset Version Snapshot",
)
def create_version_snapshot(
    req: DatasetVersionCreate,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    service = DatasetVersionService(db)
    return service.create_version_snapshot(
        dataset_id=req.dataset_id,
        semver_tag=req.semver_tag,
        version_title=req.version_title,
        created_by=user.username,
        description=req.description,
    )


@router.put(
    "/versions/{version_id}/approve",
    response_model=DatasetVersionResponse,
    summary="Approve or Deprecate Dataset Version (Admin / Chief Underwriter)",
)
def approve_version(
    version_id: str,
    req: DatasetVersionApprovalRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN])),
):
    service = DatasetVersionService(db)
    return service.approve_dataset_version(
        version_id=version_id,
        approval_status=req.approval_status,
        approver_id=user.username,
        notes=req.approval_notes,
    )


@router.get(
    "/versions/compare",
    response_model=DatasetComparisonResponse,
    summary="Compare Two Dataset Version Snapshots",
)
def compare_dataset_versions(
    version_a_id: str = Query(..., description="Source version ID"),
    version_b_id: str = Query(..., description="Target version ID"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    service = DatasetVersionService(db)
    return service.compare_versions(version_a_id, version_b_id)


@router.get(
    "/versions/{version_id}/export-ml",
    response_model=MLExportManifest,
    summary="Export Verified Empirical Records for ML Feature Store",
)
def export_ml_dataset(
    version_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_SENIOR_UNDERWRITER, ROLE_ADMIN])),
):
    service = DatasetVersionService(db)
    return service.export_ml_training_manifest(
        version_id=version_id,
        user_id=user.username,
        user_role=user.role,
    )

