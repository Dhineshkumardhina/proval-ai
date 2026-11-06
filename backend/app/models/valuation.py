"""Valuation case and estimation result database models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ValuationCaseModel(Base):
    """Institutional loan appraisal case record."""

    __tablename__ = "valuation_cases"
    __table_args__ = (
        Index("ix_valuation_cases_status_created_at", "status", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    property_id = Column(String(36), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Borrower & Underwriting info
    borrower_name = Column(String(255), nullable=False, index=True)
    co_borrower_name = Column(String(255), nullable=True)
    cibil_score = Column(Integer, default=750)
    loan_requested = Column(Float, nullable=False)
    declared_agreement_value = Column(Float, nullable=False)
    branch = Column(String(128), nullable=False)
    assigned_underwriter = Column(String(128), nullable=False)

    # Workflow state
    status = Column(String(32), default="READY_FOR_APPROVAL", index=True)
    status_label = Column(String(64), default="Ready for Approval")

    # Underwriter adjustments & risk limits
    underwriter_haircut_pct = Column(Float, default=0.0)
    distress_discount_pct = Column(Float, default=17.0)
    ltv_ratio_pct = Column(Float, default=75.0)
    legal_risk_penalty_pct = Column(Float, default=0.0)

    # Statutory & Legal Verification Fields
    rera_registration = Column(String(128), default="")
    bbmp_plan_approval_no = Column(String(128), default="")
    title_chain_years = Column(Integer, default=30)
    encumbrance_status = Column(String(64), default="NIL_ENCUMBRANCE")

    # Structured Document, Inspection & Comparables Collections
    comparables = Column(JSON, default=list)
    document_fields = Column(JSON, default=list)
    survey_photos = Column(JSON, default=list)
    audit_notes = Column(JSON, default=list)

    # Phase 7B: Pilot Case Management & Advisory Safety Controls
    case_reference = Column(String(64), nullable=True, index=True)
    assigned_valuer = Column(String(128), default="Empaneled Field Valuer")
    reviewing_credit_officer = Column(String(128), default="")
    valuation_engine_version = Column(String(32), default="hedonic-scorecard-v0.2.0")
    valuation_methodology = Column(String(64), default="DETERMINISTIC_HEDONIC")
    advisory_classification = Column(String(32), default="ADVISORY_ONLY")
    divergence_pct = Column(Float, default=0.0)
    requires_senior_review = Column(Boolean, default=False)
    human_sign_off_by = Column(String(128), nullable=True)
    human_sign_off_date = Column(DateTime(timezone=True), nullable=True)
    human_sign_off_notes = Column(String(1000), default="")

    # Data Provenance
    data_source = Column(String(64), nullable=False, default="synthetic-demo")

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )

    # Relationships
    property = relationship("PropertyRecord", back_populates="valuation_cases")
    valuation_results = relationship("ValuationResultModel", back_populates="case", cascade="all, delete-orphan")
    institution = relationship("InstitutionModel", backref="valuation_cases")


class ValuationResultModel(Base):
    """Persisted valuation calculation result and attribution scorecard."""

    __tablename__ = "valuation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("valuation_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)

    # Engine & Provenance Metadata
    engine_version = Column(String(32), nullable=False, default="0.2.0")
    engine_type = Column(String(64), nullable=False, default="provisional rule-based estimation")
    data_source = Column(String(64), nullable=False, default="synthetic-demo")

    # Valuation Metrics
    carpet_area_sqft = Column(Float, nullable=False)
    super_built_up_area_sqft = Column(Float, nullable=False)
    unadjusted_rate_per_sqft = Column(Float, nullable=False)
    rule_adjusted_rate_per_sqft = Column(Float, nullable=False)
    circle_rate_per_sqft = Column(Float, nullable=False)

    # Assessed Monetary Figures
    gross_market_value = Column(Float, nullable=False)
    net_assessed_value = Column(Float, nullable=False)
    distress_liquidation_value = Column(Float, nullable=False)
    max_sanction_amount = Column(Float, nullable=False)

    # Risk & Credibility Metrics
    deviation_from_circle_rate_pct = Column(Float, nullable=False)
    confidence_score_pct = Column(Float, nullable=False)
    risk_tier = Column(String(32), nullable=False)

    # Detailed Attribution Waterfall (Stored as structured JSON)
    attribution_breakdown = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    # Relationships
    case = relationship("ValuationCaseModel", back_populates="valuation_results")
