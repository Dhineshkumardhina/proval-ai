"""PropVal AI FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, get_db
from app.core.seed import seed_demonstration_cases
from app.core.logging import setup_logging
from app.core.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import (
    liveness_check as health_liveness_check,
    readiness_check as health_readiness_check,
    get_health as health_diagnostic_check,
)
from app.core.telemetry import init_telemetry, observability_registry

# Initialize structured logging subsystem
setup_logging(environment=settings.ENVIRONMENT)
logger = logging.getLogger("propval.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: validate environment, initialize schema, and seed demo cases."""
    # 1. Strict validation of production environment variables at startup
    logger.info("Initializing PropVal AI application (Environment: %s)...", settings.ENVIRONMENT)
    settings.validate_production_startup()

    # 2. Ensure tables exist for local SQLite zero-friction startup
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    # 3. Seed demonstration cases if database is empty
    db = SessionLocal()
    try:
        seed_demonstration_cases(db)
    finally:
        db.close()

    logger.info("PropVal AI application startup completed successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Institutional Valuation & Underwriting Backend for Indian Housing Finance Companies.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# OpenTelemetry Distributed Tracing & Observability (Phase 6E)
init_telemetry(app=app, engine=engine)

# Middleware Pipeline (Executed in reverse order of addition)
# 1. Security HTTP Headers & Cookie hardening
app.add_middleware(SecurityHeadersMiddleware)
# 2. Rate limiting & DoS defense
app.add_middleware(RateLimitMiddleware)
# 3. Correlation ID & structured access logging
app.add_middleware(RequestLoggingMiddleware)

# CORS Configuration: strict origin whitelist
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Global defensive exception handler: prevent sensitive internal stack trace leakage."""
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    logger.error("Internal server error on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. The incident has been recorded for institutional review."},
    )


# Root level health checks (satisfies orchestrator probes and GET /health, /health/live, /health/ready)
@app.get("/health/live", tags=["Health"], summary="Root Liveness Probe")
def root_liveness():
    """Root liveness probe for orchestrators."""
    return health_liveness_check()


@app.get("/health/ready", tags=["Health"], summary="Root Readiness Probe")
def root_readiness(response: Response, db: Session = Depends(get_db)):
    """Root readiness probe verifying database, ML engine, and Gemini availability."""
    return health_readiness_check(response=response, db=db)


@app.get("/health", tags=["Health"], summary="Root System Health Status")
def root_health(response: Response, db: Session = Depends(get_db)):
    """Root comprehensive system health check."""
    return health_diagnostic_check(response=response, db=db)


@app.get("/metrics", tags=["Observability"], summary="Root Observability Metrics Endpoint")
def root_metrics(db: Session = Depends(get_db)):
    """Root operational observability metrics for monitoring systems."""
    observability_registry.record_db_pool_status(engine)
    return observability_registry.get_summary(db_session=db)


# Include V1 Router under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
