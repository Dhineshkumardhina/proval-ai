"""PropVal AI Institutional Valuation & Underwriting Math Engine.

NOTE: This is a provisional rule-based estimation engine implementing
deterministic hedonic scorecard adjustments for property valuation and credit appraisal.
It is NOT a trained machine learning model, deep neural network, or predictive AI.
Designed for Indian Housing Finance Companies (HFCs) and Bank Credit Committees.
"""

import math
from typing import Literal, Tuple
from app.schemas.valuation import AttributionFactor, ValuationInputParams, ValuationResponse


def js_round(val: float) -> int:
    """Emulate JavaScript's Math.round (half toward +infinity for positive numbers)."""
    if math.isnan(val) or math.isinf(val):
        return 0
    if val >= 0:
        return math.floor(val + 0.5)
    return math.ceil(val - 0.5)


def format_indian_number(num: float) -> str:
    """Format a plain number with Indian comma grouping (e.g. 14250000 -> 1,42,50,000)."""
    if num is None or math.isnan(num):
        return "0"
    s = str(math.floor(abs(num)))
    if len(s) <= 3:
        return s
    last_three = s[-3:]
    others = s[:-3]
    parts = []
    while len(others) > 2:
        parts.insert(0, others[-2:])
        others = others[:-2]
    if others:
        parts.insert(0, others)
    return ",".join(parts) + "," + last_three


def format_indian_currency(amount: float, mode: Literal["full", "short"] = "full") -> str:
    """Format currency according to Indian denomination rules (Lakhs, Crores)."""
    if amount is None or math.isnan(amount):
        return "₹0"
    is_negative = amount < 0
    abs_amount = abs(amount)
    sign = "-" if is_negative else ""

    if mode == "short":
        if abs_amount >= 10000000:
            # 1 Crore = 10,000,000
            cr = f"{abs_amount / 10000000:.2f}"
            return f"{sign}₹{cr} Cr"
        elif abs_amount >= 100000:
            # 1 Lakh = 100,000
            lk = f"{abs_amount / 100000:.2f}"
            return f"{sign}₹{lk} L"
        else:
            return f"{sign}₹{format_indian_number(js_round(abs_amount))}"

    return f"{sign}₹{format_indian_number(js_round(abs_amount))}"


def calculate_valuation(params: ValuationInputParams) -> ValuationResponse:
    """Compute deterministic hedonic property valuation including scorecard attribution breakdown.

    Uses bounded adjustments and RERA carpet-area based valuation math.
    Matches TypeScript calculation logic with 100% numerical parity.
    """
    # Defensive input sanitization
    raw_carpet = params.carpetAreaSqFt
    carpet_area_sqft = max(0.0, 0.0 if (raw_carpet is None or math.isnan(raw_carpet)) else float(raw_carpet))

    raw_base_rate = params.baseMarketRatePerSqFt
    base_market_rate_per_sqft = max(0.0, 0.0 if (raw_base_rate is None or math.isnan(raw_base_rate)) else float(raw_base_rate))

    super_built_up_area_sqft = 0.0 if (params.superBuiltUpAreaSqFt is None or math.isnan(params.superBuiltUpAreaSqFt)) else float(params.superBuiltUpAreaSqFt)
    circle_rate_per_sqft = 0.0 if (params.circleRatePerSqFt is None or math.isnan(params.circleRatePerSqFt)) else float(params.circleRatePerSqFt)
    floor_rise_factor = 0.0 if (params.floorRiseFactor is None or math.isnan(params.floorRiseFactor)) else float(params.floorRiseFactor)
    road_width_factor = 0.0 if (params.roadWidthFactor is None or math.isnan(params.roadWidthFactor)) else float(params.roadWidthFactor)
    amenities_premium = 0.0 if (params.amenitiesPremium is None or math.isnan(params.amenitiesPremium)) else float(params.amenitiesPremium)
    structural_depreciation = 0.0 if (params.structuralDepreciation is None or math.isnan(params.structuralDepreciation)) else float(params.structuralDepreciation)

    underwriter_haircut_pct = 0.0 if (params.underwriterHaircutPct is None or math.isnan(params.underwriterHaircutPct)) else float(params.underwriterHaircutPct)
    distress_discount_pct = 17.0 if (params.distressDiscountPct is None or math.isnan(params.distressDiscountPct)) else float(params.distressDiscountPct)
    ltv_ratio_pct = 75.0 if (params.ltvRatioPct is None or math.isnan(params.ltvRatioPct)) else float(params.ltvRatioPct)
    legal_risk_penalty_pct = 0.0 if (params.legalRiskPenaltyPct is None or math.isnan(params.legalRiskPenaltyPct)) else float(params.legalRiskPenaltyPct)

    # Scorecard adjusted rate per sq ft on Carpet Area (floor minimum ₹1,000/sqft)
    net_adjustment = (
        floor_rise_factor
        + road_width_factor
        + amenities_premium
        - abs(structural_depreciation)
    )

    rule_adjusted_rate_per_sqft = max(1000.0, base_market_rate_per_sqft + net_adjustment)
    ai_adjusted_rate_per_sqft = rule_adjusted_rate_per_sqft

    # Gross Valuation (carpet area based)
    gross_market_value = js_round(rule_adjusted_rate_per_sqft * carpet_area_sqft)

    # Underwriter hair-cut adjustment & legal risk penalty (safely bounded)
    safe_haircut_pct = max(-90.0, min(50.0, underwriter_haircut_pct))
    safe_legal_penalty_pct = max(0.0, min(100.0, legal_risk_penalty_pct))
    underwriter_multiplier = 1.0 + safe_haircut_pct / 100.0
    legal_multiplier = 1.0 - safe_legal_penalty_pct / 100.0
    net_assessed_value = max(0, js_round(gross_market_value * underwriter_multiplier * legal_multiplier))

    # Forced Sale / Distress Liquidation Value (standard HFC metric)
    safe_distress_discount_pct = max(5.0, min(50.0, distress_discount_pct))
    distress_liquidation_value = js_round(net_assessed_value * (1.0 - safe_distress_discount_pct / 100.0))

    # Max Loan Sanction Amount based on permitted LTV (75% - 80% NHB cap)
    safe_ltv_ratio_pct = min(90.0, max(30.0, ltv_ratio_pct))
    max_sanction_amount = js_round(net_assessed_value * (safe_ltv_ratio_pct / 100.0))

    # Deviation from Circle Rate (Guideline Value)
    safe_circle_rate = max(0.0, circle_rate_per_sqft)
    if safe_circle_rate > 0:
        raw_dev = ((ai_adjusted_rate_per_sqft - safe_circle_rate) / safe_circle_rate) * 100.0
        deviation_from_circle_rate_pct = round(raw_dev, 1)
    else:
        deviation_from_circle_rate_pct = 0.0

    # Attribution Waterfall Breakdown
    attribution_breakdown = [
        AttributionFactor(
            factor="Micro-Market Baseline",
            impactPerSqFt=base_market_rate_per_sqft,
            description="Indicative micro-market baseline rate (synthetic benchmark, not verified transaction evidence)",
            category="neutral",
        ),
        AttributionFactor(
            factor="Floor Rise Factor",
            impactPerSqFt=floor_rise_factor,
            description="High-floor premium (+4th floor and above)" if floor_rise_factor >= 0 else "Ground/lower floor discount",
            category="positive" if floor_rise_factor >= 0 else "negative",
        ),
        AttributionFactor(
            factor="Road Access & Arterial Width",
            impactPerSqFt=road_width_factor,
            description="60ft+ master plan arterial road frontage" if road_width_factor > 0 else "Sub-30ft narrow approach road",
            category="positive" if road_width_factor >= 0 else "negative",
        ),
        AttributionFactor(
            factor="Gated Amenities & Security",
            impactPerSqFt=amenities_premium,
            description="Clubhouse, power backup, swimming pool, 24/7 security & STP",
            category="positive",
        ),
        AttributionFactor(
            factor="Age & Structural Depreciation",
            impactPerSqFt=-abs(structural_depreciation),
            description="Asset vintage and physical maintenance wear factor",
            category="negative",
        ),
    ]

    # Heuristic confidence score calculation (rule-based deduction, not statistically calibrated)
    base_confidence = 95.5
    if abs(deviation_from_circle_rate_pct) > 35:
        base_confidence -= 10.0
    elif abs(deviation_from_circle_rate_pct) > 20:
        base_confidence -= 4.2

    if safe_legal_penalty_pct > 0:
        base_confidence -= 8.5

    confidence_score_pct = max(65.0, min(99.4, round(base_confidence, 1)))

    # Deterministic Risk Tier Evaluation
    risk_tier: Literal["LOW_RISK", "MODERATE_RISK", "HIGH_ALERT"] = "LOW_RISK"
    if deviation_from_circle_rate_pct > 40 or safe_legal_penalty_pct > 5 or confidence_score_pct < 80:
        risk_tier = "HIGH_ALERT"
    elif deviation_from_circle_rate_pct > 20 or safe_haircut_pct < -5 or confidence_score_pct < 90:
        risk_tier = "MODERATE_RISK"

    return ValuationResponse(
        carpetAreaSqFt=carpet_area_sqft,
        superBuiltUpAreaSqFt=super_built_up_area_sqft,
        unadjustedRatePerSqFt=base_market_rate_per_sqft,
        ruleAdjustedRatePerSqFt=rule_adjusted_rate_per_sqft,
        aiAdjustedRatePerSqFt=ai_adjusted_rate_per_sqft,
        circleRatePerSqFt=circle_rate_per_sqft,
        grossMarketValue=gross_market_value,
        netAssessedValue=net_assessed_value,
        distressLiquidationValue=distress_liquidation_value,
        maxSanctionAmount=max_sanction_amount,
        deviationFromCircleRatePct=deviation_from_circle_rate_pct,
        confidenceScorePct=confidence_score_pct,
        riskTier=risk_tier,
        attributionBreakdown=attribution_breakdown,
        engineVersion="0.2.0",
        engineType="provisional rule-based estimation",
        dataSource=params.dataSource or "synthetic-demo",
        isProvisional=True,
    )

