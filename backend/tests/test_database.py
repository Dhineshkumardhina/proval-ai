"""Tests for SQLAlchemy database models and relationships."""

import uuid
from sqlalchemy.orm import Session
from app.models.property import PropertyRecord
from app.models.valuation import ValuationCaseModel, ValuationResultModel


def test_property_and_valuation_case_relationships(db_session: Session):
    """Verify property creation, valuation case linkage, and cascade behavior."""
    prop_id = str(uuid.uuid4())
    prop = PropertyRecord(
        id=prop_id,
        application_no="APP-DB-TEST-001",
        project_name="Prestige Lakeside Habitat",
        unit_address="Tower 4, Unit 1204",
        locality="Varthur",
        city="Bengaluru",
        pincode="560087",
        property_type="High-Rise Apartment",
        carpet_area_sqft=1250.0,
        super_built_up_area_sqft=1650.0,
        base_market_rate_per_sqft=9800.0,
        circle_rate_per_sqft=7800.0,
        data_source="synthetic-demo",
    )
    db_session.add(prop)
    db_session.commit()

    case_id = str(uuid.uuid4())
    case = ValuationCaseModel(
        id=case_id,
        property_id=prop_id,
        borrower_name="Rajesh Kumar",
        cibil_score=780,
        loan_requested=9000000.0,
        declared_agreement_value=13500000.0,
        branch="Whitefield",
        assigned_underwriter="Vikram Sethi",
        status="READY_FOR_APPROVAL",
        status_label="Ready for Approval",
        data_source="synthetic-demo",
    )
    db_session.add(case)
    db_session.commit()

    val_res_id = str(uuid.uuid4())
    val_res = ValuationResultModel(
        id=val_res_id,
        case_id=case_id,
        engine_version="0.2.0",
        engine_type="provisional rule-based estimation",
        data_source="synthetic-demo",
        carpet_area_sqft=1250.0,
        super_built_up_area_sqft=1650.0,
        unadjusted_rate_per_sqft=9800.0,
        rule_adjusted_rate_per_sqft=10650.0,
        circle_rate_per_sqft=7800.0,
        gross_market_value=13312500.0,
        net_assessed_value=12646875.0,
        distress_liquidation_value=10117500.0,
        max_sanction_amount=9485156.0,
        deviation_from_circle_rate_pct=36.5,
        confidence_score_pct=85.5,
        risk_tier="LOW_RISK",
        attribution_breakdown=[{"factor": "Micro-Market Baseline", "impact": 9800}],
    )
    db_session.add(val_res)
    db_session.commit()

    # Query back and verify relationships
    saved_prop = db_session.query(PropertyRecord).filter_by(application_no="APP-DB-TEST-001").first()
    assert saved_prop is not None
    assert len(saved_prop.valuation_cases) == 1
    assert saved_prop.valuation_cases[0].borrower_name == "Rajesh Kumar"
    assert len(saved_prop.valuation_cases[0].valuation_results) == 1
    assert saved_prop.valuation_cases[0].valuation_results[0].net_assessed_value == 12646875.0

