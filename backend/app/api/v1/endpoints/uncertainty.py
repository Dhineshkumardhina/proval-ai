"""FastAPI endpoints for statistical uncertainty quantification and conformal prediction."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserSession, get_current_user
from app.schemas.uncertainty import (
    CalibrationGateAuditResponse,
    UncertaintyPredictionRequest,
    UncertaintyPredictionResponse,
    UncertaintyStatusResponse,
)
from app.ml.calibration_gate import evaluate_calibration_gate
from app.ml.uncertainty_service import uncertainty_service

router = APIRouter(prefix="/uncertainty", tags=["Statistical Uncertainty & Conformal Prediction"])


@router.get(
    "/status",
    response_model=UncertaintyStatusResponse,
    summary="Get Conformal Calibration & Uncertainty Status",
    description="Query whether statistical prediction intervals (90%/95%) are genuinely calibrated, or whether they remain gated.",
)
def get_uncertainty_status(db: Session = Depends(get_db)):
    """Retrieve uncertainty subsystem calibration state and conceptual taxonomy."""
    return uncertainty_service.get_status(db)


@router.get(
    "/gate-check/{dataset_id}",
    response_model=CalibrationGateAuditResponse,
    summary="Audit Dataset for Conformal Calibration",
    description="Verify whether an ingested dataset qualifies as an independent holdout calibration corpus (>= 100 verified non-synthetic records).",
)
def audit_calibration_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Run calibration gate audit on a candidate dataset."""
    return evaluate_calibration_gate(db, dataset_id)


@router.post(
    "/predict",
    response_model=UncertaintyPredictionResponse,
    summary="Valuation with Conformal Prediction Intervals (or Explicit Fallback)",
    description="Generate property valuation point estimate with distribution-free prediction bounds [Lower, Upper]. Withholds intervals when calibration data is unavailable. Requires authentication.",
)
def predict_valuation_uncertainty(
    req: UncertaintyPredictionRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Generate valuation with conformal bounds or explicit uncalibrated status."""
    return uncertainty_service.predict_with_uncertainty(db, req)

