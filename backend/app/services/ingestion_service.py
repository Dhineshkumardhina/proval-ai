"""Dataset ingestion pipeline, quality engine, and normalization service."""

import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    RejectedRecordModel,
    DuplicateRecordModel,
    DataQualityReportModel,
)
from app.services.privacy_service import scrub_raw_payload_dict

COLUMN_SYNONYMS = {
    "price": [
        "price", "transaction_price", "registered_price", "sale_amount",
        "value", "declared_value", "agreement_value", "cost", "total_price"
    ],
    "area": [
        "carpet_area", "carpet_area_sqft", "area", "size", "sqft",
        "carpet_sqft", "built_up_area", "super_built_up_area", "area_sqft"
    ],
    "area_unit": [
        "unit", "area_unit", "unit_of_measure", "measurement", "uom"
    ],
    "project": [
        "project", "project_name", "society", "building", "property_name",
        "apartment_name", "development"
    ],
    "locality": [
        "locality", "sector", "area_name", "sub_market", "location",
        "micro_market", "neighborhood"
    ],
    "city": [
        "city", "metro", "region", "district", "town"
    ],
    "date": [
        "date", "sale_date", "reg_date", "transaction_date", "registration_date",
        "deed_date", "agreement_date"
    ],
    "property_type": [
        "property_type", "type", "asset_type", "bhk", "configuration", "category"
    ],
    "floor": [
        "floor", "floor_no", "level", "unit_floor"
    ],
    "total_floors": [
        "total_floors", "floors", "height", "building_floors"
    ],
    "pincode": [
        "pincode", "pin_code", "postal_code", "zip"
    ],
    "guideline_rate": [
        "circle_rate", "guideline_rate", "ready_reckoner_rate", "sro_rate", "circle_rate_per_sqft"
    ],
    "latitude": [
        "lat", "latitude", "y"
    ],
    "longitude": [
        "lon", "long", "longitude", "x"
    ],
}


def sanitize_csv_formula_injection(val: Any) -> str:
    """Sanitize text to neutralize spreadsheet formula injection (CSV/DDE attacks).

    If text begins with '=', '+', '-', '@', '\t', or '\r', prefix with a single quote.
    """
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


def normalize_currency(raw_val: Any) -> Optional[float]:
    """Parse Indian currency representations into numeric INR (e.g. '₹1.45 Cr' -> 14,500,000)."""
    if raw_val is None or (isinstance(raw_val, float) and math.isnan(raw_val)):
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)

    s = str(raw_val).strip()
    if not s or s.lower() in ["nan", "null", "none", "na"]:
        return None

    # Remove currency symbol and spaces
    clean = re.sub(r"[₹$,\s]", "", s).lower()

    try:
        # Match Crores (Cr)
        if "cr" in clean or "crore" in clean:
            num = float(re.findall(r"[\d\.]+", clean)[0])
            return num * 10000000.0
        # Match Lakhs (L / Lakh)
        if "l" in clean or "lakh" in clean:
            num = float(re.findall(r"[\d\.]+", clean)[0])
            return num * 100000.0
        # Direct numeric parse
        return float(clean)
    except Exception:
        return None


def normalize_area(raw_area: Any, raw_unit: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
    """Convert multiple Indian land/carpet area measurement units to square feet."""
    if raw_area is None or (isinstance(raw_area, float) and math.isnan(raw_area)):
        return None, "Missing area value"

    unit_str = str(raw_unit).lower().strip() if raw_unit else ""
    val: Optional[float] = None

    if isinstance(raw_area, (int, float)):
        val = float(raw_area)
    else:
        s = str(raw_area).lower().strip()
        # Check if unit is embedded in area string (e.g. "120 sq yd", "105 sqm")
        if "sq yd" in s or "sq yard" in s or "gaj" in s:
            unit_str = "sq_yd"
        elif "sq m" in s or "sqm" in s or "sq meter" in s:
            unit_str = "sq_m"
        elif "gunta" in s:
            unit_str = "gunta"
        elif "ground" in s:
            unit_str = "ground"

        clean = re.sub(r"[^\d\.]", "", s)
        try:
            val = float(clean)
        except Exception:
            return None, f"Unparseable area string: '{raw_area}'"

    if val is None or val <= 0:
        return None, "Area must be greater than zero"

    # Multipliers to Square Feet
    if any(u in unit_str for u in ["sq_yd", "sq yd", "yard", "gaj"]):
        return round(val * 9.0, 2), None
    if any(u in unit_str for u in ["sq_m", "sq m", "sqm", "meter"]):
        return round(val * 10.7639, 2), None
    if "gunta" in unit_str:
        return round(val * 1089.0, 2), None
    if "ground" in unit_str:
        return round(val * 2400.0, 2), None

    # Default assumed square feet
    return round(val, 2), None


def normalize_date(raw_date: Any) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
    """Parse transaction dates and compute transaction quarter (e.g. '2024-Q3')."""
    if raw_date is None or (isinstance(raw_date, float) and math.isnan(raw_date)):
        return None, None, "Missing transaction date"

    dt = None
    if isinstance(raw_date, datetime):
        dt = raw_date if raw_date.tzinfo else raw_date.replace(tzinfo=timezone.utc)
    elif isinstance(raw_date, pd.Timestamp):
        dt = raw_date.to_pydatetime()
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    else:
        date_str = str(raw_date).strip()
        for fmt in [
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%b-%Y", "%d %b %Y", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%SZ"
        ]:
            try:
                parsed = datetime.strptime(date_str, fmt)
                dt = parsed.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

    if not dt:
        return None, None, f"Unparseable date format: '{raw_date}'"

    now = datetime.now(timezone.utc)
    if dt > now:
        return None, None, f"Impossible future transaction date: {dt.strftime('%Y-%m-%d')}"
    if dt.year < 1990:
        return None, None, f"Transaction date older than institutional threshold (1990): {dt.year}"

    quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
    return dt, quarter, None


def normalize_property_type(raw_type: Any) -> str:
    """Normalize raw property classification strings into canonical categories."""
    if not raw_type or pd.isna(raw_type):
        return "High-Rise Apartment"
    s = str(raw_type).lower().strip()
    if any(k in s for k in ["villa", "bungalow", "row house"]):
        return "Gated Villa"
    if any(k in s for k in ["floor", "independent floor", "builder floor"]):
        return "Independent Floor"
    if any(k in s for k in ["plot", "land", "layout", "site"]):
        return "Residential Plot"
    if any(k in s for k in ["commercial", "sco", "office", "retail", "shop"]):
        return "Commercial SCO"
    return "High-Rise Apartment"


def compute_fingerprint(
    city: str, locality: str, project: str, area: float, price: float, date_str: str
) -> str:
    """Generate deterministic SHA-256 hash to detect repeated/duplicate transactions."""
    raw_key = f"{city.strip().lower()}|{locality.strip().lower()}|{project.strip().lower()}|{area:.1f}|{price:.0f}|{date_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def detect_column_mapping(df_columns: List[str], custom_mapping: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Map arbitrary uploaded CSV/Excel headers to canonical internal schema keys."""
    mapping = {}
    clean_cols = {re.sub(r"[\s\-_]", "", str(c).lower()): c for c in df_columns}

    for canonical_key, synonyms in COLUMN_SYNONYMS.items():
        if custom_mapping and canonical_key in custom_mapping and custom_mapping[canonical_key] in df_columns:
            mapping[canonical_key] = custom_mapping[canonical_key]
            continue

        matched = False
        # Phase 1: Exact match against clean column names
        for syn in synonyms:
            clean_syn = re.sub(r"[\s\-_]", "", syn.lower())
            if clean_syn in clean_cols:
                mapping[canonical_key] = clean_cols[clean_syn]
                matched = True
                break

        # Phase 2: Substring inclusion match if exact match not found (skip single-char abbreviations)
        if not matched:
            for syn in synonyms:
                clean_syn = re.sub(r"[\s\-_]", "", syn.lower())
                if len(clean_syn) <= 2:
                    continue
                for clean_col, orig_col in clean_cols.items():
                    # Only match if this column is not already bound to another field
                    if orig_col not in mapping.values() and clean_syn in clean_col:
                        mapping[canonical_key] = orig_col
                        matched = True
                        break
                if matched:
                    break

    return mapping


def ingest_dataset(
    db: Session,
    file_bytes: bytes,
    filename: str,
    metadata: Dict[str, Any],
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[DatasetMetadataModel, DataQualityReportModel]:
    """Ingest CSV or Excel file, validate each row, record errors/duplicates, and compute quality metrics.

    Guarantees atomic transaction execution; rolls back on any parsing, validation, or database failure.
    """
    try:
        return _ingest_dataset_impl(db, file_bytes, filename, metadata, custom_mapping)
    except Exception:
        db.rollback()
        raise


def _ingest_dataset_impl(
    db: Session,
    file_bytes: bytes,
    filename: str,
    metadata: Dict[str, Any],
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[DatasetMetadataModel, DataQualityReportModel]:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    lower_filename = filename.lower()
    file_format = "xlsx" if (lower_filename.endswith(".xlsx") or lower_filename.endswith(".xls")) else "csv"

    # 1. Parse File to DataFrame
    if file_format == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))

    MAX_DATASET_ROWS = 50000
    if len(df) > MAX_DATASET_ROWS:
        raise ValueError(
            f"Dataset contains {len(df):,} rows, exceeding maximum institutional processing limit of {MAX_DATASET_ROWS:,} records."
        )

    df_columns = list(df.columns)
    col_map = detect_column_mapping(df_columns, custom_mapping)

    dataset = DatasetMetadataModel(
        name=metadata.get("name", filename),
        description=metadata.get("description", "Uploaded real estate transaction records"),
        source_type=metadata.get("sourceType", "user_upload"),
        license_type=metadata.get("licenseType", "commercial_restricted"),
        data_source_provenance=metadata.get("provenance", f"File '{filename}' uploaded by underwriter"),
        file_format=file_format,
        original_filename=filename,
        file_hash_sha256=file_hash,
        total_rows=len(df),
        status="INGESTING",
    )
    db.add(dataset)
    db.flush()

    valid_records = []
    seen_fingerprints: Dict[str, str] = {}
    valid_count = 0
    rejected_count = 0
    duplicate_count = 0

    city_distribution: Dict[str, int] = {}
    type_distribution: Dict[str, int] = {}
    temporal_distribution: Dict[str, int] = {}
    prices: List[float] = []

    pending_transactions: List[ImportedTransactionModel] = []
    pending_rejections: List[RejectedRecordModel] = []
    pending_duplicates: List[DuplicateRecordModel] = []

    # 2. Iterate and Validate Rows using vectorized dictionary rows (high throughput)
    records = df.to_dict(orient="records")
    for idx, row in enumerate(records):
        raw_row_data = {str(k): (None if (isinstance(v, float) and math.isnan(v)) or v is None else v) for k, v in row.items()}
        # Apply pre-persistence DPDP PII scrubbing
        raw_row_data, _, _ = scrub_raw_payload_dict(raw_row_data)

        # Extract mapped values
        raw_price = row.get(col_map.get("price"))
        raw_area = row.get(col_map.get("area"))
        raw_unit = row.get(col_map.get("area_unit"))
        raw_date = row.get(col_map.get("date"))
        raw_project = row.get(col_map.get("project"), "Unnamed Project")
        raw_locality = row.get(col_map.get("locality"), "Central Sub-Market")
        raw_city = row.get(col_map.get("city"), "Bengaluru")
        raw_prop_type = row.get(col_map.get("property_type"))
        raw_lat = row.get(col_map.get("latitude"))
        raw_lon = row.get(col_map.get("longitude"))
        raw_guideline = row.get(col_map.get("guideline_rate"))

        # Validation Rule 1: Price Check
        norm_price = normalize_currency(raw_price)
        if norm_price is None or norm_price <= 0:
            pending_rejections.append(RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                rejection_code="MISSING_PRICE",
                rejection_reason=f"Invalid or missing transaction price: '{raw_price}'",
                raw_data=raw_row_data,
            ))
            rejected_count += 1
            continue

        # Validation Rule 2: Area Check & Unit Normalization
        norm_area, area_err = normalize_area(raw_area, raw_unit)
        if norm_area is None:
            pending_rejections.append(RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                rejection_code="INVALID_AREA",
                rejection_reason=area_err or "Invalid property area",
                raw_data=raw_row_data,
            ))
            rejected_count += 1
            continue

        if norm_area < 50.0 or norm_area > 100000.0:
            pending_rejections.append(RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                rejection_code="INVALID_AREA",
                rejection_reason=f"Area out of physical bounds (50 to 100,000 sq ft): {norm_area} sq ft",
                raw_data=raw_row_data,
            ))
            rejected_count += 1
            continue

        # Validation Rule 3: Extreme Price per Sq Ft Outlier Check
        price_per_sqft = round(norm_price / norm_area, 2)
        if price_per_sqft < 500.0 or price_per_sqft > 300000.0:
            pending_rejections.append(RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                rejection_code="EXTREME_PRICE_OUTLIER",
                rejection_reason=f"Rate per sq ft ₹{price_per_sqft:,.0f} violates institutional limits (₹500 to ₹3,00,000/sq ft)",
                raw_data=raw_row_data,
            ))
            rejected_count += 1
            continue

        # Validation Rule 4: Date Validation
        norm_date, quarter, date_err = normalize_date(raw_date)
        if norm_date is None or quarter is None:
            pending_rejections.append(RejectedRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                rejection_code="IMPOSSIBLE_DATE",
                rejection_reason=date_err or "Invalid transaction date",
                raw_data=raw_row_data,
            ))
            rejected_count += 1
            continue

        # Validation Rule 5: Geographic Bounds Check (India lat: 6.5 to 37.5, lon: 68.0 to 97.5)
        lat = float(raw_lat) if raw_lat is not None and not pd.isna(raw_lat) else None
        lon = float(raw_lon) if raw_lon is not None and not pd.isna(raw_lon) else None
        if lat is not None and lon is not None:
            if not (6.5 <= lat <= 37.5 and 68.0 <= lon <= 97.5):
                pending_rejections.append(RejectedRecordModel(
                    dataset_id=dataset.id,
                    row_index=idx,
                    rejection_code="OUT_OF_BOUNDS_COORDINATES",
                    rejection_reason=f"Coordinates ({lat}, {lon}) outside Indian national territory bounding box",
                    raw_data=raw_row_data,
                ))
                rejected_count += 1
                continue

        # Validation Rule 6: Duplicate Detection via Fingerprint Hash
        date_str = norm_date.strftime("%Y-%m-%d")
        fingerprint = compute_fingerprint(
            city=str(raw_city),
            locality=str(raw_locality),
            project=str(raw_project),
            area=norm_area,
            price=norm_price,
            date_str=date_str,
        )

        if fingerprint in seen_fingerprints:
            pending_duplicates.append(DuplicateRecordModel(
                dataset_id=dataset.id,
                row_index=idx,
                fingerprint_hash=fingerprint,
                matched_transaction_id=seen_fingerprints[fingerprint],
                raw_data=raw_row_data,
            ))
            duplicate_count += 1
            continue

        # Valid Record Assembly
        tx_id = str(uuid.uuid4())
        seen_fingerprints[fingerprint] = tx_id
        prop_type = normalize_property_type(raw_prop_type)
        city_name = sanitize_csv_formula_injection(raw_city)
        locality_name = sanitize_csv_formula_injection(raw_locality)
        project_name = sanitize_csv_formula_injection(raw_project)

        guideline_rate = normalize_currency(raw_guideline)
        dev_pct = None
        if guideline_rate and guideline_rate > 0:
            dev_pct = round(((price_per_sqft - guideline_rate) / guideline_rate) * 100.0, 1)

        raw_floor = row.get(col_map.get("floor")) if col_map.get("floor") else None
        parsed_floor = 1
        if raw_floor is not None and not pd.isna(raw_floor):
            try:
                parsed_floor = int(float(str(raw_floor).strip()))
            except (ValueError, TypeError):
                parsed_floor = 1

        raw_tf = row.get(col_map.get("total_floors")) if col_map.get("total_floors") else None
        parsed_tf = 1
        if raw_tf is not None and not pd.isna(raw_tf):
            try:
                parsed_tf = int(float(str(raw_tf).strip()))
            except (ValueError, TypeError):
                parsed_tf = 1

        tx = ImportedTransactionModel(
            id=tx_id,
            dataset_id=dataset.id,
            row_index=idx,
            fingerprint_hash=fingerprint,
            city=city_name,
            locality=locality_name,
            sub_market=metadata.get("subMarket"),
            pincode=str(row.get(col_map.get("pincode"), "560001")).strip(),
            project_name=project_name,
            unit_number=str(row.get("unit_number", "")),
            property_type=prop_type,
            transaction_type="REGISTRATION",
            transaction_date=norm_date,
            transaction_quarter=quarter,
            carpet_area_sqft=norm_area,
            super_built_up_area_sqft=round(norm_area * 1.3, 2),
            floor_no=parsed_floor,
            total_floors=parsed_tf,
            transaction_price=norm_price,
            price_per_sqft=price_per_sqft,
            guideline_rate_per_sqft=guideline_rate,
            deviation_from_guideline_pct=dev_pct,
            latitude=lat,
            longitude=lon,
            is_verified_deed=True,
            data_source="imported-deed",
            raw_data=raw_row_data,
        )
        pending_transactions.append(tx)
        valid_count += 1
        prices.append(norm_price)

        # Aggregate distributions
        city_distribution[city_name] = city_distribution.get(city_name, 0) + 1
        type_distribution[prop_type] = type_distribution.get(prop_type, 0) + 1
        temporal_distribution[quarter] = temporal_distribution.get(quarter, 0) + 1

    # Batch persist validated records, rejections, and duplicates
    if pending_transactions:
        db.add_all(pending_transactions)
    if pending_rejections:
        db.add_all(pending_rejections)
    if pending_duplicates:
        db.add_all(pending_duplicates)

    # 3. Compute Statistical Quality Metrics (vectorized calculation)
    total = max(1, len(df))
    missingness_series = (df[df_columns].isna().sum() / total) * 100.0
    missingness = {col: round(float(missingness_series[col]), 2) for col in df_columns}

    price_stats = {}
    if prices:
        prices_series = pd.Series(prices)
        q25 = float(prices_series.quantile(0.25))
        q75 = float(prices_series.quantile(0.75))
        price_stats = {
            "median": round(float(prices_series.median()), 2),
            "mean": round(float(prices_series.mean()), 2),
            "min": round(float(prices_series.min()), 2),
            "max": round(float(prices_series.max()), 2),
            "q25": round(q25, 2),
            "q75": round(q75, 2),
            "iqr": round(q75 - q25, 2),
        }

    # Evaluation against institutional ML training target (>= 1,000 valid verified records)
    meets_ml = valid_count >= 1000
    if meets_ml:
        summary = f"Dataset meets minimum ML readiness threshold ({valid_count:,} valid records >= 1,000 target)."
    else:
        summary = (
            f"Dataset currently has {valid_count:,} valid records. "
            f"ML model training remains GATED pending additional empirical records to meet the 1,000-record threshold."
        )

    # 4. Finalize Dataset & Report
    dataset.total_rows = total
    dataset.valid_rows = valid_count
    dataset.rejected_rows = rejected_count
    dataset.duplicate_rows = duplicate_count
    dataset.status = "COMPLETED"
    dataset.is_usable_for_ml = meets_ml

    # Automatically set initial governance status to UNDER_REVIEW upon successful ingestion
    if dataset.approval_status == "DRAFT":
        dataset.approval_status = "UNDER_REVIEW"

    # Persist verification evidence provenance for validated transactions (Objective 7)
    from app.models.verification import VerificationEvidenceModel, TransactionLifecycleState
    evidence_items = []
    for tx in pending_transactions:
        canonical_tx_str = json.dumps({
            "fingerprint": tx.fingerprint_hash,
            "city": tx.city,
            "locality": tx.locality,
            "price": tx.transaction_price,
            "area": tx.carpet_area_sqft,
            "date": tx.transaction_date.isoformat(),
        }, sort_keys=True, separators=(",", ":"))
        tx_hash = hashlib.sha256(canonical_tx_str.encode("utf-8")).hexdigest()
        ev = VerificationEvidenceModel(
            transaction_id=tx.id,
            verification_status=TransactionLifecycleState.VERIFIED,
            verifier_id="INGESTION_SERVICE",
            verifier_method="FILE_UPLOAD_NORMALIZATION",
            source_origin=dataset.source_type,
            source_document_ref=dataset.original_filename,
            original_record_hash=tx.fingerprint_hash,
            normalized_record_hash=tx_hash,
            dataset_version="v0.1.0-draft",
            verification_evidence_details={
                "dataset_id": dataset.id,
                "row_index": tx.row_index,
                "price_per_sqft": tx.price_per_sqft,
            },
        )
        evidence_items.append(ev)
    if evidence_items:
        db.add_all(evidence_items)

    quality_report = DataQualityReportModel(
        dataset_id=dataset.id,
        total_records=total,
        valid_records=valid_count,
        rejected_records=rejected_count,
        duplicate_records=duplicate_count,
        missing_value_percentages=missingness,
        geographic_distribution=city_distribution,
        property_type_distribution=type_distribution,
        price_metrics=price_stats,
        temporal_distribution=dict(sorted(temporal_distribution.items())),
        meets_ml_criteria=meets_ml,
        readiness_summary=summary,
    )
    db.add(quality_report)
    db.commit()
    db.refresh(dataset)
    db.refresh(quality_report)

    return dataset, quality_report
