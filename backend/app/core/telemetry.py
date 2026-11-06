"""OpenTelemetry distributed tracing, metrics registry, and observability instrumentation.

Adheres to cloud-native OpenTelemetry standards, W3C trace context propagation,
and financial-grade PII/credential redaction in trace spans.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional
from threading import Lock

from opentelemetry import trace
from opentelemetry.trace import TracerProvider, Span
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.config import settings
from app.core.logging import redact_sensitive_text

logger = logging.getLogger("propval.telemetry")

# Thread-safe singleton registry
_metrics_lock = Lock()


class SensitiveDataSpanProcessor(SpanProcessor):
    """OpenTelemetry span processor that sanitizes span attributes and descriptions.

    Guarantees that credentials, tokens, bearer headers, Aadhaar, PAN, and database
    passwords cannot leak into remote trace collectors (e.g., Datadog, Jaeger, CloudWatch).
    """

    def on_start(self, span: Span, parent_context: Any = None) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            # Sanitize attributes
            if hasattr(span, "_attributes") and span._attributes:
                for key, val in list(span._attributes.items()):
                    if isinstance(val, str):
                        span._attributes[key] = redact_sensitive_text(val)
                    elif isinstance(val, (list, tuple)):
                        span._attributes[key] = [
                            redact_sensitive_text(str(v)) if isinstance(v, str) else v
                            for v in val
                        ]
            # Sanitize status description
            if hasattr(span, "status") and span.status and span.status.description:
                span.status.description = redact_sensitive_text(span.status.description)
        except Exception:
            # Defensive: span processing failure must never crash application
            pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class ObservabilityRegistry:
    """In-memory operational metrics collector for real-time institutional monitoring."""

    def __init__(self):
        self._api_requests_total = 0
        self._api_failures_total = 0
        self._api_latencies: List[float] = []

        self._db_latencies: List[float] = []
        self._db_pool_checkedin = 0
        self._db_pool_checkedout = 0
        self._db_pool_size = 0

        self._background_job_failures = 0
        self._ml_inference_latencies: List[float] = []
        self._valuation_calculation_failures = 0
        self._authentication_failures = 0
        self._audit_chain_failures = 0

    def record_api_request(self, status_code: int, duration_ms: float) -> None:
        with _metrics_lock:
            self._api_requests_total += 1
            if status_code >= 400:
                self._api_failures_total += 1
            self._api_latencies.append(duration_ms)
            if len(self._api_latencies) > 1000:
                self._api_latencies = self._api_latencies[-500:]

    def record_db_latency(self, latency_ms: float) -> None:
        with _metrics_lock:
            self._db_latencies.append(latency_ms)
            if len(self._db_latencies) > 500:
                self._db_latencies = self._db_latencies[-250:]

    def record_db_pool_status(self, engine: Any) -> None:
        if not engine:
            return
        try:
            pool = getattr(engine, "pool", None)
            if pool:
                with _metrics_lock:
                    self._db_pool_size = pool.size()
                    self._db_pool_checkedin = getattr(pool, "checkedin", lambda: 0)()
                    self._db_pool_checkedout = getattr(pool, "checkedout", lambda: 0)()
        except Exception:
            pass

    def record_background_job_failure(self) -> None:
        with _metrics_lock:
            self._background_job_failures += 1

    def record_ml_inference(self, latency_ms: float) -> None:
        with _metrics_lock:
            self._ml_inference_latencies.append(latency_ms)
            if len(self._ml_inference_latencies) > 500:
                self._ml_inference_latencies = self._ml_inference_latencies[-250:]

    def record_valuation_failure(self) -> None:
        with _metrics_lock:
            self._valuation_calculation_failures += 1

    def record_authentication_failure(self) -> None:
        with _metrics_lock:
            self._authentication_failures += 1

    def record_audit_chain_failure(self) -> None:
        with _metrics_lock:
            self._audit_chain_failures += 1

    def get_summary(self, db_session: Any = None) -> Dict[str, Any]:
        """Aggregate operational metrics across all monitored subsystems."""
        with _metrics_lock:
            avg_api_lat = (
                round(sum(self._api_latencies) / len(self._api_latencies), 2)
                if self._api_latencies
                else 0.0
            )
            p95_api_lat = (
                round(sorted(self._api_latencies)[int(len(self._api_latencies) * 0.95)], 2)
                if self._api_latencies
                else 0.0
            )
            avg_db_lat = (
                round(sum(self._db_latencies) / len(self._db_latencies), 2)
                if self._db_latencies
                else 0.0
            )
            avg_ml_lat = (
                round(sum(self._ml_inference_latencies) / len(self._ml_inference_latencies), 2)
                if self._ml_inference_latencies
                else 0.0
            )

            metrics = {
                "api": {
                    "totalRequests": self._api_requests_total,
                    "totalFailures": self._api_failures_total,
                    "avgLatencyMs": avg_api_lat,
                    "p95LatencyMs": p95_api_lat,
                },
                "database": {
                    "avgLatencyMs": avg_db_lat,
                    "poolSize": self._db_pool_size,
                    "poolCheckedIn": self._db_pool_checkedin,
                    "poolCheckedOut": self._db_pool_checkedout,
                },
                "backgroundJobs": {
                    "failures": self._background_job_failures,
                },
                "machineLearning": {
                    "inferencesMonitored": len(self._ml_inference_latencies),
                    "avgInferenceLatencyMs": avg_ml_lat,
                },
                "valuation": {
                    "calculationFailures": self._valuation_calculation_failures,
                },
                "security": {
                    "authenticationFailures": self._authentication_failures,
                    "auditChainFailures": self._audit_chain_failures,
                },
                "telemetry": {
                    "otelEnabled": settings.OTEL_ENABLED,
                    "serviceName": settings.OTEL_SERVICE_NAME,
                    "exporterEndpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                },
            }

        # Query data ingestion lifecycle status if db_session available
        if db_session:
            try:
                from sqlalchemy import text
                res = db_session.execute(
                    text("SELECT lifecycle_state, COUNT(*) FROM deeds GROUP BY lifecycle_state")
                ).fetchall()
                ingestion_counts = {row[0]: row[1] for row in res}
                metrics["dataIngestion"] = {
                    "countsByState": ingestion_counts,
                    "totalDeeds": sum(ingestion_counts.values()),
                }
            except Exception:
                metrics["dataIngestion"] = {"status": "unavailable"}

        return metrics


observability_registry = ObservabilityRegistry()


def init_telemetry(app: Any, engine: Any = None) -> Optional[TracerProvider]:
    """Initialize OpenTelemetry tracer provider, instruments, and sanitizing processors.

    Fails open safely: monitoring errors will never prevent the application from serving requests.
    """
    try:
        resource = Resource.create(
            {
                "service.name": settings.OTEL_SERVICE_NAME,
                "service.version": settings.VERSION,
                "deployment.environment": settings.ENVIRONMENT,
            }
        )

        tracer_provider = SDKTracerProvider(resource=resource)

        # 1. Add sensitive data scrubbing processor
        tracer_provider.add_span_processor(SensitiveDataSpanProcessor())

        # 2. Add OTLP exporter processor if enabled
        if settings.OTEL_ENABLED:
            endpoint = f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces"
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OpenTelemetry OTLP HTTP span exporter configured for %s", endpoint)

        # 3. Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # 4. Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            excluded_urls="health,health/live,health/ready",
        )

        # 5. Instrument SQLAlchemy
        if engine is not None:
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                tracer_provider=tracer_provider,
                skip_dep_check=True,
            )

        # 6. Instrument HTTPX client
        HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(
            "OpenTelemetry instrumentation successfully initialized for FastAPI, SQLAlchemy, and HTTPX."
        )
        return tracer_provider

    except Exception as exc:
        logger.warning(
            "OpenTelemetry initialization encountered an issue: %s. Continuing in fallback mode.",
            str(exc),
        )
        return None


def get_current_trace_context() -> Dict[str, str]:
    """Retrieve current OpenTelemetry W3C trace identifiers."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span_ctx = span.get_span_context()
        if span_ctx.is_valid:
            return {
                "traceId": format(span_ctx.trace_id, "032x"),
                "spanId": format(span_ctx.span_id, "016x"),
            }
    return {}


def inject_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject W3C traceparent context into outbound HTTP request headers."""
    try:
        propagator = TraceContextTextMapPropagator()
        propagator.inject(headers)
    except Exception:
        pass
    return headers
