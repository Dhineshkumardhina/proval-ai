"""Pydantic schemas for AI Underwriter Assistant (Phase 2G)."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RedactPreviewRequest(BaseModel):
    """Request payload to test or preview PII redaction."""

    text: str = Field(..., description="Raw text containing potential PII")


class RedactPreviewResponse(BaseModel):
    """Response payload with redacted text and audit metrics."""

    original_length: int
    redacted_text: str
    redactions_count: int
    redaction_types: List[str]


class AIStatusResponse(BaseModel):
    """Operational status of the Gemini / AI Underwriter integration."""

    configured: bool = Field(..., description="Whether GEMINI_API_KEY is configured in backend environment")
    model: str = Field(..., description="Active Gemini model name or fallback identifier")
    provider: str = Field(..., description="'gemini' or 'deterministic_fallback'")
    cloud_processing_enabled: bool = Field(..., description="Whether cloud API calls are enabled")
    privacy_guard_active: bool = Field(True, description="Indicates active DPDP Act 2023 PII scrubbing")
    rate_limit_per_minute: int = Field(..., description="Backend rate limit throttle")
    regulatory_framework: str = Field(..., description="Data protection and credit compliance standard")
    disclaimer: str = Field(..., description="Advisory disclaimer for institutional credit underwriting")


class AIUnderwriterFactor(BaseModel):
    """Individual value or risk driver evaluated by the underwriter assistant."""

    factor_name: str
    impact: str  # POSITIVE, NEGATIVE, NEUTRAL
    details: str


class AIUnderwriterReport(BaseModel):
    """Structured executive underwriter briefing synthesized from collateral evidence."""

    valuation_summary: str = Field(..., description="Executive summary of valuation evidence")
    major_valuation_factors: List[AIUnderwriterFactor] = Field(..., description="Detailed value drivers")
    comparable_evidence_analysis: str = Field(..., description="Analysis of comparable sales and spatial proximity")
    location_considerations: str = Field(..., description="Micro-market infrastructure and spatial dynamics")
    data_quality_concerns: List[str] = Field(..., description="Data completeness and synthetic/heuristic limitations")
    legal_regulatory_risks: List[str] = Field(..., description="Title, EC, RERA, and municipal compliance observations")
    valuation_limitations: List[str] = Field(..., description="Provisional rule-based caveats and absence of live ML")
    underwriter_recommendations: List[str] = Field(..., description="Actionable verification checklist for credit officer")
    recommendation_decision_role: str = Field(..., description="Explicit disclaimer on underwriter final authority")


class AIExplainCaseResponse(BaseModel):
    """Full API response for an underwriter briefing."""

    case_id: str
    provider: str  # "gemini" or "deterministic_fallback"
    model_name: str
    status: str
    pii_redacted_count: int
    report: AIUnderwriterReport
    disclaimer: str
    generated_at: str

