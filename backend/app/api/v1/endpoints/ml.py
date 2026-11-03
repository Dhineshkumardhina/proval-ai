"""FastAPI endpoints for ML valuation, pre-training gate audit, benchmarks, and SHAP explainability."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    UserSession,
    get_current_user,
    require_roles,
    ROLE_ADMIN,
    ROLE_SENIOR_UNDERWRITER,
)
from app.models.ml_model import MLModelRegistryModel
from app.schemas.ml import (
    MLModelStatusResponse,
    MLModelSummaryResponse,
    MLPredictionRequest,
    MLPredictionResponse,
    MLTrainingGateAuditResponse,
    MLTrainingRequest,
    SHAPFeatureContribution,
)
from app.ml.readiness_gate import evaluate_training_gate
from app.ml.trainer import train_valuation_model
from app.ml.model_service import ml_model_service
from app.ml.preprocessing import build_feature_vector
from app.ml.explainability import explain_catboost_prediction

router = APIRouter(prefix="/ml", tags=["Machine Learning Valuation Engine"])


@router.get(
    "/status",
    response_model=MLModelStatusResponse,
    summary="Get ML Engine & Training Gate Status",
    description="Check whether a trained ML model is actively serving predictions, or whether the system is operating in rule-based mode.",
)
def get_ml_status(db: Session = Depends(get_db)):
    """Retrieve real-time ML subsystem status and readiness."""
    return ml_model_service.get_ml_status(db)


@router.get(
    "/gate-check/{dataset_id}",
    response_model=MLTrainingGateAuditResponse,
    summary="Evaluate Pre-Training Gate on Dataset",
    description="Inspect whether an ingested dataset passes the strict 1,000-record threshold, geographic diversity, and non-synthetic criteria.",
)
def check_training_gate(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Run pre-training readiness gate audit."""
    return evaluate_training_gate(db, dataset_id)


@router.post(
    "/train",
    response_model=MLModelSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger ML Model Training (Strictly Gated)",
    description="Train CatBoost and benchmark models on an authentic ingested dataset. Training is strictly blocked if sample size < 1,000 or provenance is synthetic.",
)
def trigger_training(
    req: MLTrainingRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(require_roles([ROLE_ADMIN, ROLE_SENIOR_UNDERWRITER])),
):
    """Attempt ML model training. Rejects execution if readiness criteria are not met."""
    model_record = train_valuation_model(
        db=db,
        dataset_id=req.datasetId,
        algorithm=req.algorithm,
        user_name=f"{user.name} ({user.role})",
    )

    return MLModelSummaryResponse(
        id=model_record.id,
        version=model_record.version,
        algorithm=model_record.algorithm,
        datasetId=model_record.dataset_id,
        metrics=model_record.metrics,
        benchmarkComparisons=model_record.benchmark_comparisons,
        featureNames=model_record.feature_names,
        status=model_record.status,
        isProductionReady=model_record.is_production_ready,
        trainingRecordsCount=model_record.training_records_count,
        testRecordsCount=model_record.test_records_count,
        trainedAt=model_record.trained_at,
    )


@router.get(
    "/models",
    response_model=List[MLModelSummaryResponse],
    summary="List ML Model Registry & Benchmarks",
    description="Retrieve catalog of trained models, candidate models, and blocked training attempts.",
)
def list_models(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """List model versions in the registry."""
    query = db.query(MLModelRegistryModel).order_by(MLModelRegistryModel.created_at.desc())
    if status_filter:
        query = query.filter(MLModelRegistryModel.status == status_filter.upper())
    models = query.all()

    return [
        MLModelSummaryResponse(
            id=m.id,
            version=m.version,
            algorithm=m.algorithm,
            datasetId=m.dataset_id,
            metrics=m.metrics,
            benchmarkComparisons=m.benchmark_comparisons,
            featureNames=m.feature_names,
            status=m.status,
            isProductionReady=m.is_production_ready,
            trainingRecordsCount=m.training_records_count,
            testRecordsCount=m.test_records_count,
            trainedAt=m.trained_at,
        )
        for m in models
    ]


@router.post(
    "/predict",
    response_model=MLPredictionResponse,
    summary="Predict Property Valuation (ML or Fallback)",
    description="Generate a valuation estimate. Uses CatBoost + SHAP if an active model exists; otherwise transparently falls back to statutory rule-based estimation. Requires authentication.",
)
def predict_valuation(
    req: MLPredictionRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Inference endpoint with transparent fallback."""
    return ml_model_service.predict(db, req)


@router.post(
    "/explain",
    response_model=List[SHAPFeatureContribution],
    summary="Generate SHAP Feature Attributions",
    description="Compute TreeSHAP contributions for an active ML model. Rejects if only rule-based engine is active. Requires authentication.",
)
def explain_features(
    req: MLPredictionRequest,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Extract local SHAP attributions. Refuses to label rule-based math as SHAP."""
    active_info = ml_model_service.get_active_model(db)
    if active_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "SHAP explanations are only available for trained Machine Learning models. "
                "The system is currently operating on the rule-based baseline engine. "
                "Rule-based calculations use statutory hedonic multipliers and must never be misrepresented as SHAP values."
            ),
        )

    _, model = active_info
    feature_row = build_feature_vector(
        city=req.city,
        locality=req.locality,
        property_type=req.propertyType,
        carpet_area_sqft=req.carpetAreaSqFt,
        floor_no=req.floorNo,
        total_floors=req.totalFloors,
        guideline_rate_per_sqft=req.guidelineRatePerSqFt,
        age_years=req.ageYears,
        transaction_quarter=req.transactionQuarter,
    )

    _, contributions = explain_catboost_prediction(model, feature_row)
    return contributions

