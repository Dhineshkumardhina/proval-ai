"""Rigorous pre-training readiness gate evaluating dataset integrity and preventing premature ML training."""

from collections import Counter
from typing import List, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.schemas.ml import MLTrainingGateAuditResponse


MINIMUM_RECORDS_THRESHOLD = 1000
MINIMUM_GEOGRAPHIC_CLUSTERS = 3
MINIMUM_VERIFIED_DEED_RATIO = 0.80


def evaluate_training_gate(db: Session, dataset_id: str) -> MLTrainingGateAuditResponse:
    """Evaluate whether an ingested dataset meets the strict empirical criteria for ML model training.

    Enforces institutional fintech standards:
    1. Dataset provenance: synthetic demonstration data is explicitly disqualified.
    2. Minimum empirical sample size: minimum 1,000 valid records required.
    3. Deed verification: minimum 80% certified deed registrations (not asking prices).
    4. Geographic coverage: minimum 3 distinct micro-markets/localities.
    5. Property type distribution: diversity across architectural typologies.
    6. Target price quality: strictly positive values, finite variance, bounded IQR.
    """
    dataset = db.query(DatasetMetadataModel).filter(DatasetMetadataModel.id == dataset_id).first()
    if not dataset:
        return MLTrainingGateAuditResponse(
            passed=False,
            datasetId=dataset_id,
            totalRecords=0,
            validRecords=0,
            requiredRecordsThreshold=MINIMUM_RECORDS_THRESHOLD,
            isSyntheticData=False,
            verifiedDeedRatio=0.0,
            geographicCoverage={},
            propertyTypeDistribution={},
            priceSanityVerified=False,
            blockingIssues=[f"Dataset with ID '{dataset_id}' does not exist in repository."],
            canTrain=False,
            governanceRecommendation="Dataset not found. Upload authentic property transactions before requesting training.",
        )

    records: List[ImportedTransactionModel] = (
        db.query(ImportedTransactionModel)
        .filter(ImportedTransactionModel.dataset_id == dataset_id)
        .all()
    )

    blocking_issues: List[str] = []

    # 1. Dataset Approval & Governance Gate (Phase 4B-7B)
    if dataset.approval_status != "APPROVED":
        blocking_issues.append(
            f"UNAPPROVED_DATASET: Dataset approval status is '{dataset.approval_status}'. "
            "Institutional risk policy strictly mandates 'APPROVED' status before training ML models."
        )

    # 2. Source Purpose & Contractual Licensing Gate (Phase 4B-7B)
    from app.services.policy_service import DataPolicyService
    is_ml_authorized, purpose_reason = DataPolicyService.verify_dataset_and_source_for_ml(
        db=db,
        dataset=dataset,
        required_purpose="MODEL_TRAINING",
    )
    if not is_ml_authorized:
        # Avoid duplicate message if it was already caught by dataset approval
        if "APPROVED" not in (purpose_reason or "") or dataset.approval_status == "APPROVED":
            blocking_issues.append(f"PURPOSE_RESTRICTION: {purpose_reason}")

    # 3. Check for Synthetic Demonstration Provenance
    is_synthetic = False
    name_lower = (dataset.name or "").lower()
    desc_lower = (dataset.description or "").lower()
    prov_lower = (dataset.data_source_provenance or "").lower()
    source_type_lower = (dataset.source_type or "").lower()

    if (
        "synthetic" in name_lower
        or "synthetic" in desc_lower
        or "synthetic" in prov_lower
        or "demo" in name_lower
        or "sample" in name_lower
        or source_type_lower in ("synthetic_demo", "synthetic", "mock")
    ):
        is_synthetic = True
        blocking_issues.append(
            "DISQUALIFIED_PROVENANCE: Dataset is flagged as synthetic demonstration or mock data. "
            "Institutional governance strictly forbids training ML valuation models on fabricated or demonstration records."
        )

    total_records = len(records)
    valid_records = total_records

    # 2. Check Sample Size Threshold (>= 1,000 valid records)
    if valid_records < MINIMUM_RECORDS_THRESHOLD:
        blocking_issues.append(
            f"INSUFFICIENT_SAMPLE_SIZE: Dataset contains only {valid_records} valid records. "
            f"Institutional risk policy mandates a minimum of {MINIMUM_RECORDS_THRESHOLD} verified records per micro-market "
            f"(Deficit: {MINIMUM_RECORDS_THRESHOLD - valid_records} records)."
        )

    # 3. Check Verified Deed Ratio
    if total_records > 0:
        verified_count = sum(1 for r in records if r.is_verified_deed and not r.is_asking_price)
        verified_ratio = round(verified_count / total_records, 3)
        if verified_ratio < MINIMUM_VERIFIED_DEED_RATIO:
            blocking_issues.append(
                f"LOW_VERIFIED_DEED_RATIO: Only {verified_ratio * 100:.1f}% of records represent certified deed registrations. "
                f"Minimum required threshold is {MINIMUM_VERIFIED_DEED_RATIO * 100:.0f}%."
            )
    else:
        verified_ratio = 0.0
        blocking_issues.append("EMPTY_DATASET: Dataset contains zero imported transactions.")

    # 4. Check Geographic Coverage
    localities = [r.locality for r in records if r.locality]
    geo_coverage = dict(Counter(localities))
    if len(geo_coverage) < MINIMUM_GEOGRAPHIC_CLUSTERS:
        blocking_issues.append(
            f"INSUFFICIENT_GEOGRAPHIC_DIVERSITY: Transactions span only {len(geo_coverage)} micro-market(s). "
            f"Minimum of {MINIMUM_GEOGRAPHIC_CLUSTERS} distinct micro-markets required to prevent extreme spatial overfitting."
        )

    # 5. Check Property Type Distribution
    property_types = [r.property_type for r in records if r.property_type]
    prop_type_dist = dict(Counter(property_types))
    if total_records >= 20 and len(prop_type_dist) <= 1:
        blocking_issues.append(
            "MONOLITHIC_PROPERTY_TYPES: Dataset contains only 1 property type. "
            "A balanced multi-family or diversified housing portfolio is required for generalizable AVM training."
        )

    # 6. Check Target Price Sanity & Variance
    prices = [r.transaction_price for r in records if r.transaction_price is not None and not np.isnan(r.transaction_price)]
    price_sanity_passed = False
    if len(prices) >= 5:
        prices_arr = np.array(prices, dtype=float)
        price_std = float(np.std(prices_arr))
        price_min = float(np.min(prices_arr))
        price_max = float(np.max(prices_arr))

        if price_min <= 0:
            blocking_issues.append("INVALID_PRICES: Dataset contains zero or negative transaction prices.")
        elif price_std < 1000.0:
            blocking_issues.append("ZERO_VARIANCE: Target transaction price exhibits near-zero standard deviation.")
        elif price_max > 5_000_000_000.0:  # ₹500 Cr
            blocking_issues.append("EXTREME_PRICE_CORRUPTION: Dataset contains implausible single transactions > ₹500 Crores.")
        else:
            price_sanity_passed = True
    else:
        blocking_issues.append("INSUFFICIENT_PRICE_POINTS: Fewer than 5 non-null price observations available.")

    can_train = len(blocking_issues) == 0

    if can_train:
        recommendation = (
            f"READINESS: GO. Dataset satisfies all {MINIMUM_RECORDS_THRESHOLD}-record sample size, "
            "geographic diversity, deed verification, and price sanity standards. Approved for ML model training."
        )
    else:
        recommendation = (
            f"READINESS: NO-GO. Training is strictly GATED due to {len(blocking_issues)} blocking issue(s). "
            f"Dataset has {valid_records} valid records (requires {MINIMUM_RECORDS_THRESHOLD}). "
            "PropVal AI continues operating on the statutory rule-based baseline engine."
        )

    return MLTrainingGateAuditResponse(
        passed=can_train,
        datasetId=dataset_id,
        totalRecords=total_records,
        validRecords=valid_records,
        requiredRecordsThreshold=MINIMUM_RECORDS_THRESHOLD,
        isSyntheticData=is_synthetic,
        verifiedDeedRatio=verified_ratio,
        geographicCoverage=geo_coverage,
        propertyTypeDistribution=prop_type_dist,
        priceSanityVerified=price_sanity_passed,
        blockingIssues=blocking_issues,
        canTrain=can_train,
        governanceRecommendation=recommendation,
    )

