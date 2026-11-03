"""Strict pre-calibration gate evaluating model existence, dataset separation, and provenance integrity."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.ml_model import MLModelRegistryModel
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.models.uncertainty import CalibrationArtifactModel
from app.schemas.uncertainty import CalibrationGateAuditResponse


MINIMUM_CALIBRATION_RECORDS = 100


def evaluate_calibration_gate(
    db: Session,
    calibration_dataset_id: Optional[str] = None,
) -> CalibrationGateAuditResponse:
    """Evaluate whether conformal prediction calibration can be executed or served.

    Prerequisites:
    1. A verified, production-ready ML model must exist.
    2. A separate calibration dataset with legitimate provenance must be available.
    3. Minimum 100 genuine holdout calibration records are required.
    4. Zero synthetic demo records or training/calibration leakage.
    """
    blocking_issues: List[str] = []

    # 1. Verify Active Validated ML Model Existence
    active_model = (
        db.query(MLModelRegistryModel)
        .filter(
            MLModelRegistryModel.status == "ACTIVE",
            MLModelRegistryModel.is_production_ready == True,
        )
        .order_by(MLModelRegistryModel.created_at.desc())
        .first()
    )

    if not active_model:
        blocking_issues.append(
            "MISSING_VALIDATED_MODEL: No production-ready ML model exists in registry. "
            "Model training remains GATED due to insufficient empirical records (<1,000 threshold). "
            "Statistical conformal calibration requires an underlying validated predictive model."
        )

    # 2. Check Calibration Dataset / Calibration Artifact
    active_model_version = active_model.version if active_model else None
    cal_records_count = 0
    is_synthetic = False
    is_disjoint = True

    if calibration_dataset_id:
        cal_dataset = (
            db.query(DatasetMetadataModel)
            .filter(DatasetMetadataModel.id == calibration_dataset_id)
            .first()
        )

        if not cal_dataset:
            blocking_issues.append(f"DATASET_NOT_FOUND: Calibration dataset '{calibration_dataset_id}' does not exist.")
        else:
            # Check provenance
            name_lower = (cal_dataset.name or "").lower()
            desc_lower = (cal_dataset.description or "").lower()
            source_type_lower = (cal_dataset.source_type or "").lower()

            if (
                "synthetic" in name_lower
                or "demo" in name_lower
                or "sample" in name_lower
                or source_type_lower in ("synthetic_demo", "mock")
            ):
                is_synthetic = True
                blocking_issues.append(
                    "DISQUALIFIED_CALIBRATION_PROVENANCE: Calibration dataset is flagged as synthetic or demonstration data. "
                    "Conformal prediction intervals must be calibrated exclusively against certified empirical transaction deeds."
                )

            # Check disjointness from training data
            if active_model and active_model.dataset_id == calibration_dataset_id:
                is_disjoint = False
                blocking_issues.append(
                    "DATASET_LEAKAGE: Calibration dataset is identical to training dataset. "
                    "Split conformal prediction requires a strictly independent calibration partition to guarantee valid coverage."
                )

            # Check calibration record count
            cal_records = (
                db.query(ImportedTransactionModel)
                .filter(ImportedTransactionModel.dataset_id == calibration_dataset_id)
                .all()
            )
            cal_records_count = len(cal_records)

            if cal_records_count < MINIMUM_CALIBRATION_RECORDS:
                blocking_issues.append(
                    f"INSUFFICIENT_CALIBRATION_SAMPLE: Dataset contains only {cal_records_count} records. "
                    f"Institutional calibration requires a minimum of {MINIMUM_CALIBRATION_RECORDS} holdout observations "
                    f"(Deficit: {MINIMUM_CALIBRATION_RECORDS - cal_records_count} records)."
                )
    else:
        # Check if an existing approved calibration artifact is in registry
        if active_model:
            existing_artifact = (
                db.query(CalibrationArtifactModel)
                .filter(
                    CalibrationArtifactModel.model_version == active_model.version,
                    CalibrationArtifactModel.status == "ACTIVE",
                )
                .first()
            )
            if not existing_artifact:
                blocking_issues.append(
                    f"UNCALIBRATED_MODEL: Active model '{active_model.version}' has no associated conformal calibration artifact."
                )
            else:
                cal_records_count = existing_artifact.calibration_records_count

    can_calibrate = len(blocking_issues) == 0
    status_str = "CALIBRATION_READY" if can_calibrate else "UNCERTAINTY_NOT_CALIBRATED"

    if can_calibrate:
        notice = "All conformal prediction prerequisites satisfied. Distribution-free prediction intervals are approved."
    else:
        notice = (
            f"UNCERTAINTY_NOT_CALIBRATED: Prediction interval generation is BLOCKED due to {len(blocking_issues)} issue(s). "
            "PropVal AI strictly refuses to manufacture simulated intervals or uncalibrated confidence percentages."
        )

    return CalibrationGateAuditResponse(
        canCalibrate=can_calibrate,
        status=status_str,
        activeModelAvailable=active_model is not None,
        activeModelVersion=active_model_version,
        calibrationRecordsCount=cal_records_count,
        minimumRequiredCalibrationRecords=MINIMUM_CALIBRATION_RECORDS,
        isSyntheticData=is_synthetic,
        isDatasetDisjointFromTraining=is_disjoint,
        blockingIssues=blocking_issues,
        governanceNotice=notice,
    )

