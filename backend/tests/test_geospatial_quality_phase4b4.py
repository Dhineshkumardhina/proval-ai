"""Unit tests for Phase 4B-4 Indian Geospatial Data Quality, Cadastral & Regional Units Engine."""

import pytest
from app.normalization.geo_normalizer import (
    normalize_state,
    normalize_district,
    normalize_subdistrict,
    normalize_city,
    normalize_pincode,
    validate_and_normalize_coordinates,
    haversine_distance_km,
)
from app.normalization.unit_converter import (
    parse_and_normalize_area,
    REGIONAL_CONVERSIONS,
)
from app.normalization.models import (
    AreaUnit,
    BoundaryType,
    CadastralParcelMetadata,
    SpatialProximityFeatures,
    NormalizedTransactionRecord,
)
from app.normalization.engine import PropertyNormalizationEngine


def test_administrative_geography_normalization():
    """Verify Indian State, District, Subdistrict and City normalization."""
    # State aliases
    st1, _ = normalize_state("tn")
    assert st1 == "Tamil Nadu"
    st2, _ = normalize_state("mh")
    assert st2 == "Maharashtra"
    st3, _ = normalize_state("national capital territory of delhi")
    assert st3 == "Delhi"

    # District canonicalization
    d1, _ = normalize_district("poona")
    assert d1 == "Pune"
    d2, _ = normalize_district("madras")
    assert d2 == "Chennai"
    d3, _ = normalize_district("vizag")
    assert d3 == "Visakhapatnam"

    # Subdistrict / Taluk canonicalization
    sd1, _ = normalize_subdistrict("bangalore south")
    assert sd1 == "Bengaluru South"
    sd2, _ = normalize_subdistrict("serilingampally")
    assert sd2 == "Serilingampally"
    sd3, _ = normalize_subdistrict("andheri")
    assert sd3 == "Andheri"

    # City canonicalization
    c1, _ = normalize_city("blr")
    assert c1 == "Bengaluru"
    c2, _ = normalize_city("bombay")
    assert c2 == "Mumbai"
    c3, _ = normalize_city("gurgaon")
    assert c3 == "Gurugram"


def test_pincode_postal_circle_cross_validation():
    """Verify PIN code 6-digit structure and cross-reference with postal circle states."""
    # Valid Bengaluru PIN matching Karnataka (56)
    pin1, err1 = normalize_pincode("560066", expected_state="Karnataka")
    assert err1 is None
    assert pin1 == "560066"

    # PIN mismatching declared state (e.g., Delhi PIN 110001 given for Maharashtra)
    pin2, err2 = normalize_pincode("110001", expected_state="Maharashtra")
    assert pin2 == "110001"
    assert "mismatches declared state 'Maharashtra'" in err2

    # Malformed PIN
    pin3, err3 = normalize_pincode("012345")
    assert pin3 is None
    assert "Invalid Indian PIN code format" in err3


def test_coordinate_validation_and_precision_preservation():
    """Verify national and state bounding boxes, precision capture, and coordinate retention."""
    # Valid high-precision coordinates (Bengaluru tech park)
    res = validate_and_normalize_coordinates("12.9351789", "77.6244832", state="Karnataka")
    assert res.error_message is None
    assert res.latitude == 12.935179
    assert res.longitude == 77.624483
    assert res.original_latitude == 12.9351789
    assert res.original_longitude == 77.6244832
    assert res.precision_digits == 7

    # Inverted coordinates inside India
    res_inv = validate_and_normalize_coordinates(77.624483, 12.935178, state="Karnataka")
    assert res_inv.error_message is None
    assert res_inv.latitude == 12.935178
    assert res_inv.longitude == 77.624483

    # Coordinates falling completely outside India (e.g. New York)
    res_intl = validate_and_normalize_coordinates(40.7128, -74.0060)
    assert "outside Indian geographic boundaries" in res_intl.error_message
    assert res_intl.latitude is None

    # Coordinates inside India but outside specified state boundary
    # Mumbai coordinates (Lat 19.076, Lon 72.877) claimed to be in Karnataka
    res_mismatch = validate_and_normalize_coordinates(19.076, 72.877, state="Karnataka")
    assert res_mismatch.latitude is None
    assert "outside authoritative boundary for Karnataka" in res_mismatch.error_message


def test_regional_area_conversions_state_specific():
    """Verify state-specific land measurements (UP Bigha vs Bengal Bigha, Ankanam, Ground, Marla)."""
    # 1. Uttar Pradesh Bigha (Standard Pukka Bigha = 27,000 sqft)
    sqft_up, orig_val_up, orig_unit_up, _ = parse_and_normalize_area(1.0, "bigha", state="Uttar Pradesh")
    assert orig_unit_up == "BIGHA"
    assert orig_val_up == 1.0
    assert sqft_up == 27000.0

    # 2. West Bengal Bigha (Standard Cottah based = 14,400 sqft)
    sqft_wb, orig_val_wb, orig_unit_wb, _ = parse_and_normalize_area(1.0, "bigha", state="West Bengal")
    assert orig_unit_wb == "BIGHA"
    assert sqft_wb == 14400.0

    # 3. Haryana Marla & Kanal (1 Marla = 272.25 sqft, 1 Kanal = 5445 sqft)
    sqft_marla, _, _, _ = parse_and_normalize_area(2.0, "marla", state="Haryana")
    assert sqft_marla == 544.5

    sqft_kanal, _, _, _ = parse_and_normalize_area(1.0, "kanal", state="Haryana")
    assert sqft_kanal == 5445.0

    # 4. Tamil Nadu Ground (2400 sqft) & Kuzhi (144 sqft)
    sqft_gr, _, _, _ = parse_and_normalize_area(2.0, "ground", state="Tamil Nadu")
    assert sqft_gr == 4800.0

    sqft_kuzhi, _, _, _ = parse_and_normalize_area(10.0, "kuzhi", state="Tamil Nadu")
    assert sqft_kuzhi == 1440.0

    # 5. Andhra Pradesh Ankanam (72 sqft)
    sqft_ank, _, _, _ = parse_and_normalize_area(10.0, "ankanam", state="Andhra Pradesh")
    assert sqft_ank == 720.0


def test_haversine_distance_calculation():
    """Verify great-circle distance between two known Indian landmarks."""
    # Vidhana Soudha (12.9797, 77.5907) to Kempegowda Intl Airport (13.1986, 77.7066) ~27-28 km
    dist = haversine_distance_km(12.9797, 77.5907, 13.1986, 77.7066)
    assert 26.0 <= dist <= 29.0


def test_cadastral_metadata_and_spatial_features_in_normalization():
    """Verify normalization engine retains Survey/Gat numbers, parcel boundaries, and spatial proximity."""
    engine = PropertyNormalizationEngine(source_id="src-bhu-01", source_code="BHU_PUNE")

    raw_record = {
        "registration_number": "MAH-PUN-8831/2024",
        "registration_date": "2024-06-20",
        "price": "₹95 Lakhs",
        "area": 2.5,
        "unit": "gunta",
        "state": "Maharashtra",
        "district": "Pune",
        "sub_district": "Haveli",
        "locality": "Wagholi",
        "pincode": "412207",
        "project": "Riverview Enclave",
        "property_type": "Residential Plot",
        "sro_office": "Haveli SRO 4",
        "latitude": 18.579342,
        "longitude": 73.982315,
        "survey_number": "Survey 112",
        "gat_number": "Gat No. 45/2",
        "hissa_number": "3B",
        "ward_number": "PMC Ward 14",
        "revenue_village": "Wagholi",
        "is_cadastral_verified": True,
        "is_gps_verified": True,
        "spatial_features": {
            "distance_to_metro_km": 4.2,
            "distance_to_railway_km": 14.5,
            "distance_to_arterial_road_km": 0.35,
            "distance_to_school_km": 1.1,
            "distance_to_hospital_km": 2.4,
            "nearby_transaction_density_1km": 38,
            "geographic_comparables_count_2km": 19,
        },
    }

    norm_tx, err = engine.normalize_record(raw_record, row_index=1, dataset_version="v2.1.0")
    assert err is None
    assert norm_tx is not None

    # Verify Area normalization (2.5 Gunta * 1089 = 2722.5 sqft)
    assert norm_tx.carpet_area_sqft == 2722.5
    assert norm_tx.original_area_value == 2.5
    assert norm_tx.original_area_unit == "GUNTA"

    # Verify Cadastral metadata
    assert norm_tx.cadastral.survey_number == "Survey 112"
    assert norm_tx.cadastral.gat_number == "Gat No. 45/2"
    assert norm_tx.cadastral.hissa_number == "3B"
    assert norm_tx.cadastral.revenue_village == "Wagholi"
    assert norm_tx.cadastral.ward_number == "PMC Ward 14"
    assert norm_tx.cadastral.is_cadastral_verified is True
    assert norm_tx.cadastral.boundary_type == BoundaryType.CADASTRAL_PARCEL

    # Verify Spatial features
    assert norm_tx.spatial_features.is_spatial_derived is True
    assert norm_tx.spatial_features.distance_to_metro_km == 4.2
    assert norm_tx.spatial_features.distance_to_railway_km == 14.5
    assert norm_tx.spatial_features.nearby_transaction_density_1km == 38
    assert norm_tx.spatial_features.geographic_comparables_count_2km == 19

    # Verify Original coordinate precision
    assert norm_tx.original_latitude == 18.579342
    assert norm_tx.original_longitude == 73.982315
    assert norm_tx.coordinate_precision_digits == 6

