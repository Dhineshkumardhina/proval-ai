"""Central API v1 router definition."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, valuation, cases, auth, comparables, datasets, ml, uncertainty, ai, audit

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

# AI Underwriter Assistant & Gemini Integration endpoints (Phase 2G)
api_router.include_router(ai.router, prefix="/ai", tags=["AI Underwriter"])

# Tamper-Evident Audit Trail & Model Governance endpoints (Phase 2H)
api_router.include_router(audit.router, prefix="/audit", tags=["Tamper-Evident Audit"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
