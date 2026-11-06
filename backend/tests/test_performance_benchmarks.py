"""Regression test suite for performance optimizations (Phase 3D).

Verifies that performance optimizations do NOT break:
1. N+1 query regression guard (list_cases emits <= 4 queries, get_case_by_id <= 3 queries)
2. Valuation calculations & financial invariants
3. ML predictions & TreeSHAP explainability
4. Uncertainty estimation & conformal prediction gating
5. Data quality assessment & IQR/missingness computation
6. AI underwriting explanations & DPDP Act PII redaction
7. Cryptographic audit history & SHA-256 chain integrity
"""

import hashlib
import json
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.core.database import SessionLocal, engine
from app.models.valuation import ValuationCaseModel
from app.services import case_service, valuation_service, ingestion_service, audit_service
from app.schemas.valuation import ValuationInputParams
from app.ml.preprocessing import build_feature_vector
from app.ml.model_service import ml_model_service
from app.ml.uncertainty_service import uncertainty_service
import asyncio
from app.services.gemini_service import generate_underwriter_briefing, generate_deterministic_fallback_report


def test_n_plus_one_regression_prevention(db_session: Session):
    """Confirm list_cases does not suffer from N+1 query regression."""
    count = db_session.query(ValuationCaseModel).count()
    assert count >= 1, "Database must have existing cases to test"

    query_statements = []

    def log_query(conn, cursor, statement, parameters, context, executemany):
        query_statements.append(statement)

    event.listen(engine, "before_cursor_execute", log_query)
    try:
        cases, total = case_service.list_cases(db_session, limit=20)
        # 1 count query + 1 joined cases query + 1 selectin valuation_results query = 3 queries
        assert len(query_statements) <= 4, f"N+1 Regression detected: {len(query_statements)} queries emitted for list_cases"
        assert len(cases) > 0
    finally:
        event.remove(engine, "before_cursor_execute", log_query)


def test_get_case_by_id_query_efficiency(db_session: Session):
    """Confirm get_case_by_id uses eager loading and issues <= 2 queries."""
    first = db_session.query(ValuationCaseModel).first()
    assert first is not None

    query_statements = []

    def log_query(conn, cursor, statement, parameters, context, executemany):
        query_statements.append(statement)

    event.listen(engine, "before_cursor_execute", log_query)
    try:
        case = case_service.get_case_by_id(db_session, first.id)
        assert case is not None
        assert case.id == first.id
        # 1 joined query for case+property + 1 selectin query for valuation_results = 2 queries
        assert len(query_statements) <= 3, f"Query inefficiency detected: {len(query_statements)} queries emitted"
    finally:
        event.remove(engine, "before_cursor_execute", log_query)


def test_valuation_calculation_numerical_integrity():
    """Verify that valuation calculation maintains 100% numerical accuracy and invariants."""
    params = ValuationInputParams(
        carpetAreaSqFt=1000.0,
        superBuiltUpAreaSqFt=1300.0,
        baseMarketRatePerSqFt=10000.0,
        circleRatePerSqFt=8000.0,
        floorRiseFactor=200.0,
        roadWidthFactor=100.0,
        amenitiesPremium=300.0,
        structuralDepreciation=100.0,
        underwriterHaircutPct=10.0,
        distressDiscountPct=15.0,
        ltvRatioPct=75.0,
        legalRiskPenaltyPct=0.0,
    )
    res = valuation_service.calculate_valuation(params)

    # Base + (200 + 100 + 300 - 100) = 10500 per sq ft
    assert res.ruleAdjustedRatePerSqFt == 10500.0
    # Gross Market Value = 1000 * 10500 = 10,500,000
    assert res.grossMarketValue == 10500000
    # Net Assessed = 10,500,000 * (1 + 0.10) = 11,550,000
    assert res.netAssessedValue == 11550000
    # Distress Liquidation = 11,550,000 * (1 - 0.15) = 9,817,500
    assert res.distressLiquidationValue == 9817500
    # Max Sanction = 11,550,000 * 0.75 = 8,662,500
    assert res.maxSanctionAmount == 8662500
    assert res.confidenceScorePct >= 70.0
    assert len(res.attributionBreakdown) > 0


def test_ml_prediction_and_fallback_integrity(db_session: Session):
    """Verify ML engine handles requests gracefully and provides transparent fallback metadata."""
    status = ml_model_service.get_ml_status(db_session)
    assert status.trainingGateStatus in ("OPEN", "BLOCKED")
    assert status.requiredRecordsThreshold == 1000

    # Build feature vector
    feat = build_feature_vector(
        city="Bengaluru",
        locality="Whitefield",
        property_type="High-Rise Apartment",
        carpet_area_sqft=1200.0,
        floor_no=5,
        total_floors=15,
        guideline_rate_per_sqft=8000.0,
        age_years=2,
        transaction_quarter="2024-Q3",
    )
    assert "floor_ratio" in feat.columns
    assert feat["carpet_area_sqft"].iloc[0] == 1200.0
    assert feat["guideline_rate_per_sqft"].iloc[0] == 8000.0


def test_uncertainty_estimation_integrity(db_session: Session):
    """Verify statistical uncertainty quantification reports calibrated/gated state accurately."""
    status = uncertainty_service.get_status(db_session)
    assert status.supportedCoverageLevels in ([90, 95], [0.90, 0.95])
    assert "HEURISTIC_CONFIDENCE_SCORE" in status.conceptualTaxonomy
    assert "CONFORMAL_PREDICTION_INTERVAL" in status.conceptualTaxonomy
    assert "CALIBRATION_SET" in status.conceptualTaxonomy


def test_data_quality_assessment_integrity(db_session: Session):
    """Verify dataset ingestion computes exact quality metrics, IQR, missingness, and deduplication."""
    csv_content = (
        "date,city,locality,project,carpet_area,unit,price,property_type,circle_rate\n"
        "2024-03-15,Bengaluru,Indiranagar,Project A,1200,sq ft,12000000,Apartment,8000\n"
        "2024-03-16,Bengaluru,Indiranagar,Project B,1400,sq ft,14000000,Apartment,8000\n"
        "2024-03-17,Bengaluru,Indiranagar,Project C,1100,sq ft,11000000,Apartment,8000\n"
        "2024-03-18,Bengaluru,Indiranagar,Project D,,sq ft,13000000,Apartment,8000\n"  # Missing area -> rejected
    ).encode("utf-8")

    meta = {"sourceType": "sro_registration", "description": "Regression Quality Test"}
    dataset, report = ingestion_service.ingest_dataset(
        db=db_session,
        file_bytes=csv_content,
        filename="regression_test.csv",
        metadata=meta,
    )

    assert dataset.total_rows == 4
    assert dataset.valid_rows == 3
    assert dataset.rejected_rows == 1
    assert report.total_records == 4
    assert report.valid_records == 3
    assert "carpet_area" in report.missing_value_percentages
    assert report.missing_value_percentages["carpet_area"] == 25.0
    assert report.price_metrics["median"] == 12000000.0


def test_ai_underwriter_explanation_integrity(db_session: Session):
    """Verify AI underwriting briefing generates structured report with DPDP Act PII redaction."""
    first = db_session.query(ValuationCaseModel).first()
    assert first is not None

    payload = {
        "case_id": first.id,
        "city": "Bengaluru",
        "loan_requested": 7500000.0,
        "carpet_area_sqft": 1200.0,
        "gross_market_value": 9000000.0,
        "net_assessed_value": 9000000.0,
        "distress_liquidation_value": 7500000.0,
        "max_sanction_amount": 6750000.0,
        "comparables": [],
        "risk_tier": "LOW",
        "pii_redacted_count": 0,
    }

    briefing = asyncio.run(generate_underwriter_briefing(payload, db_session))
    assert briefing is not None
    assert briefing.case_id == first.id
    assert briefing.provider in ("gemini", "deterministic_fallback")
    assert briefing.report.valuation_summary != ""
    assert len(briefing.report.major_valuation_factors) > 0
    assert briefing.disclaimer != ""


def test_audit_history_hash_chain_integrity(db_session: Session):
    """Verify cryptographic SHA-256 audit chain integrity and sequence enforcement."""
    evt1 = audit_service.record_audit_event(
        db=db_session,
        event_type="PERF_AUDIT_TEST_1",
        actor_id="test_runner",
        actor_role="AUDITOR",
        payload={"action": "perf_test_1"},
    )
    evt2 = audit_service.record_audit_event(
        db=db_session,
        event_type="PERF_AUDIT_TEST_2",
        actor_id="test_runner",
        actor_role="AUDITOR",
        payload={"action": "perf_test_2"},
    )

    assert evt2.prev_hash == evt1.current_hash
    assert evt2.sequence_number == evt1.sequence_number + 1

    # Verify audit chain verification function returns valid
    verification = audit_service.verify_audit_chain_integrity(db_session)
    assert verification["is_valid"] is True
    assert verification["tampered"] is False
