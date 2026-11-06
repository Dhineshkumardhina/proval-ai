"""Institutional tenant and credit policy database models (Phase 5B).

Enables multi-tenancy for Housing Finance Companies (HFCs), NBFCs, Banks,
and Valuation Partner Organizations with strict data isolation and policy customization.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class InstitutionModel(Base):
    """Institutional partner tenant entity."""

    __tablename__ = "institutions"
    __table_args__ = (
        Index("ix_institutions_code_status", "code", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    institution_type = Column(String(64), nullable=False, default="HFC")  # HFC, NBFC, BANK, VALUATION_FIRM
    status = Column(String(32), default="ACTIVE", index=True)  # ONBOARDING, ACTIVE, SUSPENDED, INACTIVE

    # Corporate & Statutory Identifiers
    cin_or_registration_no = Column(String(128), default="")
    rbi_nhb_registration_no = Column(String(128), default="")

    # Primary Contact & Operations
    primary_contact_name = Column(String(128), default="")
    primary_contact_email = Column(String(255), nullable=False)
    primary_contact_phone = Column(String(32), default="")
    registered_office_address = Column(Text, default="")

    # Branch Hierarchy: list of {"code": "BR01", "name": "...", "city": "...", "state": "...", "tier": "METRO"}
    branches = Column(JSON, default=list)

    # Domain Whitelist for SSO & authorized user provisioning: e.g. ["apexhfc.com"]
    authorized_domains = Column(JSON, default=list)

    # Data Retention & Regulatory Compliance (RBI / PMLA mandate 8 years minimum)
    retention_period_years = Column(Integer, default=8)

    # B2B Partner API Authentication
    api_key_prefix = Column(String(16), nullable=True)  # e.g. "pv_live_apx_"
    api_key_hash = Column(String(64), nullable=True)    # SHA-256 hash of API secret
    webhook_url = Column(String(500), nullable=True)

    # Phase 7B: Pilot Authorization & Legal Agreements Framework
    agreement_status = Column(String(32), default="PENDING", index=True)  # PENDING, DRAFT, UNDER_REVIEW, EXECUTED, EXPIRED
    agreement_reference = Column(String(128), default="")
    agreement_signed_date = Column(DateTime(timezone=True), nullable=True)
    agreement_signatory_name = Column(String(128), default="")
    agreement_signatory_title = Column(String(128), default="")
    agreement_evidence_url = Column(String(500), default="")

    dpa_status = Column(String(32), default="PENDING")  # PENDING, DRAFT, UNDER_REVIEW, EXECUTED, EXPIRED
    dpa_reference = Column(String(128), default="")
    dpa_signed_date = Column(DateTime(timezone=True), nullable=True)
    dpa_signatory_name = Column(String(128), default="")

    pilot_authorization_status = Column(String(32), default="UNAUTHORIZED", index=True)  # UNAUTHORIZED, PENDING_REVIEW, AUTHORIZED, SUSPENDED, REVOKED
    pilot_commencement_date = Column(DateTime(timezone=True), nullable=True)
    pilot_expiry_date = Column(DateTime(timezone=True), nullable=True)
    authorized_pilot_participants = Column(JSON, default=list)  # List of authorized email/username handles
    approved_data_categories = Column(JSON, default=list)  # ["COLLATERAL_DEED", "PROPERTY_ATTRIBUTES"]
    permitted_purposes = Column(JSON, default=list)  # ["SHADOW_VALUATION_PILOT"]
    approved_operational_scope = Column(JSON, default=dict)  # {"max_cases": 100, "allowed_cities": ["Bengaluru"]}
    approval_evidence_reference = Column(String(255), default="")
    is_pilot_approved = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    policy = relationship("InstitutionPolicyModel", back_populates="institution", uselist=False, cascade="all, delete-orphan")


class InstitutionPolicyModel(Base):
    """Institution-specific credit underwriting & valuation policy configuration."""

    __tablename__ = "institution_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    # Credit & Risk Tolerances
    max_ltv_pct = Column(Float, default=75.0, nullable=False)
    default_distress_discount_pct = Column(Float, default=17.0, nullable=False)
    max_underwriter_haircut_pct = Column(Float, default=25.0, nullable=False)
    circle_rate_tolerance_pct = Column(Float, default=20.0, nullable=False)
    min_cibil_score = Column(Integer, default=700, nullable=False)

    # Statutory & Legal Policy Rules
    mandatory_title_search_years = Column(Integer, default=30, nullable=False)
    require_rera_for_ongoing = Column(Boolean, default=True, nullable=False)
    require_nil_encumbrance = Column(Boolean, default=True, nullable=False)

    # Tiered Sanction Approval Hierarchy:
    # List of {"tier": 1, "max_amount": 5000000, "role_required": "CREDIT_UNDERWRITER", "label": "Branch Credit Underwriter"}
    approval_hierarchy = Column(JSON, default=list)

    # Audit & Inspection Requirements
    audit_requirements = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    institution = relationship("InstitutionModel", back_populates="policy")

