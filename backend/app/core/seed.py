"""Seed initial demonstration valuation cases into the database on startup."""

import json
import logging
import os
import uuid
from sqlalchemy.orm import Session
from app.models.property import PropertyRecord
from app.models.valuation import ValuationCaseModel, ValuationResultModel
from app.schemas.valuation import ValuationInputParams
from app.services.valuation_service import calculate_valuation

logger = logging.getLogger("propval.seed")


def seed_demonstration_cases(db: Session) -> int:
    """Populate database with the 6 standard synthetic demonstration cases if empty."""
    existing_count = db.query(ValuationCaseModel).count()
    if existing_count > 0:
        return 0

    json_path = os.path.join(os.path.dirname(__file__), "initial_cases.json")
    if not os.path.exists(json_path):
        logger.warning("Seed file %s not found. Skipping automatic seeding.", json_path)
        return 0

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
    except Exception as e:
        logger.error("Failed to load initial demonstration cases: %s", str(e))
        return 0

    inserted_count = 0
    for item in cases_data:
        try:
            prop_id = str(uuid.uuid4())
            # 1. Create Property Record
            prop = PropertyRecord(
                id=prop_id,
                application_no=item["applicationNo"],
                project_name=item["projectName"],
                unit_address=item["unitAddress"],
                locality=item["locality"],
                city=item["city"],
                pincode=item.get("pincode", "560001"),
                property_type=item.get("propertyType", "High-Rise Apartment"),
                carpet_area_sqft=float(item["carpetAreaSqFt"]),
                super_built_up_area_sqft=float(item["superBuiltUpAreaSqFt"]),
                floor_no=int(item.get("floorNo", 1)),
                total_floors=int(item.get("totalFloors", 1)),
                age_years=int(item.get("ageYears", 0)),
                road_width_ft=float(item.get("roadWidthFt", 30.0)),
                circle_rate_per_sqft=float(item["circleRatePerSqFt"]),
                base_market_rate_per_sqft=float(item["baseMarketRatePerSqFt"]),
                floor_rise_factor=float(item.get("floorRiseFactor", 0.0)),
                road_width_factor=float(item.get("roadWidthFactor", 0.0)),
                amenities_premium=float(item.get("amenitiesPremium", 0.0)),
                structural_depreciation=float(item.get("structuralDepreciation", 0.0)),
                data_source=item.get("dataSource", "synthetic-demo"),
            )
            db.add(prop)

            # 2. Create Valuation Case
            case = ValuationCaseModel(
                id=item["id"],
                property_id=prop_id,
                borrower_name=item["borrowerName"],
                co_borrower_name=item.get("coBorrowerName"),
                cibil_score=int(item.get("cibilScore", 750)),
                loan_requested=float(item["loanRequested"]),
                declared_agreement_value=float(item["declaredAgreementValue"]),
                branch=item.get("branch", "Main Lending Branch"),
                assigned_underwriter=item.get("assignedUnderwriter", "V. Sundaram (Sr. Underwriter)"),
                status=item.get("status", "READY_FOR_APPROVAL"),
                status_label=item.get("statusLabel", "Ready for Underwriter Sign-off"),
                underwriter_haircut_pct=float(item.get("underwriterHaircutPct", 0.0)),
                distress_discount_pct=float(item.get("distressDiscountPct", 18.0)),
                ltv_ratio_pct=float(item.get("ltvRatioPct", 75.0)),
                legal_risk_penalty_pct=float(item.get("legalRiskPenaltyPct", 0.0)),
                rera_registration=item.get("reraRegistration", ""),
                bbmp_plan_approval_no=item.get("bbmpPlanApprovalNo", ""),
                title_chain_years=int(item.get("titleChainYears", 30)),
                encumbrance_status=item.get("encumbranceStatus", "NIL_ENCUMBRANCE"),
                comparables=item.get("comparables", []),
                document_fields=item.get("documentFields", []),
                survey_photos=item.get("surveyPhotos", []),
                audit_notes=item.get("auditNotes", []),
                data_source=item.get("dataSource", "synthetic-demo"),
            )
            db.add(case)

            # 3. Calculate and Persist Baseline Valuation Result
            val_params = ValuationInputParams(
                carpetAreaSqFt=float(item["carpetAreaSqFt"]),
                superBuiltUpAreaSqFt=float(item["superBuiltUpAreaSqFt"]),
                baseMarketRatePerSqFt=float(item["baseMarketRatePerSqFt"]),
                circleRatePerSqFt=float(item["circleRatePerSqFt"]),
                floorRiseFactor=float(item.get("floorRiseFactor", 0.0)),
                roadWidthFactor=float(item.get("roadWidthFactor", 0.0)),
                amenitiesPremium=float(item.get("amenitiesPremium", 0.0)),
                structuralDepreciation=float(item.get("structuralDepreciation", 0.0)),
                underwriterHaircutPct=float(item.get("underwriterHaircutPct", 0.0)),
                distressDiscountPct=float(item.get("distressDiscountPct", 18.0)),
                ltvRatioPct=float(item.get("ltvRatioPct", 75.0)),
                legalRiskPenaltyPct=float(item.get("legalRiskPenaltyPct", 0.0)),
                dataSource=item.get("dataSource", "synthetic-demo"),
            )
            val_res = calculate_valuation(val_params)

            db_val_res = ValuationResultModel(
                case_id=item["id"],
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
            db.add(db_val_res)
            inserted_count += 1
        except Exception as item_err:
            logger.error("Failed to seed case %s: %s", item.get("id"), str(item_err))

    db.commit()
    logger.info("Successfully seeded %d demonstration cases into database.", inserted_count)

    # Seed demonstration audit events for initial hash chain
    seed_demonstration_audit_trail(db)

    return inserted_count


def seed_demonstration_audit_trail(db: Session) -> int:
    """Populate initial cryptographic SHA-256 hash chain with baseline demonstration audit events."""
    from app.models.audit import AuditEventModel
    from app.services.audit_service import (
        record_audit_event,
        EVENT_ADMIN_ACTION,
        EVENT_CASE_CREATED,
        EVENT_VALUATION_CALCULATED,
    )

    if db.query(AuditEventModel).count() > 0:
        return 0

    events_created = 0

    # 1. System Genesis Event
    record_audit_event(
        db=db,
        event_type=EVENT_ADMIN_ACTION,
        actor_id="system.bootstrap",
        actor_role="ADMIN",
        payload={
            "action": "LEDGER_GENESIS_INITIALIZATION",
            "description": "PropVal AI Tamper-Evident SHA-256 Audit Trail Genesis Block initialized.",
            "version": "1.0.0",
        },
    )
    events_created += 1

    # 2. Add audit blocks for initial cases
    cases = db.query(ValuationCaseModel).all()
    for c in cases:
        record_audit_event(
            db=db,
            event_type=EVENT_CASE_CREATED,
            actor_id=c.assigned_underwriter or "v.sundaram",
            actor_role="SENIOR_UNDERWRITER",
            case_id=c.id,
            payload={
                "case_id": c.id,
                "status": c.status,
                "branch": c.branch,
                "loan_requested": c.loan_requested,
                "declared_agreement_value": c.declared_agreement_value,
            },
        )
        events_created += 1

        record_audit_event(
            db=db,
            event_type=EVENT_VALUATION_CALCULATED,
            actor_id="valuation.engine",
            actor_role="SYSTEM",
            case_id=c.id,
            payload={
                "case_id": c.id,
                "engine_type": "provisional rule-based estimation",
                "underwriter_haircut_pct": c.underwriter_haircut_pct,
                "distress_discount_pct": c.distress_discount_pct,
                "ltv_ratio_pct": c.ltv_ratio_pct,
            },
        )
        events_created += 1

    logger.info("Successfully seeded %d audit events into cryptographic hash chain.", events_created)
    return events_created

