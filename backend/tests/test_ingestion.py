"""Comprehensive automated tests for Dataset Ingestion, Quality Engine & ML Partitioning."""

import os
import pytest
from fastapi.testclient import TestClient
from app.services.ingestion_service import (
    normalize_currency,
    normalize_area,
    normalize_date,
    detect_column_mapping,
)


SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "samples", "sample_bengaluru_transactions.csv"
)
SAMPLE_XLSX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "samples", "sample_bengaluru_transactions.xlsx"
)


# =====================================================================
# UNIT TESTS: NORMALIZATION ENGINES (CURRENCY, AREA, DATES, MAPPINGS)
# =====================================================================

def test_normalize_currency_lakhs_crores_and_symbols():
    """Verify Indian currency parsing across numerical, Crore, Lakh and formatted text."""
    assert normalize_currency("₹1.45 Cr") == 14500000.0
    assert normalize_currency("1.20 Crore") == 12000000.0
    assert normalize_currency("95 Lakhs") == 9500000.0
    assert normalize_currency("85 L") == 8500000.0
    assert normalize_currency("₹1,42,50,000") == 14250000.0
    assert normalize_currency(18500000) == 18500000.0
    assert normalize_currency("NaN") is None
    assert normalize_currency(None) is None


def test_normalize_area_multipliers():
    """Verify area conversion to standard square feet across multiple units."""
    # sq yd -> x9
    area_yd, err_yd = normalize_area(100, "sq yd")
    assert err_yd is None
    assert area_yd == 900.0

    # sqm -> x10.7639
    area_m, err_m = normalize_area(100, "sqm")
    assert err_m is None
    assert area_m == 1076.39

    # gunta -> x1089
    area_g, err_g = normalize_area(2, "gunta")
    assert err_g is None
    assert area_g == 2178.0

    # sqft -> x1
    area_ft, err_ft = normalize_area(1250, "sqft")
    assert err_ft is None
    assert area_ft == 1250.0

    # Invalid / Zero / Negative
    assert normalize_area(0)[0] is None
    assert normalize_area(-50)[0] is None
    assert normalize_area("bad_text")[0] is None


def test_normalize_date_and_quarter_derivation():
    """Verify transaction date parsing, impossible future date detection, and quarter derivation."""
    dt, quarter, err = normalize_date("2024-03-15")
    assert err is None
    assert dt is not None
    assert dt.year == 2024 and dt.month == 3
    assert quarter == "2024-Q1"

    dt2, q2, err2 = normalize_date("19-Aug-2024")
    assert err2 is None
    assert q2 == "2024-Q3"

    # Impossible future date rejected
    _, _, future_err = normalize_date("2035-01-01")
    assert future_err is not None
    assert "future" in future_err.lower()

    # Vintage older than 1990 rejected
    _, _, old_err = normalize_date("1985-06-15")
    assert old_err is not None
    assert "1990" in old_err


def test_detect_column_mapping_synonyms():
    """Verify intelligent header synonym mapping for arbitrary real estate tables."""
    cols = ["Sale_Amount", "Carpet_SqFt", "Unit_Of_Measure", "Society_Name", "Micro_Market", "Registration_Date"]
    mapping = detect_column_mapping(cols)

    assert mapping["price"] == "Sale_Amount"
    assert mapping["area"] == "Carpet_SqFt"
    assert mapping["area_unit"] == "Unit_Of_Measure"
    assert mapping["project"] == "Society_Name"
    assert mapping["locality"] == "Micro_Market"
    assert mapping["date"] == "Registration_Date"


# =====================================================================
# INTEGRATION TESTS: CSV & EXCEL INGESTION, AUDIT & DATA QUALITY
# =====================================================================

def test_ingest_csv_dataset_and_quality_audit(client: TestClient):
    """Test full CSV file ingestion, duplicate detection, rejection audits, and quality report."""
    assert os.path.exists(SAMPLE_CSV_PATH), f"Sample CSV file {SAMPLE_CSV_PATH} must exist"

    with open(SAMPLE_CSV_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample_bengaluru_transactions.csv", file_bytes, "text/csv")},
        data={
            "name": "Bengaluru Sample Registered Deeds 2024-2025",
            "description": "Representative residential deed transactions across Bengaluru sub-markets",
            "sourceType": "academic_research",
            "licenseType": "cc_by_4_0",
            "provenance": "Mendeley / Open Data Indian Real Estate Research Benchmark",
        },
    )
    assert response.status_code == 201
    report = response.json()

    assert report["totalRecords"] == 20
    assert report["validRecords"] == 14
    assert report["rejectedRecords"] == 5
    assert report["duplicateRecords"] == 1
    assert report["validityRatePct"] == 70.0
    assert report["meetsMlCriteria"] is False  # 14 records < 1000 threshold
    assert "GATED" in report["readinessSummary"] or "threshold" in report["readinessSummary"]

    dataset_id = report["datasetId"]

    # Verify dataset catalog listing
    list_res = client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    datasets = list_res.json()
    assert any(d["id"] == dataset_id for d in datasets)

    # Verify normalized valid records
    records_res = client.get(f"/api/v1/datasets/{dataset_id}/records?limit=20")
    assert records_res.status_code == 200
    records = records_res.json()
    assert len(records) == 14
    first_record = records[0]
    assert first_record["city"] == "Bengaluru"
    assert first_record["carpetAreaSqFt"] > 0
    assert first_record["transactionPrice"] > 0
    assert first_record["pricePerSqFt"] > 0
    assert first_record["transactionQuarter"].startswith("2024-") or first_record["transactionQuarter"].startswith("2025-")

    # Verify rejected records and rejection reasons
    rejected_res = client.get(f"/api/v1/datasets/{dataset_id}/rejected")
    assert rejected_res.status_code == 200
    rejected = rejected_res.json()
    assert len(rejected) == 5
    rejection_codes = [r["rejectionCode"] for r in rejected]
    assert "MISSING_PRICE" in rejection_codes
    assert "INVALID_AREA" in rejection_codes
    assert "EXTREME_PRICE_OUTLIER" in rejection_codes
    assert "IMPOSSIBLE_DATE" in rejection_codes
    assert "OUT_OF_BOUNDS_COORDINATES" in rejection_codes

    # Verify duplicate records
    dup_res = client.get(f"/api/v1/datasets/{dataset_id}/duplicates")
    assert dup_res.status_code == 200
    duplicates = dup_res.json()
    assert len(duplicates) == 1
    assert duplicates[0]["fingerprintHash"] is not None

    # Verify readiness assessment endpoint
    readiness_res = client.get(f"/api/v1/datasets/{dataset_id}/readiness")
    assert readiness_res.status_code == 200
    readiness = readiness_res.json()
    assert readiness["validRecords"] == 14
    assert readiness["meetsMlCriteria"] is False


def test_ingest_excel_dataset(client: TestClient):
    """Test full Excel (.xlsx) file ingestion and parity with CSV processing."""
    assert os.path.exists(SAMPLE_XLSX_PATH), f"Sample Excel file {SAMPLE_XLSX_PATH} must exist"

    with open(SAMPLE_XLSX_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample_bengaluru_transactions.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={
            "name": "Bengaluru Excel Ingestion Test",
            "sourceType": "user_upload",
            "licenseType": "commercial_restricted",
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert report["totalRecords"] == 20
    assert report["validRecords"] == 14
    assert report["rejectedRecords"] == 5
    assert report["duplicateRecords"] == 1


def test_ml_preparation_out_of_time_and_spatial_split(client: TestClient):
    """Test temporal Out-of-Time train/val/test splitting and leakage protection."""
    with open(SAMPLE_CSV_PATH, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample_for_ml.csv", file_bytes, "text/csv")},
        data={
            "name": "Bengaluru ML Preparation Corpus",
            "sourceType": "academic_research",
            "licenseType": "cc_by_4_0",
        },
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["datasetId"]

    split_res = client.post(
        f"/api/v1/datasets/{dataset_id}/prepare-ml?trainRatio=0.70&valRatio=0.15&testRatio=0.15"
    )
    assert split_res.status_code == 200
    split_data = split_res.json()

    assert split_data["totalUsableRecords"] == 14
    assert split_data["trainRecords"] > 0
    assert split_data["validationRecords"] > 0
    assert split_data["testRecords"] > 0
    assert split_data["trainRecords"] + split_data["validationRecords"] + split_data["testRecords"] == 14
    assert split_data["isLeakageGuarded"] is True
    assert "train" in split_data["temporalSplit"]
    assert "test" in split_data["temporalSplit"]
    assert len(split_data["selectedFeatures"]) >= 8
    assert split_data["targetVariable"] == "transaction_price"


def test_guard_against_ml_training_on_synthetic_demonstration_data(client: TestClient):
    """Verify that attempting to prepare ML on synthetic demonstration datasets is rejected."""
    # Upload synthetic dataset
    with open(SAMPLE_CSV_PATH, "rb") as f:
        file_bytes = f.read()

    synth_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("synthetic_demo.csv", file_bytes, "text/csv")},
        data={
            "name": "Synthetic Demonstration Corpus",
            "sourceType": "synthetic_benchmark",
            "licenseType": "synthetic_demo",
        },
    )
    assert synth_res.status_code == 201
    synth_id = synth_res.json()["datasetId"]

    # Attempt to split synthetic dataset for ML
    split_res = client.post(f"/api/v1/datasets/{synth_id}/prepare-ml")
    assert split_res.status_code == 400
    err_detail = split_res.json()["detail"]
    assert "synthetic" in err_detail.lower()


def test_upload_empty_file_rejected(client: TestClient):
    """Uploading an empty 0-byte file returns HTTP 400."""
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
        data={"name": "Empty File"},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
