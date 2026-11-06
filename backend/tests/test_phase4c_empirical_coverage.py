"""Tests for Phase 4C empirical coverage tracking service and API."""

import pytest
from datetime import datetime, timezone
from app.models.dataset import ImportedTransactionModel, DatasetMetadataModel
from app.dataset_management.empirical_coverage import EmpiricalCoverageService


def test_empirical_coverage_service_synthetic_filtered_out(db_session):
    """Verify that synthetic, mock, and unverified records are strictly excluded from empirical counts."""
    # Create parent dataset
    dataset = DatasetMetadataModel(
        name="Test Ingestion Dataset",
        source_type="commercial_license",
        license_type="commercial_restricted",
        file_format="csv",
        original_filename="deeds.csv",
        file_hash_sha256="abc123hash",
        total_rows=3,
        valid_rows=3,
        status="COMPLETED",
    )
    db_session.add(dataset)
    db_session.flush()

    # 1. Synthetic demo transaction
    rec_synth = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=1,
        fingerprint_hash="hash_synth_1",
        data_source="synthetic-demo",
        city="Bengaluru",
        locality="Indiranagar",
        project_name="Demo Heights",
        property_type="APARTMENT",
        carpet_area_sqft=1200.0,
        transaction_date=datetime(2025, 6, 15, tzinfo=timezone.utc),
        transaction_quarter="2025Q2",
        transaction_price=12000000.0,
        price_per_sqft=10000.0,
        is_verified_deed=True,
        is_asking_price=False,
        raw_data={},
    )
    # 2. Unverified empirical deed
    rec_unverified = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=2,
        fingerprint_hash="hash_emp_unverified",
        data_source="propequity",
        city="Bengaluru",
        locality="Whitefield",
        project_name="Prestige Park",
        property_type="APARTMENT",
        carpet_area_sqft=1100.0,
        transaction_date=datetime(2025, 7, 20, tzinfo=timezone.utc),
        transaction_quarter="2025Q3",
        transaction_price=8000000.0,
        price_per_sqft=7272.72,
        is_verified_deed=False,  # NOT verified
        is_asking_price=False,
        raw_data={},
    )
    # 3. Verified empirical deed
    rec_empirical = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=3,
        fingerprint_hash="hash_emp_verified",
        data_source="propequity",
        city="Bengaluru",
        locality="Whitefield",
        project_name="Brigade Woods",
        property_type="APARTMENT",
        carpet_area_sqft=1350.0,
        transaction_date=datetime(2025, 8, 10, tzinfo=timezone.utc),
        transaction_quarter="2025Q3",
        transaction_price=11000000.0,
        price_per_sqft=8148.14,
        is_verified_deed=True,
        is_asking_price=False,
        raw_data={},
    )
    db_session.add_all([rec_synth, rec_unverified, rec_empirical])
    db_session.flush()

    coverage = EmpiricalCoverageService.get_empirical_coverage(db_session)
    assert coverage["total_verified_empirical_deeds"] == 1
    assert coverage["ml_eligibility_status"] == "GATED"
    assert coverage["target_threshold"] == 1000
    assert len(coverage["city_distribution"]) == 1
    assert coverage["city_distribution"][0]["city"] == "Bengaluru"
    assert coverage["city_distribution"][0]["count"] == 1
    assert coverage["property_size_brackets"]["1,000 - 1,500 sqft"] == 1
    assert coverage["price_range_brackets"]["₹1Cr - ₹2.5 Crores"] == 1


def test_empirical_coverage_api_endpoint(client, auth_headers):
    """Verify GET /api/v1/datasets/empirical-coverage endpoint integration."""
    response = client.get("/api/v1/datasets/empirical-coverage", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_verified_empirical_deeds" in data
    assert "ml_eligibility_status" in data
    assert "target_threshold" in data
    assert data["target_threshold"] == 1000
    assert "city_distribution" in data
    assert "property_size_brackets" in data
    assert "price_range_brackets" in data
