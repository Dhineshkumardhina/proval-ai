# PropVal AI — Phase 6E: Observability Architecture & Monitoring Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6E — Dependency Harmonization & Observability Remediation  
**Date:** 2026-11-05  
**Author:** Senior Python Backend Engineer, DevSecOps Engineer, and OpenTelemetry Specialist  
**Status:** **OPERATIONAL & VERIFIED**

---

## 1. Observability Architecture Overview

The PropVal AI observability subsystem has been upgraded to a cloud-native, production-grade telemetry pipeline adhering to OpenTelemetry (OTel) standards, W3C Distributed Trace Context specifications, and strict Indian financial regulatory requirements regarding data privacy and credential protection.

```mermaid
flowchart TD
    Client["Client / Upstream HFC Gateway\n(X-Request-ID, traceparent)"]
    FastAPI["FastAPI Application\n(FastAPIInstrumentor)"]
    Middleware["RequestLoggingMiddleware\n(Correlation ID, Latency, Access Log)"]
    SpanProc["SensitiveDataSpanProcessor\n(Redacts PII, Tokens, DB Passwords)"]
    StructuredLog["StructuredJsonFormatter\n(JSON Log with traceId & spanId)"]
    OTLP["OTLPSpanExporter\n(HTTP/Protobuf to OTel Collector / AWS CloudWatch)"]
    SQLAlchemy["SQLAlchemy Engine\n(SQLAlchemyInstrumentor)"]
    HTTPX["HTTPX Client (Gemini, SRO APIs)\n(HTTPXClientInstrumentor)"]
    MetricsReg["ObservabilityRegistry\n(In-Memory Metrics & Probe Collector)"]

    Client --> FastAPI
    FastAPI --> Middleware
    Middleware --> MetricsReg
    FastAPI --> SpanProc
    SpanProc --> OTLP
    FastAPI --> SQLAlchemy
    FastAPI --> HTTPX
    Middleware --> StructuredLog
```

---

## 2. Distributed Tracing & Instrumentation

### 2.1 Trace Provider & Exporters
* **Tracer Provider:** OpenTelemetry `SDKTracerProvider` configured with standard resource attributes:
  * `service.name`: `propval-ai-backend`
  * `service.version`: `0.2.0`
  * `deployment.environment`: `development` / `production`
* **OTLP HTTP Exporter:** `OTLPSpanExporter` configured to export spans via HTTP/JSON or Protobuf to an OpenTelemetry Collector or backend endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT`, default `http://localhost:4318/v1/traces`).
* **Conditional Activation:** In development, traces can be inspected locally or collected in memory; in production, `OTEL_ENABLED=true` activates background batch exporting via `BatchSpanProcessor`.

### 2.2 Framework & Client Instrumentations
1. **FastAPI Instrumentation (`FastAPIInstrumentor`):**
   * Automatically intercepts incoming HTTP requests, creates root server spans, records HTTP route templates (`/api/v1/cases/{case_id}`), HTTP method, and response status codes.
   * Probes (`/health`, `/health/live`, `/health/ready`) are excluded from tracing to prevent spamming APM quotas.
2. **Database Instrumentation (`SQLAlchemyInstrumentor`):**
   * Automatically creates child spans for every SQL query executed across PostgreSQL and SQLite.
   * Records statement types, execution durations, and database error states.
   * Uses `skip_dep_check=True` to guarantee flawless execution on SQLAlchemy 2.1.3.
3. **HTTP Client Instrumentation (`HTTPXClientInstrumentor`):**
   * Instruments outbound HTTP requests (e.g. Gemini AI underwriter probes, SRO registry lookups, external geocoders).
   * Automatically injects W3C `traceparent` and `tracestate` headers into outbound requests for end-to-end distributed trace continuity.

---

## 3. Correlation IDs & Structured Logging

### 3.1 Trace & Log Correlation
A core requirement for enterprise financial observability is linking application log events directly with distributed traces.

In [`backend/app/core/logging.py`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/app/core/logging.py), the `StructuredJsonFormatter` inspects the active OpenTelemetry span context:
```python
# OpenTelemetry distributed trace correlation (Phase 6E)
try:
    from opentelemetry import trace
    span = trace.get_current_span()
    if span and span.is_recording():
        span_ctx = span.get_span_context()
        if span_ctx.is_valid:
            log_payload["traceId"] = format(span_ctx.trace_id, "032x")
            log_payload["spanId"] = format(span_ctx.span_id, "016x")
except Exception:
    pass
```

### 3.2 Output Log Schema
Every JSON log emitted in production includes:
```json
{
  "timestamp": "2026-11-05T18:17:50.123456+00:00",
  "level": "INFO",
  "logger": "propval.access",
  "message": "HTTP POST /api/v1/valuation/calculate 200 (14.2ms)",
  "requestId": "req-9a8b7c6d5e4f",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "spanId": "00f067aa0ba902b7",
  "clientIp": "192.168.1.10",
  "method": "POST",
  "path": "/api/v1/valuation/calculate",
  "status_code": 200,
  "duration_ms": 14.2
}
```

---

## 4. Financial-Grade Sensitive Data Redaction & Failure Safety

### 4.1 Sensitive Data Span Processor
To prevent sensitive financial data, Personally Identifiable Information (PII), and internal database passwords from being transmitted to third-party APM vendors (Datadog, AWS CloudWatch, Grafana Cloud), a custom `SensitiveDataSpanProcessor` (`backend/app/core/telemetry.py`) inspects and sanitizes all span attributes and status descriptions on completion:
* **Database Connection Strings:** `postgresql://app_user:[REDACTED]@db.prod.internal:5432/propval`
* **Authorization Headers:** `Bearer [REDACTED]`
* **Indian Identity PII:** Aadhaar numbers (`[REDACTED_AADHAAR]`) and PAN cards (`[REDACTED_PAN]`)
* **Applicant Contact Data:** Emails (`[REDACTED_EMAIL]`) and Indian mobile phone numbers (`[REDACTED_PHONE]`)

### 4.2 Fail-Safe Resilience
* Monitoring and telemetry exceptions are isolated within `try...except` boundaries.
* If the OTLP remote collector is unavailable, timeout-bound, or returns HTTP 5xx errors, the application **fails open safely**: user requests continue to be served with zero disruption, and the incident is logged without exposing secret credentials.

---

## 5. Observability Requirements & Metric Registry

The in-memory `ObservabilityRegistry` tracks the 10 mandated operational metrics in real time:

| Monitored Dimension | Collection Mechanism | Monitored Metric Fields |
|:---|:---|:---|
| **API Latency** | `RequestLoggingMiddleware` | `avgLatencyMs`, `p95LatencyMs` |
| **Request Failures** | `RequestLoggingMiddleware` | `totalRequests`, `totalFailures` |
| **Database Latency** | `check_db_connectivity` probe | `avgLatencyMs` (real execution of `SELECT 1`) |
| **Database Connection Pool** | SQLAlchemy Engine Pool inspection | `poolSize`, `poolCheckedIn`, `poolCheckedOut` |
| **Background Job Failures** | Ingestion pipeline counters | `backgroundJobs.failures` |
| **Data Ingestion Status** | DB deed status aggregation | `countsByState` (`RAW`, `STAGED`, `CERTIFIED`, `REJECTED`, `QUARANTINED`) |
| **ML Inference Latency** | `MLModelService` inference timer | `inferencesMonitored`, `avgInferenceLatencyMs` |
| **Valuation Calculation Failures** | Valuation engine failure handler | `valuation.calculationFailures` |
| **Authentication Failures** | Security event logger | `security.authenticationFailures` |
| **Audit-Chain Failures** | Tamper-evident ledger verifier | `security.auditChainFailures` |

### 5.1 Operational Endpoints
1. `GET /metrics`: Root monitoring endpoint for Prometheus / AWS CloudWatch agent scrapers.
2. `GET /api/v1/metrics`: API v1 operational metrics endpoint.
3. `GET /health`: Deep diagnostic probe combining component health, DB latency, and audit-chain integrity.
4. `GET /health/live`: Lightweight liveness probe for Kubernetes container orchestrators.
5. `GET /health/ready`: Dependency readiness probe for load balancers.

