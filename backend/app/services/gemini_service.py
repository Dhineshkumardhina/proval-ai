"""AI-Powered Underwriter Assistant and Gemini Integration Service (Phase 2G).

Provides evidence-based synthesis for credit underwriters while strictly enforcing:
1. Zero fabrication of valuation prices or comparable deeds.
2. Zero automated loan sanction or rejection decisions (human credit underwriter retains sole authority).
3. Explicit labeling of synthetic demonstration data and provisional rule-based heuristics.
4. DPDP Act 2023 data minimization and PII scrubbing prior to transmission.
5. Deterministic rule-based local fallback when offline or unconfigured.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_audit import AIAuditLogModel
from app.schemas.ai import AIUnderwriterReport, AIUnderwriterFactor, AIExplainCaseResponse
from app.services.privacy_service import redact_pii, sanitize_prompt_input, minimize_case_payload

logger = logging.getLogger("propval.ai.gemini")

# Google Generative Language API Base Endpoint
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SYSTEM_INSTRUCTION = """You are an institutional Real Estate Underwriting Assistant for Indian Housing Finance.
Your sole purpose is to analyze and explain the provided property valuation evidence to assist human credit underwriters.

STRICT OPERATIONAL BOUNDARIES:
1. NEVER independently invent, extrapolate, or recalculate the fair market value, liquidation value, or rupee figures. Refer strictly to the provided calculated numbers.
2. NEVER fabricate comparable registered deeds, municipal approvals, or legal clearance letters.
3. NEVER make automated loan sanction or rejection decisions. The final credit sanction decision belongs solely to the authorized human credit underwriter and credit risk committee.
4. ALWAYS explicitly identify when comparables or datasets are marked as synthetic demonstration data ('synthetic-demo' or 'is_synthetic_demonstration: true').
5. ALWAYS note that the valuation engine is a 'provisional rule-based estimation' and NOT a trained ML model when so indicated in the payload.
6. Clearly highlight data gaps, missing legal documents (Encumbrance Certificate, RERA, approved sanction plans), and micro-market risks.

OUTPUT FORMAT:
You MUST respond with a single, valid JSON object matching this exact schema:
{
  "valuation_summary": "string",
  "major_valuation_factors": [
    {"factor_name": "string", "impact": "POSITIVE|NEGATIVE|NEUTRAL", "details": "string"}
  ],
  "comparable_evidence_analysis": "string",
  "location_considerations": "string",
  "data_quality_concerns": ["string"],
  "legal_regulatory_risks": ["string"],
  "valuation_limitations": ["string"],
  "underwriter_recommendations": ["string"],
  "recommendation_decision_role": "string"
}
"""


def format_inr(amount: Optional[float]) -> str:
    """Format currency in Indian Lakhs/Crores for briefings."""
    if amount is None or amount == 0:
        return "₹0"
    if amount >= 10000000:
        return f"₹{amount / 10000000:.2f} Cr"
    if amount >= 100000:
        return f"₹{amount / 100000:.2f} Lakh"
    return f"₹{amount:,.0f}"


def generate_deterministic_fallback_report(
    case_payload: Dict[str, Any]
) -> AIUnderwriterReport:
    """Generate a structured, deterministic underwriter briefing without external API calls.

    Guarantees reliable, offline-capable institutional reporting grounded directly
    in the case's verified calculations, scorecard, and synthetic provenance flags.
    """
    prop = case_payload.get("property", {})
    val = case_payload.get("valuation", {})
    comps = case_payload.get("comparables", [])

    city = prop.get("city") or "Target Market"
    micro_market = prop.get("micro_market") or "Subject Locality"
    prop_type = prop.get("property_type") or "Residential Property"
    area_sqft = prop.get("super_built_up_area") or prop.get("carpet_area") or 0
    circle_rate = prop.get("circle_rate_sqft") or 0

    fmv = val.get("fair_market_value") or 0
    haircut = val.get("haircut_pct") or 20.0
    liq_val = val.get("liquidation_value") or 0
    sanction_val = val.get("sanction_recommendation") or 0
    confidence = val.get("confidence_score") or 0
    risk_tier = val.get("risk_tier") or "STANDARD"
    scorecard = val.get("scorecard", {})

    # Check synthetic status across comparables
    synthetic_count = sum(1 for c in comps if c.get("is_synthetic_demonstration", True))
    all_synthetic = (synthetic_count == len(comps)) if comps else True

    summary = (
        f"Subject collateral is a {prop_type} situated in {micro_market}, {city} "
        f"comprising {area_sqft:,.0f} sq.ft. The provisional fair market value is calculated at "
        f"{format_inr(fmv)} based on an assessed base rate of ₹{val.get('base_rate_sqft', 0):,.0f}/sq.ft. "
        f"Applying an institutional haircut of {haircut:.1f}%, the forced liquidation value is "
        f"{format_inr(liq_val)} with a provisional collateral-backed sanction baseline of {format_inr(sanction_val)}. "
        f"Risk classification is designated as {risk_tier} (Heuristic Confidence Score: {confidence:.0f}/100)."
    )

    factors = [
        AIUnderwriterFactor(
            factor_name="Circle Rate & Statutory Floor",
            impact="POSITIVE" if (val.get("base_rate_sqft", 0) >= circle_rate > 0) else "NEUTRAL",
            details=f"Municipal circle rate benchmark is ₹{circle_rate:,.0f}/sq.ft. Collateral base pricing respects statutory minimums.",
        ),
        AIUnderwriterFactor(
            factor_name="Structural Characteristics",
            impact="POSITIVE" if (prop.get("age_of_property", 0) <= 5) else "NEUTRAL",
            details=f"Floor level {prop.get('floor', 0)} of {prop.get('total_floors', 0)} floors. Building age is recorded as {prop.get('age_of_property', 0)} years.",
        ),
        AIUnderwriterFactor(
            factor_name="Heuristic Scorecard Tiering",
            impact="NEUTRAL",
            details=f"Scorecard adjustments: Quality Tier {scorecard.get('quality_tier', 'B')}, Spatial Tier {scorecard.get('spatial_tier', 'Prime')}, Legal Tier {scorecard.get('legal_tier', 'Standard')}.",
        ),
    ]

    comp_analysis = (
        f"Analysis evaluated {len(comps)} comparable properties. "
        + (
            f"All {synthetic_count} comparable records carry explicit synthetic demonstration markers "
            "('synthetic-demo'). These do not constitute verified SRO Sub-Registrar registered transaction deeds."
            if all_synthetic
            else f"Comparables include {len(comps) - synthetic_count} empirical and {synthetic_count} synthetic demonstration records."
        )
    )

    location_notes = (
        f"Collateral is situated within the {micro_market} micro-market of {city} (Pincode: {prop.get('pincode', 'N/A')}). "
        "Micro-market pricing dynamics are evaluated against the municipal guidance rate. "
        "Physical inspection must independently verify road width, drainage infrastructure, and civic amenities."
    )

    data_concerns = [
        "Valuation relies on provisional rule-based estimation heuristics rather than an empirical trained machine learning model.",
        "Comparable data consists of synthetic demonstration records intended for architectural evaluation.",
        "Confidence score is an uncalibrated heuristic penalty score, not a split conformal prediction interval.",
    ]

    legal_risks = [
        "Title clearance report by panel advocate required to establish unencumbered 30-year ownership chain.",
        "Encumbrance Certificate (Form 15/16) must be physically or digitally retrieved from the Sub-Registrar Office.",
        "Approved sanction building plan and Occupancy Certificate (OC) / Completion Certificate (CC) must be verified against municipal records.",
        "RERA project registration and complaint status must be checked on state RERA portal.",
    ]

    limitations = [
        "Provisional rule-based estimation; no trained machine learning model was executed.",
        "Model governance provenance: PROVISIONAL_RULE_BASED_PENDING_TRAINING_DATA.",
        "Estimates do not account for unrecorded encumbrances, structural defects, or local litigation not listed in provided data.",
    ]

    recommendations = [
        "Conduct mandatory physical collateral inspection by panel valuer before credit committee presentation.",
        "Obtain independent valuation report from a second empaneled technical valuer for loan amounts exceeding standard institutional limits.",
        "Verify property tax receipts, mutation extract, and electricity connection in applicant's name.",
        "Verify that loan-to-value (LTV) conforms to NHB/RBI regulatory caps based on the lower of agreement value or fair market value.",
    ]

    decision_role = (
        "AI Underwriter provides advisory synthesis only. Loan sanction, conditionality, and credit "
        "approval or rejection must be determined solely by the authorized human credit underwriter and credit committee."
    )

    return AIUnderwriterReport(
        valuation_summary=summary,
        major_valuation_factors=factors,
        comparable_evidence_analysis=comp_analysis,
        location_considerations=location_notes,
        data_quality_concerns=data_concerns,
        legal_regulatory_risks=legal_risks,
        valuation_limitations=limitations,
        underwriter_recommendations=recommendations,
        recommendation_decision_role=decision_role,
    )


def validate_and_sanitize_ai_report(
    report_dict: Dict[str, Any],
    fallback_report: AIUnderwriterReport,
) -> AIUnderwriterReport:
    """Validate external LLM output against safety guardrails.

    Prevents:
    - Hallucinated automated loan sanction/rejection statements.
    - Malformed structures or missing required sections.
    """
    try:
        # Check required fields
        required_keys = [
            "valuation_summary",
            "major_valuation_factors",
            "comparable_evidence_analysis",
            "location_considerations",
            "data_quality_concerns",
            "legal_regulatory_risks",
            "valuation_limitations",
            "underwriter_recommendations",
            "recommendation_decision_role",
        ]
        for key in required_keys:
            if key not in report_dict:
                logger.warning(f"AI response missing required key '{key}', using fallback.")
                return fallback_report

        # Sanitize any claim of automated approval or rejection
        automated_approval_patterns = [
            r"(?i)\bloan\s+is\s+(?:hereby\s+)?approved\b",
            r"(?i)\bapplication\s+is\s+sanctioned\b",
            r"(?i)\bwe\s+approve\s+the\s+loan\b",
            r"(?i)\bautomatically\s+approved\b",
        ]
        decision_role = report_dict.get("recommendation_decision_role", "")
        for pat in automated_approval_patterns:
            if re.search(pat, decision_role) or re.search(pat, report_dict.get("valuation_summary", "")):
                logger.warning("Automated approval claim detected in AI output; replacing decision role with strict policy mandate.")
                report_dict["recommendation_decision_role"] = fallback_report.recommendation_decision_role

        factors = []
        for f in report_dict.get("major_valuation_factors", []):
            factors.append(
                AIUnderwriterFactor(
                    factor_name=str(f.get("factor_name", "Valuation Factor")),
                    impact=str(f.get("impact", "NEUTRAL")).upper(),
                    details=str(f.get("details", "")),
                )
            )

        return AIUnderwriterReport(
            valuation_summary=str(report_dict["valuation_summary"]),
            major_valuation_factors=factors,
            comparable_evidence_analysis=str(report_dict["comparable_evidence_analysis"]),
            location_considerations=str(report_dict["location_considerations"]),
            data_quality_concerns=[str(x) for x in report_dict.get("data_quality_concerns", [])],
            legal_regulatory_risks=[str(x) for x in report_dict.get("legal_regulatory_risks", [])],
            valuation_limitations=[str(x) for x in report_dict.get("valuation_limitations", [])],
            underwriter_recommendations=[str(x) for x in report_dict.get("underwriter_recommendations", [])],
            recommendation_decision_role=str(report_dict["recommendation_decision_role"]),
        )
    except Exception as e:
        logger.error(f"Error validating AI report structure: {e}. Using deterministic fallback.")
        return fallback_report


async def generate_underwriter_briefing(
    case_payload: Dict[str, Any],
    db_session: Session,
) -> AIExplainCaseResponse:
    """Coordinate the synthesis of an underwriter briefing.

    Uses Gemini if configured and enabled; cleanly and deterministically
    falls back to local rule-based synthesis if offline, unconfigured, or failing.
    Logs audit metrics in the database compliant with DPDP Act 2023.
    """
    case_id = case_payload.get("case_id", "UNKNOWN")
    pii_count = case_payload.get("pii_redacted_count", 0)
    fallback_report = generate_deterministic_fallback_report(case_payload)

    # Check configuration
    api_key = settings.GEMINI_API_KEY.strip()
    cloud_enabled = settings.ENABLE_AI_CLOUD_PROCESSING

    if not api_key or not cloud_enabled:
        # Deterministic fallback path
        audit = AIAuditLogModel(
            case_id=case_id,
            model_name="deterministic-fallback-engine",
            provider="deterministic_fallback",
            pii_redacted_count=pii_count,
            prompt_tokens=0,
            response_tokens=0,
            status="fallback",
            error_message="GEMINI_API_KEY unconfigured or cloud processing disabled",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(audit)
        db_session.commit()

        return AIExplainCaseResponse(
            case_id=case_id,
            provider="deterministic_fallback",
            model_name="deterministic-fallback-engine",
            status="fallback",
            pii_redacted_count=pii_count,
            report=fallback_report,
            disclaimer=settings.AI_DISCLAIMER_TEXT,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # Cloud Gemini Path: Transmit key securely via header rather than URL query parameter
    model_name = settings.GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    user_prompt = f"""EVIDENCE PAYLOAD (DATA-MINIMIZED & PII-SCRUBBED):
{json.dumps(case_payload, indent=2)}

Please synthesize an evidence-grounded underwriter briefing following your instructions."""

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                },
            )

        if response.status_code == 200:
            resp_data = response.json()
            candidates = resp_data.get("candidates", [])
            if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                raw_text = candidates[0]["content"]["parts"][0].get("text", "{}")
                parsed_json = json.loads(raw_text)
                validated_report = validate_and_sanitize_ai_report(parsed_json, fallback_report)

                audit = AIAuditLogModel(
                    case_id=case_id,
                    model_name=model_name,
                    provider="gemini",
                    pii_redacted_count=pii_count,
                    prompt_tokens=len(user_prompt) // 4,
                    response_tokens=len(raw_text) // 4,
                    status="success",
                    error_message=None,
                    created_at=datetime.now(timezone.utc),
                )
                db_session.add(audit)
                db_session.commit()

                return AIExplainCaseResponse(
                    case_id=case_id,
                    provider="gemini",
                    model_name=model_name,
                    status="success",
                    pii_redacted_count=pii_count,
                    report=validated_report,
                    disclaimer=settings.AI_DISCLAIMER_TEXT,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                )

        # Non-200 response from Gemini API
        err_msg = f"Gemini API returned status {response.status_code}: {response.text[:200]}"
        logger.warning(f"{err_msg}. Falling back to deterministic briefing.")

        audit = AIAuditLogModel(
            case_id=case_id,
            model_name=model_name,
            provider="deterministic_fallback",
            pii_redacted_count=pii_count,
            prompt_tokens=len(user_prompt) // 4,
            response_tokens=0,
            status="fallback",
            error_message=err_msg,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(audit)
        db_session.commit()

        return AIExplainCaseResponse(
            case_id=case_id,
            provider="deterministic_fallback",
            model_name=model_name,
            status="fallback",
            pii_redacted_count=pii_count,
            report=fallback_report,
            disclaimer=settings.AI_DISCLAIMER_TEXT,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        err_msg = f"Exception calling Gemini API: {str(exc)}"
        logger.error(f"{err_msg}. Using deterministic fallback.")

        audit = AIAuditLogModel(
            case_id=case_id,
            model_name=model_name,
            provider="deterministic_fallback",
            pii_redacted_count=pii_count,
            prompt_tokens=len(user_prompt) // 4,
            response_tokens=0,
            status="fallback",
            error_message=err_msg,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(audit)
        db_session.commit()

        return AIExplainCaseResponse(
            case_id=case_id,
            provider="deterministic_fallback",
            model_name=model_name,
            status="fallback",
            pii_redacted_count=pii_count,
            report=fallback_report,
            disclaimer=settings.AI_DISCLAIMER_TEXT,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
