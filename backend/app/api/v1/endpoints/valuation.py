"""Institutional property valuation endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.valuation import ValuationInputParams, ValuationResponse
from app.services.valuation_service import calculate_valuation
from app.services import audit_service
from app.models.valuation import ValuationCaseModel, ValuationResultModel
from app.core.security import get_optional_current_user, UserSession

router = APIRouter()
logger = logging.getLogger("propval.api.valuation")


@router.post(
    "/estimate",
    response_model=ValuationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Institutional Property Valuation",
    description="Computes deterministic hedonic property valuation including scorecard attribution breakdown.",
)
def estimate_valuation(
    params: ValuationInputParams,
    db: Session = Depends(get_db),
    user: Optional[UserSession] = Depends(get_optional_current_user),
) -> ValuationResponse:
    """Accept validated valuation parameters, execute valuation math, and return structured result."""
    try:
        # Execute mathematical calculation
        result = calculate_valuation(params)

        # Only persist valuation result for audit tracking if an explicit valid caseId is provided
        if params.caseId:
            case_obj = db.query(ValuationCaseModel).filter(ValuationCaseModel.id == params.caseId).first()
            if not case_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Valuation case '{params.caseId}' not found.",
                )
            try:
                db_result = ValuationResultModel(
                    case_id=params.caseId,
                    engine_version=result.engineVersion,
                    engine_type=result.engineType,
                    data_source=result.dataSource,
                    carpet_area_sqft=result.carpetAreaSqFt,
                    super_built_up_area_sqft=result.superBuiltUpAreaSqFt,
                    unadjusted_rate_per_sqft=result.unadjustedRatePerSqFt,
                    rule_adjusted_rate_per_sqft=result.ruleAdjustedRatePerSqFt,
                    circle_rate_per_sqft=result.circleRatePerSqFt,
                    gross_market_value=float(result.grossMarketValue),
                    net_assessed_value=float(result.netAssessedValue),
                    distress_liquidation_value=float(result.distressLiquidationValue),
                    max_sanction_amount=float(result.maxSanctionAmount),
                    deviation_from_circle_rate_pct=result.deviationFromCircleRatePct,
                    confidence_score_pct=result.confidenceScorePct,
                    risk_tier=result.riskTier,
                    attribution_breakdown=[
                        factor.model_dump(by_alias=True) for factor in result.attributionBreakdown
                    ],
                )
                db.add(db_result)
                db.commit()

                # Record event in SHA-256 hash chain linked to this case
                actor = user.username if user else "valuation.engine"
                actor_role = user.role if user else "SYSTEM"
                audit_service.record_audit_event(
                    db=db,
                    event_type=audit_service.EVENT_VALUATION_CALCULATED,
                    actor_id=actor,
                    actor_role=actor_role,
                    case_id=params.caseId,
                    payload={
                        "case_id": params.caseId,
                        "net_assessed_value": result.netAssessedValue,
                        "max_sanction_amount": result.maxSanctionAmount,
                        "engine_type": result.engineType,
                        "risk_tier": result.riskTier,
                    },
                )
            except Exception as db_err:
                db.rollback()
                logger.warning("Audit persistence skipped: %s", str(db_err))

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Valuation calculation error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Valuation calculation could not be completed. Please verify input parameters.",
        )

