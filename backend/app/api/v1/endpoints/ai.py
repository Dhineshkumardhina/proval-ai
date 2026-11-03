"""FastAPI endpoints for AI Underwriter Assistant & Gemini Integration (Phase 2G)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, UserSession
from app.schemas.ai import (
    AIStatusResponse,
    AIExplainCaseResponse,
    RedactPreviewRequest,
    RedactPreviewResponse,
)
from app.services import case_service, audit_service
from app.services.privacy_service import redact_pii, sanitize_prompt_input, minimize_case_payload
from app.services.gemini_service import generate_underwriter_briefing

logger = logging.getLogger("propval.ai.endpoints")

router = APIRouter()


@router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="Get AI Underwriter Assistant Status",
    description="Check whether Gemini integration is active, which model is configured, and DPDP Act 2023 compliance status.",
)
def get_ai_status(
    user: UserSession = Depends(get_current_user),
) -> AIStatusResponse:
    """Return operational status of the AI Assistant."""
    has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    provider = "gemini" if (has_key and settings.ENABLE_AI_CLOUD_PROCESSING) else "deterministic_fallback"

    return AIStatusResponse(
        configured=has_key,
        model=settings.GEMINI_MODEL if has_key else "deterministic-fallback-engine",
        provider=provider,
        cloud_processing_enabled=settings.ENABLE_AI_CLOUD_PROCESSING,
        privacy_guard_active=True,
        rate_limit_per_minute=settings.GEMINI_RATE_LIMIT_PER_MINUTE,
        regulatory_framework="DPDP Act 2023 & Institutional Credit Underwriting Norms",
        disclaimer=settings.AI_DISCLAIMER_TEXT,
    )


@router.post(
    "/redact-preview",
    response_model=RedactPreviewResponse,
    summary="Preview PII Redaction",
    description="Test the DPDP Act 2023 PII scrubbing engine on arbitrary input text.",
)
def preview_pii_redaction(
    payload: RedactPreviewRequest,
    user: UserSession = Depends(get_current_user),
) -> RedactPreviewResponse:
    """Preview PII redaction and prompt sanitization."""
    redacted_text, count, detected_types = redact_pii(payload.text)
    sanitized_text, injection_flag = sanitize_prompt_input(redacted_text)
    if injection_flag and "PROMPT_INJECTION" not in detected_types:
        detected_types.append("PROMPT_INJECTION")

    return RedactPreviewResponse(
        original_length=len(payload.text),
        redacted_text=sanitized_text,
        redactions_count=count + (1 if injection_flag else 0),
        redaction_types=detected_types,
    )


@router.post(
    "/explain-case/{case_id}",
    response_model=AIExplainCaseResponse,
    summary="Generate AI Underwriter Briefing for Case",
    description="Synthesize an executive collateral briefing. Strictly enforces evidence grounding and zero value fabrication.",
)
async def explain_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: UserSession = Depends(get_current_user),
) -> AIExplainCaseResponse:
    """Generate underwriter briefing for a collateral case."""
    case_obj = case_service.get_case_by_id(db, case_id)
    if not case_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation case '{case_id}' not found.",
        )

    # Format notes from audit notes
    notes_list = []
    if case_obj.auditNotes:
        for n in case_obj.auditNotes:
            note_content = n.note if hasattr(n, "note") else str(n)
            notes_list.append(note_content)
    combined_notes = " ".join(notes_list)

    property_data = {
        "property_type": case_obj.propertyType,
        "city": case_obj.city,
        "micro_market": case_obj.locality,
        "sub_market": case_obj.projectName,
        "pincode": case_obj.pincode,
        "super_built_up_area": case_obj.superBuiltUpAreaSqFt,
        "carpet_area": case_obj.carpetAreaSqFt,
        "floor": case_obj.floorNo,
        "total_floors": case_obj.totalFloors,
        "age_of_property": case_obj.ageYears,
        "circle_rate_sqft": case_obj.circleRatePerSqFt,
        "road_width_ft": case_obj.roadWidthFt,
    }

    latest_val = case_obj.latestValuation
    base_price = (
        getattr(latest_val, "ruleAdjustedRatePerSqFt", None)
        or getattr(latest_val, "unadjustedRatePerSqFt", None)
        or case_obj.baseMarketRatePerSqFt
        or 0.0
    )
    valuation_result = {
        "engine_type": latest_val.engineType if latest_val else "provisional rule-based estimation",
        "base_price_sqft": base_price,
        "final_valuation_amount": latest_val.netAssessedValue if latest_val else 0,
        "haircut_pct": case_obj.underwriterHaircutPct,
        "liquidation_value": latest_val.distressLiquidationValue if latest_val else 0,
        "sanction_recommendation": latest_val.maxSanctionAmount if latest_val else 0,
        "confidence_score": latest_val.confidenceScorePct if latest_val else 0,
        "risk_tier": latest_val.riskTier if latest_val else "STANDARD",
        "scorecard": {
            "quality_tier": "B" if (case_obj.ageYears or 0) > 5 else "A",
            "spatial_tier": "Prime" if (case_obj.roadWidthFt or 0) >= 40 else "Standard",
            "legal_tier": case_obj.encumbranceStatus or "Standard",
        },
        "model_governance_provenance": "PROVISIONAL_RULE_BASED_PENDING_TRAINING_DATA",
    }

    comps_list = []
    if case_obj.comparables:
        for comp in case_obj.comparables:
            if hasattr(comp, "model_dump"):
                comps_list.append(comp.model_dump())
            elif isinstance(comp, dict):
                comps_list.append(comp)

    case_data = {
        "id": case_obj.id,
        "status": case_obj.status,
        "notes": combined_notes,
    }

    # Minimize payload and scrub any PII compliant with DPDP Act 2023
    minimized_payload = minimize_case_payload(
        case_data=case_data,
        property_data=property_data,
        valuation_result=valuation_result,
        comparables=comps_list,
    )

    # Synthesize briefing (Gemini if key exists, or deterministic fallback)
    response = await generate_underwriter_briefing(
        case_payload=minimized_payload,
        db_session=db,
    )

    # Record AI explanation generation in SHA-256 audit chain
    audit_service.record_audit_event(
        db=db,
        event_type=audit_service.EVENT_AI_EXPLANATION_GENERATED,
        actor_id=user.username,
        actor_role=user.role,
        case_id=case_id,
        payload={
            "case_id": case_id,
            "provider": response.provider,
            "model_name": response.model_name,
            "pii_redacted_count": response.pii_redacted_count,
            "status": response.status,
        },
    )

    return response
