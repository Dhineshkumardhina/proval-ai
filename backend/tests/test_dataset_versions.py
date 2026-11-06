"""Comprehensive test suite for Phase 4A-5 Institutional Dataset Management & Version Snapshots."""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, Base, engine
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.dataset_version import DatasetVersionModel
from app.dataset_management.version_service import DatasetVersionService


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def seeded_dataset_with_transactions(db_session: Session):
    """Seed a test dataset with 15 verified transaction records."""
    ds = DatasetMetadataModel(
        name=f"Dataset_Version_Test_{uuid.uuid4().hex[:6]}",
        source_type="commercial_license",
        license_type="commercial_restricted",
        data_source_provenance="Institutional SRO Feed",
        file_format="api_stream",
        original_filename="stream",
        file_hash_sha256=uuid.uuid4().hex,
        status="COMPLETED",
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)

    txs = []
    for i in range(1, 16):
        tx = ImportedTransactionModel(
            dataset_id=ds.id,
            row_index=i,
            fingerprint_hash=f"FINGERPRINT-{ds.id[:8]}-{i:04d}",
            city="Bengaluru Urban",
            locality="Whitefield",
            sub_market="Mahadevapura",
            pincode="560066",
            project_name=f"Prestige Tech View {i}",
            unit_number=f"U-{i}",
            property_type="High-Rise Apartment",
            transaction_type="REGISTRATION",
            transaction_date=datetime(2024, (i % 12) + 1, 15, tzinfo=timezone.utc),
            transaction_quarter="2024-Q3",
            carpet_area_sqft=1250.0 + (i * 10),
            transaction_price=12000000.0 + (i * 200000),
            price_per_sqft=9600.0,
            guideline_rate_per_sqft=8500.0,
            latitude=12.9698,
            longitude=77.7499,
            is_verified_deed=True,
            is_asking_price=False,
            data_source="B2B_ZAPKEY_BLR",
            raw_data={"row": i},
        )
        txs.append(tx)
    db_session.add_all(txs)
    db_session.commit()

    return ds


# =========================================================================
# 1. Version Snapshot Creation & Checksum Integrity
# =========================================================================

def test_create_dataset_version_snapshot(db_session: Session, seeded_dataset_with_transactions: DatasetMetadataModel):
    """Verify version snapshot creation locks checksum and record manifests."""
    service = DatasetVersionService(db_session)
    ver = service.create_version_snapshot(
        dataset_id=seeded_dataset_with_transactions.id,
        semver_tag="v1.0.0",
        version_title="Initial Q3 Baseline Snapshot",
        created_by="senior_underwriter",
        description="First sealed snapshot of Bengaluru Urban deeds",
    )

    assert ver.semver_tag == "v1.0.0"
    assert ver.verified_records == 15
    assert len(ver.dataset_checksum_sha256) == 64
    assert len(ver.included_transaction_ids) == 15
    assert ver.geographic_distribution.get("Bengaluru Urban") == 15
    assert ver.approval_status == "DRAFT"
    assert ver.is_ml_eligible is False  # 15 < 1000 empirical target


def test_immutable_version_tag_collision(db_session: Session, seeded_dataset_with_transactions: DatasetMetadataModel):
    """Verify attempting to create duplicate semver tag on same dataset is blocked."""
    service = DatasetVersionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.create_version_snapshot(
            dataset_id=seeded_dataset_with_transactions.id,
            semver_tag="v1.0.0",
            version_title="Duplicate attempt",
            created_by="senior_underwriter",
        )
    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


# =========================================================================
# 2. Version Approval Lifecycle
# =========================================================================

def test_approve_dataset_version(db_session: Session, seeded_dataset_with_transactions: DatasetMetadataModel):
    """Verify version approval transitions status and records audit metadata."""
    service = DatasetVersionService(db_session)
    ver = (
        db_session.query(DatasetVersionModel)
        .filter(
            DatasetVersionModel.dataset_id == seeded_dataset_with_transactions.id,
            DatasetVersionModel.semver_tag == "v1.0.0",
        )
        .first()
    )
    approved = service.approve_dataset_version(
        version_id=ver.id,
        approval_status="APPROVED",
        approver_id="chief_credit_officer",
        notes="Validated against SRO Shivajinagar index",
    )
    assert approved.approval_status == "APPROVED"
    assert approved.approved_by == "chief_credit_officer"
    assert approved.approved_at is not None


# =========================================================================
# 3. Dataset Version Comparison
# =========================================================================

def test_compare_dataset_versions(db_session: Session, seeded_dataset_with_transactions: DatasetMetadataModel):
    """Verify exact diffing between two snapshots (added, removed, common records)."""
    service = DatasetVersionService(db_session)
    ver_v1 = (
        db_session.query(DatasetVersionModel)
        .filter(
            DatasetVersionModel.dataset_id == seeded_dataset_with_transactions.id,
            DatasetVersionModel.semver_tag == "v1.0.0",
        )
        .first()
    )

    # Ingest 5 more records into dataset
    new_txs = []
    for i in range(16, 21):
        tx = ImportedTransactionModel(
            dataset_id=seeded_dataset_with_transactions.id,
            row_index=i,
            fingerprint_hash=f"FINGERPRINT-NEW-{i:04d}",
            city="Bengaluru Urban",
            locality="Whitefield",
            project_name=f"Sobha New Phase {i}",
            property_type="High-Rise Apartment",
            transaction_date=datetime(2024, 11, 1, tzinfo=timezone.utc),
            transaction_quarter="2024-Q4",
            carpet_area_sqft=1500.0,
            transaction_price=15000000.0,
            price_per_sqft=10000.0,
            is_verified_deed=True,
            is_asking_price=False,
            data_source="B2B_ZAPKEY_BLR",
            raw_data={"row": i},
        )
        new_txs.append(tx)
    db_session.add_all(new_txs)
    db_session.commit()

    # Create v1.1.0 snapshot
    ver_v2 = service.create_version_snapshot(
        dataset_id=seeded_dataset_with_transactions.id,
        semver_tag="v1.1.0",
        version_title="Q4 Incremental Sync",
        created_by="data_engineer",
    )

    diff = service.compare_versions(ver_v1.id, ver_v2.id)
    assert diff.source_version == "v1.0.0"
    assert diff.target_version == "v1.1.0"
    assert diff.common_record_count == 15
    assert diff.added_record_count == 5
    assert diff.removed_record_count == 0
    assert diff.newly_verified_records == 5
    assert diff.quality_metric_changes["checksum_changed"] is True


# =========================================================================
# 4. ML Export Gating Invariant
# =========================================================================

def test_ml_export_gated_below_threshold(db_session: Session, seeded_dataset_with_transactions: DatasetMetadataModel):
    """Verify ML export strictly rejects snapshots with < 1,000 verified empirical records."""
    service = DatasetVersionService(db_session)
    ver = (
        db_session.query(DatasetVersionModel)
        .filter(
            DatasetVersionModel.dataset_id == seeded_dataset_with_transactions.id,
            DatasetVersionModel.semver_tag == "v1.0.0",
        )
        .first()
    )

    # Approve parent dataset and version snapshot to reach the empirical deed count gate
    seeded_dataset_with_transactions.approval_status = "APPROVED"
    ver.approval_status = "APPROVED"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        service.export_ml_training_manifest(ver.id)

    assert exc_info.value.status_code == 400
    assert "ML Export Gated" in exc_info.value.detail
    assert "minimum of 1,000 verified empirical deed transactions is required" in exc_info.value.detail
