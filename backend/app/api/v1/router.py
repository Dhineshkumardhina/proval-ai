"""Central API v1 router definition."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    valuation,
    cases,
    auth,
    comparables,
    datasets,
    ml,
    uncertainty,
    ai,
    audit,
    acquisition,
    dataset_versions,
    governance,
    institutions,
)

api_router = APIRouter()

# Health endpoints
api_router.include_router(health.router, tags=["Health"])

# Valuation calculation endpoints
api_router.include_router(valuation.router, prefix="/valuation", tags=["Valuation"])

# Machine Learning Valuation Engine endpoints
api_router.include_router(ml.router, tags=["Machine Learning"])

# Statistical Uncertainty Quantification & Conformal Prediction endpoints
api_router.include_router(uncertainty.router, prefix="/ml", tags=["Uncertainty Quantification"])

# Valuation Case Management endpoints
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])

# Comparable deeds search endpoints
api_router.include_router(comparables.router, prefix="/comparables", tags=["Comparables"])

# Datasets and Real Estate Ingestion endpoints
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])

# Real Estate Data Acquisition & Connectors (Phase 4A)
api_router.include_router(acquisition.router, prefix="/acquisition", tags=["Data Acquisition"])

# Institutional Dataset Management & Version Snapshots (Phase 4A-5)
api_router.include_router(dataset_versions.router, prefix="/datasets/management", tags=["Dataset Versions"])

# AI Underwriter Assistant & Gemini Integration endpoints (Phase 2G)
api_router.include_router(ai.router, prefix="/ai", tags=["AI Underwriter"])

# Tamper-Evident Audit Trail & Model Governance endpoints (Phase 2H)
api_router.include_router(audit.router, prefix="/audit", tags=["Tamper-Evident Audit"])

# Institutional Data Quality & Governance Surveillance Dashboard (Phase 4B-5)
api_router.include_router(governance.router, prefix="/governance", tags=["Data Governance Dashboard"])

# Institutional Partner Tenancy & Multi-Tenancy endpoints (Phase 5B)
api_router.include_router(institutions.router, prefix="/institutions", tags=["Institutional Tenancy"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
