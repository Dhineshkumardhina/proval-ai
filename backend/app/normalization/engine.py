"""Core Indian property transaction normalization engine."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.normalization.models import (
    BoundaryType,
    CadastralParcelMetadata,
    MissingDataReason,
    NormalizedTransactionRecord,
    SpatialProximityFeatures,
)
from app.normalization.unit_converter import parse_and_normalize_area
from app.normalization.currency_normalizer import normalize_transaction_amount
from app.normalization.geo_normalizer import (
    normalize_state,
    normalize_district,
    normalize_subdistrict,
    normalize_city,
    normalize_pincode,
    validate_and_normalize_coordinates,
)
from app.services.ingestion_service import normalize_date, normalize_property_type

logger = logging.getLogger("propval.normalization")


class PropertyNormalizationEngine:
    """Standardizes heterogeneous real estate records into canonical PropVal AI schema."""

    def __init__(self, source_id: str, source_code: str):
        self.source_id = source_id
        self.source_code = source_code

    def compute_record_fingerprint(
        self,
        state: str,
        district: str,
        sro_office: str,
        reg_number: str,
        reg_year: str,
        unit_number: Optional[str] = None,
    ) -> str:
        """Deterministic hash for duplicate deed prevention."""
        canonical = (
            f"{state.strip().upper()}|{district.strip().upper()}|"
            f"{sro_office.strip().upper()}|{reg_year.strip()}|"
            f"{reg_number.strip().upper()}|{(unit_number or '').strip().upper()}"
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def normalize_record(
        self,
        raw_row: Dict[str, Any],
        row_index: int,
        dataset_version: Optional[str] = None,
    ) -> Tuple[Optional[NormalizedTransactionRecord], Optional[str]]:
        """Convert a single raw transaction payload into a NormalizedTransactionRecord.

        Returns:
            (normalized_record, error_reason)
        """
        missing_map: Dict[str, MissingDataReason] = {}

        # 1. Transaction Amount & Currency
        raw_amount = (
            raw_row.get("transaction_amount")
            or raw_row.get("price")
            or raw_row.get("registered_price")
            or raw_row.get("sale_amount")
            or raw_row.get("value")
            or raw_row.get("agreement_value")
        )
        norm_amount, amount_err = normalize_transaction_amount(raw_amount)
        if norm_amount is None:
            return None, f"Amount Validation Error: {amount_err}"

        # Preliminary State identification for regional conversion
        prelim_state = str(raw_row.get("state") or raw_row.get("circle") or "Karnataka").strip()
        state_name, state_err = normalize_state(prelim_state)
        if state_err:
            missing_map["state"] = MissingDataReason.UNKNOWN

        # 2. Area & Unit Normalization with Regional Rules
        raw_area = (
            raw_row.get("carpet_area_sqft")
            or raw_row.get("carpet_area")
            or raw_row.get("area")
            or raw_row.get("size")
            or raw_row.get("built_up_area")
        )
        raw_unit = raw_row.get("unit") or raw_row.get("area_unit") or raw_row.get("measurement")
        norm_sqft, orig_area_val, orig_unit, area_err = parse_and_normalize_area(
            raw_area, raw_unit, state=state_name
        )
        if norm_sqft is None:
            return None, f"Area Validation Error: {area_err}"

        # Bound checks: Carpet area must be plausible for an Indian property
        if norm_sqft < 50.0 or norm_sqft > 100000.0:
            return None, f"Carpet area {norm_sqft:.1f} sqft falls outside admissible physical range (50 - 100,000 sqft)"

        # Built-up Area & Super Built-up Area Normalization
        raw_bua = raw_row.get("built_up_area_sqft") or raw_row.get("built_up_area") or raw_row.get("bua")
        norm_bua_sqft = None
        if raw_bua is not None:
            norm_bua, _, _, _ = parse_and_normalize_area(raw_bua, raw_unit, state=state_name)
            norm_bua_sqft = norm_bua

        raw_sbua = (
            raw_row.get("super_built_up_area_sqft")
            or raw_row.get("super_built_up_area")
            or raw_row.get("sbua")
            or raw_row.get("saleable_area")
        )
        norm_sbua_sqft = None
        if raw_sbua is not None:
            norm_sbua, _, _, _ = parse_and_normalize_area(raw_sbua, raw_unit, state=state_name)
            norm_sbua_sqft = norm_sbua

        # 3. Registration Date & Quarter
        raw_date = (
            raw_row.get("registration_date")
            or raw_row.get("date")
            or raw_row.get("sale_date")
            or raw_row.get("deed_date")
            or raw_row.get("agreement_date")
        )
        norm_date, quarter, date_err = normalize_date(raw_date)
        if norm_date is None or quarter is None:
            return None, f"Date Validation Error: {date_err}"

        # 4. Geographic & Administrative Normalization
        raw_dist = raw_row.get("district") or raw_row.get("city") or "Bengaluru Urban"
        district_name, dist_err = normalize_district(raw_dist)
        if dist_err:
            missing_map["district"] = MissingDataReason.UNKNOWN

        raw_city_input = raw_row.get("city") or raw_dist
        city_name, _ = normalize_city(raw_city_input)

        raw_subdist = raw_row.get("sub_district") or raw_row.get("taluk") or raw_row.get("tehsil") or raw_row.get("mandal")
        subdistrict_name, subdist_err = normalize_subdistrict(raw_subdist)
        if not subdistrict_name:
            missing_map["sub_district"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        locality = str(raw_row.get("locality") or raw_row.get("area_name") or raw_row.get("micro_market") or "General Locality").strip().title()

        raw_pin = raw_row.get("pincode") or raw_row.get("postal_code") or raw_row.get("pin_code")
        pin_clean, pin_err = normalize_pincode(raw_pin, expected_state=state_name)
        if pin_err and not pin_clean:
            missing_map["postal_code"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        # 5. Coordinate Bounds, Precision Preservation & PostGIS Preparation
        raw_lat = raw_row.get("latitude") or raw_row.get("lat")
        raw_lon = raw_row.get("longitude") or raw_row.get("lon") or raw_row.get("long")
        coord_res = validate_and_normalize_coordinates(
            raw_lat, raw_lon, state=state_name
        )
        lat_clean, lon_clean, coord_err = coord_res.latitude, coord_res.longitude, coord_res.error_message
        orig_lat, orig_lon, precision_digits = coord_res.original_latitude, coord_res.original_longitude, coord_res.precision_digits
        if coord_err:
            missing_map["coordinates"] = MissingDataReason.INVALID
        elif lat_clean is None:
            missing_map["coordinates"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        # 6. Revenue Land & Cadastral Metadata Extraction
        survey_no = raw_row.get("survey_number") or raw_row.get("sy_no") or raw_row.get("survey_no")
        gat_no = raw_row.get("gat_number") or raw_row.get("gat_no")
        hissa_no = raw_row.get("hissa_number") or raw_row.get("hissa_no")
        ward_no = raw_row.get("ward_number") or raw_row.get("ward_no") or raw_row.get("ward")
        rev_village = raw_row.get("revenue_village") or raw_row.get("village") or raw_row.get("mauza")
        hobli = raw_row.get("hobli") or raw_row.get("circle")
        khata = raw_row.get("khata_type") or raw_row.get("khata")
        patta = raw_row.get("patta_number") or raw_row.get("patta_chitta")
        khasra = raw_row.get("khasra_number") or raw_row.get("khasra") or raw_row.get("khewat")

        cadastral_verified = bool(raw_row.get("is_cadastral_verified", False))
        boundary_type = (
            BoundaryType.CADASTRAL_PARCEL if (cadastral_verified and (survey_no or gat_no or khasra))
            else (BoundaryType.POINT_VERIFIED if (lat_clean and raw_row.get("is_gps_verified"))
                  else BoundaryType.POINT_APPROXIMATE)
        )

        cadastral_meta = CadastralParcelMetadata(
            survey_number=str(survey_no).strip() if survey_no else None,
            gat_number=str(gat_no).strip() if gat_no else None,
            hissa_number=str(hissa_no).strip() if hissa_no else None,
            ward_number=str(ward_no).strip() if ward_no else None,
            revenue_village=str(rev_village).strip().title() if rev_village else None,
            hobli_or_circle=str(hobli).strip().title() if hobli else None,
            khata_type=str(khata).strip() if khata else None,
            patta_chitta_number=str(patta).strip() if patta else None,
            khasra_number=str(khasra).strip() if khasra else None,
            boundary_type=boundary_type,
            is_cadastral_verified=cadastral_verified,
        )

        # 7. Spatial Features (Future Valuation Infrastructure)
        spatial_data = raw_row.get("spatial_features") or {}
        spatial_features = SpatialProximityFeatures(
            distance_to_metro_km=spatial_data.get("distance_to_metro_km") or raw_row.get("distance_to_metro_km"),
            distance_to_railway_km=spatial_data.get("distance_to_railway_km") or raw_row.get("distance_to_railway_km"),
            distance_to_arterial_road_km=spatial_data.get("distance_to_arterial_road_km") or raw_row.get("distance_to_arterial_road_km"),
            distance_to_school_km=spatial_data.get("distance_to_school_km") or raw_row.get("distance_to_school_km"),
            distance_to_hospital_km=spatial_data.get("distance_to_hospital_km") or raw_row.get("distance_to_hospital_km"),
            municipal_ward=cadastral_meta.ward_number or raw_row.get("municipal_ward"),
            nearby_transaction_density_1km=spatial_data.get("nearby_transaction_density_1km") or raw_row.get("nearby_transaction_density_1km"),
            geographic_comparables_count_2km=spatial_data.get("geographic_comparables_count_2km") or raw_row.get("geographic_comparables_count_2km"),
            is_spatial_derived=bool(spatial_data or raw_row.get("distance_to_metro_km")),
        )

        # 8. Property Physical Classifications
        raw_prop_type = raw_row.get("property_type") or raw_row.get("category") or raw_row.get("type")
        prop_type = normalize_property_type(raw_prop_type)

        proj_name = str(
            raw_row.get("project_name")
            or raw_row.get("project")
            or raw_row.get("building")
            or raw_row.get("society")
            or "Standalone Development"
        ).strip()

        unit_no = raw_row.get("unit_number") or raw_row.get("flat_no") or raw_row.get("unit")
        unit_str = str(unit_no).strip() if unit_no is not None else None
        if not unit_str:
            missing_map["unit_number"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        floor_no = raw_row.get("floor_number") or raw_row.get("floor_no") or raw_row.get("floor")
        floor_int = int(floor_no) if floor_no is not None and str(floor_no).isdigit() else None
        if floor_int is None:
            missing_map["floor_number"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        total_floors = raw_row.get("total_floors") or raw_row.get("floors")
        total_floors_int = int(total_floors) if total_floors is not None and str(total_floors).isdigit() else None
        if total_floors_int is None:
            missing_map["total_floors"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        # 9. Guideline Rate & Deviation
        raw_guideline = raw_row.get("guideline_rate_per_sqft") or raw_row.get("circle_rate") or raw_row.get("ready_reckoner_rate")
        guideline_rate = None
        deviation_pct = None
        if raw_guideline is not None:
            try:
                guideline_rate = float(raw_guideline)
                if guideline_rate > 0:
                    deviation_pct = round(((norm_amount / norm_sqft - guideline_rate) / guideline_rate) * 100.0, 2)
            except (ValueError, TypeError):
                missing_map["guideline_rate_per_sqft"] = MissingDataReason.INVALID
        else:
            missing_map["guideline_rate_per_sqft"] = MissingDataReason.NOT_PROVIDED_BY_SOURCE

        # 10. Provenance & Registration Identity
        sro = str(raw_row.get("sro_office") or raw_row.get("sro") or "Sub-Registrar Office").strip()
        reg_no = str(raw_row.get("registration_number") or raw_row.get("doc_no") or f"REG-{row_index}").strip()
        reg_year = str(norm_date.year)

        fingerprint = self.compute_record_fingerprint(
            state=state_name,
            district=district_name,
            sro_office=sro,
            reg_number=reg_no,
            reg_year=reg_year,
            unit_number=unit_str,
        )

        canonical_payload_str = json.dumps(raw_row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        raw_hash = hashlib.sha256(canonical_payload_str.encode("utf-8")).hexdigest()

        tx_record = NormalizedTransactionRecord(
            transaction_id=f"TX-{self.source_code}-{fingerprint[:12].upper()}",
            registration_reference=reg_no,
            registration_date=norm_date,
            transaction_quarter=quarter,
            transaction_amount=norm_amount,
            currency="INR",
            transaction_type=str(raw_row.get("deed_type") or raw_row.get("transaction_type") or "REGISTRATION").upper(),
            price_per_sqft=round(norm_amount / norm_sqft, 2),
            guideline_rate_per_sqft=guideline_rate,
            deviation_from_guideline_pct=deviation_pct,
            country="India",
            state=state_name,
            district=district_name,
            sub_district=subdistrict_name,
            city=city_name,
            locality=locality,
            postal_code=pin_clean,
            latitude=lat_clean,
            longitude=lon_clean,
            original_latitude=orig_lat,
            original_longitude=orig_lon,
            coordinate_precision_digits=precision_digits,
            sro_office=sro,
            cadastral=cadastral_meta,
            spatial_features=spatial_features,
            project_name=proj_name,
            unit_number=unit_str,
            property_type=prop_type,
            property_subtype=raw_row.get("property_subtype"),
            carpet_area_sqft=norm_sqft,
            built_up_area_sqft=norm_bua_sqft,
            super_built_up_area_sqft=norm_sbua_sqft,
            land_area_sqft=norm_sqft if prop_type == "Residential Plot" else None,
            original_area_value=orig_area_val,
            original_area_unit=orig_unit,
            construction_year=raw_row.get("construction_year"),
            age_years=raw_row.get("age_years"),
            floor_number=floor_int,
            total_floors=total_floors_int,
            source_id=self.source_id,
            source_reference=sro,
            acquisition_timestamp=datetime.now(timezone.utc),
            original_record_hash=raw_hash,
            fingerprint_hash=fingerprint,
            dataset_version=dataset_version,
            verification_status="VERIFIED_EMPIRICAL_DEED" if raw_row.get("is_verified", True) else "UNVERIFIED",
            is_verified_deed=bool(raw_row.get("is_verified", True)),
            is_asking_price=False,
            missing_fields_taxonomy=missing_map,
            raw_payload=raw_row,
        )

        return tx_record, None
