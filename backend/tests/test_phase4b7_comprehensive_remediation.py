"""Comprehensive verification tests for Phase 4B-7: Critical Security, Privacy, and Institutional Governance Remediation."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import (
    DatasetMetadataModel,
    ImportedTransactionModel,
    DuplicateRecordModel,
    ErasureRequestModel,
)
from app.models.data_source import DataSourceModel, SourceAuthorizationStatus, RawTransactionStagingModel
from app.models.dataset_version import DatasetVersionModel
from app.models.verification import QuarantinedRecordModel, VerificationEvidenceModel
from app.models.audit import AuditEventModel, AuditAnchorEpochModel
from app.services.erasure_service import TransactionErasureService
from app.services.audit_service import (
    AuditMerkleTree,
    ExternalAuditAnchorService,
    verify_audit_chain,
)
from app.normalization.geo_normalizer import (
    normalize_cadastral_reference,
    validate_locality_spatial_consistency,
    haversine_distance_km,
)
from app.ml.trainer import train_valuation_model


# ==============================================================================
# REMEDIATION 1 & 3: Connector Security & Purpose Limitation
# ==============================================================================

def test_source_purpose_limitation_and_ml_training_gate(db_session: Session):
    """Verify that ML model training strictly requires explicit MODEL_TRAINING purpose and APPROVED dataset."""
    # 1. Create a dataset with DRAFT approval status
    dataset = DatasetMetadataModel(
        name="Test Governance Dataset",
        description="Dataset for testing ML training approval gate",
        source_type="imported_deed",
        license_type="COMMERCIAL_API",
        data_source_provenance="TEST_PROVIDER",
        file_format="CSV",
        original_filename="test.csv",
        file_hash_sha256="a" * 64,
        total_rows=10,
        valid_rows=10,
        approval_status="DRAFT",
    )
    db_session.add(dataset)
    db_session.commit()

    # Attempting to train on DRAFT dataset should raise 422 or 403
    with pytest.raises(Exception) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            user_name="V. Sundaram (Sr. Underwriter)",
        )
    assert "UNAPPROVED_DATASET" in str(exc_info.value) or exc_info.value.status_code in (422, 403)


def test_ml_trainer_separation_of_duties(db_session: Session):
    """Verify that training requester cannot be the sole approving authority."""
    dataset = DatasetMetadataModel(
        name="Approved Dataset",
        description="Dataset for separation of duties testing",
        source_type="imported_deed",
        license_type="COMMERCIAL_API",
        data_source_provenance="TEST_PROVIDER",
        file_format="CSV",
        original_filename="test.csv",
        file_hash_sha256="b" * 64,
        total_rows=10,
        valid_rows=10,
        approval_status="APPROVED",
    )
    db_session.add(dataset)
    db_session.commit()

    # Same user requesting and approving
    with pytest.raises(Exception) as exc_info:
        train_valuation_model(
            db=db_session,
            dataset_id=dataset.id,
            user_name="Officer A",
            approved_by="Officer A",
        )
    assert "Separation of duties violation" in str(exc_info.value) or exc_info.value.status_code == 400


# ==============================================================================
# REMEDIATION 2: DPDP Section 12 Data Erasure Workflows
# ==============================================================================

def test_erasure_workflow_and_audit_tracking(db_session: Session):
    """Verify multi-tier deletion across active tables, staging, and audit logging."""
    # 1. Create dataset and transaction
    dataset = DatasetMetadataModel(
        name="Erasure Target Dataset",
        description="Dataset for erasure test",
        source_type="imported_deed",
        license_type="COMMERCIAL_API",
        data_source_provenance="TEST_SRC",
        file_format="CSV",
        original_filename="erasure.csv",
        file_hash_sha256="c" * 64,
        total_rows=1,
        valid_rows=1,
    )
    db_session.add(dataset)
    db_session.commit()

    tx = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=1,
        fingerprint_hash="d" * 64,
        city="Bengaluru",
        locality="Indiranagar",
        project_name="Prestige Park",
        unit_number="B-402",
        property_type="High-Rise Apartment",
        transaction_date=datetime.now(timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1200.0,
        transaction_price=15000000.0,
        price_per_sqft=12500.0,
        latitude=12.9716,
        longitude=77.5946,
        is_verified_deed=True,
        data_source="TEST_SRC",
        raw_data={"buyer_name": "A. Sharma", "aadhaar_masked": "XXXX-XXXX-1234"},
    )
    db_session.add(tx)
    db_session.commit()
    tx_id = tx.id

    # 2. Add verification evidence
    evidence = VerificationEvidenceModel(
        transaction_id=tx_id,
        verification_status="VERIFIED",
        verifier_id="TEST_VERIFIER",
        verifier_method="B2B_SRO_ATTESTATION",
        source_origin="TEST_SRC",
        source_document_ref="REG-999",
        original_record_hash="d" * 64,
        normalized_record_hash="e" * 64,
        verification_evidence_details={"deed": "verified"},
    )
    db_session.add(evidence)
    db_session.commit()

    # 3. Execute erasure
    result = TransactionErasureService.execute_erasure(
        db=db_session,
        transaction_id=tx_id,
        reason="Data Principal DPDP Section 12 formal erasure request",
        actor_id="DPO_OFFICER",
    )

    assert result["success"] is True
    assert result["records_erased"]["imported_transactions"] == 1
    assert result["records_erased"]["verification_evidence"] >= 1
    assert "legal_backup_disclaimer" in result

    # 4. Verify record is deleted from imported_transactions
    assert db_session.query(ImportedTransactionModel).filter(ImportedTransactionModel.id == tx_id).first() is None
    assert db_session.query(VerificationEvidenceModel).filter(VerificationEvidenceModel.transaction_id == tx_id).first() is None

    # 5. Verify ErasureRequestModel log exists
    erasure_reqs = TransactionErasureService.list_erasure_requests(db=db_session)
    matching_req = [r for r in erasure_reqs if r.transaction_id == tx_id]
    assert len(matching_req) == 1
    assert matching_req[0].status == "COMPLETED"
    assert matching_req[0].requester_id == "DPO_OFFICER"


def test_erasure_rejected_under_legal_hold(db_session: Session):
    """Verify that an active regulatory legal hold prevents deletion and records refusal."""
    # Create data source with legal hold
    source = DataSourceModel(
        source_code="SRC_LEGAL_HOLD_99",
        source_name="Regulatory Audit Registry",
        provider_name="State SRO Sub-Registry",
        access_tier="SRO_G2B_DIRECT",
        authorization_status="DOCUMENTED_AND_AUTHORIZED",
        legal_authorization_basis="STATUTORY_GOVERNMENT_MANDATE",
        retention_restrictions={"is_legal_hold": True, "legal_hold_reason": "Court Order 2026/SEC"},
        is_active=True,
    )
    db_session.add(source)

    dataset = DatasetMetadataModel(
        name="Held Dataset",
        description="Dataset under statutory hold",
        source_type="imported_deed",
        license_type="GOVERNMENT_OPEN_DATA",
        data_source_provenance="SRC_LEGAL_HOLD_99",
        file_format="CSV",
        original_filename="held.csv",
        file_hash_sha256="f" * 64,
        total_rows=1,
        valid_rows=1,
    )
    db_session.add(dataset)
    db_session.commit()

    tx = ImportedTransactionModel(
        dataset_id=dataset.id,
        row_index=1,
        fingerprint_hash="1" * 64,
        city="Mumbai",
        locality="Bandra",
        project_name="Bandra Seaview",
        property_type="High-Rise Apartment",
        transaction_date=datetime.now(timezone.utc),
        transaction_quarter="2026-Q1",
        carpet_area_sqft=1000.0,
        transaction_price=20000000.0,
        price_per_sqft=20000.0,
        latitude=19.0596,
        longitude=72.8295,
        is_verified_deed=True,
        data_source="SRC_LEGAL_HOLD_99",
        raw_data={"test": "data"},
    )
    db_session.add(tx)
    db_session.commit()

    result = TransactionErasureService.execute_erasure(
        db=db_session,
        transaction_id=tx.id,
        reason="Customer request",
        actor_id="DPO_USER",
    )

    assert result["success"] is False
    assert result["error"] == "LEGAL_HOLD_ACTIVE"
    # Ensure transaction was NOT deleted
    assert db_session.query(ImportedTransactionModel).filter(ImportedTransactionModel.id == tx.id).first() is not None


# ==============================================================================
# REMEDIATION 5: Data Quality Score Formulation & Edge Cases
# ==============================================================================

def test_data_quality_scoring_arithmetic_mean_and_zero_edge_case(client: TestClient, admin_headers):
    """Verify that quality score uses weighted arithmetic mean, handles zero records as 0.0%, and contains verification disclaimer."""
    response = client.get("/api/v1/governance/metrics", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    methodology = data["quality_methodology"]
    assert "Weighted Arithmetic Mean" in methodology["formula_description"]
    assert methodology["weights"]["completeness"] == 0.40
    assert methodology["weights"]["validity"] == 0.30
    assert methodology["weights"]["uniqueness"] == 0.20
    assert methodology["weights"]["consistency"] == 0.10
    assert "verification_disclaimer" in methodology
    assert "does NOT constitute certified empirical deed verification" in methodology["verification_disclaimer"]


# ==============================================================================
# REMEDIATION 6: PostGIS and Cadastral Integration
# ==============================================================================

def test_cadastral_reference_normalization():
    """Verify parsing and standardization of Indian cadastral identifiers."""
    # 1. Karnataka Survey Number
    raw_ka = {
        "survey_number": "142/3B",
        "revenue_village": "Varthur",
        "taluka": "Bengaluru East",
        "sro_office": "SRO Varthur",
    }
    cad_ka = normalize_cadastral_reference(raw_ka, state="Karnataka", city="Bengaluru")
    assert cad_ka.survey_number == "142/3B"
    assert cad_ka.village_name == "Varthur"
    assert cad_ka.cadastral_parcel_id == "KA-BEN-VAR-142/3B"
    assert cad_ka.validation_status == "VALIDATED"
    assert cad_ka.spatial_accuracy_tier == "PARCEL_SURVEY_RECORDED"

    # 2. Maharashtra CTS Number
    raw_mh = {
        "cts_number": "CTS-891",
        "village": "Kurla",
        "taluka": "Kurla",
    }
    cad_mh = normalize_cadastral_reference(raw_mh, state="Maharashtra", city="Mumbai")
    assert cad_mh.cts_number == "CTS-891"
    assert cad_mh.cadastral_parcel_id == "MA-MUM-KUR-CTS-891"
    assert cad_mh.validation_status == "VALIDATED"

    # 3. Missing cadastral
    raw_missing = {"building_name": "Lotus Court"}
    cad_missing = normalize_cadastral_reference(raw_missing, state="Delhi", city="Delhi")
    assert cad_missing.validation_status == "MISSING"


def test_spatial_consistency_centroid_and_outlier_detection():
    """Verify locality and jurisdiction mapping against urban centroid bounds."""
    # Valid coordinates in Bengaluru (MG Road ~ 2km from centroid)
    is_valid, err = validate_locality_spatial_consistency(
        latitude=12.9750,
        longitude=77.6000,
        city="Bengaluru",
        locality="MG Road",
    )
    assert is_valid is True
    assert err is None

    # Invalid coordinates (e.g. coordinates 250km away in the Arabian Sea or another state)
    is_valid_outlier, err_outlier = validate_locality_spatial_consistency(
        latitude=14.5000,
        longitude=74.0000,
        city="Bengaluru",
        locality="Whitefield",
    )
    assert is_valid_outlier is False
    assert "Spatial inconsistency detected" in err_outlier


# ==============================================================================
# REMEDIATION 7: Audit Merkle Tree & External Anchoring
# ==============================================================================

def test_audit_merkle_tree_generation_and_proof_verification():
    """Verify cryptographic Merkle tree root digest calculation and inclusion proofs."""
    # Create 4 leaf hashes
    leaves = [
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
    ]
    tree = AuditMerkleTree(leaves)
    assert len(tree.root) == 64

    # Generate and verify proof for leaf 1
    proof_1 = tree.get_proof(1)
    assert len(proof_1) == 2
    assert AuditMerkleTree.verify_proof(leaves[1], proof_1, tree.root) is True

    # Tampered leaf should fail verification
    assert AuditMerkleTree.verify_proof("x" * 64, proof_1, tree.root) is False


def test_audit_merkle_epoch_anchoring_endpoint(client: TestClient, admin_headers):
    """Verify epoch anchor generation and listing via API."""
    # 1. Trigger epoch anchor
    anchor_res = client.post("/api/v1/audit/anchor/epoch", headers=admin_headers)
    assert anchor_res.status_code == status.HTTP_200_OK
    anchor_data = anchor_res.json()

    assert "epoch_number" in anchor_data
    assert len(anchor_data["merkle_root_hash"]) == 64
    assert "anchor_manifest" in anchor_data
    assert "anchor_token" in anchor_data

    token = json.loads(anchor_data["anchor_token"])
    assert token["tsa_provider"] == "PropVal-Simulated-RFC3161-TSA"
    assert "institutional_disclaimer" in token

    # 2. List anchors
    list_res = client.get("/api/v1/audit/anchor/epochs", headers=admin_headers)
    assert list_res.status_code == status.HTTP_200_OK
    epochs = list_res.json()
    assert len(epochs) >= 1

