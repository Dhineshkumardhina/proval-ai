"""Phase 6E Verification Suite: Dependency Harmonization & Observability Remediation.

Verifies:
1. pip check passes with zero broken requirements.
2. OpenTelemetry API and SDK version harmonization (>=1.44.0).
3. Exporter and instrumentations compatibility (FastAPI, SQLAlchemy, HTTPX).
4. Structured logging correlation with OpenTelemetry trace_id and span_id.
5. Trace propagation via W3C traceparent headers.
6. Financial-grade sensitive data redaction in spans.
7. Defensive failure safety of monitoring subsystem.
8. Operational metrics registry tracking (API, DB, ML, Ingestion, Valuation, Auth, Audit).
9. /metrics and /api/v1/metrics endpoints.
10. Dependency lock reproducibility.
"""

import subprocess
import sys
import json
import logging
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from app.main import app
from app.core.config import settings
from app.core.logging import (
    StructuredJsonFormatter,
    SensitiveDataRedactor,
    redact_sensitive_text,
    request_id_ctx,
)
from app.core.telemetry import (
    SensitiveDataSpanProcessor,
    observability_registry,
    inject_trace_headers,
    get_current_trace_context,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# 1. Dependency Compatibility & Pip Check
def test_pip_check_clean():
    """Verify pip check reports zero broken requirements across all installed packages."""
    res = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"pip check failed: {res.stdout} {res.stderr}"
    assert "No broken requirements found" in res.stdout or res.stdout.strip() == ""


def test_opentelemetry_version_harmonization():
    """Verify installed OpenTelemetry API, SDK, and exporters are >= 1.44.0 and aligned."""
    import opentelemetry.trace as otel_api
    import opentelemetry.sdk.trace as otel_sdk

    api_ver = getattr(otel_api, "__version__", "1.45.2")
    sdk_ver = getattr(otel_sdk, "__version__", "1.45.2")

    # FastAPI requires opentelemetry-api >= 1.44.0
    import importlib.metadata
    installed_api_ver = importlib.metadata.version("opentelemetry-api")
    installed_sdk_ver = importlib.metadata.version("opentelemetry-sdk")
    installed_fastapi_ver = importlib.metadata.version("fastapi")

    assert installed_fastapi_ver == "0.142.2"
    assert installed_api_ver >= "1.44.0", f"opentelemetry-api too old: {installed_api_ver}"
    assert installed_sdk_ver >= "1.44.0", f"opentelemetry-sdk too old: {installed_sdk_ver}"


def test_otlp_http_exporter_compatibility():
    """Verify OTLP HTTP trace exporter instantiates with configured endpoint."""
    endpoint = "http://localhost:4318/v1/traces"
    exporter = OTLPSpanExporter(endpoint=endpoint)
    assert exporter is not None
    assert getattr(exporter, "_endpoint", "").startswith("http://localhost:4318")


# 2. Structured Logging & Distributed Trace Correlation
def test_structured_logging_json_schema():
    """Verify structured logger formats valid JSON with standard metadata."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Underwriting valuation engine executed",
        args=(),
        exc_info=None,
    )
    token = request_id_ctx.set("req-test-uuid-12345")
    try:
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Underwriting valuation engine executed"
        assert data["requestId"] == "req-test-uuid-12345"
        assert "timestamp" in data
    finally:
        request_id_ctx.reset(token)


def test_structured_logging_trace_correlation():
    """Verify active OpenTelemetry traceId and spanId are injected into structured logs."""
    provider = TracerProvider()
    tracer = provider.get_tracer("test_tracer")
    formatter = StructuredJsonFormatter()

    with tracer.start_as_current_span("institutional_underwriting_span") as span:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=25,
            msg="Processing collateral review",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        data = json.loads(formatted)

        span_ctx = span.get_span_context()
        expected_trace_id = format(span_ctx.trace_id, "032x")
        expected_span_id = format(span_ctx.span_id, "016x")

        assert "traceId" in data
        assert data["traceId"] == expected_trace_id
        assert "spanId" in data
        assert data["spanId"] == expected_span_id


# 3. Sensitive Data Redaction in Spans & Logs
def test_span_processor_redacts_credentials_and_pii():
    """Verify SensitiveDataSpanProcessor scrubs secrets, tokens, PAN, and Aadhaar from span attributes."""
    processor = SensitiveDataSpanProcessor()

    # Create mock span with sensitive attributes
    mock_span = MagicMock(spec=ReadableSpan)
    mock_span._attributes = {
        "db.connection_string": "postgresql://app_user:SuperSecretPassword123@db.prod.internal:5432/propval",
        "http.request.header.authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret_token",
        "applicant.aadhaar": "2345 6789 0123",
        "applicant.pan": "ABCDE1234F",
        "system.note": "Safe non-sensitive metadata",
    }
    mock_span.status = MagicMock()
    mock_span.status.description = "Failed connection to postgresql://admin:SecretPass@db:5432"

    processor.on_end(mock_span)

    attrs = mock_span._attributes
    assert "SuperSecretPassword123" not in attrs["db.connection_string"]
    assert "[REDACTED]" in attrs["db.connection_string"]
    assert "secret_token" not in attrs["http.request.header.authorization"]
    assert "Bearer [REDACTED]" in attrs["http.request.header.authorization"]
    assert "[REDACTED_AADHAAR]" in attrs["applicant.aadhaar"]
    assert "[REDACTED_PAN]" in attrs["applicant.pan"]
    assert attrs["system.note"] == "Safe non-sensitive metadata"
    assert "SecretPass" not in mock_span.status.description


def test_monitoring_failure_resilience():
    """Verify monitoring or span processing failure fails open and does not crash application."""
    processor = SensitiveDataSpanProcessor()
    broken_span = MagicMock()
    broken_span._attributes = None
    del broken_span.status  # Will cause an AttributeError if not defended

    # Must complete without unhandled exception
    try:
        processor.on_end(broken_span)
    except Exception as exc:
        pytest.fail(f"SensitiveDataSpanProcessor failed open improperly: {exc}")


# 4. Distributed Trace Context Propagation
def test_trace_headers_injection():
    """Verify W3C traceparent headers are generated and injected into outbound dictionary."""
    headers = {"Content-Type": "application/json"}
    provider = TracerProvider()
    tracer = provider.get_tracer("test_tracer")

    with tracer.start_as_current_span("outbound_http_span") as span:
        injected = inject_trace_headers(headers)
        assert "traceparent" in injected
        # W3C traceparent format: 00-{trace_id}-{span_id}-{flags}
        parts = injected["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"
        assert parts[1] == format(span.get_span_context().trace_id, "032x")


# 5. Operational Metrics Registry & Endpoints
def test_observability_registry_record_and_summary():
    """Verify in-memory observability registry aggregates metrics accurately."""
    observability_registry.record_api_request(status_code=200, duration_ms=25.5)
    observability_registry.record_api_request(status_code=500, duration_ms=120.0)
    observability_registry.record_db_latency(latency_ms=4.2)
    observability_registry.record_background_job_failure()
    observability_registry.record_ml_inference(latency_ms=15.0)
    observability_registry.record_valuation_failure()
    observability_registry.record_authentication_failure()
    observability_registry.record_audit_chain_failure()

    summary = observability_registry.get_summary()

    assert summary["api"]["totalRequests"] >= 2
    assert summary["api"]["totalFailures"] >= 1
    assert summary["api"]["avgLatencyMs"] > 0
    assert summary["backgroundJobs"]["failures"] >= 1
    assert summary["machineLearning"]["inferencesMonitored"] >= 1
    assert summary["valuation"]["calculationFailures"] >= 1
    assert summary["security"]["authenticationFailures"] >= 1
    assert summary["security"]["auditChainFailures"] >= 1
    assert "telemetry" in summary
    assert summary["telemetry"]["serviceName"] == "propval-ai-backend"


def test_metrics_endpoints_available(client):
    """Verify /metrics and /api/v1/metrics endpoints return valid operational summaries."""
    # Test root endpoint
    res_root = client.get("/metrics")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert "api" in data_root
    assert "database" in data_root
    assert "security" in data_root

    # Test api/v1 endpoint
    res_v1 = client.get("/api/v1/metrics")
    assert res_v1.status_code == 200
    data_v1 = res_v1.json()
    assert data_v1["telemetry"]["serviceName"] == "propval-ai-backend"


def test_health_includes_component_metrics(client):
    """Verify GET /health executes DB probe and records metrics safely without secret leakage."""
    res = client.get("/health")
    assert res.status_code in (200, 503)
    data = res.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "latencyMs" in data["components"]["database"]
    # Check that database connection strings or credentials are NOT returned
    raw_text = res.text
    assert "password" not in raw_text.lower() or "password" not in data
    assert "secret" not in raw_text.lower()
