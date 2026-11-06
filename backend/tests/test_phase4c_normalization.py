"""Comprehensive Unit Tests for Phase 4C Normalization Engine."""

import pytest
from app.normalization.engine import PropertyNormalizationEngine
from app.normalization.unit_converter import parse_and_normalize_area
from app.normalization.currency_normalizer import normalize_transaction_amount
from app.normalization.geo_normalizer import normalize_cadastral_reference, validate_locality_spatial_consistency


def test_area_unit_conversions_regional_standards():
    """Verify conversion of Indian land and apartment measurement units into standard sqft."""
    # 1. Standard Metric / Imperial
    sqft_res, _, _, _ = parse_and_normalize_area(1200, "sqft")
    assert sqft_res == 1200.0

    sqm_res, _, _, _ = parse_and_normalize_area(100, "sqm")
    assert round(sqm_res, 1) == 1076.4

    sqyd_res, _, _, _ = parse_and_normalize_area(200, "sqyd")
    assert sqyd_res == 1800.0  # 200 * 9

    acre_res, _, _, _ = parse_and_normalize_area(2, "acre")
    assert acre_res == 87120.0  # 2 * 43560

    # 2. Regional Units: South India
    ground_res, _, _, _ = parse_and_normalize_area(1, "ground", state="Tamil Nadu")
    assert ground_res == 2400.0

    cent_res, _, _, _ = parse_and_normalize_area(10, "cent", state="Kerala")
    assert cent_res == 4356.0  # 10 * 435.6

    ankanam_res, _, _, _ = parse_and_normalize_area(10, "ankanam", state="Andhra Pradesh")
    assert ankanam_res == 720.0  # 10 * 72

    gunta_res, _, _, _ = parse_and_normalize_area(2, "gunta", state="Karnataka")
    assert gunta_res == 2178.0  # 2 * 1089

    # 3. Regional Units: North & East India
    marla_res, _, _, _ = parse_and_normalize_area(4, "marla", state="Punjab")
    assert marla_res == 1089.0  # 4 * 272.25

    kanal_res, _, _, _ = parse_and_normalize_area(2, "kanal", state="Haryana")
    assert kanal_res == 10890.0  # 2 * 5445

    biswa_res, _, _, _ = parse_and_normalize_area(2, "biswa", state="Uttar Pradesh")
    assert biswa_res == 2700.0  # 2 * 1350

    cottah_res, _, _, _ = parse_and_normalize_area(3, "cottah", state="West Bengal")
    assert cottah_res == 2160.0  # 3 * 720


def test_normalization_engine_extracts_carpet_bua_sbua():
    """Verify that PropertyNormalizationEngine normalizes carpet, built-up, and super built-up areas."""
    engine = PropertyNormalizationEngine(source_id="SRC_TEST", source_code="TEST_SRC")
    raw_record = {
        "transaction_amount": 12500000,
        "carpet_area": 1100,
        "built_up_area": 1300,
        "super_built_up_area": 1500,
        "unit": "sqft",
        "registration_date": "2026-02-15",
        "city": "Bengaluru",
        "district": "Bengaluru Urban",
        "locality": "Whitefield",
        "project_name": "Prestige Boulevard",
        "property_type": "High-Rise Apartment",
        "unit_number": "Flat 802",
        "floor_number": 8,
        "total_floors": 24,
        "survey_number": "142/3A",
        "village": "Varthur",
    }

    norm_tx, err = engine.normalize_record(raw_record, row_index=1)
    assert err is None
    assert norm_tx is not None
    assert norm_tx.carpet_area_sqft == 1100.0
    assert norm_tx.built_up_area_sqft == 1300.0
    assert norm_tx.super_built_up_area_sqft == 1500.0
    assert norm_tx.transaction_amount == 12500000.0
    assert norm_tx.price_per_sqft == round(12500000.0 / 1100.0, 2)
    assert norm_tx.cadastral.survey_number == "142/3A"
    assert norm_tx.cadastral.revenue_village == "Varthur"


def test_inr_currency_normalization():
    """Verify handling of diverse Indian financial numeral notations."""
    val1, err1 = normalize_transaction_amount("₹ 1.25 Crore")
    assert val1 == 12500000.0
    assert err1 is None

    val2, err2 = normalize_transaction_amount("75.5 Lakhs")
    assert val2 == 7550000.0
    assert err2 is None

    val3, err3 = normalize_transaction_amount("1,45,00,000")
    assert val3 == 14500000.0
    assert err3 is None


def test_cadastral_reference_normalization():
    """Verify canonical cadastral parcel structuring."""
    res = normalize_cadastral_reference(
        raw_data={
            "survey_number": "45/2B",
            "village": "Bellandur",
            "taluka": "Bengaluru East",
        },
        city="Bengaluru",
        state="Karnataka",
    )
    assert res.survey_number == "45/2B"
    assert res.village_name == "Bellandur"
    assert res.taluka_tehsil == "Bengaluru East"
    assert res.spatial_accuracy_tier == "PARCEL_SURVEY_RECORDED"
    assert res.cadastral_parcel_id == "KA-BEN-BEL-45/2B"
