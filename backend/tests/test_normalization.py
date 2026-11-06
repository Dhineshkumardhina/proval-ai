"""Comprehensive test suite for Phase 4A-3 Indian Property Transaction Data Normalization Engine."""

import pytest
from datetime import datetime, timezone

from app.normalization.models import AreaUnit, MissingDataReason, NormalizedTransactionRecord
from app.normalization.unit_converter import (
    parse_and_normalize_area,
    SQM_TO_SQFT,
    SQYD_TO_SQFT,
    ACRE_TO_SQFT,
    GUNTA_TO_SQFT,
    GROUND_TO_SQFT,
)
from app.normalization.currency_normalizer import normalize_transaction_amount
from app.normalization.geo_normalizer import (
    normalize_state,
    normalize_district,
    normalize_pincode,
    validate_and_normalize_coordinates,
)
from app.normalization.engine import PropertyNormalizationEngine


# =========================================================================
# 1. Area Unit Conversion Tests
# =========================================================================

def test_area_conversion_sqft():
    """Verify square feet parsing preserves original value."""
    sqft, orig_val, orig_unit, err = parse_and_normalize_area("1,250 sqft")
    assert err is None
    assert sqft == 1250.0
    assert orig_val == 1250.0
    assert orig_unit == "SQFT"


def test_area_conversion_sqm():
    """Verify square metres conversion to square feet."""
    sqft, orig_val, orig_unit, err = parse_and_normalize_area(100.0, "sq_m")
    assert err is None
    assert orig_val == 100.0
    assert orig_unit == "SQM"
    assert sqft == round(100.0 * SQM_TO_SQFT, 2)  # ~1076.39 sqft


def test_area_conversion_regional_units():
    """Verify regional units: Gaj/SqYd, Gunta (Karnataka/MH), Ground (TN), Acre."""
    # 1. Square Yards / Gaj
    sqft_yd, _, unit_yd, err_yd = parse_and_normalize_area("200 gaj")
    assert err_yd is None
    assert unit_yd == "SQYD"
    assert sqft_yd == 200.0 * 9.0  # 1800.0 sqft

    # 2. Gunta (1089 sqft)
    sqft_g, _, unit_g, err_g = parse_and_normalize_area(2.0, "gunta")
    assert err_g is None
    assert unit_g == "GUNTA"
    assert sqft_g == 2178.0

    # 3. Ground (2400 sqft)
    sqft_gr, _, unit_gr, err_gr = parse_and_normalize_area(1.5, "ground")
    assert err_gr is None
    assert unit_gr == "GROUND"
    assert sqft_gr == 3600.0

    # 4. Acre (43560 sqft)
    sqft_ac, _, unit_ac, err_ac = parse_and_normalize_area(0.25, "acre")
    assert err_ac is None
    assert unit_ac == "ACRE"
    assert sqft_ac == 10890.0


def test_area_conversion_invalid_and_negative():
    """Verify zero, negative, or unparseable area is rejected."""
    _, _, _, err1 = parse_and_normalize_area(-150)
    assert "must be strictly positive" in err1

    _, _, _, err2 = parse_and_normalize_area("invalid_area_text")
    assert "Cannot parse numeric area" in err2


# =========================================================================
# 2. Currency and Monetary Amount Tests
# =========================================================================

def test_currency_normalization_crores_lakhs_thousands():
    """Verify standard Indian financial notations parse accurately without rounding drift."""
    # ₹1.45 Cr -> 14,500,000
    val_cr, err_cr = normalize_transaction_amount("₹1.45 Cr")
    assert err_cr is None
    assert val_cr == 14500000.0

    # ₹85.5 Lakhs -> 8,550,000
    val_lakh, err_lakh = normalize_transaction_amount("85.5 Lakhs")
    assert err_lakh is None
    assert val_lakh == 8550000.0

    # ₹750k -> 750,000
    val_k, err_k = normalize_transaction_amount("750k")
    assert err_k is None
    assert val_k == 750000.0

    # Raw integer
    val_raw, err_raw = normalize_transaction_amount(18500000)
    assert err_raw is None
    assert val_raw == 18500000.0


def test_currency_normalization_negative_and_nominal():
    """Verify negative amounts and nominal values below ₹1,000 are rejected."""
    _, err_neg = normalize_transaction_amount("-5000000")
    assert "Negative transaction amounts are prohibited" in err_neg

    _, err_low = normalize_transaction_amount("₹500")
    assert "below minimum plausible consideration floor" in err_low


# =========================================================================
# 3. Geographic Normalization & Bounds Tests
# =========================================================================

def test_state_and_district_canonicalization():
    """Verify state and district aliases map to official canonical names."""
    state_ka, _ = normalize_state("ka")
    assert state_ka == "Karnataka"

    state_mh, _ = normalize_state("maharashtra")
    assert state_mh == "Maharashtra"

    dist_blr, _ = normalize_district("bangalore")
    assert dist_blr == "Bengaluru Urban"

    dist_mum, _ = normalize_district("bombay")
    assert dist_mum == "Mumbai City"


def test_pincode_validation():
    """Verify Indian 6-digit postal code validation."""
    clean_pin, err = normalize_pincode("560 066")
    assert err is None
    assert clean_pin == "560066"

    _, err_bad = normalize_pincode("012345")
    assert "Invalid Indian PIN code format" in err_bad


def test_coordinates_spatial_validation():
    """Verify coordinate bounds validation and automatic swap for inverted lat/lon."""
    # Valid Bengaluru coords: Lat ~12.97, Lon ~77.59
    lat, lon, err = validate_and_normalize_coordinates(12.9716, 77.5946)
    assert err is None
    assert lat == 12.9716
    assert lon == 77.5946

    # Inverted lat/lon (Lon in lat position, Lat in lon position)
    lat_inv, lon_inv, err_inv = validate_and_normalize_coordinates(77.5946, 12.9716)
    assert err_inv is None
    assert lat_inv == 12.9716
    assert lon_inv == 77.5946

    # Out of Indian bounds (e.g. London: Lat 51.5, Lon -0.12)
    _, _, err_out = validate_and_normalize_coordinates(51.5074, -0.1278)
    assert "outside Indian geographic boundaries" in err_out


# =========================================================================
# 4. End-to-End Property Normalization Engine Tests
# =========================================================================

def test_normalization_engine_end_to_end():
    """Verify full normalization lifecycle: provenance, fields, units, and missing data taxonomy."""
    engine = PropertyNormalizationEngine(source_id="src-zap-01", source_code="ZAPKEY_BLR")
    raw_record = {
        "registration_number": "DOC-9912/2024",
        "registration_date": "15-Aug-2024",
        "price": "₹1.85 Cr",
        "area": 1450.0,
        "unit": "sqft",
        "state": "KA",
        "district": "Bangalore Urban",
        "locality": "Whitefield",
        "pincode": "560066",
        "project": "Prestige Lakeside Habitat",
        "unit_number": "T3-1402",
        "property_type": "High-Rise Apartment",
        "sro_office": "Shivajinagar SRO",
        "guideline_rate_per_sqft": 9200.0,
        "latitude": 12.9698,
        "longitude": 77.7499,
        "is_verified": True,
    }

    norm_tx, err = engine.normalize_record(raw_record, row_index=1, dataset_version="v1.0.0")
    assert err is None
    assert norm_tx is not None
    assert isinstance(norm_tx, NormalizedTransactionRecord)

    # Validate economic normalization
    assert norm_tx.transaction_amount == 18500000.0
    assert norm_tx.carpet_area_sqft == 1450.0
    assert norm_tx.price_per_sqft == round(18500000.0 / 1450.0, 2)
    assert norm_tx.currency == "INR"
    assert norm_tx.transaction_quarter == "2024-Q3"

    # Validate geographic normalization
    assert norm_tx.state == "Karnataka"
    assert norm_tx.district == "Bengaluru Urban"
    assert norm_tx.locality == "Whitefield"
    assert norm_tx.postal_code == "560066"
    assert norm_tx.latitude == 12.9698
    assert norm_tx.longitude == 77.7499

    # Validate provenance & fingerprinting
    assert norm_tx.source_id == "src-zap-01"
    assert norm_tx.dataset_version == "v1.0.0"
    assert norm_tx.is_verified_deed is True
    assert norm_tx.is_asking_price is False
    assert len(norm_tx.fingerprint_hash) == 64
    assert len(norm_tx.original_record_hash) == 64

    # Validate missing data classification
    assert "floor_number" in norm_tx.missing_fields_taxonomy
    assert norm_tx.missing_fields_taxonomy["floor_number"] == MissingDataReason.NOT_PROVIDED_BY_SOURCE


def test_normalization_engine_rejection_on_fatal_missing_price():
    """Verify engine returns error when transaction price cannot be established."""
    engine = PropertyNormalizationEngine(source_id="src-zap-01", source_code="ZAPKEY_BLR")
    bad_record = {
        "registration_number": "DOC-ERR/2024",
        "registration_date": "2024-05-10",
        "price": "NaN",
        "area": 1200.0,
    }
    norm_tx, err = engine.normalize_record(bad_record, row_index=1)
    assert norm_tx is None
    assert "Amount Validation Error" in err

