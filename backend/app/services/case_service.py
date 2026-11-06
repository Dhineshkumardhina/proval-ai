"""Case management business logic and lifecycle operations."""

import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from sqlalchemy import or_, desc

from app.models.property import PropertyRecord
from app.models.valuation import ValuationCaseModel, ValuationResultModel
from app.schemas.case import (
    ValuationCaseCreate,
    ValuationCaseUpdate,
    ValuationCaseResponse,
)
from app.schemas.valuation import ValuationInputParams, ValuationResponse, AttributionFactor
from app.services.valuation_service import calculate_valuation


STATUS_LABELS = {
    "READY_FOR_APPROVAL": "Ready for Underwriter Sign-off",
    "APPROVED": "Approved & Digitally Certified",
    "REVIEW_REQUIRED": "Under Risk Committee Review",
    "HIGH_ALERT": "Critical Alert / Discrepancy",
    "REJECTED": "Valuation Rejected",
}


def to_case_response(case: ValuationCaseModel) -> ValuationCaseResponse:
    """Transform SQLAlchemy models into frontend-compatible ValuationCaseResponse."""
    prop: PropertyRecord = case.property

    latest_val = None
    if case.valuation_results:
        # Sort by creation date descending
        latest_res = sorted(case.valuation_results, key=lambda r: r.created_at, reverse=True)[0]
        attribution_factors = []
        for factor_data in (latest_res.attribution_breakdown or []):
            attribution_factors.append(
                AttributionFactor(
                    factor=factor_data.get("factor", "Adjustment"),
                    impactPerSqFt=float(factor_data.get("impactPerSqFt", 0.0)),
                    description=factor_data.get("description", ""),
                    category=factor_data.get("category", "neutral"),
                )
            )

        latest_val = ValuationResponse(
            carpetAreaSqFt=latest_res.carpet_area_sqft,
            superBuiltUpAreaSqFt=latest_res.super_built_up_area_sqft,
            unadjustedRatePerSqFt=latest_res.unadjusted_rate_per_sqft,
            ruleAdjustedRatePerSqFt=latest_res.rule_adjusted_rate_per_sqft,
            aiAdjustedRatePerSqFt=latest_res.rule_adjusted_rate_per_sqft,
            circleRatePerSqFt=latest_res.circle_rate_per_sqft,
            grossMarketValue=int(latest_res.gross_market_value),
            netAssessedValue=int(latest_res.net_assessed_value),
            distressLiquidationValue=int(latest_res.distress_liquidation_value),
            maxSanctionAmount=int(latest_res.max_sanction_amount),
            deviationFromCircleRatePct=latest_res.deviation_from_circle_rate_pct,
            confidenceScorePct=latest_res.confidence_score_pct,
            riskTier=latest_res.risk_tier,  # type: ignore
            attributionBreakdown=attribution_factors,
            engineVersion=latest_res.engine_version,
            engineType=latest_res.engine_type,
            dataSource=latest_res.data_source,
            isProvisional=True,
            calculatedAt=latest_res.created_at,
        )

    created_at_str = case.created_at.strftime("%d-%b-%Y") if case.created_at else "Just now"
    updated_at_str = case.updated_at.strftime("%d-%b-%Y %H:%M IST") if case.updated_at else "Just now"

    return ValuationCaseResponse(
        id=case.id,
        dataSource=case.data_source,
        applicationNo=prop.application_no,
        borrowerName=case.borrower_name,
        coBorrowerName=case.co_borrower_name,
        cibilScore=case.cibil_score,
        loanRequested=case.loan_requested,
        declaredAgreementValue=case.declared_agreement_value,
        propertyType=prop.property_type,
        unitAddress=prop.unit_address,
        projectName=prop.project_name,
        locality=prop.locality,
        city=prop.city,
        pincode=prop.pincode,
        branch=case.branch,
        carpetAreaSqFt=prop.carpet_area_sqft,
        superBuiltUpAreaSqFt=prop.super_built_up_area_sqft,
        floorNo=prop.floor_no,
        totalFloors=prop.total_floors,
        ageYears=prop.age_years,
        roadWidthFt=prop.road_width_ft,
        circleRatePerSqFt=prop.circle_rate_per_sqft,
        baseMarketRatePerSqFt=prop.base_market_rate_per_sqft,
        floorRiseFactor=prop.floor_rise_factor,
        roadWidthFactor=prop.road_width_factor,
        amenitiesPremium=prop.amenities_premium,
        structuralDepreciation=prop.structural_depreciation,
        status=case.status,
        statusLabel=case.status_label or STATUS_LABELS.get(case.status, case.status),
        underwriterHaircutPct=case.underwriter_haircut_pct,
        distressDiscountPct=case.distress_discount_pct,
        ltvRatioPct=case.ltv_ratio_pct,
        legalRiskPenaltyPct=case.legal_risk_penalty_pct,
        assignedUnderwriter=case.assigned_underwriter,
        institutionId=case.institution_id,
        caseReference=getattr(case, "case_reference", None) or prop.application_no,
        assignedValuer=getattr(case, "assigned_valuer", "Empaneled Field Valuer") or "Empaneled Field Valuer",
        reviewingCreditOfficer=getattr(case, "reviewing_credit_officer", "") or "",
        valuationEngineVersion=getattr(case, "valuation_engine_version", "hedonic-scorecard-v0.2.0") or "hedonic-scorecard-v0.2.0",
        valuationMethodology=getattr(case, "valuation_methodology", "DETERMINISTIC_HEDONIC") or "DETERMINISTIC_HEDONIC",
        advisoryClassification="ADVISORY_ONLY",
        divergencePct=float(getattr(case, "divergence_pct", 0.0) or 0.0),
        requiresSeniorReview=bool(getattr(case, "requires_senior_review", False)),
        humanSignOffBy=getattr(case, "human_sign_off_by", None),
        humanSignOffDate=case.human_sign_off_date.isoformat() if getattr(case, "human_sign_off_date", None) else None,
        humanSignOffNotes=getattr(case, "human_sign_off_notes", "") or "",
        createdAt=created_at_str,
        lastUpdated=updated_at_str,
        reraRegistration=case.rera_registration or "",
        bbmpPlanApprovalNo=case.bbmp_plan_approval_no or "",
        titleChainYears=case.title_chain_years or 30,
        encumbranceStatus=case.encumbrance_status or "NIL_ENCUMBRANCE",
        comparables=case.comparables or [],
        documentFields=case.document_fields or [],
        surveyPhotos=case.survey_photos or [],
        auditNotes=case.audit_notes or [],
        latestValuation=latest_val,
    )


def list_cases(
    db: Session,
    city: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    institution_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ValuationCaseResponse], int]:
    """Retrieve valuation cases with filtering, search, and pagination."""
    query = db.query(ValuationCaseModel).join(PropertyRecord)

    if institution_id:
        query = query.filter(ValuationCaseModel.institution_id == institution_id)
    if city:
        query = query.filter(PropertyRecord.city == city)
    if status:
        query = query.filter(ValuationCaseModel.status == status)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                PropertyRecord.application_no.ilike(search_pattern),
                ValuationCaseModel.borrower_name.ilike(search_pattern),
                PropertyRecord.project_name.ilike(search_pattern),
                PropertyRecord.locality.ilike(search_pattern),
            )
        )

    total = query.count()
    cases = (
        query.options(
            contains_eager(ValuationCaseModel.property),
            selectinload(ValuationCaseModel.valuation_results),
        )
        .order_by(desc(ValuationCaseModel.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [to_case_response(c) for c in cases], total


def get_case_by_id(db: Session, case_id: str) -> Optional[ValuationCaseResponse]:
    """Retrieve a single case by ID with full relations."""
    case = (
        db.query(ValuationCaseModel)
        .options(
            joinedload(ValuationCaseModel.property),
            selectinload(ValuationCaseModel.valuation_results),
        )
        .filter(ValuationCaseModel.id == case_id)
        .first()
    )
    if not case:
        return None
    return to_case_response(case)


def create_case(db: Session, case_in: ValuationCaseCreate) -> ValuationCaseResponse:
    """Create new property record and valuation case, calculate baseline estimate, and save."""
    institution_id = case_in.institutionId
    new_case_id = f"case-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    prop_id = str(uuid.uuid4())
    app_no = f"HFC-{case_in.city[:3].upper()}-2026-{uuid.uuid4().hex[:5].upper()}"

    # Default city rates if not specified
    base_rate = case_in.baseMarketRatePerSqFt
    if base_rate is None or base_rate <= 0:
        base_rate = 24000.0 if case_in.city == "Mumbai" else 21000.0 if case_in.city == "Delhi-NCR" else 9500.0 if case_in.city == "Bengaluru" else 8000.0

    circle_rate = case_in.circleRatePerSqFt
    if circle_rate is None or circle_rate <= 0:
        circle_rate = 20000.0 if case_in.city == "Mumbai" else 17500.0 if case_in.city == "Delhi-NCR" else 7000.0 if case_in.city == "Bengaluru" else 6000.0

    floor_rise = case_in.floorRiseFactor if case_in.floorRiseFactor is not None else (300.0 if case_in.floorNo > 4 else 0.0)

    # 1. Create Property
    prop = PropertyRecord(
        id=prop_id,
        institution_id=institution_id,
        application_no=app_no,
        project_name=case_in.projectName,
        unit_address=case_in.unitAddress,
        locality=case_in.locality,
        city=case_in.city,
        pincode=case_in.pincode,
        property_type=case_in.propertyType,
        carpet_area_sqft=case_in.carpetAreaSqFt,
        super_built_up_area_sqft=case_in.superBuiltUpAreaSqFt,
        floor_no=case_in.floorNo,
        total_floors=case_in.totalFloors,
        age_years=case_in.ageYears,
        road_width_ft=case_in.roadWidthFt,
        circle_rate_per_sqft=circle_rate,
        base_market_rate_per_sqft=base_rate,
        floor_rise_factor=floor_rise,
        road_width_factor=case_in.roadWidthFactor or 250.0,
        amenities_premium=case_in.amenitiesPremium or 400.0,
        structural_depreciation=case_in.structuralDepreciation or 80.0,
        data_source=case_in.dataSource,
    )

    # 2. Build default synthetic comparables and OCR extract if none passed
    comparables = case_in.comparables or [
        {
            "id": f"comp-{uuid.uuid4().hex[:6]}",
            "dataSource": "synthetic-demo",
            "sroRegNo": f"SRO-{case_in.city[:3].upper()}-2026-BK1-{uuid.uuid4().hex[:4].upper()}",
            "regDate": datetime.now(timezone.utc).strftime("%d-%b-%Y"),
            "propertyName": f"{case_in.projectName} (Adjacent Wing)",
            "unitNo": f"{case_in.floorNo}04",
            "carpetAreaSqFt": case_in.carpetAreaSqFt,
            "superBuiltUpAreaSqFt": case_in.superBuiltUpAreaSqFt,
            "registeredPrice": int(case_in.declaredAgreementValue * 0.98),
            "ratePerSqFt": int((case_in.declaredAgreementValue * 0.98) / max(1, case_in.carpetAreaSqFt)),
            "distanceMeters": 150,
            "similarityScorePct": 95,
            "weightInEstimate": 0.5,
            "floor": case_in.floorNo,
            "coordinates": {"x": 50, "y": 50},
        }
    ]

    document_fields = case_in.documentFields or [
        {
            "label": "SRO Registered Deed",
            "applicantDeclared": f"BK-1/{uuid.uuid4().hex[:4].upper()}/2024",
            "sroIndexExtract": "Simulated registry check template (synthetic demo)",
            "matchStatus": "MATCHED",
        },
        {
            "label": "Carpet Area (RERA)",
            "applicantDeclared": f"{case_in.carpetAreaSqFt} sq ft",
            "sroIndexExtract": f"{case_in.carpetAreaSqFt} sq ft sanctioned",
            "matchStatus": "MATCHED",
        },
    ]

    survey_photos = case_in.surveyPhotos or [
        {
            "id": f"photo-{uuid.uuid4().hex[:6]}",
            "title": "Building Entrance & Façade",
            "category": "Exterior",
            "latLong": "12.9716° N, 77.5946° E",
            "capturedAt": "Today 10:00 AM",
            "surveyor": "Kishore Gowda (ID: INSP-089)",
            "surveyorId": "INSP-089",
            "status": "VERIFIED",
            "description": "Modern residential tower with clear approach road.",
            "imageUrl": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80",
        }
    ]

    audit_notes = case_in.auditNotes or ["Case ingested into valuation engine pipeline."]

    # 3. Calculate Valuation Estimate First
    val_params = ValuationInputParams(
        carpetAreaSqFt=case_in.carpetAreaSqFt,
        superBuiltUpAreaSqFt=case_in.superBuiltUpAreaSqFt,
        baseMarketRatePerSqFt=base_rate,
        circleRatePerSqFt=circle_rate,
        floorRiseFactor=floor_rise,
        roadWidthFactor=case_in.roadWidthFactor or 250.0,
        amenitiesPremium=case_in.amenitiesPremium or 400.0,
        structuralDepreciation=case_in.structuralDepreciation or 80.0,
        underwriterHaircutPct=case_in.underwriterHaircutPct,
        distressDiscountPct=case_in.distressDiscountPct,
        ltvRatioPct=case_in.ltvRatioPct,
        legalRiskPenaltyPct=case_in.legalRiskPenaltyPct,
        dataSource=case_in.dataSource,
    )
    val_res = calculate_valuation(val_params)

    # Phase 7B: Valuation Divergence & Risk Review Gates
    net_val = float(val_res.netAssessedValue)
    declared_val = float(case_in.declaredAgreementValue)
    divergence_pct = (abs(net_val - declared_val) / declared_val * 100.0) if declared_val > 0 else 0.0
    requires_senior_review = bool(divergence_pct > 15.0 or val_res.riskTier == "HIGH_ALERT")

    initial_status = "READY_FOR_APPROVAL"
    initial_status_label = "Ready for Underwriter Sign-off"

    # 4. Create Case Record
    case = ValuationCaseModel(
        id=new_case_id,
        institution_id=case_in.institutionId,
        property_id=prop_id,
        case_reference=case_in.caseReference or app_no,
        borrower_name=case_in.borrowerName,
        co_borrower_name=case_in.coBorrowerName,
        cibil_score=case_in.cibilScore,
        loan_requested=case_in.loanRequested,
        declared_agreement_value=case_in.declaredAgreementValue,
        branch=case_in.branch,
        assigned_underwriter=case_in.assignedUnderwriter,
        assigned_valuer=case_in.assignedValuer or "Empaneled Field Valuer",
        reviewing_credit_officer=case_in.reviewingCreditOfficer or "",
        valuation_engine_version="hedonic-scorecard-v0.2.0",
        valuation_methodology="DETERMINISTIC_HEDONIC",
        advisory_classification="ADVISORY_ONLY",
        divergence_pct=round(divergence_pct, 2),
        requires_senior_review=requires_senior_review,
        status=initial_status,
        status_label=initial_status_label,
        underwriter_haircut_pct=case_in.underwriterHaircutPct,
        distress_discount_pct=case_in.distressDiscountPct,
        ltv_ratio_pct=case_in.ltvRatioPct,
        legal_risk_penalty_pct=case_in.legalRiskPenaltyPct,
        rera_registration=case_in.reraRegistration or f"PRM/{case_in.city[:2].upper()}/RERA/2026/0014",
        bbmp_plan_approval_no=case_in.bbmpPlanApprovalNo or f"PLAN/{case_in.city[:3].upper()}/2024/889",
        title_chain_years=case_in.titleChainYears,
        encumbrance_status=case_in.encumbranceStatus,
        comparables=comparables,
        document_fields=document_fields,
        survey_photos=survey_photos,
        audit_notes=audit_notes,
        data_source=case_in.dataSource,
    )

    db_val = ValuationResultModel(
        case_id=new_case_id,
        institution_id=institution_id,
        engine_version=val_res.engineVersion,
        engine_type=val_res.engineType,
        data_source=val_res.dataSource,
        carpet_area_sqft=val_res.carpetAreaSqFt,
        super_built_up_area_sqft=val_res.superBuiltUpAreaSqFt,
        unadjusted_rate_per_sqft=val_res.unadjustedRatePerSqFt,
        rule_adjusted_rate_per_sqft=val_res.ruleAdjustedRatePerSqFt,
        circle_rate_per_sqft=val_res.circleRatePerSqFt,
        gross_market_value=float(val_res.grossMarketValue),
        net_assessed_value=float(val_res.netAssessedValue),
        distress_liquidation_value=float(val_res.distressLiquidationValue),
        max_sanction_amount=float(val_res.maxSanctionAmount),
        deviation_from_circle_rate_pct=val_res.deviationFromCircleRatePct,
        confidence_score_pct=val_res.confidenceScorePct,
        risk_tier=val_res.riskTier,
        attribution_breakdown=[f.model_dump(by_alias=True) for f in val_res.attributionBreakdown],
    )

    try:
        db.add(prop)
        db.add(case)
        db.add(db_val)
        db.commit()
        db.refresh(case)
    except Exception:
        db.rollback()
        raise

    return to_case_response(case)


def update_case(db: Session, case_id: str, case_in: ValuationCaseUpdate) -> Optional[ValuationCaseResponse]:
    """Update case parameters, recalculate valuation, and persist result."""
    case = db.query(ValuationCaseModel).filter(ValuationCaseModel.id == case_id).first()
    if not case:
        return None

    prop: PropertyRecord = case.property

    # Update underwriter/case params
    if case_in.borrowerName is not None:
        case.borrower_name = case_in.borrowerName
    if case_in.coBorrowerName is not None:
        case.co_borrower_name = case_in.coBorrowerName
    if case_in.cibilScore is not None:
        case.cibil_score = case_in.cibilScore
    if case_in.loanRequested is not None:
        case.loan_requested = case_in.loanRequested
    if case_in.declaredAgreementValue is not None:
        case.declared_agreement_value = case_in.declaredAgreementValue
    if case_in.underwriterHaircutPct is not None:
        case.underwriter_haircut_pct = case_in.underwriterHaircutPct
    if case_in.distressDiscountPct is not None:
        case.distress_discount_pct = case_in.distressDiscountPct
    if case_in.ltvRatioPct is not None:
        case.ltv_ratio_pct = case_in.ltvRatioPct
    if case_in.legalRiskPenaltyPct is not None:
        case.legal_risk_penalty_pct = case_in.legalRiskPenaltyPct
    if case_in.status is not None:
        case.status = case_in.status
        case.status_label = case_in.statusLabel or STATUS_LABELS.get(case_in.status, case_in.status)
    if case_in.assignedUnderwriter is not None:
        case.assigned_underwriter = case_in.assignedUnderwriter
    if case_in.auditNotes is not None:
        case.audit_notes = case_in.auditNotes

    # Update property params
    if case_in.carpetAreaSqFt is not None:
        prop.carpet_area_sqft = case_in.carpetAreaSqFt
    if case_in.superBuiltUpAreaSqFt is not None:
        prop.super_built_up_area_sqft = case_in.superBuiltUpAreaSqFt
    if case_in.circleRatePerSqFt is not None:
        prop.circle_rate_per_sqft = case_in.circleRatePerSqFt
    if case_in.baseMarketRatePerSqFt is not None:
        prop.base_market_rate_per_sqft = case_in.baseMarketRatePerSqFt
    if case_in.floorRiseFactor is not None:
        prop.floor_rise_factor = case_in.floorRiseFactor
    if case_in.roadWidthFactor is not None:
        prop.road_width_factor = case_in.roadWidthFactor
    if case_in.amenitiesPremium is not None:
        prop.amenities_premium = case_in.amenitiesPremium
    if case_in.structuralDepreciation is not None:
        prop.structural_depreciation = case_in.structuralDepreciation

    case.updated_at = datetime.now(timezone.utc)
    prop.updated_at = datetime.now(timezone.utc)

    # Recalculate valuation with updated numbers
    val_params = ValuationInputParams(
        carpetAreaSqFt=prop.carpet_area_sqft,
        superBuiltUpAreaSqFt=prop.super_built_up_area_sqft,
        baseMarketRatePerSqFt=prop.base_market_rate_per_sqft,
        circleRatePerSqFt=prop.circle_rate_per_sqft,
        floorRiseFactor=prop.floor_rise_factor,
        roadWidthFactor=prop.road_width_factor,
        amenitiesPremium=prop.amenities_premium,
        structuralDepreciation=prop.structural_depreciation,
        underwriterHaircutPct=case.underwriter_haircut_pct,
        distressDiscountPct=case.distress_discount_pct,
        ltvRatioPct=case.ltv_ratio_pct,
        legalRiskPenaltyPct=case.legal_risk_penalty_pct,
        dataSource=case.data_source,
    )
    val_res = calculate_valuation(val_params)

    db_val = ValuationResultModel(
        case_id=case_id,
        institution_id=case.institution_id,
        engine_version=val_res.engineVersion,
        engine_type=val_res.engineType,
        data_source=val_res.dataSource,
        carpet_area_sqft=val_res.carpetAreaSqFt,
        super_built_up_area_sqft=val_res.superBuiltUpAreaSqFt,
        unadjusted_rate_per_sqft=val_res.unadjustedRatePerSqFt,
        rule_adjusted_rate_per_sqft=val_res.ruleAdjustedRatePerSqFt,
        circle_rate_per_sqft=val_res.circleRatePerSqFt,
        gross_market_value=float(val_res.grossMarketValue),
        net_assessed_value=float(val_res.netAssessedValue),
        distress_liquidation_value=float(val_res.distressLiquidationValue),
        max_sanction_amount=float(val_res.maxSanctionAmount),
        deviation_from_circle_rate_pct=val_res.deviationFromCircleRatePct,
        confidence_score_pct=val_res.confidenceScorePct,
        risk_tier=val_res.riskTier,
        attribution_breakdown=[f.model_dump(by_alias=True) for f in val_res.attributionBreakdown],
    )
    try:
        db.add(db_val)
        db.commit()
        db.refresh(case)
        return to_case_response(case)
    except Exception:
        db.rollback()
        raise


def update_case_status(
    db: Session,
    case_id: str,
    new_status: str,
    audit_note: Optional[str] = None,
    human_sign_off_by: Optional[str] = None,
    human_sign_off_notes: Optional[str] = None,
    actor_role: Optional[str] = None,
) -> Optional[ValuationCaseResponse]:
    """Transition case workflow status and record audit ledger note with pilot safety controls."""
    case = db.query(ValuationCaseModel).filter(ValuationCaseModel.id == case_id).first()
    if not case:
        return None

    # Mandatory Pilot Safety Controls (Phase 7B)
    if new_status == "APPROVED":
        # Control 2 & 3: Automated valuation must never independently sanction a loan.
        # Final collateral valuation and LTV decisions require authorized human approval.
        effective_sign_off = human_sign_off_by or (audit_note.strip() if audit_note else None)
        if not effective_sign_off:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Automated valuation cannot sanction loan independently. Final approval requires explicit authorized human sign-off.",
            )

        # Control 5 & 6: Valuation divergence > 15% or HIGH_ALERT requires senior underwriter review
        div_pct = float(getattr(case, "divergence_pct", 0.0) or 0.0)
        is_high_risk = bool(div_pct > 15.0 or case.status == "HIGH_ALERT" or getattr(case, "requires_senior_review", False))
        if is_high_risk and actor_role and actor_role not in ["SENIOR_UNDERWRITER", "RISK_COMMITTEE_MEMBER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Case has valuation divergence of {div_pct:.1f}% (>15%) or HIGH_ALERT and requires Senior Underwriter or Risk Committee approval. Current role: {actor_role}",
            )

        case.human_sign_off_by = human_sign_off_by or (actor_role or "Authorized Underwriter")
        case.human_sign_off_date = datetime.now(timezone.utc)
        case.human_sign_off_notes = human_sign_off_notes or (audit_note or "")

    case.status = new_status
    case.status_label = STATUS_LABELS.get(new_status, new_status)
    case.updated_at = datetime.now(timezone.utc)

    if audit_note:
        notes = list(case.audit_notes or [])
        notes.append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} - {audit_note}")
        case.audit_notes = notes

    try:
        db.commit()
        db.refresh(case)
        return to_case_response(case)
    except Exception:
        db.rollback()
        raise


def delete_case(db: Session, case_id: str) -> bool:
    """Delete a valuation case and cascade associated records."""
    case = db.query(ValuationCaseModel).filter(ValuationCaseModel.id == case_id).first()
    if not case:
        return False
    prop = case.property
    try:
        db.delete(case)
        if prop:
            db.delete(prop)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
