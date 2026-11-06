"""Tests for Phase 4C real estate transaction validation and fraud detection."""

import pytest
from app.verification.anomaly_detector import TransactionAnomalyDetector, AnomalyVerdict


def test_area_consistency_carpet_exceeds_built_up():
    """Verify that carpet area exceeding built-up area triggers quarantine."""
    record = {
        "carpet_area_sqft": 1400.0,
        "built_up_area_sqft": 1200.0,
        "super_built_up_area_sqft": 1600.0,
        "transaction_price": 9500000.0,
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert "AREA_CONSISTENCY_INCONSISTENT" in (verdict.quarantine_code or "")
    assert any("strictly exceeds built-up area" in f for f in verdict.anomalous_fields)


def test_area_consistency_built_up_exceeds_super_built_up():
    """Verify built-up area exceeding super built-up triggers quarantine."""
    record = {
        "carpet_area_sqft": 1000.0,
        "built_up_area_sqft": 1500.0,
        "super_built_up_area_sqft": 1300.0,
        "transaction_price": 8500000.0,
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert verdict.quarantine_code == "SUPER_BUILT_UP_INCONSISTENCY"


def test_area_loading_factor_anomaly():
    """Verify abnormal loading factor outside standard 1.05 - 2.0 range triggers flag."""
    record = {
        "carpet_area_sqft": 1000.0,
        "built_up_area_sqft": 1200.0,
        "super_built_up_area_sqft": 2600.0,  # 2.6x loading factor
        "transaction_price": 9500000.0,
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert any("Abnormal loading factor" in f for f in verdict.anomalous_fields)


def test_fraud_circle_rate_undervaluation():
    """Verify stamp duty undervaluation alert when price is > 30% below statutory guideline value."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 3000000.0,  # ₹3,000 / sqft
        "guideline_rate_per_sqft": 5500.0,  # Circle rate ₹5,500 / sqft -> ~45% undervaluation
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert verdict.fraud_risk_level == "HIGH"
    assert "Stamp Duty Undervaluation Alert" in (verdict.quarantine_reason or "")
    assert verdict.quarantine_code == "CIRCLE_RATE_UNDERVALUATION"


def test_fraud_circle_rate_extreme_speculation():
    """Verify benami / extreme speculation alert when price is > 250% above circle rate."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 25000000.0,  # ₹25,000 / sqft
        "guideline_rate_per_sqft": 6000.0,  # Circle rate ₹6,000 / sqft -> >300% premium
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.fraud_risk_level == "MEDIUM"
    assert "Extreme Speculation / Benami Alert" in (verdict.quarantine_reason or "")


def test_suspicious_round_number_pricing_on_fractional_area():
    """Verify round number consideration on fractional carpet area triggers EVALUATE fraud risk."""
    record = {
        "carpet_area_sqft": 1250.45,  # Fractional area
        "transaction_price": 10000000.0,  # Exact ₹1.00 Crore
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert any("Suspicious round consideration" in f for f in verdict.anomalous_fields)
    assert verdict.fraud_risk_level == "EVALUATE"


def test_city_micro_market_rate_outlier():
    """Verify rate outside city-specific micro-market range triggers outlier warning."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 1500000.0,  # ₹1,500 / sqft, below Bengaluru minimum of ₹2,500 / sqft
        "city": "Bengaluru",
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert any("deviates from Bengaluru micro-market range" in f for f in verdict.anomalous_fields)


def test_geographic_centroid_consistency_outlier():
    """Verify coordinates far outside urban centroid bounds trigger spatial outlier quarantine."""
    record = {
        "carpet_area_sqft": 1000.0,
        "transaction_price": 8000000.0,
        "city": "Bengaluru",
        "latitude": 15.5000,  # North Karnataka / Goa latitude, ~350 km from Bengaluru
        "longitude": 75.0000,
    }
    verdict: AnomalyVerdict = TransactionAnomalyDetector.inspect(record)
    assert verdict.is_anomalous is True
    assert "SPATIAL_OUTLIER_ANOMALY" in (verdict.quarantine_code or "")

