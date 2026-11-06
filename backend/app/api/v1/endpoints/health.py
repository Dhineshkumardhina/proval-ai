"""System health and operational monitoring endpoints adhering to cloud-native standards.

Provides liveness probes, readiness probes, and deep component diagnostic checks
for PostgreSQL, CatBoost/ML inference engine, and Gemini API integration.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx

from app.core.config import settings
from app.core.database import get_db, check_db_connectivity, engine
from app.services import audit_service
from app.ml.model_service import MLModelService
from app.core.telemetry import observability_registry

router = APIRouter()
ml_service = MLModelService()


def check_gemini_integration() -> Dict[str, Any]:
    """Verify Gemini API integration status.

    Requirement: An unavailable external service must not be reported as healthy.
    """
    api_key = (settings.GEMINI_API_KEY or "").strip()
    cloud_enabled = settings.ENABLE_AI_CLOUD_PROCESSING

    if not api_key or not cloud_enabled:
        return {
            "status": "mock_fallback",
            "model": settings.GEMINI_MODEL,
            "cloudProcessingEnabled": False,
            "provider": "deterministic-fallback-engine",
            "detail": "Deterministic rule-based underwriting active (no external cloud dependency)",
        }

    # If API key is provided, perform live availability probe against Gemini service via secure header
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}"
        headers = {
            "x-goog-api-key": api_key,
            "User-Agent": "PropValAI-HealthCheck/1.0",
        }
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return {
                    "status": "available",
                    "model": settings.GEMINI_MODEL,
                    "cloudProcessingEnabled": True,
                    "provider": "google-gemini",
                    "detail": "Live Gemini generative AI service reachable and responding",
                }
            else:
                return {
                    "status": "unavailable",
                    "model": settings.GEMINI_MODEL,
                    "cloudProcessingEnabled": False,
                    "error": f"Gemini API returned HTTP status {resp.status_code}",
                }
    except httpx.HTTPStatusError as he:
        return {
            "status": "unavailable",
            "model": settings.GEMINI_MODEL,
            "cloudProcessingEnabled": False,
            "error": f"Gemini API authentication/endpoint error: HTTP {he.response.status_code}",
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "model": settings.GEMINI_MODEL,
            "cloudProcessingEnabled": False,
            "error": f"Gemini service connection failure: {type(e).__name__}",
        }


def check_ml_service_status(db: Session) -> Dict[str, Any]:
    """Check availability of the machine learning inference service."""
    try:
        active_record_tuple = ml_service.get_active_model(db)
        if active_record_tuple:
            record, _ = active_record_tuple
            return {
                "status": "available",
                "trainingBlocked": False,
                "activeModel": record.model_name,
                "version": record.version,
                "algorithm": record.algorithm,
                "engineMode": "empirical_ml_inference",
            }
        return {
            "status": "gated",
            "trainingBlocked": True,
            "activeModel": None,
            "gateReason": "Requires minimum 1,000 empirical registered transaction records",
            "engineMode": "provisional_rule_based_fallback",
            "detail": "ML training gated pending empirical dataset threshold (fallback active)",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "trainingBlocked": True,
            "activeModel": None,
            "error": f"ML service error: {str(exc)}",
        }


@router.get("/health/live", summary="Application Liveness Probe")
def liveness_check():
    """Liveness probe: verifies that the FastAPI process is responsive and event loop is alive.

    Always returns 200 OK while the server process can handle requests.
    Used by container orchestrators to decide whether to restart the container.
    """
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="Application Readiness Probe")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """Readiness probe: validates critical dependencies before routing traffic.

    Checks:
    - PostgreSQL database connectivity
    - ML inference engine status
    - External Gemini service reachability (if configured)

    If database is unavailable, returns HTTP 503.
    An unavailable external service is not reported as healthy.
    """
    is_connected, db_latency_ms, db_dialect = check_db_connectivity(db)
    ml_status = check_ml_service_status(db)
    gemini_status = check_gemini_integration()

    # Database is a hard requirement for readiness
    if not is_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "ready": False,
            "database": "unavailable",
            "detail": "Database connectivity probe failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # External service health governance: unavailable external service must not be reported as healthy
    is_external_degraded = gemini_status.get("status") == "unavailable" or ml_status.get("status") == "unavailable"
    overall_status = "degraded" if is_external_degraded else "ready"

    return {
        "status": overall_status,
        "ready": True,
        "database": "connected",
        "latencyMs": db_latency_ms,
        "mlEngine": ml_status.get("status"),
        "geminiIntegration": gemini_status.get("status"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health", summary="Comprehensive System Health Status")
def get_health(response: Response, db: Session = Depends(get_db)):
    """Deep component-level diagnostic check providing audit integrity, DB metrics, and ML/AI status."""
    is_connected, db_latency_ms, db_dialect = check_db_connectivity(db)
    db_status = "connected" if is_connected else "unavailable"

    # Audit trail verification check
    audit_status = "unverified"
    audit_valid = False
    event_count = 0
    try:
        report = audit_service.verify_audit_chain(db)
        audit_valid = report.is_valid
        audit_status = "verified" if audit_valid else "degraded"
        event_count = report.total_events
    except Exception:
        audit_status = "unavailable"

    # ML engine status
    ml_status = check_ml_service_status(db)

    # Gemini integration status
    gemini_status = check_gemini_integration()

    # Health evaluation:
    # 1. Unhealthy if database or audit chain fails
    # 2. Degraded if Gemini is configured but unavailable, or ML is unavailable
    # 3. Healthy if DB, audit trail, and components are fully operational
    if is_connected:
        observability_registry.record_db_latency(db_latency_ms)

    if not audit_valid and audit_status != "unverified":
        observability_registry.record_audit_chain_failure()

    if db_status != "connected" or not audit_valid:
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif gemini_status.get("status") == "unavailable" or ml_status.get("status") == "unavailable":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "engineType": settings.ENGINE_TYPE,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": {
                "status": db_status,
                "dialect": db_dialect,
                "latencyMs": db_latency_ms,
            },
            "auditTrail": {
                "status": audit_status,
                "chainIntegrity": audit_valid,
                "eventCount": event_count,
            },
            "mlEngine": ml_status,
            "aiAssistant": gemini_status,
            "geminiIntegration": gemini_status,
        },
    }


@router.get("/metrics", summary="Operational Observability Metrics")
@router.get("/health/metrics", summary="Operational Observability Metrics Alias")
def get_operational_metrics(db: Session = Depends(get_db)):
    """System-wide operational metrics for CloudWatch, Datadog, Prometheus, or institutional APM."""
    observability_registry.record_db_pool_status(engine)
    return observability_registry.get_summary(db_session=db)
