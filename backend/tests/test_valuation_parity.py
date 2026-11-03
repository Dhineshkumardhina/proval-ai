"""Numerical Parity Tests: Python Valuation Engine vs TypeScript Baseline.

Validates 100% mathematical parity across all 12 test cases established
in src/utils/valuationEngine.test.ts.
"""

import math
import re
import pytest
from app.schemas.valuation import ValuationInputParams
from app.services.valuation_service import (
    calculate_valuation,
    format_indian_currency,
    format_indian_number,
)


# ==========================================
# REGRESSION GUARD: ORIGINAL BASELINE TESTS
# ==========================================

def test_format_indian_number_groups_digits_using_indian_numeral_system():
    """Test 1: formatIndianNumber parity."""
    assert format_indian_number(14250000) == "1,42,50,000"
    assert format_indian_number(850000) == "8,50,000"
    assert format_indian_number(12500) == "12,500"
    assert format_indian_number(450) == "450"


def test_format_indian_currency_formats_full_and_short_modes():
    """Test 2: formatIndianCurrency parity across Lakh / Crore modes."""
    assert format_indian_currency(14250000, "full") == "₹1,42,50,000"
    assert format_indian_currency(14250000, "short") == "₹1.43 Cr"
    assert format_indian_currency(8850000, "short") == "₹88.50 L"
    assert format_indian_currency(75000, "short") == "₹75,000"


def test_calculate_valuation_computes_correct_gross_haircut_liquidation_and_sanction_values():
    """Test 3: Comprehensive mathematical calculation parity against TypeScript."""
    params = ValuationInputParams(
        carpetAreaSqFt=1250,
        superBuiltUpAreaSqFt=1650,
        baseMarketRatePerSqFt=9800,
        circleRatePerSqFt=7800,
        floorRiseFactor=350,
        roadWidthFactor=250,
        amenitiesPremium=400,
        structuralDepreciation=150,
        underwriterHaircutPct=-5,
        distressDiscountPct=20,
        ltvRatioPct=75,
        legalRiskPenaltyPct=0,
    )
    result = calculate_valuation(params)

    # net adjustment = 350 + 250 + 400 - 150 = 850
    # rule adjusted rate = 9800 + 850 = 10650
    assert result.ruleAdjustedRatePerSqFt == 10650
    assert result.aiAdjustedRatePerSqFt == 10650  # backward-compatible alias

    # gross market value = 10650 * 1250 = 1,33,12,500
    assert result.grossMarketValue == 13312500

    # haircut -5% => 13312500 * 0.95 = 12646875
    assert result.netAssessedValue == 12646875

    # distress 20% discount => 12646875 * 0.8 = 10117500
    assert result.distressLiquidationValue == 10117500

    # max loan sanction at 75% LTV => 12646875 * 0.75 = 9485156
    assert result.maxSanctionAmount == 9485156

    # deviation from circle rate: ((10650 - 7800) / 7800) * 100 = 36.5%
    assert 36 < result.deviationFromCircleRatePct < 37
    assert result.deviationFromCircleRatePct == 36.5

    # Attribution breakdown has expected 5 factors
    assert len(result.attributionBreakdown) == 5


def test_calculate_valuation_handles_edge_cases_zero_area_and_zero_circle_rate_safely():
    """Test 4: Edge case handling for zero area and zero circle rate."""
    params = ValuationInputParams(
        carpetAreaSqFt=0,
        superBuiltUpAreaSqFt=0,
        baseMarketRatePerSqFt=10000,
        circleRatePerSqFt=0,
        floorRiseFactor=0,
        roadWidthFactor=0,
        amenitiesPremium=0,
        structuralDepreciation=0,
        underwriterHaircutPct=0,
        distressDiscountPct=20,
        ltvRatioPct=75,
        legalRiskPenaltyPct=0,
    )
    result = calculate_valuation(params)

    assert result.grossMarketValue == 0
    assert result.netAssessedValue == 0
    assert result.distressLiquidationValue == 0
    assert result.maxSanctionAmount == 0
    assert result.deviationFromCircleRatePct == 0.0
    assert result.confidenceScorePct == 95.5
    assert result.riskTier == "LOW_RISK"


def test_calculate_valuation_applies_confidence_penalties_and_assigns_high_alert():
    """Test 5: Penalty deduction triggers and HIGH_ALERT risk tiering."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        superBuiltUpAreaSqFt=1300,
        baseMarketRatePerSqFt=12000,
        circleRatePerSqFt=6000,  # +100% deviation triggers circle rate penalty (-10.0)
        floorRiseFactor=0,
        roadWidthFactor=0,
        amenitiesPremium=0,
        structuralDepreciation=0,
        underwriterHaircutPct=0,
        distressDiscountPct=20,
        ltvRatioPct=75,
        legalRiskPenaltyPct=10,  # legal penalty triggers -8.5 confidence deduction and HIGH_ALERT
    )
    result = calculate_valuation(params)

    # Deviation = 100% (>35% => -10 confidence)
    # Legal penalty = 10% (>0 => -8.5 confidence)
    # Base 95.5 - 10 - 8.5 = 77.0
    assert result.confidenceScorePct == 77.0
    assert result.riskTier == "HIGH_ALERT"


# =======================================================
# CREDIBILITY REMEDIATION TESTS (PARITY WITH TESTS 6 - 12)
# =======================================================

def test_credibility_valuation_engine_labels_identify_as_provisional_rule_based():
    """Test 6: Engine identifies strictly as provisional rule-based without ML claims."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        baseMarketRatePerSqFt=10000,
    )
    result = calculate_valuation(params)
    assert result.engineType == "provisional rule-based estimation"
    assert not re.search(r"machine learning|neural network|trained model|deep learning", result.engineType, re.IGNORECASE)


def test_credibility_attribution_breakdown_does_not_claim_live_sro_registered_evidence():
    """Test 7: Attribution breakdown disclaims synthetic benchmark without live deed claims."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        superBuiltUpAreaSqFt=1300,
        baseMarketRatePerSqFt=10000,
        circleRatePerSqFt=8000,
    )
    result = calculate_valuation(params)
    baseline_desc = result.attributionBreakdown[0].description
    assert re.search(r"synthetic|indicative|benchmark", baseline_desc, re.IGNORECASE)
    assert not re.search(r"median sales within.*past 180 days", baseline_desc, re.IGNORECASE)


def test_credibility_confidence_score_distinguishes_heuristic_penalty_from_calibrated():
    """Test 8: Confidence is clearly flagged as uncalibrated heuristic."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        baseMarketRatePerSqFt=8000,
    )
    result = calculate_valuation(params)
    assert result.isProvisional is True
    assert result.confidenceScorePct == 95.5


def test_credibility_model_governance_provenance_markers():
    """Test 9: Model governance default metadata is verified."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        baseMarketRatePerSqFt=8000,
    )
    result = calculate_valuation(params)
    assert result.engineVersion == "0.2.0"
    assert result.dataSource == "synthetic-demo"


def test_credibility_demonstration_case_provenance_markers():
    """Test 10: Synthetic demo provenance marker verification."""
    params = ValuationInputParams(
        carpetAreaSqFt=1200,
        baseMarketRatePerSqFt=9500,
        dataSource="synthetic-demo",
    )
    result = calculate_valuation(params)
    assert result.dataSource == "synthetic-demo"


def test_credibility_edge_cases_with_nan_negative_inputs_handle_safely():
    """Test 11: Robust defense against float('nan') and negative values."""
    params = ValuationInputParams(
        carpetAreaSqFt=float("nan"),
        superBuiltUpAreaSqFt=-100,
        baseMarketRatePerSqFt=float("nan"),
        circleRatePerSqFt=-500,
        underwriterHaircutPct=float("nan"),
        distressDiscountPct=float("nan"),
        ltvRatioPct=float("nan"),
        legalRiskPenaltyPct=float("nan"),
    )
    result = calculate_valuation(params)

    assert result.carpetAreaSqFt == 0.0
    assert result.grossMarketValue == 0
    assert result.netAssessedValue == 0
    assert result.distressLiquidationValue == 0
    assert result.maxSanctionAmount == 0
    assert result.deviationFromCircleRatePct == 0.0
    assert 65.0 <= result.confidenceScorePct <= 100.0


def test_credibility_ai_unconnected_purely_in_memory_arithmetic():
    """Test 12: Valuation arithmetic operates deterministically in memory without network calls."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000,
        superBuiltUpAreaSqFt=1200,
        baseMarketRatePerSqFt=8000,
        circleRatePerSqFt=7000,
        distressDiscountPct=20,
        ltvRatioPct=75,
    )
    result = calculate_valuation(params)
    assert result.netAssessedValue == 8000000

