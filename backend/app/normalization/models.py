"""Standardized Pydantic models and Enums for normalized Indian real estate transactions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MissingDataReason(str, Enum):
    """Classification taxonomy for missing attributes in property records."""
    UNKNOWN = "UNKNOWN"
    NOT_PROVIDED_BY_SOURCE = "NOT_PROVIDED_BY_SOURCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"
    REQUIRES_MANUAL_VERIFICATION = "REQUIRES_MANUAL_VERIFICATION"


class AreaUnit(str, Enum):
    """Supported land and built-up area measurement units."""
    SQFT = "SQFT"
    SQM = "SQM"
    SQYD = "SQYD"
    VAAR = "VAAR"
    ACRE = "ACRE"
    HECTARE = "HECTARE"
    GUNTA = "GUNTA"
    GROUND = "GROUND"
    CENT = "CENT"
    ANKANAM = "ANKANAM"
    BIGHA = "BIGHA"
    BISWA = "BISWA"
    MARLA = "MARLA"
    KANAL = "KANAL"
    COTTAH = "COTTAH"
    CHATAK = "CHATAK"
    KUZHI = "KUZHI"
    MAA = "MAA"


class BoundaryType(str, Enum):
    """Type and verification level of geospatial boundaries."""
    POINT_APPROXIMATE = "POINT_APPROXIMATE"          # Rough geocoded point from address/locality
    POINT_VERIFIED = "POINT_VERIFIED"                # Surveyor verified GPS point
    CADASTRAL_PARCEL = "CADASTRAL_PARCEL"            # PostGIS polygon from state revenue / BhuNaksha
    MUNICIPAL_WARD = "MUNICIPAL_WARD"                # Ward polygon from local urban body (e.g. BBMP)
    VILLAGE_BOUNDARY = "VILLAGE_BOUNDARY"            # Revenue village / Mauza cadastral map


class SpatialProximityFeatures(BaseModel):
    """Derived institutional geospatial metrics for hedonic and ML property valuation."""
    distance_to_metro_km: Optional[float] = None
    distance_to_railway_km: Optional[float] = None
    distance_to_arterial_road_km: Optional[float] = None
    distance_to_school_km: Optional[float] = None
    distance_to_hospital_km: Optional[float] = None
    municipal_ward: Optional[str] = None
    nearby_transaction_density_1km: Optional[int] = None
    geographic_comparables_count_2km: Optional[int] = None
    is_spatial_derived: bool = False


class CadastralParcelMetadata(BaseModel):
    """Official Indian revenue and cadastral land parcel identifiers."""
    survey_number: Optional[str] = None           # e.g., '142/3B' (South/West India)
    gat_number: Optional[str] = None              # e.g., 'Gat No. 89' (Maharashtra)
    hissa_number: Optional[str] = None            # Sub-division number
    ward_number: Optional[str] = None             # Municipal corporation ward (e.g. BBMP Ward 85)
    revenue_village: Optional[str] = None         # Revenue village / Mauza
    hobli_or_circle: Optional[str] = None         # Revenue Hobli or Circle
    khata_type: Optional[str] = None              # e.g., 'A Khata', 'B Khata', 'E-Khata' (Karnataka)
    patta_chitta_number: Optional[str] = None     # Tamil Nadu Patta/Chitta reference
    khasra_number: Optional[str] = None           # North India Khasra / Khewat / Khatoni
    boundary_type: BoundaryType = BoundaryType.POINT_APPROXIMATE
    is_cadastral_verified: bool = False           # Only true if verified against official state portal


class NormalizedTransactionRecord(BaseModel):
    """Canonical representation of an Indian property transaction deed."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 1. Transaction Economics & Registration
    transaction_id: str
    registration_reference: str
    registration_date: datetime
    transaction_quarter: str  # e.g., '2024-Q3'
    transaction_amount: float
    currency: str = "INR"
    transaction_type: str = "REGISTRATION"  # REGISTRATION, RESALE, NEW_SALE, LEASE, MORTGAGE
    price_per_sqft: float
    guideline_rate_per_sqft: Optional[float] = None
    deviation_from_guideline_pct: Optional[float] = None

    # 2. Location & Administrative Geography
    country: str = "India"
    state: str
    district: str
    sub_district: Optional[str] = None
    city: Optional[str] = None
    locality: str
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    original_latitude: Optional[float] = None
    original_longitude: Optional[float] = None
    coordinate_precision_digits: Optional[int] = None
    sro_office: Optional[str] = None

    # 3. Revenue Land & Cadastral Metadata
    cadastral: CadastralParcelMetadata = Field(default_factory=CadastralParcelMetadata)

    # 4. Spatial Features & Valuation Infrastructure
    spatial_features: SpatialProximityFeatures = Field(default_factory=SpatialProximityFeatures)

    # 5. Property Attributes
    project_name: str
    unit_number: Optional[str] = None
    property_type: str  # e.g. High-Rise Apartment, Residential Plot, Independent Villa, Commercial Office
    property_subtype: Optional[str] = None
    carpet_area_sqft: float
    built_up_area_sqft: Optional[float] = None
    super_built_up_area_sqft: Optional[float] = None
    land_area_sqft: Optional[float] = None
    original_area_value: float
    original_area_unit: str
    construction_year: Optional[int] = None
    age_years: Optional[int] = None
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None

    # 6. Provenance & Audit Traceability
    source_id: str
    source_reference: str
    acquisition_timestamp: datetime
    original_record_hash: str
    fingerprint_hash: str
    dataset_version: Optional[str] = None
    verification_status: str = "VERIFIED_EMPIRICAL_DEED"
    is_verified_deed: bool = True
    is_asking_price: bool = False

    # 7. Missing Data & Diagnostic Map
    missing_fields_taxonomy: Dict[str, MissingDataReason] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
