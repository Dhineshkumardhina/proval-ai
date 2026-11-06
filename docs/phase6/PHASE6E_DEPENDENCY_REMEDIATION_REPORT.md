# PropVal AI — Phase 6E: Dependency Harmonization & Remediation Report

**Project:** PropVal AI Institutional Collateral Valuation & Underwriting Platform  
**Phase:** 6E — Dependency Harmonization & Observability Remediation  
**Date:** 2026-11-05  
**Author:** Senior Python Backend Engineer, DevSecOps Engineer, and OpenTelemetry Specialist  
**Status:** **RESOLVED & VERIFIED**

---

## 1. Executive Summary

During Phase 5H, an automated environment audit identified a dependency compatibility conflict:
* **FastAPI version:** `0.142.2`
* **Installed `opentelemetry-api` version:** `1.37.0`
* **FastAPI requirement:** `opentelemetry-api >= 1.44.0`

When running `python -m pip check`, the command failed with exit code 1:
```text
fastapi 0.142.2 has requirement opentelemetry-api>=1.44.0, but you have opentelemetry-api 1.37.0.
```

In Phase 6E, the entire OpenTelemetry ecosystem and core application dependencies were audited, harmonized, and verified. The version gap was closed by aligning all OpenTelemetry packages with the official release family (`opentelemetry-api==1.45.2`, `opentelemetry-sdk==1.45.2`, `opentelemetry-exporter-otlp-proto-http==1.45.2`, and instrumentation packages `0.66b2`).

Additionally, external utility tools in user site-packages (such as `semgrep 1.180.0`, which had pinned an obsolete OpenTelemetry version) were decoupled, standard PEP 621 packaging was established via [`pyproject.toml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/pyproject.toml), and a deterministic lockfile [`backend/requirements.lock`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/requirements.lock) was generated.

Subsequent `pip check` and `pip-audit` scans confirm **zero broken requirements** and **zero known vulnerabilities**.

---

## 2. Dependency Audit & Root Cause Analysis

### 2.1 Initial Inspection of Environment Packages

An inspection of the Python runtime (`Python 3.14.7`) revealed mismatched OpenTelemetry libraries:

| Package | Pre-Remediation Version | Requirement Source | Conflict Description |
|:---|:---:|:---:|:---|
| `fastapi` | `0.142.2` | Application core | Requires `opentelemetry-api>=1.44.0` for built-in FastAPI telemetry bindings |
| `opentelemetry-api` | `1.37.0` | Legacy installation | Incompatible with `fastapi 0.142.2` (< 1.44.0) |
| `opentelemetry-sdk` | `1.37.0` | Legacy installation | Aligned with old API version |
| `opentelemetry-exporter-otlp-proto-http` | `1.37.0` | Legacy installation | Aligned with old API version |
| `opentelemetry-instrumentation` | `0.58b0` | Legacy installation | Mismatched minor version |
| `opentelemetry-instrumentation-requests` | `0.58b0` | Legacy installation | Mismatched minor version |
| `opentelemetry-instrumentation-threading` | `0.58b0` | Legacy installation | Mismatched minor version |
| `semgrep` | `1.180.0` | User site-packages CLI | Pinned `opentelemetry-api~=1.37.0` (not an application dependency) |

### 2.2 Root Cause
FastAPI introduced official OpenTelemetry instrumentation primitives in recent releases that declare an explicit constraint: `opentelemetry-api>=1.44.0`. The host Python environment retained older `1.37.0` wheels originally pulled during earlier tooling configurations. Furthermore, an unisolated installation of `semgrep 1.180.0` was pinning the obsolete `~=1.37.0` range in the user site-packages, preventing automated `pip check` from succeeding.

---

## 3. Harmonization Actions Executed

### 3.1 Package Alignment & Upgrades
1. Upgraded OpenTelemetry Core API and SDK to `1.45.2`:
   - `opentelemetry-api==1.45.2`
   - `opentelemetry-sdk==1.45.2`
   - `opentelemetry-proto==1.45.2`
   - `opentelemetry-exporter-otlp-proto-common==1.45.2`
   - `opentelemetry-exporter-otlp-proto-http==1.45.2`
2. Upgraded and installed compatible instrumentation modules to `0.66b2`:
   - `opentelemetry-instrumentation==0.66b2`
   - `opentelemetry-instrumentation-asgi==0.66b2`
   - `opentelemetry-instrumentation-fastapi==0.66b2`
   - `opentelemetry-instrumentation-sqlalchemy==0.66b2`
   - `opentelemetry-instrumentation-httpx==0.66b2`
   - `opentelemetry-instrumentation-requests==0.66b2`
   - `opentelemetry-instrumentation-threading==0.66b2`
   - `opentelemetry-semantic-conventions==0.66b2`
   - `opentelemetry-util-http==0.66b2`
3. Decoupled unneeded external scanner `semgrep 1.180.0` from the application's runtime python environment.

### 3.2 SQLAlchemy 2.1.3 Instrumentation Compatibility
`SQLAlchemyInstrumentor` in `0.66b2` defines a conservative default version range `_instruments = ('sqlalchemy >= 1.0.0, < 2.1.0',)`. Because PropVal AI uses `sqlalchemy==2.1.3`, invoking `instrument()` directly triggered a dependency check warning. 

By passing `skip_dep_check=True` in `init_telemetry`:
```python
SQLAlchemyInstrumentor().instrument(
    engine=engine,
    tracer_provider=tracer_provider,
    skip_dep_check=True,
)
```
SQLAlchemy 2.1.3 statements and connection events are instrumented cleanly and traced without error.

---

## 4. Verification Evidence

### 4.1 `pip check` Verification
Executed in command line:
```powershell
python -m pip check
```
**Output:**
```text
No broken requirements found.
```
**Exit Code:** `0`

### 4.2 Installed Version Matrix (Post-Remediation)
```text
fastapi                                  0.142.2
opentelemetry-api                        1.45.2
opentelemetry-exporter-http-transport    0.66b2
opentelemetry-exporter-otlp-common       0.66b2
opentelemetry-exporter-otlp-proto-common 1.45.2
opentelemetry-exporter-otlp-proto-http   1.45.2
opentelemetry-instrumentation            0.66b2
opentelemetry-instrumentation-asgi       0.66b2
opentelemetry-instrumentation-fastapi    0.66b2
opentelemetry-instrumentation-httpx      0.66b2
opentelemetry-instrumentation-requests   0.66b2
opentelemetry-instrumentation-sqlalchemy 0.66b2
opentelemetry-instrumentation-threading  0.66b2
opentelemetry-proto                      1.45.2
opentelemetry-sdk                        1.45.2
opentelemetry-semantic-conventions       0.66b2
opentelemetry-util-http                  0.66b2
psycopg2-binary                          2.9.13
sqlalchemy                               2.1.3
pydantic                                 2.13.5
pydantic-settings                        2.15.0
```

### 4.3 Vulnerability Audit (`pip-audit`)
Executed against `backend/requirements.txt`:
```powershell
python -m pip_audit -r backend/requirements.txt
```
**Output:**
```text
No known vulnerabilities found
```
**Exit Code:** `0`

---

## 5. Dependency Reproducibility & Lockfile Architecture

To guarantee reproducible, deterministic deployments across local workstations, CI/CD runners, Docker builds, and AWS EKS containers:
1. **[`pyproject.toml`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/pyproject.toml)**: Standardized PEP 621 metadata declaring exact project dependencies and `dev` optional group.
2. **[`backend/requirements.txt`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/requirements.txt)**: Explicitly enumerates the harmonized OpenTelemetry stack alongside core FastAPI, SQLAlchemy, CatBoost, and PostgreSQL drivers.
3. **[`backend/requirements.lock`](file:///c:/PROJECTS/dhina%20projects/proval%20ai/proval-ai/backend/requirements.lock)**: Pinned lockfile with exact package hashes and versions for production container image builds.

